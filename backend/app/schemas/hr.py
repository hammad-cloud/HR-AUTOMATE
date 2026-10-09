from datetime import date, datetime, time
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AfterValidator, BaseModel, Field, field_validator, model_validator

from app.core.context import Role
from app.schemas.common import APIModel


class EmployeeSummary(APIModel):
    id: UUID
    employee_code: str
    full_name: str
    email: str
    department: str
    job_title: str
    is_active: bool


class EmployeeDetail(EmployeeSummary):
    manager_id: UUID | None
    manager_name: str | None
    join_date: date
    role: Role | None
    # None when the caller is not entitled to see it (PR-5).
    salary: Decimal | None
    salary_masked: bool


EmployeeStatus = Literal["active", "inactive"]
# PLATFORM_ADMIN is an operator account, never something HR can hand out.
AssignableRole = Literal[Role.EMPLOYEE, Role.MANAGER, Role.HR_ADMIN]
Salary = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=2)]


def _collapse_spaces(value: str) -> str:
    value = " ".join(value.split())
    if len(value) < 2:
        raise ValueError("must be at least 2 characters")
    return value


CleanText = Annotated[str, AfterValidator(_collapse_spaces)]


class CreateEmployeeRequest(BaseModel):
    full_name: CleanText = Field(min_length=2, max_length=160)
    # Same rule as login: demo tenants use reserved .test domains, so not EmailStr.
    email: str = Field(min_length=3, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    department: CleanText = Field(min_length=2, max_length=80)
    job_title: CleanText = Field(min_length=2, max_length=120)
    manager_id: UUID | None = None
    join_date: date
    salary: Salary
    national_id: str = Field(pattern=r"^\d{5}-\d{7}-\d$", description="CNIC, e.g. 35202-1234567-1")
    role: AssignableRole = Role.EMPLOYEE
    # Initial password, shared with the new hire out of band.
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def _normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class UpdateEmployeeRequest(BaseModel):
    """Partial update: only the fields sent are changed. Email, CNIC and joining date are
    identity data and stay fixed."""

    full_name: CleanText | None = Field(default=None, min_length=2, max_length=160)
    department: CleanText | None = Field(default=None, min_length=2, max_length=80)
    job_title: CleanText | None = Field(default=None, min_length=2, max_length=120)
    manager_id: UUID | None = None  # explicit null removes the manager
    salary: Salary | None = None
    role: AssignableRole | None = None

    @model_validator(mode="after")
    def _only_manager_is_nullable(self) -> "UpdateEmployeeRequest":
        for field in self.model_fields_set - {"manager_id"}:
            if getattr(self, field) is None:
                raise ValueError(f"{field} cannot be empty")
        if not self.model_fields_set:
            raise ValueError("Provide at least one field to change")
        return self

    def changes(self) -> dict[str, object]:
        return {field: getattr(self, field) for field in self.model_fields_set}


class ResetPasswordRequest(BaseModel):
    # Temporary password HR shares out of band; the employee then changes it themselves.
    new_password: str = Field(min_length=8, max_length=128)


class LeaveTypeOut(APIModel):
    id: UUID
    code: str
    name: str
    annual_quota: int


class LeaveBalanceOut(BaseModel):
    leave_type: LeaveTypeOut
    year: int
    allocated: Decimal
    used: Decimal
    pending: Decimal
    remaining: Decimal


class LeaveRequestOut(APIModel):
    id: UUID
    employee_id: UUID
    employee_name: str
    leave_type: LeaveTypeOut
    start_date: date
    end_date: date
    days: Decimal
    reason: str
    status: str
    approver_id: UUID | None
    decided_at: datetime | None
    decision_comment: str | None
    created_at: datetime


class ApplyLeaveRequest(BaseModel):
    leave_type_code: str = Field(min_length=2, max_length=20)
    start_date: date
    end_date: date
    reason: str = Field(default="", max_length=500)

    @model_validator(mode="after")
    def _check_range(self) -> "ApplyLeaveRequest":
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        if (self.end_date - self.start_date).days > 60:
            raise ValueError("A single request cannot exceed 60 calendar days")
        return self


class DecideLeaveRequest(BaseModel):
    comment: str | None = Field(default=None, max_length=500)


LeaveScope = Literal["mine", "team", "company"]


class AttendanceOut(APIModel):
    date: date
    check_in: time | None
    check_out: time | None
    status: str


class AttendanceReport(BaseModel):
    employee: EmployeeSummary
    month: str
    records: list[AttendanceOut]
    summary: dict[str, int]


class PayslipOut(APIModel):
    id: UUID
    employee_id: UUID
    month: date
    gross: Decimal
    deductions: Decimal
    net: Decimal


class DashboardStats(BaseModel):
    leave_balances: list[LeaveBalanceOut]
    pending_my_requests: int
    pending_my_approvals: int
    attendance_this_month: dict[str, int]
    team_size: int | None
    headcount: int | None
