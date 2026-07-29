"""The GUI replay loader must tolerate a FOREIGN-schema rival half (rule 20
viewer resilience): commit-verified via the shared contract, skipped from
rendering — never a crash. Headless: exercises load_steps/replay_states only."""

import hashlib
import json

from p2p_police.domain import crypto
from p2p_police.domain.crypto import canonical
from p2p_police.gui.replay import load_steps, replay_states


def our_record(step: int, role: str, move: str) -> dict:
    payload = crypto.build_step_payload(
        step, role, 1, "d" * 64, {"type": "move", "move": move}, "h", True)
    nonce = crypto.new_nonce()
    return {"payload": payload, "nonce": nonce,
            "commit": crypto.commit_hash(payload, nonce)}


def foreign_record() -> dict:
    """Commit-clean under the SHARED contract, alien payload schema."""
    payload = {"turn_no": 1, "actor": "fox", "data": {"x": 9}}
    nonce = "ab" * 16
    commit = hashlib.sha256(
        f"{canonical(payload)}|{nonce}".encode()).hexdigest()
    return {"payload": payload, "nonce": nonce, "commit": commit}


def write_log(tmp_path, opponent_records: list) -> str:
    doc = {"game_id": "a-vs-b", "sub_game_number": 1,
           "records": [our_record(1, "police", "E")],
           "opponent_records": opponent_records,
           "summary": {"end_state_digest": "ab" * 32}}
    path = tmp_path / "log_a-vs-b_g01.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    return str(path)


def test_foreign_rival_half_loads_without_crash(tmp_path) -> None:
    doc, merged, verdict = load_steps(write_log(tmp_path, [foreign_record()]))
    assert verdict == "Verified OK"  # commit-clean via the shared contract
    assert len(merged) == 1  # the foreign payload is not renderable
    states = replay_states(merged, 7, (0, 0), (3, 3))
    assert states[-1]["positions"]["police"] == (0, 1)


def test_commit_only_rival_half_loads_without_crash(tmp_path) -> None:
    _doc, merged, verdict = load_steps(write_log(tmp_path, [{"commit": "c" * 64}]))
    assert verdict == "Verified OK"
    assert len(merged) == 1


def test_forged_foreign_record_reads_tampered(tmp_path) -> None:
    record = foreign_record()
    record["payload"]["data"]["x"] = 10  # breaks the shared-contract hash
    _doc, _merged, verdict = load_steps(write_log(tmp_path, [record]))
    assert verdict == "TAMPERED"


def test_unrenderable_action_shape_is_skipped() -> None:
    payload = crypto.build_step_payload(
        1, "police", 1, "d" * 64, {"kind": "leap", "to": [9, 9]}, "h", True)
    states = replay_states([payload], 7, (0, 0), (3, 3))
    assert states[-1]["positions"]["police"] == (0, 0)  # untouched, no crash
