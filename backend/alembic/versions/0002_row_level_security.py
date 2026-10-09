"""Row-level security, least-privilege grants and the login lookup function.

Implements PR-1 (tenant_id isolation enforced by Postgres), PR-4 (document visibility),
FR-61 (append-only audit log) for the runtime role `hr_app`.

The session variables app.tenant_id / app.user_id / app.role are set per transaction from
the verified JWT (see app/db/session.py). If they are unset, every helper returns NULL and
every policy evaluates to false: the database fails closed.

Revision ID: 0002
Revises: 0001
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_ROLE = "hr_app"

# Tables whose rows all belong to exactly one tenant.
TENANT_TABLES = [
    "companies",
    "employees",
    "leave_types",
    "leave_balances",
    "leave_requests",
    "attendance",
    "payslips",
]

# Least privilege: the API may only do what the product needs.
GRANTS = {
    "tenants": "SELECT",
    "companies": "SELECT",
    "users": "SELECT",
    "employees": "SELECT",
    "leave_types": "SELECT",
    "leave_balances": "SELECT, UPDATE",
    "leave_requests": "SELECT, INSERT, UPDATE",
    "attendance": "SELECT",
    "payslips": "SELECT",
    "documents": "SELECT",
    "doc_chunks": "SELECT",
    "conversations": "SELECT, INSERT, UPDATE, DELETE",
    "messages": "SELECT, INSERT, UPDATE",
    "action_proposals": "SELECT, INSERT, UPDATE",
    # Append-only: no UPDATE or DELETE grant exists, so history cannot be rewritten.
    "audit_log": "SELECT, INSERT",
}

ALL_RLS_TABLES = [
    *TENANT_TABLES,
    "tenants",
    "users",
    "documents",
    "doc_chunks",
    "conversations",
    "messages",
    "action_proposals",
    "audit_log",
]


def upgrade() -> None:
    # --- Context helpers (STABLE SQL functions are inlined by the planner) -------------------
    op.execute(
        """
        CREATE FUNCTION app_current_tenant() RETURNS uuid LANGUAGE sql STABLE AS
          $$ SELECT NULLIF(current_setting('app.tenant_id', true), '')::uuid $$;
        CREATE FUNCTION app_current_user() RETURNS uuid LANGUAGE sql STABLE AS
          $$ SELECT NULLIF(current_setting('app.user_id', true), '')::uuid $$;
        CREATE FUNCTION app_current_role() RETURNS text LANGUAGE sql STABLE AS
          $$ SELECT NULLIF(current_setting('app.role', true), '') $$;
        """
    )

    for table in ALL_RLS_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")

    # --- Plain tenant isolation -----------------------------------------------------------
    for table in TENANT_TABLES:
        op.execute(
            f"""
            CREATE POLICY tenant_isolation ON {table}
              USING (tenant_id = app_current_tenant())
              WITH CHECK (tenant_id = app_current_tenant())
            """
        )

    op.execute(
        "CREATE POLICY tenant_isolation ON tenants USING (id = app_current_tenant())"
    )

    # A platform admin has no tenant but must still be able to read their own user row.
    op.execute(
        """
        CREATE POLICY tenant_isolation ON users
          USING (tenant_id = app_current_tenant() OR id = app_current_user())
        """
    )

    # --- Knowledge base: global docs + own tenant docs, filtered by visibility (PR-4) -----
    for table in ("documents", "doc_chunks"):
        op.execute(
            f"""
            CREATE POLICY visibility_filter ON {table}
              USING (
                (tenant_id IS NULL OR tenant_id = app_current_tenant())
                AND (visibility <> 'role:HR_ADMIN' OR app_current_role() = 'HR_ADMIN')
              )
            """
        )

    # --- Conversations are private to their author ----------------------------------------
    for table in ("conversations", "action_proposals"):
        op.execute(
            f"""
            CREATE POLICY owner_only ON {table}
              USING (user_id = app_current_user()
                     AND tenant_id IS NOT DISTINCT FROM app_current_tenant())
              WITH CHECK (user_id = app_current_user()
                          AND tenant_id IS NOT DISTINCT FROM app_current_tenant())
            """
        )
    op.execute(
        """
        CREATE POLICY owner_only ON messages
          USING (conversation_id IN (SELECT id FROM conversations))
          WITH CHECK (conversation_id IN (SELECT id FROM conversations)
                      AND tenant_id IS NOT DISTINCT FROM app_current_tenant())
        """
    )

    # --- Audit log: tenant-scoped reads, platform admin reads all, inserts must match ------
    op.execute(
        """
        CREATE POLICY audit_read ON audit_log FOR SELECT
          USING (tenant_id = app_current_tenant() OR app_current_role() = 'PLATFORM_ADMIN');
        CREATE POLICY audit_append ON audit_log FOR INSERT
          WITH CHECK (tenant_id IS NOT DISTINCT FROM app_current_tenant()
                      AND user_id = app_current_user());
        """
    )

    # --- Login lookup: the only path that reads a user before a tenant is known ------------
    op.execute(
        """
        CREATE FUNCTION app_auth_lookup(p_email text)
        RETURNS TABLE (id uuid, tenant_id uuid, company_id uuid, employee_id uuid,
                       role text, password_hash text, is_active boolean)
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$
          SELECT u.id, u.tenant_id, u.company_id, u.employee_id,
                 u.role, u.password_hash, u.is_active
          FROM users u WHERE u.email = lower(p_email)
        $$;
        REVOKE ALL ON FUNCTION app_auth_lookup(text) FROM PUBLIC;
        """
    )
    op.execute(f"GRANT EXECUTE ON FUNCTION app_auth_lookup(text) TO {APP_ROLE}")

    for table, privileges in GRANTS.items():
        op.execute(f"GRANT {privileges} ON {table} TO {APP_ROLE}")


def downgrade() -> None:
    for table in GRANTS:
        op.execute(f"REVOKE ALL ON {table} FROM {APP_ROLE}")
    op.execute("DROP FUNCTION IF EXISTS app_auth_lookup(text)")

    for table in ALL_RLS_TABLES:
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
        for policy in (
            "tenant_isolation",
            "visibility_filter",
            "owner_only",
            "audit_read",
            "audit_append",
        ):
            op.execute(f"DROP POLICY IF EXISTS {policy} ON {table}")

    op.execute(
        "DROP FUNCTION IF EXISTS app_current_tenant(); "
        "DROP FUNCTION IF EXISTS app_current_user(); "
        "DROP FUNCTION IF EXISTS app_current_role();"
    )
