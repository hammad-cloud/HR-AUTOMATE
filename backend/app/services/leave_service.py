from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import RequestContext, Role
from app.core.exceptions import BusinessRuleError, NotFoundError, PermissionDeniedError
from app.models import Employee, LeaveBalance, LeaveRequest, LeaveStatus, LeaveType
from app.permissions.policy import Capability, Scope, authorize, scope_for
from app.schemas.hr import (
    ApplyLeaveRequest,
    LeaveBalanceOut,
    LeaveRequestOut,
    LeaveScope,
    LeaveTypeOut,
)
from app.services import audit_service, leave_rules
from app.services.audit_service import Outcome
from app.services.employee_service import resolve_target, to_subject

_ACTIVE = (LeaveStatus.PENDING, LeaveStatus.APPROVED)


def _to_out(req: LeaveRequest) -> LeaveRequestOut:
    return LeaveRequestOut(
        id=req.id,
        employee_id=req.employee_id,
        employee_name=req.employee.full_name,
        leave_type=LeaveTypeOut.model_validate(req.leave_type),
        start_date=req.start_date,
        end_date=req.end_date,
        days=req.days,
        reason=req.reason,
        status=req.status,
        approver_id=req.approver_id,
        decided_at=req.decided_at,
        decision_comment=req.decision_comment,
        created_at=req.created_at,
    )


async def list_types(session: AsyncSession) -> list[LeaveTypeOut]:
    rows = (await session.scalars(select(LeaveType).order_by(LeaveType.name))).all()
    return [LeaveTypeOut.model_validate(t) for t in rows]


async def _pending_days(
    session: AsyncSession, employee_id: UUID, leave_type_id: UUID, year: int
) -> Decimal:
    total = await session.scalar(
        select(func.coalesce(func.sum(LeaveRequest.days), 0)).where(
            LeaveRequest.employee_id == employee_id,
            LeaveRequest.leave_type_id == leave_type_id,
            LeaveRequest.status == LeaveStatus.PENDING,
            func.extract("year", LeaveRequest.start_date) == year,
        )
    )
    return Decimal(total or 0)


async def get_balances(
    session: AsyncSession, ctx: RequestContext, employee_id: UUID | None, year: int | None = None
) -> list[LeaveBalanceOut]:
    employee = await resolve_target(session, ctx, Capability.VIEW_LEAVE_BALANCE, employee_id)
    year = year or date.today().year
    balances = (
        await session.scalars(
            select(LeaveBalance).where(
                LeaveBalance.employee_id == employee.id, LeaveBalance.year == year
            )
        )
    ).all()
    result = []
    for b in sorted(balances, key=lambda b: b.leave_type.name):
        pending = await _pending_days(session, employee.id, b.leave_type_id, year)
        result.append(
            LeaveBalanceOut(
                leave_type=LeaveTypeOut.model_validate(b.leave_type),
                year=year,
                allocated=b.allocated,
                used=b.used,
                pending=pending,
                remaining=b.remaining,
            )
        )
    return result


async def list_requests(
    session: AsyncSession,
    ctx: RequestContext,
    scope: LeaveScope,
    status: LeaveStatus | None = None,
    employee_id: UUID | None = None,
) -> list[LeaveRequestOut]:
    stmt = select(LeaveRequest).join(Employee, Employee.id == LeaveRequest.employee_id)
    granted = scope_for(ctx, Capability.VIEW_LEAVE_BALANCE)

    if scope == "mine":
        if ctx.employee_id is None:
            return []
        stmt = stmt.where(LeaveRequest.employee_id == ctx.employee_id)
    elif scope == "team":
        if granted < Scope.TEAM or ctx.employee_id is None:
            raise PermissionDeniedError("Only managers can view team leave requests.")
        stmt = stmt.where(Employee.manager_id == ctx.employee_id)
    else:
        if granted < Scope.COMPANY:
            raise PermissionDeniedError("Only HR admins can view company-wide leave requests.")
        stmt = stmt.where(Employee.company_id == ctx.company_id)

    if status:
        stmt = stmt.where(LeaveRequest.status == status)
    # Narrows within the scope above; it can never widen it.
    if employee_id:
        stmt = stmt.where(LeaveRequest.employee_id == employee_id)
    rows = (await session.scalars(stmt.order_by(LeaveRequest.created_at.desc()))).unique().all()
    return [_to_out(r) for r in rows]


async def list_pending_approvals(
    session: AsyncSession, ctx: RequestContext
) -> list[LeaveRequestOut]:
    """Requests the caller can act on: team (manager) or company (HR), never their own."""
    scope = scope_for(ctx, Capability.DECIDE_LEAVE)
    if scope is Scope.NONE:
        return []
    stmt = (
        select(LeaveRequest)
        .join(Employee, Employee.id == LeaveRequest.employee_id)
        .where(LeaveRequest.status == LeaveStatus.PENDING)
    )
    if ctx.employee_id is not None:
        stmt = stmt.where(LeaveRequest.employee_id != ctx.employee_id)
    if scope is Scope.TEAM:
        stmt = stmt.where(Employee.manager_id == ctx.employee_id)
    else:
        stmt = stmt.where(Employee.company_id == ctx.company_id)
    rows = (await session.scalars(stmt.order_by(LeaveRequest.start_date))).unique().all()
    return [_to_out(r) for r in rows]


