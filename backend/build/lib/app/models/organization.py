import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, Timestamped, UUIDPrimaryKey


class Tenant(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(String(120))
    slug: Mapped[str] = mapped_column(String(60), unique=True)
    plan: Mapped[str] = mapped_column(String(30), default="standard")


class Company(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "companies"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(160))


class Employee(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "employees"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), index=True
    )
    employee_code: Mapped[str] = mapped_column(String(20))
    full_name: Mapped[str] = mapped_column(String(160), index=True)
    email: Mapped[str] = mapped_column(String(254))
    department: Mapped[str] = mapped_column(String(80), index=True)
    job_title: Mapped[str] = mapped_column(String(120))
    # manager_id defines the "team" scope used by the permission policy.
    manager_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id", ondelete="SET NULL"), index=True
    )
    join_date: Mapped[date] = mapped_column(Date)
    salary: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    national_id: Mapped[str] = mapped_column(String(20))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    manager: Mapped["Employee | None"] = relationship(remote_side="Employee.id", lazy="raise")


class User(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "users"

    # NULL only for PLATFORM_ADMIN, who belongs to no tenant.
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE")
    )
    employee_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id", ondelete="CASCADE"), unique=True
    )
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(20))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # Tokens issued before this instant are rejected (password change / HR reset).
    password_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
