"""Attendance, payslips and the role-aware dashboard."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from app.api.deps import Context, Session
from app.schemas.hr import AttendanceReport, DashboardStats, PayslipOut
from app.services import attendance_service, dashboard_service, payslip_service

router = APIRouter(tags=["records"])

Month = Annotated[str | None, Query(pattern=r"^\d{4}-\d{2}$", examples=["2026-09"])]


@router.get("/attendance", response_model=AttendanceReport)
async def attendance(
    ctx: Context, session: Session, employee_id: UUID | None = None, month: Month = None
) -> AttendanceReport:
    return await attendance_service.get_report(session, ctx, employee_id, month)


@router.get("/payslips", response_model=list[PayslipOut])
async def payslips(
    ctx: Context, session: Session, employee_id: UUID | None = None, month: Month = None
) -> list[PayslipOut]:
    return await payslip_service.list_payslips(session, ctx, employee_id, month)


@router.get("/dashboard", response_model=DashboardStats)
async def dashboard(ctx: Context, session: Session) -> DashboardStats:
    return await dashboard_service.get_stats(session, ctx)
