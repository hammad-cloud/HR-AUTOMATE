from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from app.core.context import RequestContext, Role
from app.core.exceptions import BusinessRuleError, UnauthenticatedError
from app.core.redaction import REDACTED, redact
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.services.employee_service import next_employee_code
from app.services.leave_rules import (
    ensure_requestable,
    ensure_sufficient_balance,
    prorated_quota,
    working_days,
)

MONDAY = date(2026, 10, 12)


class TestLeaveRules:
    def test_working_days_skips_weekends(self):
        assert working_days(MONDAY, date(2026, 10, 18)) == 5  # Mon..Sun
        assert working_days(date(2026, 10, 17), date(2026, 10, 18)) == 0

    def test_rejects_past_dates(self):
        with pytest.raises(BusinessRuleError, match="past"):
            ensure_requestable(date(2026, 10, 1), date(2026, 10, 2), today=MONDAY)

    def test_rejects_weekend_only(self):
        with pytest.raises(BusinessRuleError, match="weekend"):
            ensure_requestable(date(2026, 10, 17), date(2026, 10, 18), today=MONDAY)

    def test_balance_counts_pending(self):
        ensure_sufficient_balance(Decimal(2), Decimal(10), Decimal(5), Decimal(3), "Casual")
        with pytest.raises(BusinessRuleError, match="Insufficient"):
            ensure_sufficient_balance(Decimal(3), Decimal(10), Decimal(5), Decimal(3), "Casual")

    def test_prorated_quota(self):
        assert prorated_quota(10, date(2025, 6, 1), 2026) == 10  # joined last year: full
        assert prorated_quota(12, date(2026, 1, 15), 2026) == 12
        assert prorated_quota(10, date(2026, 10, 12), 2026) == Decimal("2.5")  # 3 months
        assert prorated_quota(14, date(2026, 12, 1), 2026) == Decimal("1")  # 1.17 -> 1.0
        assert prorated_quota(10, date(2027, 1, 4), 2026) == 0


class TestEmployeeCodes:
    def test_continues_company_series(self):
        assert next_employee_code(["ACM-1001", "ACM-1025", "ACM-1003"]) == "ACM-1026"

    def test_ignores_foreign_formats(self):
        assert next_employee_code(["ACM-1001", "legacy7", "X-9999", "ACM-1002"]) == "ACM-1003"

    def test_first_employee(self):
        assert next_employee_code([]) == "EMP-1001"


class TestRedaction:
    def test_masks_sensitive_keys_recursively(self):
        data = {"salary": 250000, "items": [{"net": 1, "name": "Ayesha"}]}
        assert redact(data) == {"salary": REDACTED, "items": [{"net": REDACTED, "name": "Ayesha"}]}

    def test_masks_cnic_in_free_text(self):
        assert REDACTED in redact("my CNIC is 35202-1234567-1")
        assert "35202" not in redact("my CNIC is 352021234567 1")


class TestTokens:
    def test_password_roundtrip(self):
        hashed = hash_password("Correct-Horse-9")
        assert verify_password("Correct-Horse-9", hashed)
        assert not verify_password("wrong", hashed)

    def test_jwt_roundtrip_preserves_context(self):
        ctx = RequestContext(
            user_id=uuid4(),
            role=Role.MANAGER,
            tenant_id=uuid4(),
            company_id=uuid4(),
            employee_id=uuid4(),
        )
        assert decode_access_token(create_access_token(ctx)) == ctx

    def test_token_carries_sub_second_issue_time(self):
        ctx = RequestContext(uuid4(), Role.EMPLOYEE, uuid4(), uuid4(), uuid4())
        before = datetime.now(UTC)
        decoded = decode_access_token(create_access_token(ctx))
        after = datetime.now(UTC)
        # Second-truncated iat would usually fall before `before`; sub-second never does.
        assert decoded.issued_at is not None
        assert before - timedelta(milliseconds=1) <= decoded.issued_at <= after

    def test_tampered_token_rejected(self):
        ctx = RequestContext(uuid4(), Role.EMPLOYEE, uuid4(), uuid4(), uuid4())
        token = create_access_token(ctx)
        with pytest.raises(UnauthenticatedError):
            decode_access_token(token[:-2] + ("A" if token[-2] != "A" else "B") + token[-1])

    def test_tenantless_token_only_for_platform_admin(self):
        ctx = RequestContext(uuid4(), Role.EMPLOYEE, None, None, None)
        with pytest.raises(UnauthenticatedError):
            decode_access_token(create_access_token(ctx))
