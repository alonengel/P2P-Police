"""ApiGatekeeper — the single doorway for EVERY external call (guidelines §5).

No LLM/email/HTTP call may bypass this: limiter triad first, bounded retries
on transient failures, and a call log for monitoring. Limits come from
config/rate_limits.json, versioned, never hardcoded.
"""

import time
from collections.abc import Callable

from p2p_police.shared.rate_limiter import RateLimitDeniedError, ServiceLimiter


class TransientProviderError(Exception):
    """Retryable provider failure (network blip, 5xx, overload)."""


class ApiGatekeeper:
    """Input: rate_limits config dict. Output: guarded call results.
    Setup: injectable clock/sleep so tests never wait."""

    def __init__(
        self,
        rate_limits: dict,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._services = rate_limits["services"]
        self._queue_config = rate_limits.get("queue", {})
        self._limiters = {
            name: ServiceLimiter(cfg, clock) for name, cfg in self._services.items()
        }
        self._sleep = sleep
        self.call_log: list[dict] = []

    def _limiter(self, service: str) -> ServiceLimiter:
        return self._limiters.get(service) or self._limiters["default"]

    def execute(self, service: str, call: Callable[[], object]) -> object:
        """Run `call` under the service's gates with bounded retries."""
        config = self._services.get(service, self._services["default"])
        retries = int(config.get("max_retries", 3))
        backoff = float(config.get("retry_after_seconds", 5))
        attempt = 0
        limiter = self._limiter(service)
        while True:
            limiter.wait_for_token(service, self._queue_config, self._sleep)
            attempt += 1
            try:
                with limiter.concurrency:  # config-driven cap (section 5.1)
                    result = call()
                self.call_log.append({"service": service, "attempt": attempt, "ok": True})
                return result
            except TransientProviderError as error:
                self.call_log.append(
                    {"service": service, "attempt": attempt, "ok": False, "error": str(error)}
                )
                if attempt > retries:
                    raise
                self._sleep(backoff)

    def queue_status(self) -> dict:
        """Monitoring view (guidelines: gatekeeper reports its state)."""
        return {
            "calls_logged": len(self.call_log),
            "services": sorted(self._limiters),
            "dos_locked": {n: lim.dos.locked for n, lim in self._limiters.items()},
        }


__all__ = ["ApiGatekeeper", "RateLimitDeniedError", "TransientProviderError"]
