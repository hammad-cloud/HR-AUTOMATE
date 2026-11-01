"""Malformed-input robustness. Regression tests for crashes found by the OWASP ZAP API scan.

A NUL character in any string that reaches PostgreSQL used to fail inside the driver and
return 500. Every entry point must now answer with a clean 422 instead.
"""

import pytest

from tests.integration.conftest import login

API = "/api/v1"
NUL = "\x00"


@pytest.mark.parametrize(
    ("path", "params"),
    [
        ("/employees", {"search": f"a{NUL}b"}),
        ("/employees", {"search": f"'\"{NUL}<scrIpt>alert(1);</scRipt>"}),
        ("/audit", {"tool": f"x{NUL}"}),
        ("/audit", {"outcome": NUL}),
    ],
)
async def test_nul_in_query_string_is_rejected(client, path, params):
    sara = await login(client, "sara@acme.test")
    r = await client.get(API + path, params=params, headers=sara)
    assert r.status_code == 422, r.text
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.parametrize(
    ("path", "body", "auth"),
    [
        ("/auth/login", {"email": f"x{NUL}@acme.test", "password": "pw"}, False),
        ("/auth/login", {"email": "ayesha@acme.test", "password": f"a{NUL}b"}, False),
        ("/auth/password", {"current_password": "x", "new_password": f"Abc{NUL}12345"}, True),
        (
            "/leave/requests",
            {
                "leave_type_code": f"SI{NUL}CK",
                "start_date": "2027-03-03",
                "end_date": "2027-03-03",
                "reason": f"flu{NUL}",
            },
            True,
        ),
    ],
)
async def test_nul_in_json_body_is_rejected(client, path, body, auth):
    headers = await login(client, "ayesha@acme.test") if auth else {}
    r = await client.post(API + path, json=body, headers=headers)
    assert r.status_code == 422, r.text
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"
    assert "request_id" in r.json()["error"]


async def test_guard_responses_keep_security_headers(client):
    r = await client.get(f"{API}/employees", params={"search": NUL})
    assert r.status_code == 422
    assert r.headers["x-content-type-options"] == "nosniff"


async def test_malformed_json_is_a_validation_error_not_a_crash(client):
    r = await client.post(
        f"{API}/auth/login",
        content=b'{"email": "a@b.test", "password": ',
        headers={"Content-Type": "application/json"},
    )
    assert r.status_code == 422
