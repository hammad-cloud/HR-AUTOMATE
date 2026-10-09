# Architecture

## Components

| Component | Technology | Responsibility |
|---|---|---|
| Web app | Next.js 16 (App Router), Tailwind v4, shadcn/ui | HRMS screens; Backend-for-Frontend holding the session in an httpOnly cookie |
| API | FastAPI, SQLAlchemy 2 (async), Pydantic v2 | Authentication, authorization, business rules, audit |
| Database | PostgreSQL 16 + pgvector | System of record, RLS isolation, vector search (RAG milestone) |
| Migrations | Alembic | Schema, RLS policies, grants, security-definer functions |

## Request lifecycle (read)

1. The browser requests a page. Next.js `proxy.ts` makes an optimistic cookie check only.
2. A server component calls `apiFetch()` (`server-only`), attaching the JWT from the httpOnly cookie.
3. FastAPI's `get_context` verifies the JWT and builds an immutable `RequestContext`.
4. `get_session` opens one transaction and runs
   `set_config('app.tenant_id' | 'app.user_id' | 'app.role', …, is_local => true)`.
   Values come only from the verified token. They are transaction-local, so they can't leak
   across pooled connections.
5. The service loads the target record **through RLS**, then asks the policy engine for a decision.
6. Response DTOs mask fields the caller may not see (salary).
7. On `PERMISSION_DENIED`, a global exception handler writes an audit row in a separate
   transaction (so the denial survives the request rollback) and returns a typed error.

## Request lifecycle (write)

Same as above, plus:

- Business rules are re-checked inside the transaction with `SELECT … FOR UPDATE` on the request
  and balance rows (overlap, balance including pending days, status transitions, self-approval).
- An optional `Idempotency-Key` header is stored with a unique constraint per tenant; a retry
  returns the original row.
- The audit row is written in the **same** transaction as the change, so an action can't commit
  without its audit record.

## Defence in depth

| Layer | Control | Where |
|---|---|---|
| Identity | JWT verified; context never taken from client or model input | `app/core/security.py`, `app/api/deps.py` |
| Policy | Role/scope matrix, self-approval ban, salary visibility | `app/permissions/policy.py` |
| Object scope | Every ID re-loaded through RLS and re-authorized (IDOR) | `app/services/employee_service.py` |
| Database | RLS on all tenant tables; non-owner `NOBYPASSRLS` role; least-privilege grants | `alembic/versions/0002_*` |
| Audit | Append-only (no UPDATE/DELETE grant); central denial auditing; PII redaction | `app/main.py`, `app/core/redaction.py` |
| Errors | Typed error envelope with request id; no stack traces to clients | `app/main.py` |
| Frontend | httpOnly + SameSite cookie, server-only API client, security headers | `frontend/src/lib/api/client.ts`, `next.config.ts` |

## Assistant layer (upcoming milestones)

The agent orchestrator will sit beside the REST routers and reuse the service layer:

```
chat/voice ─► gateway (rate limit, input guard) ─► router (intent → model tier)
                └► tool-calling loop (≤ 8 steps) ─► tool executor
                        ├─ read tools  → services/* with the caller's RequestContext
                        ├─ write tools → action_proposals (PENDING, 10-min expiry) → confirm card
                        └─ search_knowledge → pgvector, filtered by RLS on doc_chunks
```

The `conversations`, `messages`, `action_proposals`, `documents` and `doc_chunks` tables and their
RLS policies already exist (owner-only conversations, visibility-filtered documents).
