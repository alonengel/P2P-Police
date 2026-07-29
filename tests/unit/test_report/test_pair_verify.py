"""Pair verification: two logs of one game must be individually untampered
AND mutually consistent (game_uid, digest, outcome, record-for-record)."""

import json

from p2p_police.domain import crypto
from p2p_police.report.pair_verify import cross_check, verify_pair


def _sealed(step: int, role: str) -> dict:
    payload = crypto.build_step_payload(
        step, role, 1, "d" * 64, {"type": "move", "move": "N"}, "a hint", True)
    nonce = crypto.new_nonce()
    return {"payload": payload, "nonce": nonce, "commit": crypto.commit_hash(payload, nonce)}


def _pair(tmp_path):
    a_own = [_sealed(1, "police"), _sealed(2, "police")]
    b_own = [_sealed(1, "thief"), _sealed(2, "thief")]
    summary = {"end_state_digest": "e" * 64, "outcome": "survival"}
    doc_a = {"game_uid": "uid-1", "summary": dict(summary, group_id="team-a"),
             "records": a_own, "opponent_records": [dict(r) for r in b_own]}
    doc_b = {"game_uid": "uid-1", "summary": dict(summary, group_id="team-b"),
             "records": b_own, "opponent_records": [dict(r) for r in a_own]}
    return doc_a, doc_b


def _write(tmp_path, doc_a, doc_b):
    pa, pb = tmp_path / "a.json", tmp_path / "b.json"
    pa.write_text(json.dumps(doc_a), encoding="utf-8")
    pb.write_text(json.dumps(doc_b), encoding="utf-8")
    return pa, pb


def test_consistent_pair_verifies_ok(tmp_path) -> None:
    row = verify_pair(*_write(tmp_path, *_pair(tmp_path)))
    assert row["overall"] == "Verified OK"
    assert row["problems"] == [] and row["sides"] == ["team-a", "team-b"]
    assert row["verdict_a"].startswith("Verified OK")
    assert row["verdict_b"].startswith("Verified OK")


def test_tampered_record_is_tampered_overall(tmp_path) -> None:
    doc_a, doc_b = _pair(tmp_path)
    doc_a["records"][0]["payload"]["hint"] = "rewritten after sealing"
    row = verify_pair(*_write(tmp_path, doc_a, doc_b))
    assert row["verdict_a"] == "TAMPERED" and row["overall"] == "TAMPERED"


def test_different_uid_and_digest_are_cross_mismatch(tmp_path) -> None:
    doc_a, doc_b = _pair(tmp_path)
    doc_b["game_uid"] = "uid-2"
    doc_b["summary"]["end_state_digest"] = "f" * 64
    row = verify_pair(*_write(tmp_path, doc_a, doc_b))
    assert row["overall"] == "CROSS-MISMATCH"
    assert any("game_uid" in p for p in row["problems"])
    assert any("end_state_digest" in p for p in row["problems"])


def test_missing_step_in_rivals_view_is_flagged(tmp_path) -> None:
    doc_a, doc_b = _pair(tmp_path)
    doc_b["opponent_records"].pop(0)  # B "lost" one of A's sealed steps
    problems = cross_check(doc_a, doc_b)
    assert any("missing from the rival's view" in p for p in problems)


def test_commit_swap_across_logs_is_flagged(tmp_path) -> None:
    doc_a, doc_b = _pair(tmp_path)
    forged = _sealed(1, "police")  # a different sealed record for the same key
    doc_b["opponent_records"][0] = forged
    problems = cross_check(doc_a, doc_b)
    assert any("commit differs" in p for p in problems)


def test_verdict_absence_on_rival_copy_is_tolerated(tmp_path) -> None:
    doc_a, doc_b = _pair(tmp_path)
    for record in doc_b["opponent_records"]:  # pre-audit copy: intent unknown
        record["payload"] = {k: v for k, v in record["payload"].items() if k != "verdict"}
        del record["nonce"]
    problems = cross_check(doc_a, doc_b)
    assert problems == []
