"""OWASP API2:2023 Broken Authentication - credential stuffing / brute force."""

from app.core.config import get_settings
from app.core.rate_limit import login_throttle
from tests.integration.conftest import NEW_HIRE_PASSWORD, login, onboard


async def _attempt(client, email: str, password: str):
    return await client.post("/api/v1/auth/login", json={"email": email, "password": password})


async def test_repeated_wrong_passwords_are_throttled(client):
    hr = await login(client, "sara@acme.test")
    victim = (await onboard(client, hr))["email"]

    for _ in range(login_throttle.max_failures):
        assert (await _attempt(client, victim, "guess-123")).status_code == 401

    blocked = await _attempt(client, victim, "guess-123")
    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "TOO_MANY_REQUESTS"
    assert int(blocked.headers["retry-after"]) > 0

    # Even the right password is refused while throttled, so guessing gives no signal.
    assert (await _attempt(client, victim, NEW_HIRE_PASSWORD)).status_code == 429


async def test_unknown_emails_are_throttled_like_real_ones(client):
    ghost = "no-such-user@acme.test"
    for _ in range(login_throttle.max_failures):
        assert (await _attempt(client, ghost, "x")).status_code == 401
    assert (await _attempt(client, ghost, "x")).status_code == 429


async def test_successful_login_clears_failure_count(client):
    email, password = "ayesha@acme.test", get_settings().demo_password
    for _ in range(login_throttle.max_failures - 1):
        await _attempt(client, email, "wrong")
    assert (await _attempt(client, email, password)).status_code == 200
    for _ in range(login_throttle.max_failures - 1):
        assert (await _attempt(client, email, "wrong")).status_code == 401
    assert (await _attempt(client, email, password)).status_code == 200


async def test_login_error_does_not_reveal_which_part_was_wrong(client):
    unknown = await _attempt(client, "nobody@acme.test", "whatever")
    wrong_pw = await _attempt(client, "ayesha@acme.test", "whatever")
    assert unknown.status_code == wrong_pw.status_code == 401
    assert unknown.json()["error"]["message"] == wrong_pw.json()["error"]["message"]
