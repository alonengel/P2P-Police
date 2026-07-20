"""In-process lockstep proof: two GeometricRuntimes (police + thief) wired by
loopback transports finish with the SAME outcome and end-state digest — the
unit-level version of the PRD-02 milestone."""

import random
import threading
from pathlib import Path

from p2p_police.domain.engine import GameEngine
from p2p_police.domain.primitives import Role
from p2p_police.infra.mcp_server import PeerInboxes
from p2p_police.peer.runtime import GeometricRuntime
from p2p_police.shared.config import Config
from p2p_police.strategy.brain_base import RandomBrain


class LoopbackTransport:
    """Drops payloads straight into the OPPONENT's inboxes (no network)."""

    def __init__(self, opponent_inboxes: PeerInboxes) -> None:
        self._them = opponent_inboxes

    def send_agreement(self, payload: dict, deadline) -> dict:
        self._them.agreements.put(payload)
        return {"accepted": True}

    def send_turn(self, payload: dict, deadline) -> dict:
        self._them.turns.put(payload)
        return {"accepted": True}

    def send_audit(self, payload: dict, deadline) -> dict:
        self._them.audits.put(payload)
        return {"accepted": True}


def build_runtime(role: Role, config: Config, transport, inboxes, seed: int):
    engine = GameEngine(
        config.grid_size, config.cop_start, config.thief_start, config.rule_set()
    )
    brain = RandomBrain(role, random.Random(seed))
    return GeometricRuntime(role, config, engine, transport, inboxes, brain)


def test_two_runtimes_reach_identical_end_state(config_dir: Path) -> None:
    config = Config.load(config_dir)
    police_in, thief_in = PeerInboxes(), PeerInboxes()
    police = build_runtime(Role.POLICE, config, LoopbackTransport(thief_in), police_in, 7)
    thief = build_runtime(Role.THIEF, config, LoopbackTransport(police_in), thief_in, 99)

    reports: dict[str, dict] = {}
    threads = [
        threading.Thread(target=lambda r=r, n=n: reports.update({n: r.play()}))
        for n, r in (("police", police), ("thief", thief))
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    assert set(reports) == {"police", "thief"}, "a runtime deadlocked"

    assert reports["police"]["outcome"] == reports["thief"]["outcome"]
    assert reports["police"]["end_state_digest"] == reports["thief"]["end_state_digest"]
    assert reports["police"]["digest_match"] and reports["thief"]["digest_match"]
    assert reports["police"]["turns_completed"] == reports["thief"]["turns_completed"]


class SpyBrain(RandomBrain):
    """Records exactly what information the runtime feeds the decision."""

    def decide(self, engine, belief=None):
        self.saw = belief
        return super().decide(engine, belief)


def _half_turn_feed(config: Config) -> object:
    inboxes = PeerInboxes()
    brain = SpyBrain(Role.POLICE, random.Random(5))
    runtime = GeometricRuntime(
        Role.POLICE, config,
        GameEngine(config.grid_size, config.cop_start, config.thief_start,
                   config.rule_set()),
        LoopbackTransport(PeerInboxes()), inboxes, brain)
    runtime._my_half_turn(1)
    return brain.saw


def test_info_mode_default_feeds_belief(config_dir: Path) -> None:
    config = Config.load(config_dir)
    assert _half_turn_feed(config) is not None  # the Dec-POMDP posture


def test_info_mode_exact_feeds_none(config_dir: Path) -> None:
    """Bookletter lock: positions are shared local knowledge - brains may
    read the engine directly (joint-ADR line); the switch is config-driven."""
    config = Config.load(config_dir)
    config.private.setdefault("strategy", {})["info_mode"] = "exact"
    assert _half_turn_feed(config) is None
