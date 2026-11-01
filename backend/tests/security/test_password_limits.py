"""bcrypt input limit. Regression tests for a 500 found by the OWASP ZAP API scan.

bcrypt 5 raises ValueError for input over 72 bytes, while the schemas accepted 128
characters: a long password crashed sign-in, password change, reset and onboarding.
"""

import pytest

from app.core.security import hash_password, verify_password
from tests.integration.conftest import login, new_hire

API = "/api/v1"
TOO_LONG = "A1@" + "x" * 70  # 73 bytes
MULTIBYTE = "Pässwörd-" + "é" * 32  # 41 characters, 75 bytes


def test_overlong_candidate_never_matches_and_never_raises():
    stored = hash_password("x" * 72)
    assert verify_password("x" * 72, stored)
    assert not verify_password("x" * 73, stored)  # would match if silently truncated


@pytest.mark.parametrize("password", [TOO_LONG, "x" * 128, MULTIBYTE])
async def test_sign_in_with_overlong_password_is_a_normal_401(client, password):
    r = await client.post(
        f"{API}/auth/login", json={"email": "ayesha@acme.test", "password": password}
    )
    assert r.status_code == 401


@pytest.mark.parametrize("password", [TOO_LONG, MULTIBYTE])
async def test_overlong_new_passwords_are_rejected_with_422(client, password):
    sara = await login(client, "sara@acme.test")
    colleague = (await client.get(f"{API}/employees?search=Hamza", headers=sara)).json()[0]

    attempts = [
        ("/auth/password", {"current_password": "whatever", "new_password": password}),
        (f"/employees/{colleague['id']}/reset-password", {"new_password": password}),
        ("/employees", new_hire(password=password)),
    ]
    for path, body in attempts:
        r = await client.post(API + path, json=body, headers=sara)
        assert r.status_code == 422, f"{path}: {r.status_code} {r.text}"
        assert "72" in r.json()["error"]["message"]


async def test_exactly_72_byte_password_works_end_to_end(client):
    sara = await login(client, "sara@acme.test")
    password = "Aa1@" + "z" * 68
    created = await client.post(f"{API}/employees", json=new_hire(password=password), headers=sara)
    assert created.status_code == 201, created.text
    assert await login(client, created.json()["email"], password)
