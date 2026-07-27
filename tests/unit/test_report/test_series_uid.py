"""The emitted game_uid must be the one the WIRE agreed, not a local one.

Rule 35 makes the two teams' reports the enforcement mechanism: they are
reconciled by game_uid, so a uid only we can compute makes our report
unjoinable to the sealed evidence and reads as contradictory.

The reference derives it from the flat NEGOTIATED terms
(peer/handshake.py: `derive_game_ids(terms_from_config(config), ...)`), not
from the raw config file. We mirrored the construction but fed it the whole
game.json, which is deterministic too - and permanently different.
"""

import json
from pathlib import Path

from p2p_police.domain import game_ids
from p2p_police.sdk.reporting import _series_uid
from p2p_police.shared.config import Config
from p2p_police.wire import terms as wire_terms

# Verified against the counterparty's independently computed value for the
# played series: deriving from the flat terms reproduces it to the digit.
THEIR_REPORTED_UID = "e351176a-8883-7ce6-aad8-8a50bff637d7"


def test_uid_comes_from_the_flat_negotiated_terms(config_dir: Path, monkeypatch) -> None:
    config = Config.load(config_dir)
    monkeypatch.chdir(config_dir.parent)
    flat = wire_terms.terms_from_shared(config.shared)
    expected = game_ids.derive_game_uid(flat, config.group_id, "imreeyal")
    assert _series_uid(config, "anrbj666-vs-imreeyal", "imreeyal") == expected
    # ...and NOT the whole-config derivation, which no peer can reproduce.
    assert expected != game_ids.derive_game_uid(config.shared, config.group_id, "imreeyal")


def test_uid_matches_the_counterpartys_independent_derivation() -> None:
    """The real cross-check: their peer computed this from its own config."""
    shared = json.loads(Path("config/game.json").read_text(encoding="utf-8"))
    flat = wire_terms.terms_from_shared(shared)
    assert game_ids.derive_game_uid(flat, "anrbj666", "imreeyal") == THEIR_REPORTED_UID


def test_a_stale_marker_from_different_terms_is_not_reused(
    config_dir: Path, monkeypatch, tmp_path: Path
) -> None:
    """The marker froze the FIRST uid ever written for a pairing. With the
    derivation corrected, a marker minted under the old input must not keep
    resurrecting it - it self-invalidates when the terms fingerprint moves."""
    monkeypatch.chdir(tmp_path)
    results = tmp_path / "results"
    results.mkdir()
    (results / ".game_uid_anrbj666-vs-imreeyal").write_text(
        "deadbeef:2f0c25a9-5008-03c7-2d60-645dd51be11a", encoding="utf-8")
    config = Config.load(config_dir)
    flat = wire_terms.terms_from_shared(config.shared)
    fresh = _series_uid(config, "anrbj666-vs-imreeyal", "imreeyal")
    assert fresh == game_ids.derive_game_uid(flat, config.group_id, "imreeyal")
    assert fresh != "2f0c25a9-5008-03c7-2d60-645dd51be11a"
