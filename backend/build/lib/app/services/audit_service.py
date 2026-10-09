from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import RequestContext
from app.core.logging import request_id_var
from app.core.redaction import redact, redact_text
from app.db.session import scoped_session
from app.models import AuditLog


class Outcome:
    SUCCESS = "SUCCESS"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    REJECTED = "REJECTED"  # business-rule failure
    ERROR = "ERROR"


def _build(
    ctx: RequestContext,
    *,
    event: str,
    outcome: str,
    tool: str | None,
    args: dict[str, Any] | None,
    detail: str | None,
    channel: str,
    conversation_id: UUID | None,
    user_message: str | None,
) -> AuditLog:
    return AuditLog(
        tenant_id=ctx.tenant_id,
        user_id=ctx.user_id,
        conversation_id=conversation_id,
        request_id=request_id_var.get(),
        channel=channel,
        event=event,
        tool=tool,
        user_message=redact_text(user_message) if user_message else None,
        args_redacted=redact(args) if args is not None else None,
        outcome=outcome,
        detail=redact_text(detail) if detail else None,
    )


async def record(
    session: AsyncSession,
    ctx: RequestContext,
    *,
    event: str,
    outcome: str,
    tool: str | None = None,
    args: dict[str, Any] | None = None,
    detail: str | None = None,
    channel: str = "api",
    conversation_id: UUID | None = None,
    user_message: str | None = None,
) -> None:
    """Append an audit row inside the caller's transaction (committed with the action)."""
    session.add(
        _build(
            ctx,
            event=event,
            outcome=outcome,
            tool=tool,
            args=args,
            detail=detail,
            channel=channel,
            conversation_id=conversation_id,
            user_message=user_message,
        )
    )


async def record_denial(
    ctx: RequestContext,
    *,
    event: str,
    tool: str | None = None,
    args: dict[str, Any] | None = None,
    detail: str | None = None,
    channel: str = "api",
) -> None:
    """Audit a refusal in its own transaction so it survives the request's rollback (PR-7)."""
    async with scoped_session(ctx) as session:
        session.add(
            _build(
                ctx,
                event=event,
                outcome=Outcome.PERMISSION_DENIED,
                tool=tool,
                args=args,
                detail=detail,
                channel=channel,
                conversation_id=None,
                user_message=None,
            )
        )
