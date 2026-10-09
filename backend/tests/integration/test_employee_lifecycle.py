"""Edit, deactivate / reactivate and password change through the HTTP API."""

from datetime import date, timedelta

import pytest

from tests.integration.conftest import NEW_HIRE_PASSWORD, login, onboard

pytestmark = pytest.mark.integration


async def _status(client, headers) -> int:
    return (await client.get("/api/v1/auth/me", headers=headers)).status_code


# --- Edit ------------------------------------------------------------------------------------


async def test_hr_edits_job_details_and_salary(client):
    sara = await login(client, "sara@acme.test")
    hire = await onboard(client, sara)
    r = await client.patch(
        f"/api/v1/employees/{hire['id']}",
        json={"job_title": "  Senior   Engineer ", "salary": "260000"},
        headers=sara,
    )
    assert r.status_code == 200, r.text
    assert r.json()["job_title"] == "Senior Engineer"
    assert float(r.json()["salary"]) == 260000
    assert r.json()["department"] == hire["department"]  # untouched fields stay


async def test_role_change_ends_the_users_current_session(client):
    sara = await login(client, "sara@acme.test")
    hire = await onboard(client, sara)
    hire_session = await login(client, hire["email"], NEW_HIRE_PASSWORD)
    assert await _status(client, hire_session) == 200

    r = await client.patch(
        f"/api/v1/employees/{hire['id']}", json={"role": "MANAGER"}, headers=sara
    )
    assert r.json()["role"] == "MANAGER"
    assert await _status(client, hire_session) == 401

    fresh = await login(client, hire["email"], NEW_HIRE_PASSWORD)
    assert (await client.get("/api/v1/auth/me", headers=fresh)).json()["role"] == "MANAGER"


async def test_hr_cannot_edit_own_record(client):
    sara = await login(client, "sara@acme.test")
    me = (await client.get("/api/v1/employees/me", headers=sara)).json()
    r = await client.patch(f"/api/v1/employees/{me['id']}", json={"salary": "999999"}, headers=sara)
    assert r.status_code == 403
    assert "your own employment record" in r.json()["error"]["message"]


async def test_manager_cannot_edit_direct_report(client):
    bilal = await login(client, "bilal@acme.test")
    team = (await client.get("/api/v1/employees?search=Hamza", headers=bilal)).json()
    r = await client.patch(
        f"/api/v1/employees/{team[0]['id']}", json={"job_title": "CTO"}, headers=bilal
    )
    assert r.status_code == 403


async def test_reporting_loops_are_rejected(client):
    sara = await login(client, "sara@acme.test")
    lead = await onboard(client, sara, full_name="Loop Lead")
    report = await onboard(client, sara, full_name="Loop Report", manager_id=lead["id"])

    loop = await client.patch(
        f"/api/v1/employees/{lead['id']}", json={"manager_id": report["id"]}, headers=sara
    )
    assert loop.status_code == 422
    assert loop.json()["error"]["code"] == "BUSINESS_RULE_VIOLATION"

    itself = await client.patch(
        f"/api/v1/employees/{lead['id']}", json={"manager_id": lead["id"]}, headers=sara
    )
    assert itself.status_code == 422


async def test_only_manager_may_be_cleared(client):
    sara = await login(client, "sara@acme.test")
    hire = await onboard(client, sara)
    url = f"/api/v1/employees/{hire['id']}"
    assert (await client.patch(url, json={"full_name": None}, headers=sara)).status_code == 422
    assert (await client.patch(url, json={}, headers=sara)).status_code == 422
    cleared = await client.patch(url, json={"manager_id": None}, headers=sara)
    assert cleared.status_code == 200 and cleared.json()["manager_id"] is None


# --- Deactivate / reactivate -----------------------------------------------------------------


async def test_deactivation_blocks_access_and_cancels_pending_leave(client):
    sara = await login(client, "sara@acme.test")
    hire = await onboard(client, sara, join_date=str(date(date.today().year, 1, 1)))
    hire_session = await login(client, hire["email"], NEW_HIRE_PASSWORD)

    day = date.today() + timedelta(days=7)
    while day.weekday() >= 5:
        day += timedelta(days=1)
    if day.year != date.today().year:
        pytest.skip("Too close to year end for a same-year request")
    leave = await client.post(
        "/api/v1/leave/requests",
        json={"leave_type_code": "CASUAL", "start_date": str(day), "end_date": str(day)},
        headers=hire_session,
    )
    assert leave.status_code == 201, leave.text

    r = await client.post(f"/api/v1/employees/{hire['id']}/deactivate", headers=sara)
    assert r.status_code == 200, r.text
    assert r.json()["is_active"] is False

    # Old token rejected, new sign-in refused.
    assert await _status(client, hire_session) == 401
    bad = await client.post(
        "/api/v1/auth/login", json={"email": hire["email"], "password": NEW_HIRE_PASSWORD}
    )
    assert bad.status_code == 401

    company = (await client.get("/api/v1/leave/requests?scope=company", headers=sara)).json()
    assert next(x for x in company if x["id"] == leave.json()["id"])["status"] == "CANCELLED"

    active = {e["id"] for e in (await client.get("/api/v1/employees", headers=sara)).json()}
    inactive = {
        e["id"]
        for e in (await client.get("/api/v1/employees?status=inactive", headers=sara)).json()
    }
    assert hire["id"] not in active and hire["id"] in inactive

    edit = await client.patch(
        f"/api/v1/employees/{hire['id']}", json={"job_title": "Ghost"}, headers=sara
    )
    assert edit.status_code == 422

    back = await client.post(f"/api/v1/employees/{hire['id']}/reactivate", headers=sara)
    assert back.status_code == 200 and back.json()["is_active"] is True
    await login(client, hire["email"], NEW_HIRE_PASSWORD)


