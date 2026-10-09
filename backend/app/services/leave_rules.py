"""Pure leave business rules, kept free of I/O so they are trivially unit-testable."""

from datetime import date, timedelta
from decimal import ROUND_FLOOR, Decimal

from app.core.exceptions import BusinessRuleError


def working_days(start: date, end: date) -> Decimal:
    """Count Monday-to-Friday days in the inclusive range."""
    days = sum(
        1 for offset in range((end - start).days + 1) if (start + timedelta(offset)).weekday() < 5
    )
    return Decimal(days)


def prorated_quota(annual_quota: int, join_date: date, year: int) -> Decimal:
    """Entitlement for `year` of someone who joined on `join_date`.

    Full quota if they joined in an earlier year; otherwise pro rata by the months left
    (the joining month counts), rounded down to the nearest half day.
    """
    if join_date.year < year:
        return Decimal(annual_quota)
    if join_date.year > year:
        return Decimal(0)
    months = 13 - join_date.month
    half_days = (Decimal(annual_quota * months * 2) / 12).to_integral_value(ROUND_FLOOR)
    return half_days / 2


def ensure_requestable(start: date, end: date, today: date) -> Decimal:
    if end < start:
        raise BusinessRuleError("The end date must be on or after the start date.")
    if start < today:
        raise BusinessRuleError("Leave cannot be requested for past dates.")
    days = working_days(start, end)
    if days == 0:
        raise BusinessRuleError("The selected dates fall entirely on a weekend.")
    return days


def ensure_sufficient_balance(
    requested: Decimal, allocated: Decimal, used: Decimal, pending: Decimal, type_name: str
) -> None:
    available = allocated - used - pending
    if requested > available:
        raise BusinessRuleError(
            f"Insufficient {type_name} balance: {requested} day(s) requested, "
            f"{available} available (including pending requests)."
        )
