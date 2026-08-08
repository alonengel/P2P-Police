"""Guard: the committed sparring posture is GENERIC play — uncounted warm-ups
must not leak our tuned play into a rival's cross-game profiler before a
counted series (loaded by `peer --sparring` instead of game.toml)."""

import random
from pathlib import Path

import pytest

from p2p_police.domain.primitives import Role
from p2p_police.shared.config import Config, ConfigError
from p2p_police.shared.interlock import assert_sparring_posture
from p2p_police.strategy.brain_base import resolve_brain
from p2p_police.strategy.police_brain import PoliceBrain
from p2p_police.wire import lock

ROOT = Path(__file__).resolve().parents[3]


def load_sparring() -> Config:
    return Config.load(ROOT / "config", private_file="sparring.toml")


def test_sparring_runs_the_shipped_baseline_brain_only() -> None:
    config = load_sparring()
    assert "strategy" not in config.private  # no class override, no tuned weights
    brain = resolve_brain(config, Role.POLICE, random.Random(0))
    # exactly the shipped brain, with no per-opponent overrides layered on
    assert type(brain) is PoliceBrain


def test_sparring_disarms_deception_and_tuned_terms() -> None:
    config = load_sparring()
    tuning = config.deception()
    assert tuning["max_lies"] == 0  # zero lie budget: every hint truthful
    # The invariant is that sparring carries no OVERRIDES - it inherits the
    # shipped strategy defaults like any other game, and tunes nothing per rival.
    assert "endgame" not in config.private.get("strategy", {})
    assert "info_gain" not in config.private.get("strategy", {})


def test_sparring_emails_nothing() -> None:
    config = load_sparring()
    assert "email" not in config.private  # no recipient, no mode: series email no-ops


def test_sparring_wire_shape_is_selectable() -> None:
    config = load_sparring()
    # Committed default is the league wire since fad7113 (cross-team warm-ups
    # all speak reference-v3); the --wire-shape seam still selects bookletter.
    assert lock.wire_shape(config) == lock.REFERENCE
    config.private["network"]["wire_shape"] = "bookletter"
    assert lock.wire_shape(config) == lock.BOOKLETTER


def test_sparring_identity_stays_real() -> None:
    # Rule 45 + team identity: warm-ups still declare who we really are.
    assert load_sparring().group_id == Config.load(ROOT / "config").group_id


def test_load_time_assertion_accepts_the_committed_sparring_file() -> None:
    """The structural gate `peer --sparring` runs at load must accept the
    posture we actually ship (guards the file against future drift)."""
    assert_sparring_posture(load_sparring().private)  # must not raise


def test_load_time_assertion_refuses_a_tuned_strategy_table() -> None:
    with pytest.raises(ConfigError, match=r"\[strategy\]"):
        assert_sparring_posture({"strategy": {"police_class": "pkg.mod:Cls"}})
    with pytest.raises(ConfigError, match=r"\[strategy\]"):
        assert_sparring_posture({"strategy": {"endgame": {"enabled": True}}})


def test_load_time_assertion_refuses_an_armed_email_path() -> None:
    with pytest.raises(ConfigError, match="never emails"):
        assert_sparring_posture({"email": {"mode": "send", "recipient": "x@example.com"}})
    assert_sparring_posture({"email": {"mode": "disabled"}})  # disabled plays
    assert_sparring_posture({})  # absent plays
