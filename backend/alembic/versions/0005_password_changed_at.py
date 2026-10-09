"""Track when a password last changed so older sessions can be revoked.

Revision ID: 0005
Revises: 0004
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_ROLE = "hr_app"


def upgrade() -> None:
    op.add_column("users", sa.Column("password_changed_at", sa.DateTime(timezone=True)))
    op.execute(f"GRANT UPDATE (password_changed_at) ON users TO {APP_ROLE}")


def downgrade() -> None:
    op.execute(f"REVOKE UPDATE (password_changed_at) ON users FROM {APP_ROLE}")
    op.drop_column("users", "password_changed_at")
