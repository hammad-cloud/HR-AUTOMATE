"""HTTP response hardening headers (OWASP Secure Headers Project).

The API only ever returns JSON, so the policy is as strict as possible. The interactive docs
at /docs load Swagger UI from a CDN, so they get the same headers minus the CSP.
"""

from starlette.datastructures import MutableHeaders

_BASE_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Permissions-Policy": "camera=(), geolocation=(), microphone=()",
}
_API_CSP = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
_HSTS = "max-age=63072000; includeSubDomains"
_DOCS_PATHS = ("/docs", "/openapi.json")


def apply_security_headers(headers: MutableHeaders, path: str, *, https_only: bool) -> None:
    for name, value in _BASE_HEADERS.items():
        headers.setdefault(name, value)
    if not path.startswith(_DOCS_PATHS):
        headers.setdefault("Content-Security-Policy", _API_CSP)
    if path.startswith("/api/"):
        # Responses carry personal data (salaries, CNIC): never cache them anywhere.
        headers["Cache-Control"] = "no-store"
    if https_only:
        headers.setdefault("Strict-Transport-Security", _HSTS)
