"""Guard: the committed sparring posture is GENERIC play — uncounted warm-ups
must not leak our tuned play into a rival's cross-game profiler before a
counted series (loaded by `peer --sparring` instead of game.toml)."""

import random
from pathlib import Path

from p2p_police.domain.primitives import Role
from p2p_police.shared.config import Config
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
    # exactly the shipped baseline: no solver pre-check, no info-gain arming
    assert type(brain) is PoliceBrain


def test_sparring_disarms_deception_and_tuned_terms() -> None:
    config = load_sparring()
    tuning = config.deception()
    assert tuning["max_lies"] == 0  # zero lie budget: every hint truthful
    assert config.private.get("strategy", {}).get("endgame", {}).get("enabled", False) is False
    assert config.private.get("strategy", {}).get("info_gain", {}).get("enabled", False) is False


def test_sparring_emails_nothing() -> None:
    config = load_sparring()
    assert "email" not in config.private  # no recipient, no mode: maybe_email no-ops


def test_sparring_wire_shape_is_selectable() -> None:
    config = load_sparring()
    assert lock.wire_shape(config) == lock.BOOKLETTER  # committed default
    config.private["network"]["wire_shape"] = "reference"  # the --wire-shape seam
    assert lock.wire_shape(config) == lock.REFERENCE


def test_sparring_identity_stays_real() -> None:
    # Rule 45 + team identity: warm-ups still declare who we really are.
    assert load_sparring().group_id == Config.load(ROOT / "config").group_id
