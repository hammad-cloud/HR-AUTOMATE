from collections.abc import Sequence
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import RequestContext
from app.core.exceptions import PermissionDeniedError
from app.models import AuditLog, Employee, LeaveRequest, User
from app.permissions.policy import Capability, Scope, scope_for
from app.schemas.audit import AuditEntry, AuditEntryMeta, AuditPage


async def search(
    session: AsyncSession,
    ctx: RequestContext,
    *,
    user_id: UUID | None = None,
    tool: str | None = None,
    outcome: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = 50,
    offset: int = 0,
) -> AuditPage:
    scope = scope_for(ctx, Capability.VIEW_AUDIT_LOG)
    if scope is Scope.NONE:
        raise PermissionDeniedError("Only HR admins can view the audit log.")

    stmt = select(AuditLog)
    # RLS already restricts rows; the explicit filter keeps intent obvious and index-friendly.
    if scope is Scope.COMPANY:
        stmt = stmt.where(AuditLog.tenant_id == ctx.tenant_id)
    if user_id:
        stmt = stmt.where(AuditLog.user_id == user_id)
    if tool:
        stmt = stmt.where(AuditLog.tool == tool)
    if outcome:
        stmt = stmt.where(AuditLog.outcome == outcome)
    if since:
        stmt = stmt.where(AuditLog.ts >= since)
    if until:
        stmt = stmt.where(AuditLog.ts < until)

    total = await session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = (
        await session.scalars(stmt.order_by(AuditLog.ts.desc()).limit(limit).offset(offset))
    ).all()

    # Platform admins see metadata only, never message content, arguments or names (FR-62).
    if scope is Scope.ALL_TENANTS:
        items: list[AuditEntry] | list[AuditEntryMeta] = [
            AuditEntryMeta.model_validate(r) for r in rows
        ]
    else:
        items = await _with_names(session, rows)
    return AuditPage(items=items, total=total, limit=limit, offset=offset)


def _uuid_arg(args: dict[str, Any] | None, key: str) -> UUID | None:
    try:
        return UUID(str(args[key])) if args and args.get(key) else None
    except ValueError:
        return None


async def _with_names(session: AsyncSession, rows: Sequence[AuditLog]) -> list[AuditEntry]:
    """Attach who acted and which employee it concerned, so the log reads in names, not IDs.

    Lookups run through the caller's RLS session: a name from another tenant can't appear.
    """
    user_ids = {r.user_id for r in rows if r.user_id}
    employee_ids = {e for r in rows if (e := _uuid_arg(r.args_redacted, "employee_id"))}
    leave_ids = {e for r in rows if (e := _uuid_arg(r.args_redacted, "request_id"))}

    actors: dict[UUID, str] = {}
    if user_ids:
        result = await session.execute(
            select(User.id, Employee.full_name, User.email)
            .outerjoin(Employee, Employee.id == User.employee_id)
            .where(User.id.in_(user_ids))
        )
        actors = {uid: name or email for uid, name, email in result.all()}

    leave_owner: dict[UUID, UUID] = {}
    if leave_ids:
        owners = await session.execute(
            select(LeaveRequest.id, LeaveRequest.employee_id).where(LeaveRequest.id.in_(leave_ids))
        )
        leave_owner = {request_id: owner for request_id, owner in owners.all()}
        employee_ids |= set(leave_owner.values())

    names: dict[UUID, str] = {}
    if employee_ids:
        found = await session.execute(
            select(Employee.id, Employee.full_name).where(Employee.id.in_(employee_ids))
        )
        names = {employee_id: name for employee_id, name in found.all()}

    entries = []
    for r in rows:
        subject = _uuid_arg(r.args_redacted, "employee_id")
        if subject is None and (leave := _uuid_arg(r.args_redacted, "request_id")):
            subject = leave_owner.get(leave)
        entry = AuditEntry.model_validate(r)
        entry.actor_name = actors.get(r.user_id) if r.user_id else None
        entry.subject_name = names.get(subject) if subject else None
        entries.append(entry)
    return entries
