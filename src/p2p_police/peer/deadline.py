"""Deadline tracking — "a lapsed deadline is failure, not patience" (ch. 8).

Every awaited network interaction carries one of these; waiting unbounded on
an external resource is the defining freeze bug the rulebook bans (rule 6).
Clock is injectable so tests never sleep.
"""

import time
from collections.abc import Callable


class DeadlineExpiredError(Exception):
    """The awaited event did not happen inside its window."""


class Deadline:
    """A monotonic-clock expiry window.

    Input: timeout seconds (from config, never hardcoded by callers).
    Output: remaining time / expiry checks. Setup: optional clock injection.
    """

    def __init__(self, seconds: float, clock: Callable[[], float] = time.monotonic) -> None:
        if seconds <= 0:
            raise ValueError(f"deadline must be positive, got {seconds}")
        self._clock = clock
        self._expires_at = clock() + seconds

    @property
    def expired(self) -> bool:
        return self._clock() >= self._expires_at

    def remaining(self) -> float:
        """Seconds left (never negative) — feeds queue-wait timeouts."""
        return max(0.0, self._expires_at - self._clock())

    def require(self, what: str) -> None:
        """Raise DeadlineExpiredError (naming the awaited thing) once expired."""
        if self.expired:
            raise DeadlineExpiredError(f"deadline expired while waiting for {what}")
