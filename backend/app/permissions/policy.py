"""Central permission policy: the role-permission matrix from BRD section 4.1, as code.

This module is pure (no I/O) so every rule is unit-testable. Services resolve the target
record first and then ask this module for a decision; the language model never decides access.
"""

from dataclasses import dataclass
from enum import IntEnum, StrEnum
from uuid import UUID

from app.core.context import RequestContext, Role
from app.core.exceptions import PermissionDeniedError


class Capability(StrEnum):
    ASK_KNOWLEDGE = "ask_knowledge"
    VIEW_PROFILE = "view_profile"
    MANAGE_EMPLOYEES = "manage_employees"  # onboard, edit, deactivate
    VIEW_LEAVE_BALANCE = "view_leave_balance"
    APPLY_LEAVE = "apply_leave"
    DECIDE_LEAVE = "decide_leave"  # approve or reject
    CANCEL_LEAVE = "cancel_leave"
    VIEW_ATTENDANCE = "view_attendance"
    VIEW_PAYSLIP = "view_payslip"
    VIEW_ANALYTICS = "view_analytics"
    VIEW_AUDIT_LOG = "view_audit_log"
    VIEW_METRICS = "view_metrics"


class Scope(IntEnum):
    """How far a capability reaches. Ordered so a wider scope compares greater."""

    NONE = 0
    OWN = 1
    TEAM = 2  # direct reports, plus own where the matrix says "Team + own"
    COMPANY = 3
    ALL_TENANTS = 4


_E, _M, _H, _P = Role.EMPLOYEE, Role.MANAGER, Role.HR_ADMIN, Role.PLATFORM_ADMIN

MATRIX: dict[Capability, dict[Role, Scope]] = {
    Capability.ASK_KNOWLEDGE: {_E: Scope.OWN, _M: Scope.OWN, _H: Scope.OWN, _P: Scope.OWN},
    Capability.VIEW_PROFILE: {_E: Scope.OWN, _M: Scope.TEAM, _H: Scope.COMPANY},
    Capability.MANAGE_EMPLOYEES: {_H: Scope.COMPANY},
    Capability.VIEW_LEAVE_BALANCE: {_E: Scope.OWN, _M: Scope.TEAM, _H: Scope.COMPANY},
    Capability.APPLY_LEAVE: {_E: Scope.OWN, _M: Scope.OWN, _H: Scope.OWN},
    Capability.DECIDE_LEAVE: {_M: Scope.TEAM, _H: Scope.COMPANY},
    Capability.CANCEL_LEAVE: {_E: Scope.OWN, _M: Scope.OWN, _H: Scope.COMPANY},
    Capability.VIEW_ATTENDANCE: {_E: Scope.OWN, _M: Scope.TEAM, _H: Scope.COMPANY},
    Capability.VIEW_PAYSLIP: {_E: Scope.OWN, _M: Scope.OWN, _H: Scope.COMPANY},
    Capability.VIEW_ANALYTICS: {_M: Scope.TEAM, _H: Scope.COMPANY},
    Capability.VIEW_AUDIT_LOG: {_H: Scope.COMPANY, _P: Scope.ALL_TENANTS},
    Capability.VIEW_METRICS: {_H: Scope.COMPANY, _P: Scope.ALL_TENANTS},
}

# Plain-language pieces for refusal messages, which end users and the audit log both read.
ROLE_NAMES: dict[Role, str] = {
    _E: "Employees",
    _M: "Managers",
    _H: "HR admins",
    _P: "Platform admins",
}
ACTION_TEXT: dict[Capability, str] = {
    Capability.ASK_KNOWLEDGE: "use the HR assistant",
    Capability.VIEW_PROFILE: "view employee profiles",
    Capability.MANAGE_EMPLOYEES: "manage employee records",
    Capability.VIEW_LEAVE_BALANCE: "view leave balances",
    Capability.APPLY_LEAVE: "apply for leave",
    Capability.DECIDE_LEAVE: "approve or reject leave",
    Capability.CANCEL_LEAVE: "cancel leave",
    Capability.VIEW_ATTENDANCE: "view attendance",
    Capability.VIEW_PAYSLIP: "view payslips",
    Capability.VIEW_ANALYTICS: "view analytics",
    Capability.VIEW_AUDIT_LOG: "view the audit log",
    Capability.VIEW_METRICS: "view usage metrics",
}

# Capabilities where the actor may never act on their own record (PR-6: no self-approval;
# likewise HR can't raise their own salary, change their own role or deactivate themselves).
_SELF_EXCLUDED = {
    Capability.DECIDE_LEAVE: "You cannot approve or reject your own request.",
    Capability.MANAGE_EMPLOYEES: "You cannot change your own employment record.",
}


@dataclass(frozen=True, slots=True)
class Subject:
    """The employee record an action targets, as loaded from the database."""

    employee_id: UUID
    tenant_id: UUID
    company_id: UUID
    manager_id: UUID | None


@dataclass(frozen=True, slots=True)
class Decision:
    allowed: bool
    reason: str

    def enforce(self) -> None:
        if not self.allowed:
            raise PermissionDeniedError(self.reason)


def scope_for(ctx: RequestContext, capability: Capability) -> Scope:
    return MATRIX[capability].get(ctx.role, Scope.NONE)


def authorize(ctx: RequestContext, capability: Capability, subject: Subject) -> Decision:
    """Decide whether `ctx` may exercise `capability` on `subject`.

    Checks run from the outermost boundary inwards: tenant, company, self-exclusion, scope.
    """
    scope = scope_for(ctx, capability)
    if scope is Scope.NONE:
        return Decision(False, f"{ROLE_NAMES[ctx.role]} can't {ACTION_TEXT[capability]}.")

    # Tenant isolation is checked here as well as by RLS (defence in depth).
    if scope is not Scope.ALL_TENANTS and subject.tenant_id != ctx.tenant_id:
        return Decision(False, "That record belongs to a different organisation.")
    if scope <= Scope.COMPANY and subject.company_id != ctx.company_id:
        return Decision(False, "That record belongs to a different company.")

    is_self = ctx.employee_id is not None and subject.employee_id == ctx.employee_id
    if capability in _SELF_EXCLUDED and is_self:
        return Decision(False, _SELF_EXCLUDED[capability])

    if scope >= Scope.COMPANY:
        return Decision(True, "company scope")
    if is_self:
        return Decision(True, "own record")
    if (
        scope is Scope.TEAM
        and ctx.employee_id is not None
        and subject.manager_id == ctx.employee_id
    ):
        return Decision(True, "direct report")
    return Decision(False, "You can only access records you are entitled to see.")


def can_view_salary(ctx: RequestContext, subject: Subject) -> bool:
    """PR-5: salary is visible only to its owner and to HR admins of the same company."""
    if ctx.employee_id is not None and subject.employee_id == ctx.employee_id:
        return True
    return (
        ctx.role is Role.HR_ADMIN
        and subject.tenant_id == ctx.tenant_id
        and subject.company_id == ctx.company_id
    )
