"""Reject NUL characters in request input before they reach the database.

PostgreSQL text cannot store U+0000, so a NUL in any string that reaches a query fails inside
the driver ("invalid byte sequence for encoding UTF8: 0x00") and surfaced as a 500. Found by
the OWASP ZAP API scan (security/run-scans.sh dast). No legitimate HR input contains one, so
the request is refused up front with a normal validation error.
"""

from urllib.parse import unquote_plus

from starlette.requests import Request

_JSON_ESCAPED_NUL = b"\\u0000"


async def has_nul_input(request: Request) -> bool:
    if "\x00" in unquote_plus(request.url.query) or "\x00" in request.url.path:
        return True
    if request.method in ("POST", "PUT", "PATCH"):
        body = await request.body()
        return b"\x00" in body or _JSON_ESCAPED_NUL in body
    return False
