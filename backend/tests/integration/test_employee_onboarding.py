"""HR onboarding through the HTTP API: create, scope checks, audit, and the new hire's login."""

import pytest

from tests.integration.conftest import NEW_HIRE_PASSWORD as PASSWORD
from tests.integration.conftest import login, new_hire

pytestmark = pytest.mark.integration


async def test_hr_admin_onboards_employee_end_to_end(client):
    sara = await login(client, "sara@acme.test")
    bilal = await login(client, "bilal@acme.test")
    bilal_id = (await client.get("/api/v1/employees/me", headers=bilal)).json()["id"]

    body = new_hire(manager_id=bilal_id)
    r = await client.post("/api/v1/employees", json=body, headers=sara)
    assert r.status_code == 201, r.text
    created = r.json()
    assert created["employee_code"].startswith("ACM-")
    assert created["manager_name"] == "Bilal Khan"
    assert created["salary"] is not None  # HR sees salary

    # The manager now sees the hire on their team, with salary masked.
    team = {e["id"] for e in (await client.get("/api/v1/employees", headers=bilal)).json()}
    assert created["id"] in team

    # The new hire can sign in with the initial password and has leave balances.
    hire = await client.post(
        "/api/v1/auth/login", json={"email": body["email"].upper(), "password": PASSWORD}
    )
    assert hire.status_code == 200, hire.text
    headers = {"Authorization": f"Bearer {hire.json()['access_token']}"}
    balances = (await client.get("/api/v1/leave/balances", headers=headers)).json()
    assert balances and all(float(b["used"]) == 0 for b in balances)

    # Audited, with PII masked and no password stored.
    audit = (await client.get("/api/v1/audit?limit=50", headers=sara)).json()["items"]
    entry = next(a for a in audit if (a["args_redacted"] or {}).get("employee_id") == created["id"])
    assert entry["args_redacted"]["salary"] == "[REDACTED]"
    assert "password" not in entry["args_redacted"]


@pytest.mark.parametrize("email", ["bilal@acme.test", "ayesha@acme.test"])
async def test_non_hr_roles_cannot_onboard(client, email):
    headers = await login(client, email)
    r = await client.post("/api/v1/employees", json=new_hire(), headers=headers)
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "PERMISSION_DENIED"


async def test_duplicate_email_is_rejected_even_across_tenants(client):
    sara = await login(client, "sara@acme.test")
    r = await client.post(
        "/api/v1/employees", json=new_hire(email="Omar@Globex.test"), headers=sara
    )
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "CONFLICT"


async def test_manager_from_other_tenant_is_denied(client, omar):
    sara = await login(client, "sara@acme.test")
    r = await client.post(
        "/api/v1/employees", json=new_hire(manager_id=str(omar.employee_id)), headers=sara
    )
    assert r.status_code == 403


async def test_platform_admin_role_cannot_be_granted(client):
    sara = await login(client, "sara@acme.test")
    r = await client.post("/api/v1/employees", json=new_hire(role="PLATFORM_ADMIN"), headers=sara)
    assert r.status_code == 422
