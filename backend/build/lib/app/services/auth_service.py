from datetime import UTC, datetime

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import RequestContext, Role
from app.core.exceptions import BusinessRuleError, UnauthenticatedError
from app.core.security import create_access_token, hash_password, verify_password
from app.models import Employee, Tenant, User
from app.schemas.auth import CurrentUser
from app.services import audit_service
from app.services.audit_service import Outcome

# Login happens before a tenant is known, so RLS would hide every user row. This narrowly
# scoped SECURITY DEFINER function (see migration 0002) returns only the one row needed
# to verify credentials, instead of giving the API role a bypass.
_LOOKUP = text(
    "SELECT id, tenant_id, company_id, employee_id, role, password_hash, is_active "
    "FROM app_auth_lookup(:email)"
)

# Verified against when the email is unknown, so response timing does not reveal valid emails.
_DUMMY_HASH = hash_password("timing-equaliser")


async def authenticate(session: AsyncSession, email: str, password: str) -> str:
    row = (await session.execute(_LOOKUP, {"email": email.lower()})).mappings().first()
    if row is None:
        verify_password(password, _DUMMY_HASH)
        raise UnauthenticatedError("Invalid email or password")
    if not row["is_active"] or not verify_password(password, row["password_hash"]):
        raise UnauthenticatedError("Invalid email or password")

    ctx = RequestContext(
        user_id=row["id"],
        role=Role(row["role"]),
        tenant_id=row["tenant_id"],
        company_id=row["company_id"],
        employee_id=row["employee_id"],
    )
    return create_access_token(ctx)


async def ensure_session_current(session: AsyncSession, ctx: RequestContext) -> None:
    """Reject a still-unexpired token that no longer matches the account.

    JWTs are stateless, so without this a deactivated employee, a demoted HR admin, or someone
    holding a token from before a password reset would keep access until expiry.
    One primary-key read per request.
    """
    row = (
        await session.execute(
            select(User.role, User.is_active, User.password_changed_at).where(
                User.id == ctx.user_id
            )
        )
    ).first()
    if row is None or not row.is_active or row.role != ctx.role.value:
        raise UnauthenticatedError("Your session has ended. Please sign in again.")
    if (
        row.password_changed_at is not None
        and ctx.issued_at is not None
        and ctx.issued_at < row.password_changed_at
    ):
        raise UnauthenticatedError("Your password was changed. Please sign in again.")


def set_password(user: User, new_password: str) -> None:
    """Store a new password and revoke every session issued before now."""
    user.password_hash = hash_password(new_password)
    user.password_changed_at = datetime.now(UTC)


async def change_password(
    session: AsyncSession, ctx: RequestContext, current_password: str, new_password: str
) -> str:
    """Change the caller's own password. Other sessions are signed out; this one gets a fresh
    token, which is returned."""
    user = await session.scalar(select(User).where(User.id == ctx.user_id).with_for_update())
    if user is None:
        raise UnauthenticatedError("User no longer exists")
    if not verify_password(current_password, user.password_hash):
        raise BusinessRuleError("Your current password is incorrect.")
    set_password(user, new_password)
    await session.flush()
    await audit_service.record(
        session, ctx, event="auth.password_change", tool="change_password", outcome=Outcome.SUCCESS
    )
    return create_access_token(ctx)


async def get_current_user(session: AsyncSession, ctx: RequestContext) -> CurrentUser:
    user = await session.scalar(select(User).where(User.id == ctx.user_id))
    if user is None:
        raise UnauthenticatedError("User no longer exists")

    employee: Employee | None = None
    tenant_name: str | None = None
    if ctx.employee_id:
        employee = await session.get(Employee, ctx.employee_id)
    if ctx.tenant_id:
        tenant_name = await session.scalar(select(Tenant.name).where(Tenant.id == ctx.tenant_id))

    return CurrentUser(
        user_id=user.id,
        email=user.email,
        role=ctx.role,
        tenant_id=ctx.tenant_id,
        tenant_name=tenant_name,
        company_id=ctx.company_id,
        employee_id=ctx.employee_id,
        full_name=employee.full_name if employee else "Platform Administrator",
        job_title=employee.job_title if employee else None,
        department=employee.department if employee else None,
    )
