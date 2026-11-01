"""Failed-login throttling (OWASP API2:2023 Broken Authentication, ASVS 2.2.1).

After `max_failures` wrong passwords for the same (client IP, email) inside `window_seconds`,
further attempts are refused with 429 until the window has passed - even with the right
password, so an attacker cannot keep guessing and tell when they hit. A successful login
clears the counter. Unknown emails are counted the same way, so the limiter does not reveal
which accounts exist.

State lives in process memory: correct for a single API worker. Running several workers or
replicas would need a shared store (Redis) behind the same interface.
"""

import time
from collections import deque
from threading import Lock


class LoginThrottle:
    def __init__(self, max_failures: int = 5, window_seconds: int = 900) -> None:
        self.max_failures = max_failures
        self.window_seconds = window_seconds
        self._failures: dict[tuple[str, str], deque[float]] = {}
        self._lock = Lock()

    def _recent(self, key: tuple[str, str], now: float) -> deque[float]:
        attempts = self._failures.get(key, deque())
        while attempts and now - attempts[0] >= self.window_seconds:
            attempts.popleft()
        return attempts

    def retry_after(self, client_ip: str, email: str) -> int:
        """Seconds until the next attempt is allowed; 0 when not throttled."""
        key, now = (client_ip, email.lower()), time.monotonic()
        with self._lock:
            attempts = self._recent(key, now)
            if len(attempts) < self.max_failures:
                return 0
            return max(1, int(self.window_seconds - (now - attempts[0])))

    def record_failure(self, client_ip: str, email: str) -> None:
        key, now = (client_ip, email.lower()), time.monotonic()
        with self._lock:
            attempts = self._recent(key, now)
            attempts.append(now)
            self._failures[key] = attempts

    def reset(self, client_ip: str, email: str) -> None:
        with self._lock:
            self._failures.pop((client_ip, email.lower()), None)

    def clear(self) -> None:
        with self._lock:
            self._failures.clear()


login_throttle = LoginThrottle()
