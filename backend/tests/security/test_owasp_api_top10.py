"""Black-box checks mapped to the OWASP API Security Top 10 (2023).

Each test attacks the running API the way an outside caller would: through HTTP only,
with the seeded personas of two tenants (Acme, Globex). Behaviour already covered in
tests/integration (e.g. salary masking, self-approval) is not repeated here.
"""

import base64
import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest

from app.core.config import get_settings
from tests.integration.conftest import login, new_hire, onboard

API = "/api/v1"


def _b64(data: dict) -> str:
    return base64.urlsafe_b64encode(json.dumps(data).encode()).rstrip(b"=").decode()


def _claims(ctx, **overrides) -> dict:
    now = datetime.now(UTC)
    claims = {
        "sub": str(ctx.user_id),
        "role": ctx.role.value,
        "tid": str(ctx.tenant_id),
        "cid": str(ctx.company_id),
        "eid": str(ctx.employee_id),
        "iat": now.timestamp(),
        "exp": now + timedelta(minutes=5),
    }
    return claims | overrides


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# --- API2:2023 Broken Authentication -------------------------------------------------------


@pytest.mark.parametrize(
    "path", [f"{API}/auth/me", f"{API}/employees", f"{API}/payslips", f"{API}/audit"]
)
async def test_protected_routes_require_a_token(client, path):
    r = await client.get(path)
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "UNAUTHENTICATED"


async def test_unsigned_alg_none_token_is_rejected(client, ayesha):
    header = _b64({"alg": "none", "typ": "JWT"})
    payload = _claims(ayesha, role="HR_ADMIN")
    payload["exp"] = int(payload["exp"].timestamp())
    token = f"{header}.{_b64(payload)}."
    assert (await client.get(f"{API}/auth/me", headers=_bearer(token))).status_code == 401


async def test_token_signed_with_another_key_is_rejected(client, ayesha):
    token = jwt.encode(
        _claims(ayesha, role="HR_ADMIN"), "attacker-chosen-secret-0123456789abcdef", "HS256"
    )
    assert (await client.get(f"{API}/auth/me", headers=_bearer(token))).status_code == 401


async def test_expired_token_is_rejected(client, ayesha):
    past = datetime.now(UTC) - timedelta(hours=1)
    claims = _claims(ayesha, iat=past.timestamp(), exp=past + timedelta(minutes=1))
    token = jwt.encode(claims, get_settings().jwt_secret, "HS256")
    assert (await client.get(f"{API}/auth/me", headers=_bearer(token))).status_code == 401


async def test_validly_signed_but_escalated_role_is_rejected(client, ayesha):
    """Defence in depth: even with a leaked signing key the role must match the database."""
    token = jwt.encode(_claims(ayesha, role="HR_ADMIN"), get_settings().jwt_secret, "HS256")
    assert (await client.get(f"{API}/employees", headers=_bearer(token))).status_code == 401


async def test_token_for_deleted_or_unknown_user_is_rejected(client, ayesha):
    token = jwt.encode(_claims(ayesha, sub=str(uuid4())), get_settings().jwt_secret, "HS256")
    assert (await client.get(f"{API}/auth/me", headers=_bearer(token))).status_code == 401


@pytest.mark.parametrize("value", ["Bearer", "Bearer ", "Basic YWRtaW46YWRtaW4=", "Bearer a.b.c"])
async def test_malformed_authorization_headers_are_rejected(client, value):
    r = await client.get(f"{API}/auth/me", headers={"Authorization": value})
    assert r.status_code in (401, 403)
    assert r.status_code != 500


# --- API1:2023 Broken Object Level Authorization (BOLA / IDOR) -----------------------------


async def _colleague_id(client) -> str:
    sara = await login(client, "sara@acme.test")
    return (await client.get(f"{API}/employees?search=Hamza", headers=sara)).json()[0]["id"]


@pytest.mark.parametrize(
    "template",
    [
        "/employees/{id}",
        "/attendance?employee_id={id}",
        "/leave/balances?employee_id={id}",
        "/leave/requests?scope=mine&employee_id={id}",
    ],
)
async def test_employee_cannot_read_a_colleagues_records(client, template):
    target = await _colleague_id(client)
    ayesha = await login(client, "ayesha@acme.test")
    r = await client.get(API + template.format(id=target), headers=ayesha)
    # Either refused outright, or the filter is clamped to the caller's own rows.
    assert r.status_code in (200, 403, 404), r.text
    assert target not in r.text and "Hamza" not in r.text


@pytest.mark.parametrize(
    "template",
    ["/employees/{id}", "/attendance?employee_id={id}", "/leave/balances?employee_id={id}"],
)
async def test_hr_admin_cannot_reach_another_tenant(client, omar, template):
    sara = await login(client, "sara@acme.test")
    r = await client.get(API + template.format(id=omar.employee_id), headers=sara)
    assert r.status_code in (403, 404), r.text


async def test_cannot_cancel_or_decide_another_tenants_leave(client):
    nadia = await login(client, "nadia@globex.test")
    globex_requests = (
        await client.get(f"{API}/leave/requests?scope=company", headers=nadia)
    ).json()
    assert globex_requests, "seed data should contain Globex leave requests"
    target = globex_requests[0]["id"]

    sara = await login(client, "sara@acme.test")
    for action in ("approve", "reject", "cancel"):
        r = await client.post(f"{API}/leave/requests/{target}/{action}", json={}, headers=sara)
        assert r.status_code in (403, 404), f"{action}: {r.status_code} {r.text}"


