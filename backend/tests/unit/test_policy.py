"""The role-permission matrix (BRD 4.1) and enforcement rules PR-5 / PR-6, exhaustively."""

from uuid import uuid4

import pytest

from app.core.context import RequestContext, Role
from app.core.exceptions import PermissionDeniedError
from app.permissions.policy import (
    Capability,
    Scope,
    Subject,
    authorize,
    can_view_salary,
    scope_for,
)

TENANT_A, TENANT_B = uuid4(), uuid4()
COMPANY_A, COMPANY_B = uuid4(), uuid4()
MANAGER_EMP, EMPLOYEE_EMP, OTHER_EMP, HR_EMP = uuid4(), uuid4(), uuid4(), uuid4()


def ctx(role: Role, employee_id=None, tenant=TENANT_A, company=COMPANY_A) -> RequestContext:
    return RequestContext(
        user_id=uuid4(), role=role, tenant_id=tenant, company_id=company, employee_id=employee_id
    )


def subject(employee_id, manager_id=None, tenant=TENANT_A, company=COMPANY_A) -> Subject:
    return Subject(
        employee_id=employee_id, tenant_id=tenant, company_id=company, manager_id=manager_id
    )


EMPLOYEE = ctx(Role.EMPLOYEE, EMPLOYEE_EMP)
MANAGER = ctx(Role.MANAGER, MANAGER_EMP)
HR = ctx(Role.HR_ADMIN, HR_EMP)
PLATFORM = ctx(Role.PLATFORM_ADMIN, None, tenant=None, company=None)

SELF_EMPLOYEE = subject(EMPLOYEE_EMP, manager_id=MANAGER_EMP)
SELF_MANAGER = subject(MANAGER_EMP)
DIRECT_REPORT = SELF_EMPLOYEE
NOT_MY_REPORT = subject(OTHER_EMP, manager_id=uuid4())
OTHER_TENANT = subject(uuid4(), tenant=TENANT_B, company=COMPANY_B)


@pytest.mark.parametrize(
    ("actor", "capability", "target", "allowed"),
    [
        # View profile: Own / Team + own / Company / No
        (EMPLOYEE, Capability.VIEW_PROFILE, SELF_EMPLOYEE, True),
        (EMPLOYEE, Capability.VIEW_PROFILE, NOT_MY_REPORT, False),
        (MANAGER, Capability.VIEW_PROFILE, SELF_MANAGER, True),
        (MANAGER, Capability.VIEW_PROFILE, DIRECT_REPORT, True),
        (MANAGER, Capability.VIEW_PROFILE, NOT_MY_REPORT, False),
        (HR, Capability.VIEW_PROFILE, NOT_MY_REPORT, True),
        (PLATFORM, Capability.VIEW_PROFILE, SELF_EMPLOYEE, False),
        # Payslips: Own / Own / Company / No (managers can't see team pay)
        (EMPLOYEE, Capability.VIEW_PAYSLIP, SELF_EMPLOYEE, True),
        (EMPLOYEE, Capability.VIEW_PAYSLIP, NOT_MY_REPORT, False),
        (MANAGER, Capability.VIEW_PAYSLIP, DIRECT_REPORT, False),
        (MANAGER, Capability.VIEW_PAYSLIP, SELF_MANAGER, True),
        (HR, Capability.VIEW_PAYSLIP, DIRECT_REPORT, True),
        # Approve / reject: No / Team (not own) / Company (not own)
        (EMPLOYEE, Capability.DECIDE_LEAVE, SELF_EMPLOYEE, False),
        (MANAGER, Capability.DECIDE_LEAVE, DIRECT_REPORT, True),
        (MANAGER, Capability.DECIDE_LEAVE, NOT_MY_REPORT, False),
        (MANAGER, Capability.DECIDE_LEAVE, SELF_MANAGER, False),
        (HR, Capability.DECIDE_LEAVE, NOT_MY_REPORT, True),
        (HR, Capability.DECIDE_LEAVE, subject(HR_EMP), False),
        # Apply: own only, for every HR role
        (EMPLOYEE, Capability.APPLY_LEAVE, SELF_EMPLOYEE, True),
        (HR, Capability.APPLY_LEAVE, NOT_MY_REPORT, False),
        (PLATFORM, Capability.APPLY_LEAVE, SELF_EMPLOYEE, False),
        # Attendance: Own / Team + own / Company
        (MANAGER, Capability.VIEW_ATTENDANCE, DIRECT_REPORT, True),
        (MANAGER, Capability.VIEW_ATTENDANCE, NOT_MY_REPORT, False),
        # Cancel: Own / Own / Company
        (MANAGER, Capability.CANCEL_LEAVE, DIRECT_REPORT, False),
        (HR, Capability.CANCEL_LEAVE, DIRECT_REPORT, True),
    ],
)
def test_matrix(actor, capability, target, allowed):
    assert authorize(actor, capability, target).allowed is allowed


@pytest.mark.parametrize("actor", [EMPLOYEE, MANAGER, HR])
@pytest.mark.parametrize(
    "capability",
    [
        Capability.VIEW_PROFILE,
        Capability.VIEW_PAYSLIP,
        Capability.VIEW_ATTENDANCE,
        Capability.DECIDE_LEAVE,
        Capability.VIEW_LEAVE_BALANCE,
    ],
)
def test_cross_tenant_always_denied(actor, capability):
    decision = authorize(actor, capability, OTHER_TENANT)
    assert not decision.allowed


def test_cross_company_denied_even_for_hr():
    same_tenant_other_company = subject(OTHER_EMP, company=COMPANY_B)
    assert not authorize(HR, Capability.VIEW_PROFILE, same_tenant_other_company).allowed


def test_self_approval_message_is_specific():
    decision = authorize(MANAGER, Capability.DECIDE_LEAVE, SELF_MANAGER)
    assert "own request" in decision.reason


def test_refusal_reasons_are_plain_language():
    decision = authorize(PLATFORM, Capability.VIEW_PROFILE, SELF_EMPLOYEE)
    assert decision.reason == "Platform admins can't view employee profiles."
    assert "_" not in authorize(EMPLOYEE, Capability.DECIDE_LEAVE, SELF_EMPLOYEE).reason


def test_enforce_raises_typed_error():
    with pytest.raises(PermissionDeniedError):
        authorize(EMPLOYEE, Capability.VIEW_PAYSLIP, NOT_MY_REPORT).enforce()


@pytest.mark.parametrize(
    ("actor", "expected"),
    [(EMPLOYEE, Scope.NONE), (MANAGER, Scope.NONE), (HR, Scope.COMPANY), (PLATFORM, Scope.NONE)],
)
def test_only_hr_can_manage_employees(actor, expected):
    assert scope_for(actor, Capability.MANAGE_EMPLOYEES) is expected


def test_hr_cannot_change_own_record():
    assert authorize(HR, Capability.MANAGE_EMPLOYEES, NOT_MY_REPORT).allowed
    decision = authorize(HR, Capability.MANAGE_EMPLOYEES, subject(HR_EMP))
    assert not decision.allowed and "your own employment record" in decision.reason
    assert not authorize(HR, Capability.MANAGE_EMPLOYEES, OTHER_TENANT).allowed


def test_salary_visibility():
    assert can_view_salary(EMPLOYEE, SELF_EMPLOYEE)
    assert not can_view_salary(MANAGER, DIRECT_REPORT)
    assert can_view_salary(HR, DIRECT_REPORT)
    assert not can_view_salary(HR, OTHER_TENANT)
    assert not can_view_salary(PLATFORM, SELF_EMPLOYEE)
