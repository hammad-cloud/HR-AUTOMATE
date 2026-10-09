"""Column-level UPDATE grants for editing, deactivating employees and changing passwords.

Least privilege: the API role can change only these columns. Identity data (email,
national_id, employee_code, tenant/company ids) stays immutable even if the API is compromised.
Row scope is still enforced by the existing tenant_isolation policies.

Revision ID: 0004
Revises: 0003
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_ROLE = "hr_app"
COLUMNS = {
    "employees": "full_name, department, job_title, manager_id, salary, is_active",
    "users": "role, is_active, password_hash",
}


def upgrade() -> None:
    for table, columns in COLUMNS.items():
        op.execute(f"GRANT UPDATE ({columns}) ON {table} TO {APP_ROLE}")


def downgrade() -> None:
    for table, columns in COLUMNS.items():
        op.execute(f"REVOKE UPDATE ({columns}) ON {table} FROM {APP_ROLE}")
