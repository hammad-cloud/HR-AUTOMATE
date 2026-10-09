# ADR 0001: Postgres row-level security for tenant isolation

- **Status:** Accepted
- **Date:** 2026-10-06

## Context

HR Copilot is multi-tenant, and an LLM will drive data access. A single missing
`WHERE tenant_id = …` in application code, or a prompt-injected tool argument, must not expose
another customer's data (BRD NFR-01, BO-3).

## Options

1. **Application-level filtering only.** Simple, but every query is a potential leak.
2. **Database per tenant.** Strong isolation, but heavy operations for a 2-tenant demo and awkward for cross-tenant platform metadata.
3. **Shared schema + Postgres RLS**, with the API connecting as a restricted role.

## Decision

Option 3. Every tenant table carries `tenant_id` with an RLS policy keyed on
`current_setting('app.tenant_id')`. The value is set per transaction (`set_config(…, true)`)
from the verified JWT. The API connects as `hr_app` (not owner, `NOBYPASSRLS`) with
least-privilege grants. Login uses a narrow `SECURITY DEFINER` lookup function rather than a
bypass. Application-level checks remain as a second layer.

## Consequences

- Isolation holds even with application bugs; integration tests prove it directly in SQL.
- With no context set, queries return nothing, so the database fails closed.
- Every new table needs a policy and a grant (documented in the runbook and checked by tests).
- Seeding and migrations run as the owner role, which bypasses RLS by design.
