from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response, status

from app.api.deps import Context, Session
from app.schemas.hr import (
    CreateEmployeeRequest,
    EmployeeDetail,
    EmployeeStatus,
    EmployeeSummary,
    ResetPasswordRequest,
    UpdateEmployeeRequest,
)
from app.services import employee_service

router = APIRouter(prefix="/employees", tags=["employees"])


@router.get("", response_model=list[EmployeeSummary])
async def list_employees(
    ctx: Context,
    session: Session,
    search: Annotated[str | None, Query(max_length=80)] = None,
    status_filter: Annotated[EmployeeStatus, Query(alias="status")] = "active",
) -> list[EmployeeSummary]:
    """Employees visible to the caller: self, team (manager) or company (HR admin)."""
    return await employee_service.list_employees(session, ctx, search, status_filter)


@router.post("", response_model=EmployeeDetail, status_code=status.HTTP_201_CREATED)
async def create_employee(
    body: CreateEmployeeRequest, ctx: Context, session: Session
) -> EmployeeDetail:
    """Onboard a new employee with a login account and leave balances (HR admin only)."""
    return await employee_service.create_employee(session, ctx, body)


@router.get("/me", response_model=EmployeeDetail)
async def my_profile(ctx: Context, session: Session) -> EmployeeDetail:
    return await employee_service.get_employee(session, ctx, None)


@router.get("/{employee_id}", response_model=EmployeeDetail)
async def get_employee(employee_id: UUID, ctx: Context, session: Session) -> EmployeeDetail:
    return await employee_service.get_employee(session, ctx, employee_id)


@router.patch("/{employee_id}", response_model=EmployeeDetail)
async def update_employee(
    employee_id: UUID, body: UpdateEmployeeRequest, ctx: Context, session: Session
) -> EmployeeDetail:
    """Change job details, manager, salary or access role (HR admin, never their own record)."""
    return await employee_service.update_employee(session, ctx, employee_id, body)


@router.post("/{employee_id}/deactivate", response_model=EmployeeDetail)
async def deactivate_employee(employee_id: UUID, ctx: Context, session: Session) -> EmployeeDetail:
    """Offboard: sign-in is blocked and pending leave cancelled; records are kept."""
    return await employee_service.deactivate_employee(session, ctx, employee_id)


@router.post("/{employee_id}/reset-password", status_code=status.HTTP_204_NO_CONTENT)
async def reset_password(
    employee_id: UUID, body: ResetPasswordRequest, ctx: Context, session: Session
) -> Response:
    """Set a temporary password and sign the employee out everywhere (HR admin only)."""
    await employee_service.reset_password(session, ctx, employee_id, body.new_password)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{employee_id}/reactivate", response_model=EmployeeDetail)
async def reactivate_employee(employee_id: UUID, ctx: Context, session: Session) -> EmployeeDetail:
    return await employee_service.reactivate_employee(session, ctx, employee_id)