async def test_cannot_deactivate_a_manager_with_active_reports(client):
    sara = await login(client, "sara@acme.test")
    lead = await onboard(client, sara, full_name="Team Lead")
    report = await onboard(client, sara, manager_id=lead["id"])

    blocked = await client.post(f"/api/v1/employees/{lead['id']}/deactivate", headers=sara)
    assert blocked.status_code == 422
    assert "new manager" in blocked.json()["error"]["message"]

    await client.patch(f"/api/v1/employees/{report['id']}", json={"manager_id": None}, headers=sara)
    ok = await client.post(f"/api/v1/employees/{lead['id']}/deactivate", headers=sara)
    assert ok.status_code == 200


async def test_employee_cannot_deactivate_anyone(client):
    sara = await login(client, "sara@acme.test")
    hire = await onboard(client, sara)
    ayesha = await login(client, "ayesha@acme.test")
    r = await client.post(f"/api/v1/employees/{hire['id']}/deactivate", headers=ayesha)
    assert r.status_code == 403


# --- Change password -------------------------------------------------------------------------


async def test_user_changes_own_password(client):
    sara = await login(client, "sara@acme.test")
    hire = await onboard(client, sara)
    session = await login(client, hire["email"], NEW_HIRE_PASSWORD)

    wrong = await client.post(
        "/api/v1/auth/password",
        json={"current_password": "not-it", "new_password": "Brand@New99"},
        headers=session,
    )
    assert wrong.status_code == 422
    assert "incorrect" in wrong.json()["error"]["message"]

    same = await client.post(
        "/api/v1/auth/password",
        json={"current_password": NEW_HIRE_PASSWORD, "new_password": NEW_HIRE_PASSWORD},
        headers=session,
    )
    assert same.status_code == 422

    ok = await client.post(
        "/api/v1/auth/password",
        json={"current_password": NEW_HIRE_PASSWORD, "new_password": "Brand@New99"},
        headers=session,
    )
    assert ok.status_code == 200, ok.text

    # The session used for the change is replaced by the returned token; older ones end.
    assert await _status(client, session) == 401
    fresh = {"Authorization": f"Bearer {ok.json()['access_token']}"}
    assert await _status(client, fresh) == 200

    old = await client.post(
        "/api/v1/auth/login", json={"email": hire["email"], "password": NEW_HIRE_PASSWORD}
    )
    assert old.status_code == 401
    await login(client, hire["email"], "Brand@New99")


# --- HR password reset -----------------------------------------------------------------------


async def test_hr_reset_signs_employee_out_everywhere(client):
    sara = await login(client, "sara@acme.test")
    hire = await onboard(client, sara)
    session = await login(client, hire["email"], NEW_HIRE_PASSWORD)

    r = await client.post(
        f"/api/v1/employees/{hire['id']}/reset-password",
        json={"new_password": "Temp@Reset1"},
        headers=sara,
    )
    assert r.status_code == 204, r.text
    assert await _status(client, session) == 401

    old = await client.post(
        "/api/v1/auth/login", json={"email": hire["email"], "password": NEW_HIRE_PASSWORD}
    )
    assert old.status_code == 401
    await login(client, hire["email"], "Temp@Reset1")

    audit = (await client.get("/api/v1/audit?limit=20", headers=sara)).json()["items"]
    entry = next(a for a in audit if a["event"] == "employee.password_reset")
    assert "Temp@Reset1" not in str(entry)


@pytest.mark.parametrize("email", ["bilal@acme.test", "ayesha@acme.test"])
async def test_only_hr_can_reset_passwords(client, email):
    sara = await login(client, "sara@acme.test")
    hire = await onboard(client, sara)
    headers = await login(client, email)
    r = await client.post(
        f"/api/v1/employees/{hire['id']}/reset-password",
        json={"new_password": "Temp@Reset1"},
        headers=headers,
    )
    assert r.status_code == 403


async def test_hr_cannot_reset_own_password(client):
    sara = await login(client, "sara@acme.test")
    me = (await client.get("/api/v1/employees/me", headers=sara)).json()
    r = await client.post(
        f"/api/v1/employees/{me['id']}/reset-password",
        json={"new_password": "Temp@Reset1"},
        headers=sara,
    )
    assert r.status_code == 403


async def test_leave_requests_filter_by_employee_stays_within_scope(client):
    bilal = await login(client, "bilal@acme.test")
    sara = await login(client, "sara@acme.test")
    outsider = (await client.get("/api/v1/employees?search=Sana", headers=sara)).json()[0]
    # Bilal can't see Finance's requests even when naming the employee directly.
    r = await client.get(
        f"/api/v1/leave/requests?scope=team&employee_id={outsider['id']}", headers=bilal
    )
    assert r.status_code == 200 and r.json() == []
