"""Audit cross-check of LIVE public declarations vs sealed reveals
(rules 15-16, 21-22) + the sub-game binding: a record sealed for another
sub-game re-presented at this audit is tampering evidence."""

import pytest

from p2p_police.domain import crypto
from p2p_police.domain.errors import GameRuleError
from p2p_police.wire import audit

SHARED = {
    "board_and_agents": {"grid_size": 7, "cop_start": [0, 0],
                         "thief_start": [3, 3]},
    "movement_and_barriers": {"max_barriers": 14, "max_moves": 35,
                              "survival_threshold": 2},
}


def sealed(step: int, role: str, action: dict, hint: str = "h",
           sub_game: int = 1, declared: dict | None = None) -> dict:
    payload = crypto.build_step_payload(
        step, role, sub_game, "d" * 64, action, hint, True)
    nonce = crypto.new_nonce()
    record = {"payload": payload, "nonce": nonce,
              "commit": crypto.commit_hash(payload, nonce)}
    if declared is not None:
        record["declared"] = declared
    return record


def survival_walk(police_declared: dict | None) -> tuple[list, list]:
    """Two rounds ending in survival (threshold 2): thief s1, cop s1, thief s2.
    The cop's record is the 'rival half' carrying the declarations under test."""
    ours = [sealed(1, "thief", {"type": "move", "move": "E"}),
            sealed(2, "thief", {"type": "move", "move": "W"})]
    theirs = [sealed(1, "police", {"type": "move", "move": "E"},
                     declared=police_declared)]
    return ours, theirs


def test_matching_declarations_reconstruct_clean() -> None:
    ours, theirs = survival_walk(
        {"barrier_placed": None, "capture_claim": [0, 1], "hint": "h"})
    result = audit.reconstruct(ours, theirs, SHARED, expected_sub_game=1)
    assert result["outcome"] == "survival"


def test_records_without_declared_are_not_refused() -> None:
    """Commit-only history, geometric records and pre-upgrade logs carry no
    declared block — they derive nothing and must never read TAMPERED."""
    ours, theirs = survival_walk(None)
    assert audit.reconstruct(ours, theirs, SHARED)["outcome"] == "survival"


def test_live_hint_differing_from_sealed_hint_is_tampering() -> None:
    ours, theirs = survival_walk(
        {"barrier_placed": None, "capture_claim": None, "hint": "something else"})
    with pytest.raises(GameRuleError, match="hint"):
        audit.reconstruct(ours, theirs, SHARED)


def test_undeclared_sealed_barrier_is_tampering() -> None:
    """Rules 15-16: a barrier sealed but declared as nothing live."""
    ours = [sealed(1, "thief", {"type": "move", "move": "E"}),
            sealed(2, "thief", {"type": "move", "move": "W"})]
    theirs = [sealed(1, "police", {"type": "barrier", "cell": [0, 1]},
                     declared={"barrier_placed": None, "capture_claim": None,
                               "hint": "h"})]
    with pytest.raises(GameRuleError, match="barrier"):
        audit.reconstruct(ours, theirs, SHARED)


def test_barrier_declared_at_another_cell_is_tampering() -> None:
    ours = [sealed(1, "thief", {"type": "move", "move": "E"}),
            sealed(2, "thief", {"type": "move", "move": "W"})]
    theirs = [sealed(1, "police", {"type": "barrier", "cell": [0, 1]},
                     declared={"barrier_placed": [1, 0], "capture_claim": None,
                               "hint": "h"})]
    with pytest.raises(GameRuleError, match="barrier"):
        audit.reconstruct(ours, theirs, SHARED)


def test_false_capture_claim_cell_is_tampering() -> None:
    """Rules 21-22: the live capture claim must name the cell the revealed
    action actually reached."""
    ours, theirs = survival_walk(
        {"barrier_placed": None, "capture_claim": [5, 5], "hint": "h"})
    with pytest.raises(GameRuleError, match="capture claim"):
        audit.reconstruct(ours, theirs, SHARED)


def test_record_from_another_sub_game_is_tampering() -> None:
    ours, theirs = survival_walk(None)
    with pytest.raises(GameRuleError, match="sub-game"):
        audit.reconstruct(ours, theirs, SHARED, expected_sub_game=2)


def test_verify_declared_returns_declared_block() -> None:
    record = sealed(1, "police", {"type": "move", "move": "E"},
                    declared={"barrier_placed": None, "capture_claim": [0, 1],
                              "hint": "h"})
    assert audit.verify_declared(record)["capture_claim"] == [0, 1]
    assert audit.verify_declared({"commit": "c"}) == {}
