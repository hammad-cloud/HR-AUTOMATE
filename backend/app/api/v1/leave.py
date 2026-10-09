from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, Query, status

from app.api.deps import Context, Session
from app.models import LeaveStatus
from app.schemas.hr import (
    ApplyLeaveRequest,
    DecideLeaveRequest,
    LeaveBalanceOut,
    LeaveRequestOut,
    LeaveScope,
    LeaveTypeOut,
)
from app.services import leave_service

router = APIRouter(prefix="/leave", tags=["leave"])


@router.get("/types", response_model=list[LeaveTypeOut])
async def leave_types(_: Context, session: Session) -> list[LeaveTypeOut]:
    return await leave_service.list_types(session)


@router.get("/balances", response_model=list[LeaveBalanceOut])
async def balances(
    ctx: Context,
    session: Session,
    employee_id: UUID | None = None,
    year: Annotated[int | None, Query(ge=2000, le=2100)] = None,
) -> list[LeaveBalanceOut]:
    return await leave_service.get_balances(session, ctx, employee_id, year)


@router.get("/requests", response_model=list[LeaveRequestOut])
async def list_requests(
    ctx: Context,
    session: Session,
    scope: LeaveScope = "mine",
    status_filter: Annotated[LeaveStatus | None, Query(alias="status")] = None,
    employee_id: UUID | None = None,
) -> list[LeaveRequestOut]:
    return await leave_service.list_requests(session, ctx, scope, status_filter, employee_id)


@router.get("/approvals", response_model=list[LeaveRequestOut])
async def pending_approvals(ctx: Context, session: Session) -> list[LeaveRequestOut]:
    return await leave_service.list_pending_approvals(session, ctx)


@router.post("/requests", response_model=LeaveRequestOut, status_code=status.HTTP_201_CREATED)
async def apply_leave(
    body: ApplyLeaveRequest,
    ctx: Context,
    session: Session,
    idempotency_key: Annotated[str | None, Header(max_length=80)] = None,
) -> LeaveRequestOut:
    return await leave_service.apply(session, ctx, body, idempotency_key)


@router.post("/requests/{request_id}/approve", response_model=LeaveRequestOut)
async def approve(
    request_id: UUID, body: DecideLeaveRequest, ctx: Context, session: Session
) -> LeaveRequestOut:
    return await leave_service.decide(session, ctx, request_id, approve=True, comment=body.comment)


@router.post("/requests/{request_id}/reject", response_model=LeaveRequestOut)
async def reject(
    request_id: UUID, body: DecideLeaveRequest, ctx: Context, session: Session
) -> LeaveRequestOut:
    return await leave_service.decide(session, ctx, request_id, approve=False, comment=body.comment)


@router.post("/requests/{request_id}/cancel", response_model=LeaveRequestOut)
async def cancel(request_id: UUID, ctx: Context, session: Session) -> LeaveRequestOut:
    return await leave_service.cancel(session, ctx, request_id)
