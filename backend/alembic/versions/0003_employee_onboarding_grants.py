"""Let the API role onboard employees (create employee, login account, leave balances).

The existing tenant_isolation policies already carry WITH CHECK (users falls back to its
USING clause), so inserted rows must belong to the caller's tenant.

Revision ID: 0003
Revises: 0002
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_ROLE = "hr_app"
TABLES = ["employees", "users", "leave_balances"]


def upgrade() -> None:
    for table in TABLES:
        op.execute(f"GRANT INSERT ON {table} TO {APP_ROLE}")


def downgrade() -> None:
    for table in TABLES:
        op.execute(f"REVOKE INSERT ON {table} FROM {APP_ROLE}")
