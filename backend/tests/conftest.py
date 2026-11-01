import pytest

from app.core.rate_limit import login_throttle


@pytest.fixture(autouse=True)
def _reset_login_throttle():
    """Failed logins from one test must not lock accounts used by the next."""
    login_throttle.clear()
    yield
    login_throttle.clear()
