"""OWASP API8:2023 Security Misconfiguration - response hardening headers."""

import pytest
from starlette.datastructures import MutableHeaders

from app.core.security_headers import apply_security_headers

EXPECTED = {
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
    "referrer-policy": "no-referrer",
}


@pytest.mark.parametrize("path", ["/health", "/api/v1/auth/me", "/api/v1/does-not-exist"])
async def test_hardening_headers_on_every_response(client, path):
    r = await client.get(path)
    for name, value in EXPECTED.items():
        assert r.headers.get(name) == value, f"{name} missing on {path} ({r.status_code})"
    assert "default-src 'none'" in r.headers["content-security-policy"]


async def test_api_responses_are_never_cached(client):
    r = await client.post("/api/v1/auth/login", json={"email": "nobody@acme.test", "password": "x"})
    assert r.headers["cache-control"] == "no-store"


async def test_docs_keep_working_without_strict_csp(client):
    r = await client.get("/docs")
    assert r.status_code == 200
    assert "content-security-policy" not in r.headers
    assert r.headers["x-frame-options"] == "DENY"


def test_hsts_only_when_served_over_https():
    plain, tls = MutableHeaders(), MutableHeaders()
    apply_security_headers(plain, "/health", https_only=False)
    apply_security_headers(tls, "/health", https_only=True)
    assert "strict-transport-security" not in plain
    assert tls["strict-transport-security"].startswith("max-age=63072000")


async def test_errors_do_not_leak_internals(client):
    r = await client.get("/api/v1/employees/not-a-uuid", headers={"Authorization": "Bearer x"})
    body = r.text.lower()
    for marker in ("traceback", "sqlalchemy", "asyncpg", 'file "/', "postgres"):
        assert marker not in body
