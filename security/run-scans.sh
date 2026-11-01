#!/usr/bin/env bash
# Automated security scans for HR Copilot.
#
#   ./security/run-scans.sh [sast|deps|secrets|dast|all]   (default: all)
#
# Needs Docker and the stack running (docker compose up -d db backend).
# Reports are written to security/reports/ (git-ignored).
#
# DAST sends attack traffic and creates records. Run it only against a local or
# disposable environment - never against production.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORTS="$ROOT/security/reports"
NETWORK="${COMPOSE_NETWORK:-hr-copilot_default}"
API_URL="${API_URL:-http://backend:8000}"
ZAP_IMAGE="zaproxy/zap-stable:2.16.1"
GITLEAKS_IMAGE="zricethezav/gitleaks:v8.24.3"
export MSYS_NO_PATHCONV=1 # keep Git Bash on Windows from rewriting container paths

mkdir -p "$REPORTS"
cd "$ROOT"

sast() {
  echo "==> SAST: Bandit (Python) + Ruff security rules"
  docker compose exec -T backend sh -c \
    "bandit -r app --severity-level medium -f json -o /tmp/bandit.json; rc=\$?; cat /tmp/bandit.json; exit \$rc" \
    >"$REPORTS/bandit.json" && echo "    Bandit: no medium/high issues"
  docker compose exec -T backend ruff check app --select S --quiet && echo "    Ruff S-rules: clean"
}

deps() {
  echo "==> Dependency audit: pip-audit (backend) + npm audit (frontend)"
  docker compose exec -T backend sh -c \
    "pip-audit --skip-editable --format json" \
    >"$REPORTS/pip-audit.json" && echo "    pip-audit: no known vulnerabilities"
  (cd frontend && npm audit --audit-level=high --json >"$REPORTS/npm-audit.json") &&
    echo "    npm audit: no high/critical advisories"
}

secrets() {
  echo "==> Secret scan: gitleaks over the full git history"
  docker run --rm -v "$ROOT:/repo" "$GITLEAKS_IMAGE" git /repo \
    --no-banner --redact --gitleaks-ignore-path /repo/.gitleaksignore \
    --report-format json --report-path /repo/security/reports/gitleaks.json
}

dast() {
  echo "==> DAST: OWASP ZAP API scan (authenticated as HR admin) against $API_URL"
  local password token
  password="$(grep -E '^DEMO_PASSWORD=' .env | cut -d= -f2-)"
  token="$(docker compose exec -T backend python -c "
import json, urllib.request
req = urllib.request.Request('http://localhost:8000/api/v1/auth/login',
    data=json.dumps({'email': 'sara@acme.test', 'password': '$password'}).encode(),
    headers={'Content-Type': 'application/json'})
print(json.load(urllib.request.urlopen(req))['access_token'])")"

  docker run --rm --network "$NETWORK" -v "$ROOT/security:/zap/wrk:rw" -u root "$ZAP_IMAGE" \
    zap-api-scan.py -t "$API_URL/openapi.json" -f openapi \
    -c zap/rules.tsv -r reports/zap-report.html -J reports/zap-report.json -I \
    -z "-config replacer.full_list(0).description=auth \
        -config replacer.full_list(0).enabled=true \
        -config replacer.full_list(0).matchtype=REQ_HEADER \
        -config replacer.full_list(0).matchstr=Authorization \
        -config replacer.full_list(0).regex=false \
        -config replacer.full_list(0).replacement=Bearer\ $token"
}

case "${1:-all}" in
  sast) sast ;;
  deps) deps ;;
  secrets) secrets ;;
  dast) dast ;;
  all) sast; deps; secrets; dast ;;
  *) echo "usage: $0 [sast|deps|secrets|dast|all]" >&2; exit 2 ;;
esac
