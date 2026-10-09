import re
from collections import Counter
from collections.abc import Iterable
from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from sqlalchemy import Select, false, func, or_, select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.context import RequestContext
from app.core.exceptions import BusinessRuleError, ConflictError, PermissionDeniedError
from app.core.security import hash_password
from app.models import Employee, LeaveBalance, LeaveRequest, LeaveStatus, LeaveType, User
from app.permissions.policy import (
    ACTION_TEXT,
    ROLE_NAMES,
    Capability,
    Scope,
    Subject,
    authorize,
    can_view_salary,
    scope_for,
)
from app.schemas.hr import (
    CreateEmployeeRequest,
    EmployeeDetail,
    EmployeeStatus,
    EmployeeSummary,
    UpdateEmployeeRequest,
)
from app.services import audit_service, auth_service, leave_rules
from app.services.audit_service import Outcome

NOT_VISIBLE = "You don't have access to that record, or it doesn't exist."
EMAIL_TAKEN = "An account with this email address already exists."

_CODE = re.compile(r"^([A-Z]+)-(\d+)$")
# Reporting chains are shallow; this only bounds the loop if the data is ever corrupt.
_MAX_CHAIN_DEPTH = 50


def to_subject(employee: Employee) -> Subject:
    return Subject(
        employee_id=employee.id,
        tenant_id=employee.tenant_id,
        company_id=employee.company_id,
        manager_id=employee.manager_id,
    )


async def load_subject(session: AsyncSession, employee_id: UUID) -> Employee:
    """Load an employee through RLS.

    A record in another tenant is indistinguishable from a missing one, and both are reported
    as a permission denial. Callers can't use this endpoint to learn which IDs exist.
    """
    employee = await session.get(Employee, employee_id)
    if employee is None:
        raise PermissionDeniedError(NOT_VISIBLE)
    return employee


async def resolve_target(
    session: AsyncSession, ctx: RequestContext, capability: Capability, employee_id: UUID | None
) -> Employee:
    """Resolve an optional employee_id (default: the caller) and enforce the policy on it."""
    target_id = employee_id or ctx.employee_id
    if target_id is None:
        raise PermissionDeniedError("This account is not linked to an employee record.")
    employee = await load_subject(session, target_id)
    authorize(ctx, capability, to_subject(employee)).enforce()
    return employee


def scoped_employees(
    ctx: RequestContext, capability: Capability, *, active: bool = True
) -> Select[Employee]:
    """A SELECT restricted to the employees `ctx` may see for `capability`."""
    scope = scope_for(ctx, capability)
    stmt = select(Employee).where(Employee.is_active.is_(active))
    if scope is Scope.NONE or (ctx.employee_id is None and scope < Scope.COMPANY):
        return stmt.where(false())
    if scope is Scope.OWN:
        return stmt.where(Employee.id == ctx.employee_id)
    if scope is Scope.TEAM:
        return stmt.where(
            or_(Employee.id == ctx.employee_id, Employee.manager_id == ctx.employee_id)
        )
    return stmt.where(Employee.company_id == ctx.company_id)


async def list_employees(
    session: AsyncSession,
    ctx: RequestContext,
    search: str | None = None,
    status: EmployeeStatus = "active",
) -> list[EmployeeSummary]:
    stmt = scoped_employees(ctx, Capability.VIEW_PROFILE, active=status == "active")
    if search:
        stmt = stmt.where(Employee.full_name.ilike(f"%{search}%"))
    rows = (await session.scalars(stmt.order_by(Employee.full_name))).all()
    return [EmployeeSummary.model_validate(e) for e in rows]


async def get_employee(
    session: AsyncSession, ctx: RequestContext, employee_id: UUID | None
) -> EmployeeDetail:
    employee = await resolve_target(session, ctx, Capability.VIEW_PROFILE, employee_id)
    manager = aliased(Employee)
    manager_name = None
    if employee.manager_id:
        manager_name = await session.scalar(
            select(manager.full_name).where(manager.id == employee.manager_id)
        )
    role = await session.scalar(select(User.role).where(User.employee_id == employee.id))
    show_salary = can_view_salary(ctx, to_subject(employee))
    return EmployeeDetail(
        id=employee.id,
        employee_code=employee.employee_code,
        full_name=employee.full_name,
        email=employee.email,
        department=employee.department,
        job_title=employee.job_title,
        is_active=employee.is_active,
        manager_id=employee.manager_id,
        manager_name=manager_name,
        join_date=employee.join_date,
        role=role,
        salary=employee.salary if show_salary else None,
        salary_masked=not show_salary,
    )


# --- HR administration ---------------------------------------------------------------------


def _require_hr(ctx: RequestContext) -> None:
    if (
        scope_for(ctx, Capability.MANAGE_EMPLOYEES) < Scope.COMPANY
        or ctx.tenant_id is None
        or ctx.company_id is None
    ):
        raise PermissionDeniedError(
            f"{ROLE_NAMES[ctx.role]} can't {ACTION_TEXT[Capability.MANAGE_EMPLOYEES]}."
        )


