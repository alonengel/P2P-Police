"""SimulationSdk — the single business entry point (guidelines section 4).

Every consumer (CLI now; GUI and league tooling later) goes through here.
Assembles config, engine, transport and runtime; owns no game logic itself.
"""

import json
import random
import time
from pathlib import Path

from p2p_police.domain import crypto
from p2p_police.domain.engine import GameEngine
from p2p_police.domain.errors import GameRuleError
from p2p_police.domain.primitives import Role
from p2p_police.infra.mcp_client import McpTransport
from p2p_police.infra.mcp_server import PeerInboxes, build_peer_server, start_peer_server
from p2p_police.peer.deadline import DeadlineExpiredError
from p2p_police.peer.runtime import GeometricRuntime
from p2p_police.sdk import reporting
from p2p_police.shared.config import Config
from p2p_police.strategy.brain_base import resolve_brain

MY_ROLE = Role.POLICE  # this repo IS the police agent (twin repo: thief)
SHUTDOWN_GRACE_SEC = 1.5  # let the opponent's final MCP session close cleanly


class SimulationSdk:
    """Facade over the peer's flows.

    Input: a config directory. Output: end reports as plain dicts.
    Setup: `SimulationSdk(config_dir)`; heavy resources start per call.
    """

    def __init__(self, config_dir: str = "config") -> None:
        self.config = Config.load(config_dir)

    def build_engine(self) -> GameEngine:
        pheromones = self.config.pheromones
        return GameEngine(
            self.config.grid_size,
            self.config.cop_start,
            self.config.thief_start,
            self.config.rule_set(),
            center_intensity=pheromones["pheromone_center_intensity"],
            decay=pheromones["pheromone_decay"],
            kernel_size=pheromones["pheromone_grid_size"],
        )

    def run_peer(
        self, seed: int | None = None, gui: bool = False, gui_screenshot: str | None = None
    ) -> dict:
        """Start our MCP server, connect to the opponent, play one game to
        completion (optionally with the live local-truth GUI) and report."""
        inboxes = PeerInboxes()
        server = build_peer_server(inboxes, name=f"p2p_{MY_ROLE.value}_peer")
        start_peer_server(server, self.config.my_port)
        transport = McpTransport(
            self.config.opponent_url,
            self.config.retry_backoff_sec,
            self.config.response_timeout_sec,
        )
        runtime = GeometricRuntime(
            MY_ROLE,
            self.config,
            self.build_engine(),
            transport,
            inboxes,
            resolve_brain(self.config, MY_ROLE, random.Random(seed)),
        )
        from p2p_police.peer.watchdog import Watchdog

        watchdog = Watchdog(
            float(self.config.shared["network_and_league"]["watchdog_timeout_sec"]),
            lambda: {"positions": {r.value: list(c) for r, c in runtime.engine.positions.items()},
                     "turns": runtime.engine.turns_completed,
                     "outcome": runtime.engine.outcome.value},
            transport.close,
        )
        runtime.watchdog = watchdog
        watchdog.start()
        try:
            report = self._play_with_gui(runtime, gui_screenshot) if gui else runtime.play()
        except (DeadlineExpiredError, GameRuleError) as error:
            # BLOCKER fix (rules 32/35): a technical loss is a first-class
            # outcome - it MUST still be reported and emailed, never skipped.
            report = reporting.technical_loss_report(MY_ROLE, runtime, error)
        finally:
            watchdog.stop()
        if report.get("audit") not in (None, "Verified OK"):
            # Rule 19: a failed mutual audit voids the game - no normal score.
            report["outcome"] = "technical_loss"
        report["artifacts"] = [
            str(p) for p in reporting.emit_artifacts(self.config, runtime, report)
        ]
        reporting.maybe_email(self.config, report)
        # Shutdown grace: our daemon server dies with the process; give the
        # opponent's in-flight final exchange a moment to complete cleanly.
        time.sleep(SHUTDOWN_GRACE_SEC)
        return report

    def _play_with_gui(self, runtime: GeometricRuntime, screenshot: str | None) -> dict:
        """Tk owns the main thread; the runtime plays in a worker thread."""
        import threading

        from p2p_police.gui.live_view import LiveView

        view = LiveView(self.config.grid_size, MY_ROLE.value)
        runtime.perception.on_snapshot = view.feed
        box: dict = {}
        worker = threading.Thread(target=lambda: box.update(runtime.play()), daemon=True)
        worker.start()
        view.run(screenshot_path=screenshot)
        worker.join(timeout=30)
        if not box:
            raise RuntimeError("game did not finish while the GUI was open")
        return box

    @staticmethod
    def verify_log(log_path: str) -> str:
        """Headless replay verification engine (mandatory deliverable, ch. 7):
        recompute every sealed record in a saved log -> Verified OK/TAMPERED."""
        doc = json.loads(Path(log_path).read_text(encoding="utf-8"))
        own = doc.get("records", [])
        theirs = [r for r in doc.get("opponent_records", []) if "nonce" in r]
        for record in own + theirs:
            if not crypto.verify_commit(
                record["payload"], record["nonce"], record["commit"]
            ):
                return "TAMPERED"
        return "Verified OK"
