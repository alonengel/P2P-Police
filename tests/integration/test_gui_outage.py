"""GUI-path liveness when the opponent's tunnel dies mid-game (live
cross-team finding, 2026-07-24): the worker thread classifies
technical_loss at its deadline while the transport keeps beating the
watchdog; the MOMENT the worker ends, _play_with_gui must (1) silence the
watchdog - a classified game must never "fire" 60s later - and (2) release
the Tk mainloop so the report reaches stdout instead of a zombie window."""

import threading
import time

from hidden_helpers import ScriptedBrain

from p2p_police.domain.negotiation import build_agreement
from p2p_police.domain.primitives import Role
from p2p_police.gui import live_view
from p2p_police.infra.mcp_server import PeerInboxes
from p2p_police.peer.runtime import GeometricRuntime
from p2p_police.peer.watchdog import Watchdog
from p2p_police.sdk import hidden as hidden_mod
from p2p_police.sdk import reporting
from p2p_police.sdk.sdk import SimulationSdk
from p2p_police.wire import codec, terms

MY_ROLE, RIVAL = Role.POLICE, "thief"
TURN_TIMEOUT, WATCHDOG_WINDOW = 1.5, 0.6


class StubLiveView:
    """LiveView stand-in with real Tk mainloop semantics: run() blocks until
    the view is told the game ended; a hard cap keeps a red run from hanging."""

    def __init__(self, grid_size, role, start_cell=None):
        self.snapshots: list[dict] = []
        self.finished_outcome: str | None = None
        self._done = threading.Event()

    def feed(self, snapshot: dict) -> None:
        self.snapshots.append(snapshot)

    def finish(self, outcome: str) -> None:
        self.finished_outcome = outcome
        self._done.set()

    def run(self, screenshot_path: str | None = None) -> None:
        self._done.wait(timeout=6.0)


class OutageTransport:
    """Scripted rival + tunnel death. Acks the agreement (injecting the
    rival's own), answers the first `alive` turn pushes with the rival's next
    TurnMessage, then every call retries in beat-sized slices until its
    deadline lapses - the committed McpTransport outage contract (call()
    beats; only the deadline judges the rival)."""

    def __init__(self, inboxes: PeerInboxes, agreement: dict, rival: str,
                 opener: bool, alive: int, respond: bool = True) -> None:
        self.beat = lambda: None
        self.closed = False
        self._inboxes, self._agreement = inboxes, agreement
        self._rival, self._opener, self._alive = rival, opener, alive
        self._respond = respond  # False: the rival goes silent (wait-side outage)
        self._step = 0

    def _rival_turn(self) -> dict:
        self._step += 1
        return codec.build_turn_message(
            self._step, self._rival, "slipping away", {}, f"c{self._step:07d}")

    def _outage(self, deadline) -> None:
        while True:  # connection-flavored failures forever: retry, beating
            self.beat()
            deadline.require("opponent tool call during tunnel outage")
            time.sleep(0.02)

    def send_agreement(self, payload: dict, deadline) -> dict:
        self._inboxes.agreements.put(self._agreement)
        if self._opener:
            self._inboxes.turns.put(self._rival_turn())
        return {"accepted": True}

    def send_turn(self, payload: dict, deadline) -> dict:
        if self._alive <= 0:
            self._outage(deadline)
        self._alive -= 1
        if self._respond:
            self._inboxes.turns.put(self._rival_turn())
        return {"accepted": True}

    def send_audit(self, payload: dict, deadline) -> dict:
        self._outage(deadline)
        return {}

    def send_control(self, payload: dict, deadline) -> dict:
        self._outage(deadline)
        return {}

    def close(self) -> None:
        self.closed = True


def _sdk(config_dir) -> SimulationSdk:
    sdk = SimulationSdk(str(config_dir))
    sdk.config.private["network"]["turn_timeout_seconds"] = TURN_TIMEOUT
    return sdk


def _wire_watchdog(runtime, transport, tmp_path) -> Watchdog:
    """Exactly run_peer's wiring, at drill scale."""
    watchdog = Watchdog(WATCHDOG_WINDOW, reporting.watchdog_state(runtime),
                        transport.close, dump_path=tmp_path / "dump.json",
                        poll_interval=0.05)
    runtime.watchdog = watchdog
    runtime.transport.beat = watchdog.beat
    watchdog.start()
    return watchdog


def _assert_no_fire_no_hang(report, view, watchdog, elapsed) -> None:
    assert report["outcome"] == "technical_loss"
    assert "deadline expired" in report["failure"]
    assert view.finished_outcome == "technical_loss"  # mainloop was released
    assert watchdog.fired is False  # beats ran to the end; then it was stopped
    assert elapsed < 4.5  # no zombie window between worker death and return


def test_hidden_gui_outage_reports_without_watchdog_fire(config_dir, tmp_path, monkeypatch):
    sdk = _sdk(config_dir)
    sdk.config.private["network"]["wire_shape"] = "reference"
    views: list[StubLiveView] = []
    monkeypatch.setattr(live_view, "LiveView",
                        lambda *a, **kw: views.append(StubLiveView(*a, **kw)) or views[-1])
    inboxes = PeerInboxes()
    transport = OutageTransport(inboxes, terms.build_negotiate_message(sdk.config),
                                RIVAL, opener=MY_ROLE is Role.POLICE, alive=2)
    runtime = hidden_mod.build_runtime(
        sdk.config, transport, inboxes, ScriptedBrain(MY_ROLE, []))
    watchdog = _wire_watchdog(runtime, transport, tmp_path)
    start = time.monotonic()
    try:
        report = sdk._play_with_gui(runtime, None)
    finally:
        watchdog.stop()
    _assert_no_fire_no_hang(report, views[0], watchdog, time.monotonic() - start)
    assert runtime.own.turns_completed >= 3  # the outage hit MID-game


def test_geometric_gui_outage_reports_without_watchdog_fire(config_dir, tmp_path, monkeypatch):
    sdk = _sdk(config_dir)
    views: list[StubLiveView] = []
    monkeypatch.setattr(live_view, "LiveView",
                        lambda *a, **kw: views.append(StubLiveView(*a, **kw)) or views[-1])
    inboxes = PeerInboxes()
    agreement = build_agreement(sdk.config.shared, "rivalgrp", identity={})
    # The rival acks our pushes then never answers: the wait-side outage
    # (the 13:28 live run) - the same two GUI hazards must not reappear.
    transport = OutageTransport(inboxes, agreement, RIVAL,
                                opener=False, alive=2, respond=False)
    runtime = GeometricRuntime(MY_ROLE, sdk.config, sdk.build_engine(),
                               transport, inboxes, ScriptedBrain(MY_ROLE, []))
    watchdog = _wire_watchdog(runtime, transport, tmp_path)
    start = time.monotonic()
    try:
        report = sdk._play_with_gui(runtime, None)
    finally:
        watchdog.stop()
    _assert_no_fire_no_hang(report, views[0], watchdog, time.monotonic() - start)