async def _load_for_change(
    session: AsyncSession, ctx: RequestContext, employee_id: UUID
) -> tuple[Employee, User]:
    """Lock the employee and their login, then enforce MANAGE_EMPLOYEES (incl. not-self)."""
    _require_hr(ctx)
    employee = await session.scalar(
        select(Employee).where(Employee.id == employee_id).with_for_update()
    )
    if employee is None:
        raise PermissionDeniedError(NOT_VISIBLE)
    authorize(ctx, Capability.MANAGE_EMPLOYEES, to_subject(employee)).enforce()
    user = await session.scalar(
        select(User).where(User.employee_id == employee.id).with_for_update()
    )
    if user is None:
        raise BusinessRuleError("This employee has no login account.")
    return employee, user


async def _validate_manager(
    session: AsyncSession, ctx: RequestContext, manager_id: UUID, employee_id: UUID | None
) -> None:
    """The manager must be visible, active, and not create a loop in the reporting line."""
    if manager_id == employee_id:
        raise BusinessRuleError("An employee cannot report to themselves.")
    # Same-company check comes from the policy engine; other tenants are invisible via RLS.
    manager = await resolve_target(session, ctx, Capability.VIEW_PROFILE, manager_id)
    if not manager.is_active:
        raise BusinessRuleError("The selected manager is no longer active.")
    if employee_id is None:
        return
    cursor = manager.manager_id
    for _ in range(_MAX_CHAIN_DEPTH):
        if cursor is None:
            return
        if cursor == employee_id:
            raise BusinessRuleError(
                f"{manager.full_name} already reports to this employee, directly or indirectly."
            )
        cursor = await session.scalar(select(Employee.manager_id).where(Employee.id == cursor))
    raise BusinessRuleError("The reporting line is too deep to verify.")


async def _active_report_count(session: AsyncSession, employee_id: UUID) -> int:
    return (
        await session.scalar(
            select(func.count()).where(
                Employee.manager_id == employee_id, Employee.is_active.is_(True)
            )
        )
    ) or 0


def next_employee_code(existing: Iterable[str]) -> str:
    """Next code in the company's own series, e.g. ACM-1025 -> ACM-1026."""
    parsed = [(m[1], int(m[2])) for code in existing if (m := _CODE.match(code))]
    if not parsed:
        return "EMP-1001"
    prefix = Counter(p for p, _ in parsed).most_common(1)[0][0]
    return f"{prefix}-{max(n for p, n in parsed if p == prefix) + 1}"


async def _email_in_use(session: AsyncSession, email: str) -> bool:
    # Login emails are unique across tenants. app_auth_lookup (SECURITY DEFINER) can see past
    # RLS, which is unavoidable here: the alternative is a raw unique-violation on insert.
    return bool(
        await session.scalar(
            text("SELECT EXISTS (SELECT 1 FROM app_auth_lookup(:email))"), {"email": email}
        )
        or await session.scalar(select(func.count()).where(func.lower(Employee.email) == email))
    )


async def create_employee(
    session: AsyncSession, ctx: RequestContext, payload: CreateEmployeeRequest
) -> EmployeeDetail:
    """Onboard an employee: HR record, login account and this year's leave balances, atomically."""
    _require_hr(ctx)
    assert ctx.tenant_id is not None and ctx.company_id is not None  # noqa: S101 (narrowing)

    if payload.manager_id is not None:
        await _validate_manager(session, ctx, payload.manager_id, None)

    today = date.today()
    if payload.join_date > today + timedelta(days=365):
        raise BusinessRuleError("The joining date cannot be more than a year ahead.")
    if await _email_in_use(session, payload.email):
        raise ConflictError(EMAIL_TAKEN)

    # Serialise code allocation per company so two concurrent hires never share a code.
    await session.execute(
        text("SELECT pg_advisory_xact_lock(hashtext(:key))"),
        {"key": f"employee_code:{ctx.company_id}"},
    )
    codes = await session.scalars(
        select(Employee.employee_code).where(Employee.company_id == ctx.company_id)
    )

    employee = Employee(
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        employee_code=next_employee_code(codes.all()),
        full_name=payload.full_name,
        email=payload.email,
        department=payload.department,
        job_title=payload.job_title,
        manager_id=payload.manager_id,
        join_date=payload.join_date,
        salary=payload.salary,
        national_id=payload.national_id,
    )
    session.add(employee)
    await session.flush()

    session.add(
        User(
            tenant_id=ctx.tenant_id,
            company_id=ctx.company_id,
            employee_id=employee.id,
            email=payload.email,
            password_hash=hash_password(payload.password),
            role=payload.role.value,
        )
    )
    year = max(today.year, payload.join_date.year)
    for leave_type in (await session.scalars(select(LeaveType))).all():
        session.add(
            LeaveBalance(
                tenant_id=ctx.tenant_id,
                employee_id=employee.id,
                leave_type_id=leave_type.id,
                year=year,
                allocated=leave_rules.prorated_quota(
                    leave_type.annual_quota, payload.join_date, year
                ),
            )
        )
    try:
        await session.flush()
    except IntegrityError as exc:
        # Lost a race with another signup using the same email.
        raise ConflictError(EMAIL_TAKEN) from exc

    await audit_service.record(
        session,
        ctx,
        event="employee.create",
        tool="create_employee",
        outcome=Outcome.SUCCESS,
        # Salary and national_id are masked by the audit redactor; the password never leaves.
        args=payload.model_dump(mode="json", exclude={"password"})
        | {"employee_id": str(employee.id), "employee_code": employee.employee_code},
    )
    return await get_employee(session, ctx, employee.id)


