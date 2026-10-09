"""End-to-end permission scenarios through the HTTP API (US-03, US-05, US-07, RT-02/05/08)."""

import uuid
from datetime import date, timedelta

import pytest

from tests.integration.conftest import login

pytestmark = pytest.mark.integration


async def test_login_rejects_bad_password(client):
    r = await client.post(
        "/api/v1/auth/login", json={"email": "ayesha@acme.test", "password": "nope"}
    )
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "UNAUTHENTICATED"


async def test_cross_tenant_employee_id_is_denied_and_audited(client, ayesha):
    omar = await login(client, "omar@globex.test")
    r = await client.get(f"/api/v1/payslips?employee_id={ayesha.employee_id}", headers=omar)
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "PERMISSION_DENIED"
    assert "Ayesha" not in r.text

    nadia = await login(client, "nadia@globex.test")
    audit = await client.get("/api/v1/audit?outcome=PERMISSION_DENIED", headers=nadia)
    assert audit.status_code == 200
    target = str(ayesha.employee_id)
    assert any(
        (item["args_redacted"] or {}).get("employee_id") == target for item in audit.json()["items"]
    )


async def test_acme_hr_never_sees_globex_audit(client, globex_tenant_id):
    sara = await login(client, "sara@acme.test")
    items = (await client.get("/api/v1/audit?limit=200", headers=sara)).json()["items"]
    assert all(item["tenant_id"] != str(globex_tenant_id) for item in items)


async def test_employee_cannot_read_colleague_payslip(client):
    sara = await login(client, "sara@acme.test")
    colleague = (await client.get("/api/v1/employees?search=Hamza", headers=sara)).json()[0]
    ayesha = await login(client, "ayesha@acme.test")
    r = await client.get(f"/api/v1/payslips?employee_id={colleague['id']}", headers=ayesha)
    assert r.status_code == 403


async def test_manager_salary_view_is_masked(client):
    bilal = await login(client, "bilal@acme.test")
    team = (await client.get("/api/v1/employees", headers=bilal)).json()
    report = next(e for e in team if e["full_name"] == "Hamza Raza")
    detail = (await client.get(f"/api/v1/employees/{report['id']}", headers=bilal)).json()
    assert detail["salary"] is None and detail["salary_masked"] is True


async def test_manager_cannot_approve_own_leave(client):
    bilal = await login(client, "bilal@acme.test")
    mine = (
        await client.get("/api/v1/leave/requests?scope=mine&status=PENDING", headers=bilal)
    ).json()
    assert mine, "seed data should contain a pending request for Bilal"
    r = await client.post(f"/api/v1/leave/requests/{mine[0]['id']}/approve", json={}, headers=bilal)
    assert r.status_code == 403
    assert "own request" in r.json()["error"]["message"]


async def test_manager_sees_only_direct_reports_in_approvals(client):
    bilal = await login(client, "bilal@acme.test")
    approvals = (await client.get("/api/v1/leave/approvals", headers=bilal)).json()
    team = {e["id"] for e in (await client.get("/api/v1/employees", headers=bilal)).json()}
    assert approvals
    assert all(a["employee_id"] in team for a in approvals)


async def test_apply_leave_is_idempotent(client):
    ayesha = await login(client, "ayesha@acme.test")
    start = date.today() + timedelta(days=40)
    while start.weekday() != 2:
        start += timedelta(days=1)
    if start.year != date.today().year:
        pytest.skip("Too close to year end for a same-year request")
    body = {"leave_type_code": "SICK", "start_date": str(start), "end_date": str(start)}
    headers = {**ayesha, "Idempotency-Key": uuid.uuid4().hex}

    first = await client.post("/api/v1/leave/requests", json=body, headers=headers)
    second = await client.post("/api/v1/leave/requests", json=body, headers=headers)
    assert first.status_code == 201, first.text
    assert second.json()["id"] == first.json()["id"]

    cancel = await client.post(
        f"/api/v1/leave/requests/{first.json()['id']}/cancel", headers=ayesha
    )
    assert cancel.json()["status"] == "CANCELLED"


async def test_platform_admin_sees_metadata_only(client):
    admin = await login(client, "admin@platform.test")
    page = (await client.get("/api/v1/audit", headers=admin)).json()
    assert page["items"], "expected audit entries from earlier tests"
    assert "user_message" not in page["items"][0]
    assert "args_redacted" not in page["items"][0]
