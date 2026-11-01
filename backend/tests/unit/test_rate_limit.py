from app.core import rate_limit
from app.core.rate_limit import LoginThrottle


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def make(monkeypatch, **kwargs) -> tuple[LoginThrottle, Clock]:
    clock = Clock()
    monkeypatch.setattr(rate_limit.time, "monotonic", clock)
    return LoginThrottle(**kwargs), clock


def test_allows_attempts_below_the_limit(monkeypatch):
    throttle, _ = make(monkeypatch, max_failures=3, window_seconds=60)
    for _ in range(2):
        throttle.record_failure("1.2.3.4", "a@x.test")
    assert throttle.retry_after("1.2.3.4", "a@x.test") == 0


def test_blocks_at_the_limit_and_reports_wait(monkeypatch):
    throttle, clock = make(monkeypatch, max_failures=3, window_seconds=60)
    for _ in range(3):
        throttle.record_failure("1.2.3.4", "a@x.test")
    assert throttle.retry_after("1.2.3.4", "a@x.test") == 60
    clock.now += 45
    assert throttle.retry_after("1.2.3.4", "a@x.test") == 15


def test_window_expiry_unblocks(monkeypatch):
    throttle, clock = make(monkeypatch, max_failures=2, window_seconds=60)
    throttle.record_failure("1.2.3.4", "a@x.test")
    throttle.record_failure("1.2.3.4", "a@x.test")
    clock.now += 60
    assert throttle.retry_after("1.2.3.4", "a@x.test") == 0


def test_email_is_case_insensitive_and_keys_are_isolated(monkeypatch):
    throttle, _ = make(monkeypatch, max_failures=1, window_seconds=60)
    throttle.record_failure("1.2.3.4", "A@X.test")
    assert throttle.retry_after("1.2.3.4", "a@x.test") > 0
    assert throttle.retry_after("5.6.7.8", "a@x.test") == 0
    assert throttle.retry_after("1.2.3.4", "b@x.test") == 0


def test_reset_clears_failures(monkeypatch):
    throttle, _ = make(monkeypatch, max_failures=1, window_seconds=60)
    throttle.record_failure("1.2.3.4", "a@x.test")
    throttle.reset("1.2.3.4", "a@x.test")
    assert throttle.retry_after("1.2.3.4", "a@x.test") == 0
