from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import RequestContext
from app.models import Payslip
from app.permissions.policy import Capability
from app.schemas.hr import PayslipOut
from app.services.attendance_service import parse_month
from app.services.employee_service import resolve_target


async def list_payslips(
    session: AsyncSession, ctx: RequestContext, employee_id: UUID | None, month: str | None
) -> list[PayslipOut]:
    employee = await resolve_target(session, ctx, Capability.VIEW_PAYSLIP, employee_id)
    stmt = select(Payslip).where(Payslip.employee_id == employee.id)
    if month:
        start, _ = parse_month(month)
        stmt = stmt.where(Payslip.month == start)
    rows = (await session.scalars(stmt.order_by(Payslip.month.desc()))).all()
    return [PayslipOut.model_validate(p) for p in rows]
