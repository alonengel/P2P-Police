"""Wire-shape lock: registry hash pin + the both-declare refusal rule."""

import tomllib
from pathlib import Path

import pytest

from p2p_police.domain.errors import GameRuleError
from p2p_police.shared.config import Config
from p2p_police.wire import lock

REGISTRY_PIN = "229ae6487a418c3fcb6da9be404de2f2533c288ebc228811bff6dedc4164d6f7"


def test_lock_doc_hashes_to_the_registry_pin():
    assert lock.wire_shape_sha256() == REGISTRY_PIN


def test_lock_doc_is_the_registry_envelope():
    doc = lock.wire_shape_lock_doc()
    assert set(doc) == {"family", "name", "params", "example"}
    assert doc["family"] == "wire_shape"
    assert doc["name"] == "reference-v3"
    assert doc["params"]["rival_position_computable_live"] is False
    assert doc["params"]["move_revealed"] == "at_audit"


def test_default_wire_shape_is_bookletter(config_dir):
    assert lock.wire_shape(Config.load(config_dir)) == lock.BOOKLETTER


def test_committed_game_toml_arms_the_negotiated_wire():
    """The committed default is the pair-negotiated cross-team wire; the
    bookletter runtime stays fully selectable ("bookletter") and untouched."""
    private = tomllib.loads(Path("config/game.toml").read_text(encoding="utf-8"))
    assert private["network"].get("wire_shape") == "reference"


def test_unknown_wire_shape_rejected(config_dir):
    config = Config.load(config_dir)
    config.private["network"]["wire_shape"] = "telepathy"
    with pytest.raises(GameRuleError):
        lock.wire_shape(config)


def test_default_agreement_stays_undeclared(config_dir):
    """Nothing weakened / changed for undeclared games: no new agreement
    key appears unless the reference path is explicitly armed."""
    agreement = lock.extend_agreement({}, Config.load(config_dir))
    assert "wire_shape_sha256" not in agreement


def test_reference_mode_declares_the_registry_hash(config_dir):
    config = Config.load(config_dir)
    config.private["network"]["wire_shape"] = "reference"
    agreement = lock.extend_agreement({}, config)
    assert agreement["wire_shape_sha256"] == REGISTRY_PIN


@pytest.mark.parametrize(
    ("ours", "theirs", "plays"),
    [
        (REGISTRY_PIN, REGISTRY_PIN, True),  # both declare, same doc
        (REGISTRY_PIN, "f" * 64, False),     # both declare, different docs
        (REGISTRY_PIN, None, True),          # we declare, they are silent
        (None, "f" * 64, True),              # they declare, we are silent
        (None, None, True),                  # neither declares
    ],
)
def test_both_declare_refusal_truth_table(ours, theirs, plays):
    mine = {"wire_shape_sha256": ours} if ours else {}
    other = {"wire_shape_sha256": theirs} if theirs else {}
    if plays:
        lock.verify_wire_shape(mine, other)
    else:
        with pytest.raises(GameRuleError):
            lock.verify_wire_shape(mine, other)
