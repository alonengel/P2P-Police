"""Hidden-mode capture flows + replay verification of hidden logs."""

import json

import pytest
from hidden_helpers import ScriptedBrain, hidden_config, move, play_pair

from p2p_police.domain.primitives import Role
from p2p_police.sdk.sdk import SimulationSdk

COP_WALK = [move(d) for d in ("S", "S", "S", "E", "E", "E")]


@pytest.mark.slow
def test_capture_claim_flow_lands_and_concedes(config_dir):
    """Cop walks (0,0)->(3,3); the landing claim meets the thief's honest
    concession; both sides audit clean with a consistent reconstruction."""
    reports, wire_log, _police, _thief = play_pair(
        hidden_config(config_dir),
        ScriptedBrain(Role.POLICE, COP_WALK), ScriptedBrain(Role.THIEF, []))
    assert reports["police"]["outcome"] == "capture" == reports["thief"]["outcome"]
    assert all(reports[s]["audit"] == "Verified OK" and reports[s]["digest_match"]
               for s in ("police", "thief"))
    concessions = [p for kind, p in wire_log if kind == "turn"
                   and p.get("claim_response") and p["claim_response"]["caught"]]
    assert concessions, "the truth duty must produce a concession"
    assert concessions[-1]["claim_response"]["claim"] == [3, 3]
    claims = [p["capture_claim"] for kind, p in wire_log
              if kind == "turn" and p.get("capture_claim")]
    assert claims[-1] == [3, 3]  # the cop claimed its landing cell


@pytest.mark.slow
def test_barrier_on_thief_captures_automatically(config_dir):
    """A barrier declared on the thief's cell is capture WITHOUT any claim
    (the book's automatic family) - the thief self-detects and concedes."""
    script = [move(d) for d in ("S", "S", "S", "E", "E")]
    script.append({"type": "barrier", "cell": [3, 3]})
    reports, wire_log, police, thief = play_pair(
        hidden_config(config_dir),
        ScriptedBrain(Role.POLICE, script), ScriptedBrain(Role.THIEF, []))
    assert reports["police"]["outcome"] == "capture" == reports["thief"]["outcome"]
    assert all(reports[s]["audit"] == "Verified OK" and reports[s]["digest_match"]
               for s in ("police", "thief"))
    barriers = [p["barrier_placed"] for kind, p in wire_log
                if kind == "turn" and p.get("barrier_placed")]
    assert barriers == [[3, 3]]
    assert thief.own.board.is_barrier((3, 3))  # declaration absorbed


@pytest.mark.slow
def test_hidden_log_verifies_with_the_replay_machinery(config_dir, tmp_path):
    """The replay verifier accepts hidden-mode logs unchanged: post-audit
    records carry payload+nonce+commit in the exact shape verify-log and
    the replay viewer already consume."""
    reports, _wire_log, police, _thief = play_pair(
        hidden_config(config_dir),
        ScriptedBrain(Role.POLICE, COP_WALK), ScriptedBrain(Role.THIEF, []))
    log_doc = {
        "records": police.exchange.own_records,
        "opponent_records": police.exchange.their_records,
        "summary": {"end_state_digest": reports["police"]["end_state_digest"],
                    "outcome": reports["police"]["outcome"]},
    }
    log_path = tmp_path / "log_hidden.json"
    log_path.write_text(json.dumps(log_doc, ensure_ascii=False), encoding="utf-8")
    # no config artifact rides with this tmp log: the verdict NAMES the
    # seals-only assurance instead of a silent full pass (rule 20)
    assert SimulationSdk.verify_log(str(log_path)).startswith("Verified OK")
    from p2p_police.gui.replay import load_steps  # headless helper only

    _doc, steps, verdict = load_steps(str(log_path))
    assert verdict == "Verified OK"
    assert len(steps) == len(log_doc["records"]) + len(log_doc["opponent_records"])

    tampered = json.loads(log_path.read_text(encoding="utf-8"))
    tampered["records"][0]["payload"]["hint"] = "rewritten after the fact"
    bad_path = tmp_path / "log_tampered.json"
    bad_path.write_text(json.dumps(tampered, ensure_ascii=False), encoding="utf-8")
    assert SimulationSdk.verify_log(str(bad_path)) == "TAMPERED"
