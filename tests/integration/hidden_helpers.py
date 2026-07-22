"""Shared scaffolding for the in-process hidden-mode (reference-v3) games."""

import random
import threading

from p2p_police.domain.primitives import Role
from p2p_police.infra.mcp_server import PeerInboxes
from p2p_police.shared.config import Config
from p2p_police.strategy.brain_base import BrainBase
from p2p_police.wire.hidden_runtime import HiddenRuntime
from p2p_police.wire.own_state import OwnState


class RecordingTransport:
    """Loopback into the rival's inboxes, recording every wire payload."""

    def __init__(self, opponent_inboxes: PeerInboxes, log: list) -> None:
        self._them = opponent_inboxes
        self.log = log

    def send_agreement(self, payload: dict, _deadline) -> dict:
        self.log.append(("agreement", payload))
        self._them.agreements.put(payload)
        return {"accepted": True}

    def send_turn(self, payload: dict, _deadline) -> dict:
        self.log.append(("turn", payload))
        self._them.turns.put(payload)
        return {"accepted": True}

    def send_audit(self, payload: dict, _deadline) -> dict:
        self.log.append(("audit", payload))
        self._them.audits.put(payload)
        return {"accepted": True}


class ScriptedBrain(BrainBase):
    """Plays a fixed action list, then STAYs (deterministic drills)."""

    def __init__(self, role: Role, actions: list[dict]) -> None:
        super().__init__(role, random.Random(0))
        self._actions = list(actions)

    def decide(self, engine, belief=None) -> dict:
        if self._actions:
            return self._actions.pop(0)
        return {"type": "move", "move": "STAY"}


def move(direction: str) -> dict:
    return {"type": "move", "move": direction}


def hidden_config(config_dir) -> Config:
    config = Config.load(config_dir)
    config.private["network"]["wire_shape"] = "reference"
    return config


def build_runtime(role: Role, config: Config, transport, inboxes, brain) -> HiddenRuntime:
    start = config.cop_start if role is Role.POLICE else config.thief_start
    own = OwnState(role, config.grid_size, start, config.rule_set())
    return HiddenRuntime(role, config, own, transport, inboxes, brain)


def play_pair(config: Config, police_brain, thief_brain):
    """Run one full hidden game in-process; returns (reports, wire_log,
    police_runtime, thief_runtime)."""
    police_in, thief_in = PeerInboxes(), PeerInboxes()
    wire_log: list = []
    police = build_runtime(Role.POLICE, config,
                           RecordingTransport(thief_in, wire_log), police_in, police_brain)
    thief = build_runtime(Role.THIEF, config,
                          RecordingTransport(police_in, wire_log), thief_in, thief_brain)
    reports: dict[str, dict] = {}
    threads = [
        threading.Thread(target=lambda r=r, n=n: reports.update({n: r.play()}))
        for n, r in (("police", police), ("thief", thief))
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)
    assert set(reports) == {"police", "thief"}, "a hidden runtime deadlocked"
    return reports, wire_log, police, thief
