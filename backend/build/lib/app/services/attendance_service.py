from collections import Counter
from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import RequestContext
from app.core.exceptions import BusinessRuleError
from app.models import Attendance
from app.permissions.policy import Capability
from app.schemas.hr import AttendanceOut, AttendanceReport, EmployeeSummary
from app.services.employee_service import resolve_target


def parse_month(month: str | None) -> tuple[date, date]:
    """Return [first day, first day of next month) for 'YYYY-MM' (default: current month)."""
    try:
        start = date.fromisoformat(f"{month}-01") if month else date.today().replace(day=1)
    except ValueError as exc:
        raise BusinessRuleError("Month must be in YYYY-MM format.") from exc
    end = date(start.year + start.month // 12, start.month % 12 + 1, 1)
    return start, end


async def get_report(
    session: AsyncSession, ctx: RequestContext, employee_id: UUID | None, month: str | None
) -> AttendanceReport:
    employee = await resolve_target(session, ctx, Capability.VIEW_ATTENDANCE, employee_id)
    start, end = parse_month(month)
    rows = (
        await session.scalars(
            select(Attendance)
            .where(
                Attendance.employee_id == employee.id,
                Attendance.date >= start,
                Attendance.date < end,
            )
            .order_by(Attendance.date)
        )
    ).all()
    return AttendanceReport(
        employee=EmployeeSummary.model_validate(employee),
        month=start.strftime("%Y-%m"),
        records=[AttendanceOut.model_validate(r) for r in rows],
        summary=dict(Counter(r.status for r in rows)),
    )
