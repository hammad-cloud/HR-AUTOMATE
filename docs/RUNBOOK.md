# Runbook

## Local environment

| Service | URL | Notes |
|---|---|---|
| Web app | http://localhost:3000 | `npm run dev` in `frontend/` or the `frontend` compose service |
| API + OpenAPI docs | http://localhost:8000/docs | hot-reloads from `backend/` |
| Postgres | `localhost:5440` | host port set by `DB_HOST_PORT` to avoid clashing with local installs |

## Common tasks

```bash
docker compose up -d db backend                     # start
docker compose logs -f backend                      # JSON logs with request ids
docker compose exec backend alembic upgrade head    # migrate
docker compose exec backend python -m app.seed.seed # reset demo data (truncates!)
docker compose exec backend pytest                  # tests
docker compose down                                 # stop (keeps data)
docker compose down -v                              # stop and DELETE the database volume
```

New migration:

```bash
docker compose exec backend alembic revision --autogenerate -m "describe change"
```

Any new tenant table **must** get `ENABLE ROW LEVEL SECURITY`, a `tenant_isolation` policy and an
explicit grant to `hr_app`. Add it to `TENANT_TABLES` in `tests/integration/test_rls.py` so the
isolation proof covers it.

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `port is already allocated` on db start | Another Postgres uses the port. Set `DB_HOST_PORT` in `.env` |
| API returns empty lists for everything | RLS context missing. Check that the request goes through `get_session`, not a raw session |
| `permission denied for table …` | New table without a grant to `hr_app`. Add it in a migration |
| Login fails for every persona | Seed not run, or `JWT_SECRET` changed (old cookies are invalid; the app redirects via `/logout`) |
| `failed to resolve host 'db'` | Run commands through `docker compose run/exec`, or use `localhost:5440` from the host |

## Incident tracing

Every response carries `x-request-id`. The same id appears in the API's JSON logs and in
`audit_log.request_id`, so a user-reported error can be traced end to end.
