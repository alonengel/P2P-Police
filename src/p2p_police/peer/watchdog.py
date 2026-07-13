"""Watchdog (rulebook ch. 8, rule 7): an independent monitor of the game loop.

The main loop beats a heartbeat every half-turn; if the beat stops longer
than the configured window (a wedged transport, a dead thread), the watchdog
persists the game state for post-mortem/recovery and triggers a controlled
shutdown callback instead of leaving a zombie peer. Clock injectable.
"""

import json
import threading
import time
from collections.abc import Callable
from pathlib import Path


class Watchdog:
    """Input: heartbeats + a state provider. Output: crash dump + shutdown."""

    def __init__(
        self,
        timeout_sec: float,
        state_provider: Callable[[], dict],
        on_shutdown: Callable[[], None],
        dump_path: str | Path = "results/watchdog_dump.json",
        clock: Callable[[], float] = time.monotonic,
        poll_interval: float = 1.0,
    ) -> None:
        if timeout_sec <= 0:
            raise ValueError("watchdog timeout must be positive")
        self.timeout_sec = timeout_sec
        self._state_provider = state_provider
        self._on_shutdown = on_shutdown
        self._dump_path = Path(dump_path)
        self._clock = clock
        self._poll = poll_interval
        self._last_beat = clock()
        self._stop = threading.Event()
        self.fired = False
        self._thread: threading.Thread | None = None

    def beat(self) -> None:
        """Called by the game loop every half-turn (cheap, thread-safe)."""
        self._last_beat = self._clock()

    def check(self) -> str:
        """One evaluation: 'ALIVE', or 'SHUTDOWN' after persisting state."""
        if self._clock() - self._last_beat <= self.timeout_sec:
            return "ALIVE"
        self.fired = True
        self._persist()
        self._on_shutdown()
        return "SHUTDOWN"

    def _persist(self) -> None:
        try:
            self._dump_path.parent.mkdir(parents=True, exist_ok=True)
            self._dump_path.write_text(
                json.dumps({"reason": "watchdog timeout", "state": self._state_provider()},
                           indent=2, default=str),
                encoding="utf-8",
            )
        except Exception:
            pass  # persistence is best-effort; shutdown must still happen

    def start(self) -> None:
        """Run checks on a daemon thread until stop() or a firing."""
        def loop() -> None:
            while not self._stop.wait(self._poll):
                if self.check() == "SHUTDOWN":
                    return

        self._thread = threading.Thread(target=loop, name="watchdog", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
