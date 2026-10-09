"""PII redaction for audit records and anything sent to logs (FR-64)."""

import re
from typing import Any

REDACTED = "[REDACTED]"

_SENSITIVE_KEYS = frozenset(
    {"salary", "gross", "net", "deductions", "national_id", "cnic", "password", "token"}
)
# Pakistani CNIC (12345-1234567-1) and long digit runs that look like account numbers.
_CNIC = re.compile(r"\b\d{5}-?\d{7}-?\d\b")
_LONG_NUMBER = re.compile(r"\b\d{10,}\b")


def redact_text(value: str) -> str:
    return _LONG_NUMBER.sub(REDACTED, _CNIC.sub(REDACTED, value))


def redact(value: Any) -> Any:
    """Recursively mask sensitive keys and CNIC-like strings in a JSON-compatible value."""
    if isinstance(value, dict):
        return {
            k: REDACTED if k.lower() in _SENSITIVE_KEYS else redact(v) for k, v in value.items()
        }
    if isinstance(value, list):
        return [redact(v) for v in value]
    if isinstance(value, str):
        return redact_text(value)
    return value
