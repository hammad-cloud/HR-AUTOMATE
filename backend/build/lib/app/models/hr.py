import uuid
from datetime import date, datetime, time
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, Timestamped, UUIDPrimaryKey
from app.models.organization import Employee


class LeaveStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class AttendanceStatus(StrEnum):
    PRESENT = "PRESENT"
    LATE = "LATE"
    ABSENT = "ABSENT"
    ON_LEAVE = "ON_LEAVE"
    WFH = "WFH"


class LeaveType(UUIDPrimaryKey, Base):
    __tablename__ = "leave_types"
    __table_args__ = (UniqueConstraint("tenant_id", "code"),)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )
    code: Mapped[str] = mapped_column(String(20))
    name: Mapped[str] = mapped_column(String(60))
    annual_quota: Mapped[int] = mapped_column(Integer)


class LeaveBalance(UUIDPrimaryKey, Base):
    __tablename__ = "leave_balances"
    __table_args__ = (
        UniqueConstraint("employee_id", "leave_type_id", "year"),
        CheckConstraint("used >= 0 AND used <= allocated", name="used_within_allocation"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id", ondelete="CASCADE"), index=True
    )
    leave_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leave_types.id", ondelete="CASCADE")
    )
    year: Mapped[int] = mapped_column(Integer)
    allocated: Mapped[Decimal] = mapped_column(Numeric(5, 1))
    used: Mapped[Decimal] = mapped_column(Numeric(5, 1), default=Decimal("0"))

    leave_type: Mapped[LeaveType] = relationship(lazy="joined")

    @property
    def remaining(self) -> Decimal:
        return self.allocated - self.used


class LeaveRequest(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "leave_requests"
    __table_args__ = (
        UniqueConstraint("tenant_id", "idempotency_key"),
        CheckConstraint("end_date >= start_date", name="valid_date_range"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id", ondelete="CASCADE"), index=True
    )
    leave_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leave_types.id", ondelete="RESTRICT")
    )
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    days: Mapped[Decimal] = mapped_column(Numeric(5, 1))
    reason: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(12), default=LeaveStatus.PENDING, index=True)
    approver_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id", ondelete="SET NULL")
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decision_comment: Mapped[str | None] = mapped_column(Text)
    # Guarantees a double-submitted request creates exactly one row (FR-42).
    idempotency_key: Mapped[str | None] = mapped_column(String(80))

    leave_type: Mapped[LeaveType] = relationship(lazy="joined")
    employee: Mapped[Employee] = relationship(foreign_keys=[employee_id], lazy="joined")


class Attendance(UUIDPrimaryKey, Base):
    __tablename__ = "attendance"
    __table_args__ = (UniqueConstraint("employee_id", "date"),)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id", ondelete="CASCADE"), index=True
    )
    date: Mapped[date] = mapped_column(Date, index=True)
    check_in: Mapped[time | None] = mapped_column(Time)
    check_out: Mapped[time | None] = mapped_column(Time)
    status: Mapped[str] = mapped_column(String(12))


class Payslip(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "payslips"
    __table_args__ = (UniqueConstraint("employee_id", "month"),)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id", ondelete="CASCADE"), index=True
    )
    # Always the first day of the pay month.
    month: Mapped[date] = mapped_column(Date)
    gross: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    deductions: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    net: Mapped[Decimal] = mapped_column(Numeric(12, 2))
