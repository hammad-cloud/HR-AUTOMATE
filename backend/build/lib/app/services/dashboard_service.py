from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import RequestContext
from app.models import Employee, LeaveRequest, LeaveStatus
from app.permissions.policy import Capability, Scope, scope_for
from app.schemas.hr import DashboardStats, LeaveBalanceOut
from app.services import attendance_service, leave_service


async def get_stats(session: AsyncSession, ctx: RequestContext) -> DashboardStats:
    balances: list[LeaveBalanceOut] = []
    attendance: dict[str, int] = {}
    pending_mine = 0
    if ctx.employee_id:
        balances = await leave_service.get_balances(session, ctx, None)
        attendance = (await attendance_service.get_report(session, ctx, None, None)).summary
        pending_mine = (
            await session.scalar(
                select(func.count()).where(
                    LeaveRequest.employee_id == ctx.employee_id,
                    LeaveRequest.status == LeaveStatus.PENDING,
                )
            )
            or 0
        )

    approvals = await leave_service.list_pending_approvals(session, ctx)

    scope = scope_for(ctx, Capability.VIEW_ANALYTICS)
    team_size = headcount = None
    if scope >= Scope.TEAM and ctx.employee_id:
        team_size = await session.scalar(
            select(func.count()).where(Employee.manager_id == ctx.employee_id)
        )
    if scope >= Scope.COMPANY:
        headcount = await session.scalar(
            select(func.count()).where(
                Employee.company_id == ctx.company_id, Employee.is_active.is_(True)
            )
        )

    return DashboardStats(
        leave_balances=balances,
        pending_my_requests=pending_mine,
        pending_my_approvals=len(approvals),
        attendance_this_month=attendance,
        team_size=team_size,
        headcount=headcount,
    )
