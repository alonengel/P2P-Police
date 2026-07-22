"""SDK glue for the hidden wire: runtime assembly, watchdog state provider
and technical-loss classification over `own` instead of `engine`."""

import random
from types import SimpleNamespace

from p2p_police.domain.engine import GameEngine
from p2p_police.domain.primitives import Role
from p2p_police.domain.rules import RuleSet
from p2p_police.infra.mcp_server import PeerInboxes
from p2p_police.sdk import hidden, reporting
from p2p_police.shared.config import Config
from p2p_police.strategy.brain_base import RandomBrain
from p2p_police.wire.hidden_runtime import HiddenRuntime


def _hidden_runtime(config_dir) -> HiddenRuntime:
    config = Config.load(config_dir)
    config.private["network"]["wire_shape"] = "reference"
    return hidden.build_runtime(config, transport=None, inboxes=PeerInboxes(),
                                brain=RandomBrain(Role.POLICE, random.Random(5)))


def test_build_runtime_assembles_own_state_from_my_signed_start(config_dir):
    runtime = _hidden_runtime(config_dir)
    assert isinstance(runtime, HiddenRuntime)
    assert runtime.role is Role.POLICE
    assert runtime.own.cell == (0, 0)  # cop_start from the signed terms
    assert Role.THIEF not in runtime.own.positions  # rules 8-9: structural


def test_watchdog_state_provider_never_holds_a_rival_cell(config_dir):
    """Rules 8-9 down to the crash dump: the hidden provider's positions
    block contains exactly one key - this peer's own."""
    provider = reporting.watchdog_state(_hidden_runtime(config_dir))
    state = provider()
    assert state == {"positions": {"police": [0, 0]}, "turns": 0, "outcome": "ongoing"}


def test_watchdog_state_provider_keeps_the_engine_shape_for_bookletter():
    engine = GameEngine(7, (0, 0), (3, 3), RuleSet(14, 35, 35))
    state = reporting.watchdog_state(SimpleNamespace(engine=engine))()
    assert state == {"positions": {"police": [0, 0], "thief": [3, 3]},
                     "turns": 0, "outcome": "ongoing"}


def test_technical_loss_report_digests_own_state_on_the_hidden_wire(config_dir):
    runtime = _hidden_runtime(config_dir)
    report = reporting.technical_loss_report(Role.POLICE, runtime,
                                             RuntimeError("boom"))
    assert report["outcome"] == "technical_loss"
    assert report["end_state_digest"] == runtime.own.digest()
    assert report["turns_completed"] == 0 and report["steps_sealed"] == 0
    assert report["failure"] == "RuntimeError: boom"