async def _get_balance_for_update(
    session: AsyncSession, employee_id: UUID, leave_type_id: UUID, year: int
) -> LeaveBalance:
    balance = await session.scalar(
        select(LeaveBalance)
        .where(
            LeaveBalance.employee_id == employee_id,
            LeaveBalance.leave_type_id == leave_type_id,
            LeaveBalance.year == year,
        )
        .with_for_update(of=LeaveBalance)
    )
    if balance is None:
        raise BusinessRuleError(f"No leave allocation exists for {year}.")
    return balance


async def apply(
    session: AsyncSession,
    ctx: RequestContext,
    payload: ApplyLeaveRequest,
    idempotency_key: str | None = None,
) -> LeaveRequestOut:
    employee = await resolve_target(session, ctx, Capability.APPLY_LEAVE, None)

    if idempotency_key:
        existing = await session.scalar(
            select(LeaveRequest).where(LeaveRequest.idempotency_key == idempotency_key)
        )
        if existing is not None:
            if existing.employee_id != employee.id:
                raise PermissionDeniedError("Idempotency key already used by another request.")
            return _to_out(existing)

    leave_type = await session.scalar(
        select(LeaveType).where(LeaveType.code == payload.leave_type_code.upper())
    )
    if leave_type is None:
        raise NotFoundError(f"Unknown leave type '{payload.leave_type_code}'.")
    if payload.start_date.year != payload.end_date.year:
        raise BusinessRuleError("A leave request cannot span two calendar years.")

    days = leave_rules.ensure_requestable(payload.start_date, payload.end_date, date.today())

    overlap = await session.scalar(
        select(func.count()).where(
            LeaveRequest.employee_id == employee.id,
            LeaveRequest.status.in_(_ACTIVE),
            and_(
                LeaveRequest.start_date <= payload.end_date,
                LeaveRequest.end_date >= payload.start_date,
            ),
        )
    )
    if overlap:
        raise BusinessRuleError("These dates overlap an existing pending or approved request.")

    year = payload.start_date.year
    balance = await _get_balance_for_update(session, employee.id, leave_type.id, year)
    pending = await _pending_days(session, employee.id, leave_type.id, year)
    leave_rules.ensure_sufficient_balance(
        days, balance.allocated, balance.used, pending, leave_type.name
    )

    request = LeaveRequest(
        tenant_id=employee.tenant_id,
        employee_id=employee.id,
        leave_type_id=leave_type.id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        days=days,
        reason=payload.reason,
        status=LeaveStatus.PENDING,
        idempotency_key=idempotency_key,
    )
    session.add(request)
    await session.flush()
    await session.refresh(request, ["leave_type", "employee", "created_at"])
    await audit_service.record(
        session,
        ctx,
        event="leave.apply",
        tool="apply_leave",
        outcome=Outcome.SUCCESS,
        args=payload.model_dump(mode="json") | {"request_id": str(request.id)},
    )
    return _to_out(request)


async def _load_request_for_update(session: AsyncSession, request_id: UUID) -> LeaveRequest:
    request = await session.scalar(
        select(LeaveRequest).where(LeaveRequest.id == request_id).with_for_update(of=LeaveRequest)
    )
    if request is None:
        raise PermissionDeniedError("You don't have access to that request, or it doesn't exist.")
    return request


async def decide(
    session: AsyncSession,
    ctx: RequestContext,
    request_id: UUID,
    *,
    approve: bool,
    comment: str | None,
) -> LeaveRequestOut:
    request = await _load_request_for_update(session, request_id)
    # Policy covers scope and self-approval (PR-6), re-checked at execution time (FR-41).
    authorize(ctx, Capability.DECIDE_LEAVE, to_subject(request.employee)).enforce()

    if request.status != LeaveStatus.PENDING:
        raise BusinessRuleError(f"This request is already {request.status.lower()}.")

    if approve:
        balance = await _get_balance_for_update(
            session, request.employee_id, request.leave_type_id, request.start_date.year
        )
        if request.days > balance.remaining:
            raise BusinessRuleError("The employee no longer has enough balance for this request.")
        balance.used += request.days
    elif not comment:
        raise BusinessRuleError("A reason is required when rejecting a request.")

    request.status = LeaveStatus.APPROVED if approve else LeaveStatus.REJECTED
    request.approver_id = ctx.employee_id
    request.decided_at = datetime.now(UTC)
    request.decision_comment = comment
    await session.flush()
    await audit_service.record(
        session,
        ctx,
        event="leave.approve" if approve else "leave.reject",
        tool="approve_leave" if approve else "reject_leave",
        outcome=Outcome.SUCCESS,
        args={"request_id": str(request_id), "comment": comment},
    )
    return _to_out(request)


async def cancel(session: AsyncSession, ctx: RequestContext, request_id: UUID) -> LeaveRequestOut:
    request = await _load_request_for_update(session, request_id)
    authorize(ctx, Capability.CANCEL_LEAVE, to_subject(request.employee)).enforce()

    if request.status not in _ACTIVE:
        raise BusinessRuleError(f"This request is already {request.status.lower()}.")
    # BRD 4.1: employees may cancel only their pending requests.
    if ctx.role is Role.EMPLOYEE and request.status != LeaveStatus.PENDING:
        raise BusinessRuleError("Approved leave can only be cancelled by your manager or HR.")

    if request.status == LeaveStatus.APPROVED:
        balance = await _get_balance_for_update(
            session, request.employee_id, request.leave_type_id, request.start_date.year
        )
        balance.used -= request.days

    request.status = LeaveStatus.CANCELLED
    await session.flush()
    await audit_service.record(
        session,
        ctx,
        event="leave.cancel",
        tool="cancel_leave",
        outcome=Outcome.SUCCESS,
        args={"request_id": str(request_id)},
    )
    return _to_out(request)
