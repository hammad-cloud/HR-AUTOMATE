# Test strategy

How HR Copilot is verified, what each layer proves, and how to run it. Results of the most
recent runs are in [SECURITY-REPORT.md](SECURITY-REPORT.md) and
[PERFORMANCE-REPORT.md](PERFORMANCE-REPORT.md).

## Test pyramid

| Layer | Tool | Location | What it proves | Runs in CI |
|---|---|---|---|---|
| Unit | pytest | `backend/tests/unit` | Policy matrix, leave rules, password hashing, login throttle | ✅ |
| Integration | pytest + httpx (ASGI) | `backend/tests/integration` | API behaviour against real Postgres: RLS isolation, permissions, lifecycle | ✅ |
| Security (functional) | pytest | `backend/tests/security` | OWASP API Top 10 attacks over HTTP, input robustness, headers, brute force | ✅ |
| SAST | Bandit, Ruff `S` rules | `security/run-scans.sh sast` | No insecure code patterns (medium+) in `app/` | ✅ |
| Dependency (SCA) | pip-audit, npm audit | `security/run-scans.sh deps` | No known CVEs in shipped dependencies | ✅ |
| Secret scanning | gitleaks | `security/run-scans.sh secrets` | No credentials anywhere in git history | ✅ |
| DAST | OWASP ZAP API scan | `security/run-scans.sh dast` | Running API resists ~110 active/passive attack rules | manual |
| Smoke (perf) | k6 | `perf/k6/smoke.js` | Every user journey works end to end | ✅ |
| Performance baseline | k6 | `perf/k6/performance.js` | Per-endpoint latency at a fixed request rate | manual |
| Load | k6 | `perf/k6/load.js` | SLOs hold at expected peak (50 concurrent users) | manual |
| Stress | k6 | `perf/k6/stress.js` | Where the system degrades and how it fails | manual |
| Spike | k6 | `perf/k6/spike.js` | Sudden surge is absorbed and the system recovers | manual |
| Soak | k6 | `perf/k6/soak.js` | No leak or drift over a long run | manual |

DAST and the heavier k6 runs are manual: they take minutes to hours, need a dedicated
environment, and DAST writes junk records. CI runs everything that is fast and deterministic.

## Service level objectives

Used as k6 thresholds (`perf/k6/lib/config.js`); a run that misses one exits non-zero.

| Metric | Target (normal load) |
|---|---|
| Read requests p95 | < 500 ms |
| Read requests p99 | < 1000 ms |
| Write requests p95 | < 800 ms |
| Error rate | < 1 % |
| Single endpoint p95 at 10 rps (baseline) | < 300 ms |
| Sign-in p95 at 2 rps | < 1500 ms (bcrypt cost 12 is intentionally slow) |

## Security test approach

Mapped to the **OWASP API Security Top 10 (2023)** and OWASP ASVS:

- **API1 BOLA** - cross-employee and cross-tenant object access, by id, in every module
- **API2 Broken authentication** - forged/expired/`alg=none` tokens, role escalation in a
  validly signed token, brute force (throttled, 429), uniform login errors
- **API3 Property-level authorization** - mass assignment, immutable identity fields,
  sensitive fields absent from listings
- **API4 Resource consumption** - bounded page sizes, field lengths, password length before
  bcrypt, login throttling
- **API5 Function-level authorization** - HR-only operations refused to other roles
- **API8 Misconfiguration** - security headers, CORS, error bodies without internals,
  injection payloads, NUL bytes, malformed JSON

Database-level isolation (Postgres RLS) is proven separately in
`backend/tests/integration/test_rls.py`, below the API.

## How to run

```bash
docker compose up -d db backend
docker compose exec backend python -m app.seed.seed     # once

# Functional + security tests
docker compose exec backend pytest                      # everything (190 tests)
docker compose exec backend pytest -m security          # security suite only
docker compose exec backend pytest -m "not integration" # unit only, no database

# Scanners (reports in security/reports/)
./security/run-scans.sh            # sast, deps, secrets, dast
./security/run-scans.sh sast       # or one layer at a time

# Performance (production-like API: 4 workers, no reloader)
alias perf='docker compose -f docker-compose.yml -f perf/docker-compose.perf.yml'
perf up -d db backend
perf --profile perf run --rm k6 run k6/smoke.js
perf --profile perf run --rm k6 run k6/performance.js
perf --profile perf run --rm k6 run k6/load.js
perf --profile perf run --rm k6 run k6/stress.js
perf --profile perf run --rm k6 run k6/spike.js
perf --profile perf run --rm -e SOAK_DURATION=4h k6 run k6/soak.js
```

Run security and performance tests only against local or disposable environments. DAST and
stress tests generate attack traffic and data.
