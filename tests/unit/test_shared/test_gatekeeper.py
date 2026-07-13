"""Gatekeeper triad tests (rules 28-29, guidelines section 5) on a fake clock."""

import pytest

from p2p_police.shared.gatekeeper import ApiGatekeeper, TransientProviderError
from p2p_police.shared.rate_limiter import (
    DosDetector,
    RateLimitDeniedError,
    ServiceLimiter,
    TokenBucket,
)


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


LIMITS = {
    "services": {
        "default": {"requests_per_minute": 30, "retry_after_seconds": 5, "max_retries": 3},
        "email": {
            "requests_per_minute": 5,
            "retry_after_seconds": 10,
            "max_retries": 2,
            "daily_quota_safety_threshold": 3,
        },
    }
}


def test_bucket_allows_burst_up_to_capacity_then_blocks() -> None:
    clock = FakeClock()
    bucket = TokenBucket(5, clock)
    assert all(bucket.allow() for _ in range(5))
    assert not bucket.allow()
    clock.now += 12.0  # 5/min -> one token per 12s
    assert bucket.allow()


def test_quota_threshold_blocks_before_provider_does() -> None:
    clock = FakeClock()
    limiter = ServiceLimiter(LIMITS["services"]["email"], clock)
    for _ in range(3):
        limiter.check("email")
    with pytest.raises(RateLimitDeniedError, match="quota"):
        limiter.check("email")


def test_dos_lock_trips_on_denial_storm() -> None:
    detector = DosDetector(trip_after_denials=3)
    for _ in range(3):
        detector.record(False)
    assert detector.locked
    detector = DosDetector(trip_after_denials=3)
    detector.record(False)
    detector.record(True)  # success resets the streak
    detector.record(False)
    assert not detector.locked


def test_gatekeeper_retries_transient_then_succeeds() -> None:
    clock = FakeClock()
    gate = ApiGatekeeper(LIMITS, clock=clock, sleep=lambda _s: None)
    attempts = {"n": 0}

    def flaky() -> str:
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise TransientProviderError("blip")
        return "ok"

    assert gate.execute("default", flaky) == "ok"
    assert attempts["n"] == 3
    assert gate.call_log[-1]["ok"] is True


def test_gatekeeper_gives_up_after_bounded_retries() -> None:
    gate = ApiGatekeeper(LIMITS, clock=FakeClock(), sleep=lambda _s: None)

    def always_down() -> None:
        raise TransientProviderError("down")

    with pytest.raises(TransientProviderError):
        gate.execute("default", always_down)
    assert gate.queue_status()["calls_logged"] == 4  # 1 + 3 retries


def test_unknown_service_falls_back_to_default_limits() -> None:
    gate = ApiGatekeeper(LIMITS, clock=FakeClock(), sleep=lambda _s: None)
    assert gate.execute("mystery", lambda: 42) == 42


def test_empty_bucket_queues_instead_of_rejecting() -> None:
    """Guidelines section 5.3: overflow waits for a refill, never drops."""
    clock = FakeClock()
    limits = {"services": {"default": {"requests_per_minute": 60, "max_retries": 0,
                                       "retry_after_seconds": 0}},
              "queue": {"max_depth": 5, "drain_interval_seconds": 1, "wait_timeout_seconds": 300}}

    def sleeping(seconds: float) -> None:
        clock.now += seconds  # sleeping refills the bucket on the fake clock

    gate = ApiGatekeeper(limits, clock=clock, sleep=sleeping)
    for _ in range(60):
        gate.execute("default", lambda: "ok")  # drains the burst capacity
    assert gate.execute("default", lambda: "ok") == "ok"  # queued, then served


def test_queue_backpressure_raises_when_full() -> None:
    from p2p_police.shared.rate_limiter import RateLimitDeniedError, ServiceLimiter

    clock = FakeClock()
    limiter = ServiceLimiter({"requests_per_minute": 1}, clock)
    limiter.waiters = 3
    with pytest.raises(RateLimitDeniedError, match="backpressure"):
        limiter.wait_for_token("x", {"max_depth": 3}, lambda _s: None)
