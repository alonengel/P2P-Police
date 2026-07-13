"""Gatekeeper defense triad (rulebook ch. 9, rules 28-29): token bucket,
daily quota safety threshold, DOS circuit breaker. All values from
config/rate_limits.json — never code. Clock injectable for tests.
"""

import time
from collections.abc import Callable


class RateLimitDeniedError(Exception):
    """The gate refused the call (bucket empty / quota reached / DOS lock)."""


class TokenBucket:
    """tokens <- min(C, tokens + r*dt); allow <=> tokens >= 1 (book 9.3.2)."""

    def __init__(
        self, requests_per_minute: float, clock: Callable[[], float] = time.monotonic
    ) -> None:
        if requests_per_minute <= 0:
            raise ValueError("requests_per_minute must be positive")
        self.capacity = float(requests_per_minute)
        self.refill_per_sec = requests_per_minute / 60.0
        self._tokens = self.capacity
        self._clock = clock
        self._last = clock()

    def allow(self, cost: float = 1.0) -> bool:
        now = self._clock()
        self._tokens = min(self.capacity, self._tokens + (now - self._last) * self.refill_per_sec)
        self._last = now
        if self._tokens >= cost:
            self._tokens -= cost
            return True
        return False


class QuotaManager:
    """Counts calls per day and blocks at the safety threshold — the last
    line before the provider blocks the account (429 territory)."""

    def __init__(
        self, daily_safety_threshold: int, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self.threshold = daily_safety_threshold
        self._clock = clock
        self._window_start = clock()
        self._count = 0

    def allow(self) -> bool:
        if self._clock() - self._window_start >= 86400.0:
            self._window_start = self._clock()
            self._count = 0
        if self._count >= self.threshold:
            return False
        self._count += 1
        return True


class DosDetector:
    """Circuit breaker: a storm of denials means a bug is hammering the gate;
    lock the service rather than let the account be suspended (rule 29)."""

    def __init__(self, trip_after_denials: int = 10) -> None:
        self.trip_after = trip_after_denials
        self._consecutive_denials = 0
        self.locked = False

    def record(self, allowed: bool) -> None:
        if allowed:
            self._consecutive_denials = 0
        else:
            self._consecutive_denials += 1
            if self._consecutive_denials >= self.trip_after:
                self.locked = True


class ServiceLimiter:
    """The full triad for one named service (claude/email/openrouter/...)."""

    def __init__(
        self, service_config: dict, clock: Callable[[], float] = time.monotonic
    ) -> None:
        import threading

        self.bucket = TokenBucket(service_config["requests_per_minute"], clock)
        self.quota = QuotaManager(
            service_config.get("daily_quota_safety_threshold", 10_000), clock
        )
        self.dos = DosDetector(int(service_config.get("dos_trip_after", 10)))
        # Concurrency cap (guidelines section 5.1) - config, never code.
        self.concurrency = threading.BoundedSemaphore(
            int(service_config.get("concurrent_max",
                                   service_config.get("concurrent_requests", 2)))
        )
        self.waiters = 0

    def check(self, service: str) -> None:
        """Raise RateLimitDeniedError unless every gate passes (fail fast)."""
        if self.dos.locked:
            raise RateLimitDeniedError(f"{service}: DOS lock tripped - service disabled")
        if not self.quota.allow():
            self.dos.record(False)
            raise RateLimitDeniedError(f"{service}: daily quota safety threshold reached")
        allowed = self.bucket.allow()
        self.dos.record(allowed)
        if not allowed:
            raise RateLimitDeniedError(f"{service}: token bucket empty - back off")

    def wait_for_token(
        self, service: str, queue_config: dict, sleep: Callable[[float], None]
    ) -> None:
        """Guidelines section 5.3: an exhausted bucket QUEUES, never rejects.

        FIFO-ish waiters bounded by max_depth (backpressure raises), draining
        at drain_interval until wait_timeout. Quota/DOS stops still reject -
        they protect the account, not the throughput.
        """
        deadline = self._deadline(queue_config)
        if self.waiters >= int(queue_config.get("max_depth", 100)):
            raise RateLimitDeniedError(f"{service}: queue full - backpressure")
        self.waiters += 1
        try:
            while True:
                try:
                    self.check(service)
                    return
                except RateLimitDeniedError as denial:
                    if "token bucket" not in str(denial):
                        raise
                    if deadline():
                        raise RateLimitDeniedError(
                            f"{service}: queue wait timeout"
                        ) from denial
                    sleep(float(queue_config.get("drain_interval_seconds", 0.1)))
        finally:
            self.waiters -= 1

    def _deadline(self, queue_config: dict) -> Callable[[], bool]:
        start = self.bucket._clock()
        timeout = float(queue_config.get("wait_timeout_seconds", 300))
        return lambda: self.bucket._clock() - start >= timeout
