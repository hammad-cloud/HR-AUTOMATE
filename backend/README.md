# HR Copilot API

FastAPI service for the HR Copilot HRMS. See the [root README](../README.md) for the full picture.

## Layout

```
app/
  api/            HTTP layer: dependencies, versioned routers (thin, no business logic)
  core/           config, security (JWT/bcrypt), request context, errors, logging, redaction
  db/             SQLAlchemy base + RLS-aware session factory
  models/         ORM models (organization, hr, assistant)
  permissions/    pure role-permission policy (BRD section 4.1)
  schemas/        Pydantic request/response models
  services/       business logic, reused by the REST API and (later) the agent tools
  seed/           deterministic demo data for two tenants
alembic/          migrations, including RLS policies and grants
tests/
  unit/           pure tests (policy, rules, redaction) that need no database
  integration/    tests against a real Postgres, including the RLS isolation proof
```

## Common commands

```bash
docker compose up -d db                     # start Postgres 16 + pgvector
pip install -e ".[dev]"                     # local dev install
alembic upgrade head                        # apply migrations (owner role)
python -m app.seed.seed                     # load demo tenants
uvicorn app.main:app --reload               # http://localhost:8000/docs
pytest -m "not integration"                 # unit tests
pytest -m integration                       # needs the database
ruff check . && mypy app
```