async def test_audit_log_is_tenant_scoped_even_with_user_filter(client, omar):
    sara = await login(client, "sara@acme.test")
    page = (await client.get(f"{API}/audit?user_id={omar.user_id}", headers=sara)).json()
    assert page["items"] == []


# --- API5:2023 Broken Function Level Authorization -----------------------------------------


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("POST", "/employees", "new_hire"),
        ("PATCH", "/employees/{colleague}", {"salary": "999999"}),
        ("POST", "/employees/{colleague}/deactivate", None),
        ("POST", "/employees/{colleague}/reset-password", {"new_password": "Hacked@2026"}),
        ("GET", "/audit", None),
    ],
)
@pytest.mark.parametrize("persona", ["ayesha@acme.test", "bilal@acme.test"])
async def test_hr_only_functions_are_refused_to_other_roles(client, persona, method, path, body):
    colleague = await _colleague_id(client)
    headers = await login(client, persona)
    payload = new_hire() if body == "new_hire" else body
    r = await client.request(
        method, API + path.format(colleague=colleague), json=payload, headers=headers
    )
    assert r.status_code == 403, f"{persona} {method} {path}: {r.status_code}"


# --- API3:2023 Broken Object Property Level Authorization (mass assignment) ----------------


async def test_onboarding_ignores_injected_tenant_and_privilege_fields(client, globex_tenant_id):
    sara = await login(client, "sara@acme.test")
    created = await onboard(
        client,
        sara,
        tenant_id=str(globex_tenant_id),
        company_id=str(uuid4()),
        is_active=False,
        password_hash="$2b$12$attackercontrolled",
    )
    # Created in the caller's own tenant, active, and loginable with the real password.
    detail = (await client.get(f"{API}/employees/{created['id']}", headers=sara)).json()
    assert detail["is_active"] is True
    assert (await login(client, created["email"], "Welcome@2026"))["Authorization"]


async def test_patch_cannot_change_identity_fields(client):
    sara = await login(client, "sara@acme.test")
    created = await onboard(client, sara)
    r = await client.patch(
        f"{API}/employees/{created['id']}",
        json={"job_title": "Analyst", "email": "ceo@acme.test", "national_id": "11111-1111111-1"},
        headers=sara,
    )
    assert r.status_code == 200
    assert r.json()["email"] == created["email"]


async def test_employee_sees_no_salary_of_others_in_listing(client):
    ayesha = await login(client, "ayesha@acme.test")
    listing = (await client.get(f"{API}/employees", headers=ayesha)).json()
    for row in listing:
        assert "salary" not in row and "national_id" not in row


# --- API8:2023 Security Misconfiguration / injection ---------------------------------------

SQLI_PAYLOADS = [
    "' OR '1'='1",
    "'; DROP TABLE employees; --",
    '" OR ""="',
    "%' UNION SELECT password_hash FROM users --",
    "\\x00",
]


@pytest.mark.parametrize("payload", SQLI_PAYLOADS)
async def test_search_is_not_injectable(client, payload):
    ayesha = await login(client, "ayesha@acme.test")
    baseline = (await client.get(f"{API}/employees", headers=ayesha)).json()
    r = await client.get(f"{API}/employees", params={"search": payload}, headers=ayesha)
    assert r.status_code in (200, 422)
    if r.status_code == 200:
        assert len(r.json()) <= len(baseline)
        assert "$2b$" not in r.text


async def test_stored_markup_is_returned_as_inert_json(client):
    sara = await login(client, "sara@acme.test")
    created = await onboard(client, sara, full_name="<script>alert(1)</script> Doe")
    r = await client.get(f"{API}/employees/{created['id']}", headers=sara)
    assert r.headers["content-type"].startswith("application/json")
    assert r.headers["x-content-type-options"] == "nosniff"


@pytest.mark.parametrize(
    ("path", "params"),
    [
        ("/employees", {"search": "x" * 81}),
        ("/audit", {"limit": 10_000}),
        ("/audit", {"offset": -1}),
        ("/attendance", {"month": "2026-13-01"}),
        ("/leave/balances", {"year": 99999}),
    ],
)
async def test_out_of_range_input_is_rejected_not_crashed(client, path, params):
    sara = await login(client, "sara@acme.test")
    r = await client.get(API + path, params=params, headers=sara)
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_oversized_password_is_rejected_before_hashing(client):
    r = await client.post(
        f"{API}/auth/login", json={"email": "ayesha@acme.test", "password": "a" * 10_000}
    )
    assert r.status_code == 422


async def test_cors_does_not_trust_arbitrary_origins(client):
    r = await client.options(
        f"{API}/auth/login",
        headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"},
    )
    assert r.headers.get("access-control-allow-origin") != "https://evil.example"
    assert r.headers.get("access-control-allow-origin") != "*"


async def test_unknown_routes_and_methods_fail_closed(client):
    sara = await login(client, "sara@acme.test")
    assert (await client.delete(f"{API}/employees", headers=sara)).status_code == 405
    assert (await client.get(f"{API}/admin/debug", headers=sara)).status_code == 404
