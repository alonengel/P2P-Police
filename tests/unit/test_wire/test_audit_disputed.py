"""An honest game must not self-destruct at the audit (imreeyal repo review
2026-08-03, finding #1): a cop can LAND on the thief's true cell while its
belief says otherwise — below the claim threshold nothing is declared, the
thief cannot see the co-location (hidden wire), and the game legitimately
plays on. The strict reconstruction must record that as disputed evidence
(like the foreign tier) and follow the LIVE game's claim-mediated outcome —
never raise tampering. Law captures (barrier/surrounded) stay strict: the
thief self-detects those and playing past them is genuine evidence."""

from p2p_police.domain import crypto
from p2p_police.wire import audit

TERMS = {
    "board_and_agents": {"grid_size": 7, "cop_start": [3, 2], "thief_start": [3, 3]},
    "movement_and_barriers": {"max_barriers": 14, "max_moves": 35,
                              "survival_threshold": 2},
}


def _rec(step: int, role: str, move: str, declared: dict | None = None) -> dict:
    payload = crypto.build_step_payload(step, role, 1, "d",
                                        {"type": "move", "move": move}, "h", True)
    nonce = crypto.new_nonce()
    record = {"payload": payload, "nonce": nonce,
              "commit": crypto.commit_hash(payload, nonce)}
    if declared is not None:
        record["declared"] = declared
    return record


def test_unclaimed_landing_is_disputed_evidence_not_tampering() -> None:
    """Cop lands on the thief's true cell WITHOUT a claim; the thief plays
    on (it cannot know). The replay must continue to the live outcome
    (survival) and record the co-location as disputed_capture."""
    thief = [_rec(1, "thief", "STAY"), _rec(2, "thief", "N")]
    cop = [_rec(1, "police", "E")]  # lands on (3,3) — the thief's cell
    reconstruction = audit.reconstruct(cop, thief, TERMS)
    assert reconstruction["outcome"] == "survival"  # the game the peers lived
    disputed = reconstruction["disputed_capture"]
    assert disputed is not None and disputed["cell"] == [3, 3]


def test_claimed_landing_still_terminates_as_capture() -> None:
    """A CLAIMED landing was conceded live (structural truth duty): the
    closure STAY follows and the replay ends in capture, as before."""
    thief = [_rec(1, "thief", "STAY"), _rec(2, "thief", "STAY")]  # closure
    cop = [_rec(1, "police", "E",
                declared={"capture_claim": [3, 3], "barrier_placed": None,
                          "hint": "h"})]
    reconstruction = audit.reconstruct(cop, thief, TERMS)
    assert reconstruction["outcome"] == "capture"
    assert reconstruction["disputed_capture"] is None


def test_playing_past_a_law_capture_still_raises() -> None:
    """Barrier-on-thief is self-detected by the thief (i_am_captured):
    a real action after it stays tampering evidence."""
    import pytest

    from p2p_police.domain.errors import GameRuleError

    barrier = {"type": "barrier", "cell": [3, 3]}
    payload = crypto.build_step_payload(1, "police", 1, "d", barrier, "h", True)
    nonce = crypto.new_nonce()
    cop = [{"payload": payload, "nonce": nonce,
            "commit": crypto.commit_hash(payload, nonce)}]
    thief = [_rec(1, "thief", "STAY"), _rec(2, "thief", "N")]  # plays past it
    with pytest.raises(GameRuleError):
        audit.reconstruct(cop, thief, TERMS)
