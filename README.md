# HR Copilot

**A permission-aware AI assistant for a multi-tenant HRMS.** Employees, managers and HR admins
ask questions and take actions in plain language, and the assistant can never leak data across
tenants or roles, act without confirmation, or invent facts.

The defining principle: **trust is enforced in code, not in prompts.** Postgres row-level
security, API-layer authorization and tool allow-lists hold even if the language model is
fully compromised by prompt injection.

> Status: **Milestones 1–2 complete** (HRMS foundation, security model, scoped APIs, UI).
> The assistant layer (agent loop, RAG, voice, red-team evals) builds on this foundation next.
> See [Roadmap](#roadmap).

---

## Highlights

| Concern | How it's handled |
|---|---|
| Tenant isolation | Postgres **RLS** on every tenant table; API connects as a non-owner, `NOBYPASSRLS` role; context set per transaction from the verified JWT only |
| Role & ownership scope | Pure, unit-tested policy engine encoding the BRD's role-permission matrix (own / team / company / all-tenants) |
| IDOR protection | Every referenced ID is re-loaded through RLS and re-authorized; foreign records are indistinguishable from missing ones |
| Self-approval | Prohibited regardless of role (PR-6), enforced in the policy layer |
| Salary privacy | Masked at the serializer for anyone but the owner and same-company HR (PR-5) |
| Auditability | Append-only `audit_log` (no UPDATE/DELETE grant). **Every** denial is audited centrally, with PII redacted |
| Idempotency | `Idempotency-Key` on writes; double-submits create exactly one row |
| Least privilege | The API role gets only the grants the product needs (e.g. `SELECT` only on payslips) |
| Login before tenant is known | Narrow `SECURITY DEFINER` lookup function instead of an RLS bypass |
| Frontend tokens | JWT in an **httpOnly** cookie; only Next.js server code (BFF) talks to the API |

## Architecture

```
 Browser ──► Next.js 16 (BFF: server components + server actions, httpOnly session)
                 │  Bearer JWT (server-side only)
                 ▼
            FastAPI ── JWT verify ─► RequestContext{tenant, company, user, role}
                 │                        │
                 │        services ──► policy engine (BRD 4.1 matrix, PR-1..7)
                 ▼                        │
            Postgres 16 + pgvector  ◄─────┘   SET LOCAL app.tenant_id / user_id / role
              RLS on every table · append-only audit_log · least-privilege grants
```

Details: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) · [docs/PERMISSIONS.md](docs/PERMISSIONS.md) ·
[docs/RUNBOOK.md](docs/RUNBOOK.md) · [ADRs](docs/adr)

## Quick start

Prerequisites: Docker Desktop, Node 20+ (for local frontend dev).

```bash
cp .env.example .env                                           # then fill in every value
docker compose up -d db backend                                # Postgres + API (runs migrations)
docker compose exec backend python -m app.seed.seed            # demo tenants and personas
cd frontend && npm install && npm run dev                      # http://localhost:3000
```

For `npm run dev`, put `DEMO_PASSWORD` in `frontend/.env.local` too so the persona buttons work.

Or run everything in containers: `docker compose up --build` (API docs at http://localhost:8000/docs).

### Demo personas (password: your `DEMO_PASSWORD`, or one click on the login page)

| Persona | Email | Role | Shows |
|---|---|---|---|
| Ayesha | `ayesha@acme.test` | Employee, Acme | Own leave, attendance, payslips |
| Bilal | `bilal@acme.test` | Manager, Acme | Team approvals; can't approve his own leave |
| Sara | `sara@acme.test` | HR Admin, Acme | Company-wide data and the audit log |
| Omar | `omar@globex.test` | Employee, Globex | Proves tenant isolation |
| Platform | `admin@platform.test` | Platform Admin | Audit metadata across tenants, zero HR data |

## Quality gates

```bash
docker compose exec backend pytest --cov=app        # 82 tests: policy matrix, rules, RLS proofs, API
docker compose exec backend ruff check .
cd frontend && npx eslint src && npm run build
```

The integration suite proves isolation **at the database level**: with Acme's context, an
explicit `WHERE tenant_id = <globex>` returns zero rows on every tenant table, writes into
another tenant are rejected by RLS, `UPDATE`/`DELETE` on the audit log fail with
`permission denied`, and the API role is verified to be neither superuser nor `BYPASSRLS`.

## Repository layout

```
backend/     FastAPI service (api · core · db · models · permissions · schemas · services · seed)
  alembic/   migrations: schema (0001) and RLS + grants + login function (0002)
  tests/     unit/ (pure) and integration/ (real Postgres)
frontend/    Next.js 16 App Router + Tailwind v4 + shadcn/ui
  src/app/   (app)/ authenticated routes · login · logout
  src/lib/   api client (server-only) · server actions · session · route registry
infra/       Postgres bootstrap (restricted app role)
docs/        architecture, permissions, runbook, ADRs
```

## Roadmap

| Milestone | Scope | Status |
|---|---|---|
| 1 | Repo, Docker, schema, RLS policies; cross-tenant SELECT returns 0 rows | ✅ |
| 2 | Auth, seed data, HRMS screens with scoped data | ✅ |
| 3 | Agent loop + read tools + streaming chat widget (Ctrl+K) | Next |
| 4 | Write tools, proposals, confirmation cards, idempotency | |
| 5 | RAG ingestion, tenant-filtered retrieval, citations | |
| 6 | Audit enrichment (tokens, latency, cost), redaction | Partly done |
| 7 | Voice: push-to-talk STT, TTS | |
| 8 | Eval + 30-case red-team suite as a CI hard gate; metrics dashboard | |
| 9 | Deployment, demo video | |

The service layer was designed for the assistant from day one: agent tools will call the same
`services/*` functions with the same `RequestContext`, so the model gets no capability the
user doesn't already have.
