"""Proves tenant isolation is enforced by Postgres itself, independent of application code.

These queries deliberately skip the service layer and its policy checks: if any of them
returned another tenant's rows, the database backstop (PR-1, NFR-01) would be broken.
"""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.db.session import scoped_session

pytestmark = pytest.mark.integration

TENANT_TABLES = [
    "employees",
    "leave_requests",
    "leave_balances",
    "attendance",
    "payslips",
    "leave_types",
]


@pytest.mark.parametrize("table", TENANT_TABLES)
async def test_cross_tenant_select_returns_zero_rows(table, ayesha, globex_tenant_id):
    async with scoped_session(ayesha) as session:
        # The query explicitly asks for Globex rows; RLS must still return none.
        leaked = await session.scalar(
            text(f"SELECT count(*) FROM {table} WHERE tenant_id = :t"),  # noqa: S608
            {"t": globex_tenant_id},
        )
        own = await session.scalar(text(f"SELECT count(*) FROM {table}"))  # noqa: S608
    assert leaked == 0
    assert own > 0


@pytest.mark.parametrize("table", [*TENANT_TABLES, "users", "tenants"])
async def test_no_context_means_no_rows(table):
    async with scoped_session(None) as session:
        assert await session.scalar(text(f"SELECT count(*) FROM {table}")) == 0  # noqa: S608


async def test_platform_admin_sees_no_hr_data(platform_admin):
    async with scoped_session(platform_admin) as session:
        assert await session.scalar(text("SELECT count(*) FROM employees")) == 0
        assert await session.scalar(text("SELECT count(*) FROM payslips")) == 0


async def test_cannot_write_into_another_tenant(ayesha, globex_tenant_id):
    with pytest.raises(DBAPIError, match="row-level security"):
        async with scoped_session(ayesha) as session:
            await session.execute(
                text(
                    "INSERT INTO leave_requests (tenant_id, employee_id, leave_type_id, "
                    "start_date, end_date, days, reason, status) "
                    "SELECT :t, :e, lt.id, current_date, current_date, 1, 'x', 'PENDING' "
                    "FROM leave_types lt LIMIT 1"
                ),
                {"t": globex_tenant_id, "e": ayesha.employee_id},
            )


@pytest.mark.parametrize(
    "statement", ["UPDATE audit_log SET outcome = 'SUCCESS'", "DELETE FROM audit_log"]
)
async def test_audit_log_is_append_only(ayesha, statement):
    with pytest.raises(DBAPIError, match="permission denied"):
        async with scoped_session(ayesha) as session:
            await session.execute(text(statement))


async def test_api_role_cannot_bypass_rls():
    async with scoped_session(None) as session:
        row = (
            await session.execute(
                text("SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user")
            )
        ).one()
    assert row == (False, False)