async def update_employee(
    session: AsyncSession, ctx: RequestContext, employee_id: UUID, payload: UpdateEmployeeRequest
) -> EmployeeDetail:
    employee, user = await _load_for_change(session, ctx, employee_id)
    if not employee.is_active:
        raise BusinessRuleError("Reactivate this employee before editing their record.")

    changes = payload.changes()
    if payload.manager_id is not None:
        await _validate_manager(session, ctx, payload.manager_id, employee.id)

    for field in ("full_name", "department", "job_title", "manager_id", "salary"):
        if field in changes:
            setattr(employee, field, changes[field])
    if payload.role is not None:
        # Takes effect immediately: the user's current session is rejected and they sign in
        # again with the new role (see auth_service.ensure_session_current).
        user.role = payload.role.value
    await session.flush()

    await audit_service.record(
        session,
        ctx,
        event="employee.update",
        tool="update_employee",
        outcome=Outcome.SUCCESS,
        args=payload.model_dump(mode="json", include=set(changes))
        | {"employee_id": str(employee.id)},
    )
    return await get_employee(session, ctx, employee.id)


async def deactivate_employee(
    session: AsyncSession, ctx: RequestContext, employee_id: UUID
) -> EmployeeDetail:
    """Offboard: block sign-in and cancel pending leave. History is kept, nothing is deleted."""
    employee, user = await _load_for_change(session, ctx, employee_id)
    if not employee.is_active:
        raise BusinessRuleError("This employee is already inactive.")
    reports = await _active_report_count(session, employee.id)
    if reports:
        raise BusinessRuleError(
            f"{employee.full_name} still manages {reports} active employee"
            f"{'' if reports == 1 else 's'}. Assign them a new manager first."
        )

    cancelled = await session.scalars(
        update(LeaveRequest)
        .where(
            LeaveRequest.employee_id == employee.id,
            LeaveRequest.status == LeaveStatus.PENDING,
        )
        .values(
            status=LeaveStatus.CANCELLED,
            decided_at=datetime.now(UTC),
            decision_comment="Cancelled automatically: employee deactivated.",
        )
        .returning(LeaveRequest.id)
    )
    cancelled_ids = cancelled.all()
    employee.is_active = False
    user.is_active = False
    await session.flush()

    await audit_service.record(
        session,
        ctx,
        event="employee.deactivate",
        tool="deactivate_employee",
        outcome=Outcome.SUCCESS,
        args={"employee_id": str(employee.id), "cancelled_leave_requests": len(cancelled_ids)},
    )
    return await get_employee(session, ctx, employee.id)


async def reset_password(
    session: AsyncSession, ctx: RequestContext, employee_id: UUID, new_password: str
) -> None:
    """HR sets a temporary password; every session the employee has is signed out.

    Self-excluded like the other MANAGE_EMPLOYEES actions: HR changes their own password
    through /auth/password, which requires the current one.
    """
    employee, user = await _load_for_change(session, ctx, employee_id)
    if not employee.is_active:
        raise BusinessRuleError("Reactivate this employee before resetting their password.")
    auth_service.set_password(user, new_password)
    await session.flush()
    await audit_service.record(
        session,
        ctx,
        event="employee.password_reset",
        tool="reset_password",
        outcome=Outcome.SUCCESS,
        args={"employee_id": str(employee.id)},
    )


async def reactivate_employee(
    session: AsyncSession, ctx: RequestContext, employee_id: UUID
) -> EmployeeDetail:
    employee, user = await _load_for_change(session, ctx, employee_id)
    if employee.is_active:
        raise BusinessRuleError("This employee is already active.")

    # Their old manager may have left meanwhile; HR assigns a new one afterwards.
    cleared_manager = False
    if employee.manager_id is not None:
        manager_active = await session.scalar(
            select(Employee.is_active).where(Employee.id == employee.manager_id)
        )
        if not manager_active:
            employee.manager_id = None
            cleared_manager = True
    employee.is_active = True
    user.is_active = True
    await session.flush()

    await audit_service.record(
        session,
        ctx,
        event="employee.reactivate",
        tool="reactivate_employee",
        outcome=Outcome.SUCCESS,
        args={"employee_id": str(employee.id), "cleared_inactive_manager": cleared_manager},
    )
    return await get_employee(session, ctx, employee.id)
