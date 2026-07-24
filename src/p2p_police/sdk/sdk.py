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
from p2p_police.domain.primitives import Role
from p2p_police.infra.mcp_client import McpTransport
from p2p_police.infra.mcp_server import PeerInboxes, build_peer_server, start_peer_server
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

    def __init__(self, config_dir: str = "config", private_file: str = "game.toml") -> None:
        self.config = Config.load(config_dir, private_file)

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
        self, seed: int | None = None, gui: bool = False,
        gui_screenshot: str | None = None, resume: bool = False
    ) -> dict:
        """Start our MCP server, connect to the opponent, play one game to
        completion (optionally with the live local-truth GUI) and report.
        resume=True re-arms from the crash-resume snapshot (E6) and continues."""
        inboxes = PeerInboxes()
        server = build_peer_server(inboxes, name=f"p2p_{MY_ROLE.value}_peer")
        start_peer_server(server, self.config.my_port)
        from p2p_police.infra.duplicate_transport import maybe_duplicate_outbound

        transport = maybe_duplicate_outbound(
            McpTransport(
                self.config.opponent_url,
                self.config.retry_backoff_sec,
                self.config.response_timeout_sec,
            ),
            self.config,
        )
        from p2p_police.shared.gatekeeper import ApiGatekeeper

        gatekeeper = ApiGatekeeper(self.config.rate_limits)  # ONE per run (section 5)
        from p2p_police.sdk import hidden as hidden_mod
        from p2p_police.wire import lock

        brain = resolve_brain(self.config, MY_ROLE, random.Random(seed))
        if lock.wire_shape(self.config) == lock.REFERENCE:
            # wire_shape seam: same SDK entry, the hidden-information loop
            runtime = hidden_mod.build_runtime(
                self.config, transport, inboxes, brain, gatekeeper)
            resume_mod = hidden_mod
        else:
            runtime = GeometricRuntime(MY_ROLE, self.config, self.build_engine(),
                                       transport, inboxes, brain, gatekeeper=gatekeeper)
            from p2p_police.peer import resume as resume_mod

        start_turn = resume_mod.attach(runtime, self.config, resume=resume)
        from p2p_police.peer.watchdog import Watchdog

        watchdog = Watchdog(
            float(self.config.shared["network_and_league"]["watchdog_timeout_sec"]),
            reporting.watchdog_state(runtime),
            transport.close,
        )
        runtime.watchdog = watchdog
        runtime.transport.beat = watchdog.beat  # send-retry liveness (live-session finding)
        watchdog.start()
        try:
            report = (self._play_with_gui(runtime, gui_screenshot, start_turn) if gui
                      else runtime.play(start_turn))
        except Exception as error:  # noqa: BLE001 - rules 32/35: EVERY game
            # end (any failure whatsoever) must still be reported and emailed;
            # an unreported forfeit is the worst outcome the league allows.
            report = reporting.technical_loss_report(MY_ROLE, runtime, error)
        finally:
            watchdog.stop()
        if report.get("audit") == "TAMPERED":
            # Rule 19: a FAILED mutual audit voids the game. A merely MISSING
            # audit ('not received') is dispute evidence, not tampering - the
            # played outcome stands and the logs decide.
            report["outcome"] = "technical_loss"
        if report.get("outcome") in ("capture", "survival"):
            resume_mod.discard(self.config)  # a finished game never resumes
        report["gatekeeper"] = gatekeeper.queue_status()  # section-5 monitoring view
        report["artifacts"] = [
            str(p) for p in reporting.emit_artifacts(self.config, runtime, report)
        ]
        reporting.maybe_email(self.config, report, gatekeeper)
        # Shutdown grace: our daemon server dies with the process; give the
        # opponent's in-flight final exchange a moment to complete cleanly.
        time.sleep(SHUTDOWN_GRACE_SEC)
        return report

    def _play_with_gui(self, runtime: GeometricRuntime, screenshot: str | None,
                       start_turn: int = 0) -> dict:
        """Tk owns the main thread; the runtime plays in a worker thread."""
        import threading

        from p2p_police.gui.live_view import LiveView

        view = LiveView(self.config.grid_size, MY_ROLE.value,
                        start_cell=self.config.cop_start)  # idle paint: MY start
        runtime.perception.on_snapshot = view.feed
        box: dict = {}

        def play_into_box() -> None:
            try:
                box.update(runtime.play(start_turn))
            except Exception as error:  # noqa: BLE001 - reported, never lost
                box.update(reporting.technical_loss_report(MY_ROLE, runtime, error))
            finally:
                # The game is CLASSIFIED the moment this worker ends. Silence
                # the watchdog (a classified game must never "fire" 60s later)
                # and release the Tk mainloop so the report reaches stdout -
                # never a zombie window (2026-07-24 live cross-team finding).
                runtime.watchdog.stop()
                view.finish(box.get("outcome", "technical_loss"))

        worker = threading.Thread(target=play_into_box, daemon=True)
        worker.start()
        view.run(screenshot_path=screenshot)
        # closing the window must not abandon the game: wait a full turn
        # window (not an arbitrary 30s) before declaring the run lost
        worker.join(timeout=self.config.turn_timeout_seconds + SHUTDOWN_GRACE_SEC)
        if not box:
            return reporting.technical_loss_report(
                MY_ROLE, runtime, RuntimeError("GUI closed and game did not finish")
            )
        return box

    @staticmethod
    def verify_log(log_path: str) -> str:
        """Headless replay verification engine (mandatory deliverable, ch. 7):
        recompute every sealed record in a saved log -> Verified OK/TAMPERED.
        When the game's archived config artifact is found, ALSO re-simulate
        the physics and recompute the end digest (rule 20): bookletter logs
        replay on a fresh engine; logs declaring the hidden wire replay
        through the audit reconstruction (report/lookup.py, ADR-0008)."""
        from p2p_police.wire import audit_foreign

        doc = json.loads(Path(log_path).read_text(encoding="utf-8"))
        own = doc.get("records", [])
        for record in own:
            if not crypto.verify_commit(
                record["payload"], record["nonce"], record["commit"]
            ):
                return "TAMPERED"
        # The rival's half may be sealed under a FOREIGN payload schema: the
        # commit criterion is the shared contract, checked schema-agnostically.
        for record in doc.get("opponent_records", []):
            if "nonce" in record and not audit_foreign.commit_clean(record):
                return "TAMPERED"
        from p2p_police.report import lookup

        return lookup.replay_verdict(doc, log_path)
