from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from app.api.deps import Context, Session
from app.schemas.audit import AuditPage
from app.services import audit_query_service

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=AuditPage)
async def search_audit_log(
    ctx: Context,
    session: Session,
    user_id: UUID | None = None,
    tool: Annotated[str | None, Query(max_length=40)] = None,
    outcome: Annotated[str | None, Query(max_length=24)] = None,
    since: datetime | None = None,
    until: datetime | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> AuditPage:
    return await audit_query_service.search(
        session,
        ctx,
        user_id=user_id,
        tool=tool,
        outcome=outcome,
        since=since,
        until=until,
        limit=limit,
        offset=offset,
    )
