"""Full hidden-mode (reference-v3) games in-process: the milestone proof.

Two HiddenRuntimes finish a game exchanging ONLY demo-shaped TurnMessages
(commits sealed, reveals deferred to the audit), the negotiation declares
the registry lock hash on both sides, and the end-of-game audit verifies
clean with a consistent physics reconstruction."""

import json
import random
import re

import pytest
from hidden_helpers import ScriptedBrain, hidden_config, move, play_pair

from p2p_police.domain.primitives import Role
from p2p_police.strategy.brain_base import RandomBrain
from p2p_police.wire import codec

REGISTRY_PIN = "229ae6487a418c3fcb6da9be404de2f2533c288ebc228811bff6dedc4164d6f7"
COORDINATE = re.compile(r"[\[\(]\s*\d\s*,\s*\d\s*[\]\)]|\b\d\s*,\s*\d\b")


def assert_clean(reports: dict) -> None:
    for side in ("police", "thief"):
        assert reports[side]["audit"] == "Verified OK", reports[side]
        assert reports[side]["digest_match"] is True, reports[side]
    assert reports["police"]["outcome"] == reports["thief"]["outcome"]
    assert reports["police"]["end_state_digest"] == reports["thief"]["end_state_digest"]
    assert reports["police"]["turns_completed"] == reports["thief"]["turns_completed"]


@pytest.mark.slow
def test_random_hidden_game_ends_in_a_clean_verified_audit(config_dir):
    reports, wire_log, _police, _thief = play_pair(
        hidden_config(config_dir),
        RandomBrain(Role.POLICE, random.Random(7)),
        RandomBrain(Role.THIEF, random.Random(99)))
    assert_clean(reports)
    agreements = [payload for kind, payload in wire_log if kind == "agreement"]
    assert len(agreements) == 2
    assert all(a["wire_shape_sha256"] == REGISTRY_PIN for a in agreements)


@pytest.mark.slow
def test_scripted_survival_game_reaches_the_threshold(config_dir):
    """Cop camps at (0,0); the thief runs out the clock: survival declared
    by win_claim and reproduced by the audit reconstruction."""
    reports, wire_log, _police, _thief = play_pair(
        hidden_config(config_dir),
        ScriptedBrain(Role.POLICE, []), ScriptedBrain(Role.THIEF, []))
    assert_clean(reports)
    assert reports["thief"]["outcome"] == "survival"
    assert reports["thief"]["turns_completed"] == 35
    wins = [p for kind, p in wire_log if kind == "turn" and p.get("win_claim")]
    assert wins and wins[-1]["win_claim"] == {"type": "survival"}


@pytest.mark.slow
def test_wire_secrecy_sweep_over_a_full_game(config_dir):
    """Rules 18 + 27 on the LIVE wire of a whole game: every turn message
    is exactly the demo shape; no nonce, action or verdict ever rides it;
    no hint carries a coordinate-shaped token; reveals happen only at the
    audit boundary."""
    reports, wire_log, police, thief = play_pair(
        hidden_config(config_dir),
        ScriptedBrain(Role.POLICE, [move("S"), move("E")]),
        ScriptedBrain(Role.THIEF, [move("N"), move("W")]))
    assert_clean(reports)
    shape = set(codec.REQUIRED_KEYS) | set(codec.OPTIONAL_KEYS)
    nonces = {record["nonce"]
              for record in police.exchange.own_records + thief.exchange.own_records}
    turn_messages = [payload for kind, payload in wire_log if kind == "turn"]
    assert turn_messages
    for message in turn_messages:
        assert set(message) == shape
        blob = json.dumps(message, ensure_ascii=False)
        assert '"nonce"' not in blob and '"action"' not in blob
        assert '"verdict"' not in blob and '"payload"' not in blob
        assert not any(nonce in blob for nonce in nonces), "rule 18: nonce leaked"
        assert not COORDINATE.search(message["hint"]), "rule 27: coordinates in a hint"
    audits = [payload for kind, payload in wire_log if kind == "audit"]
    assert len(audits) == 2, "reveals must happen exactly at the audit boundary"
    assert all(record.get("nonce") for audit in audits for record in audit["records"])
