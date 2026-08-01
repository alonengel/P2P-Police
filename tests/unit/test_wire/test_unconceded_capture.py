"""Rules 46/47 adjudicated from a FOREIGN rival's own revealed positions.

Live finding 2026-08-01: our cop sealed their thief into the SE corner in
three games (barriers (5,6) then (6,5), thief at (6,6)); their peer never ran
its own imprisonment check, played 23 more steps and claimed survival. A
barrier capture is self-declared under hidden information, so the REVEAL is
the only place we can prove it — and the foreign-schema tier was not looking.
"""

from p2p_police.wire import audit_foreign


def rec(step: int, cell: list) -> dict:
    return {"payload": {"step": step, "position": cell}}


def test_sealed_corner_is_named_with_its_evidence() -> None:
    walk = [rec(11, [6, 6]), rec(12, [6, 6]), rec(13, [6, 6])]
    breach = audit_foreign.unconceded_capture(walk, [(5, 6), (6, 5)], 7)
    assert breach is not None
    assert breach["cell"] == [6, 6] and breach["step"] == 11
    assert "47" in breach["rule"]
    assert breach["barriers"] == [[5, 6], [6, 5]]


def test_barrier_on_the_thief_is_rule_46() -> None:
    breach = audit_foreign.unconceded_capture([rec(4, [3, 3])], [(3, 3)], 7)
    assert breach is not None and "46" in breach["rule"]


def test_one_open_neighbour_is_not_a_capture() -> None:
    """Only the LAST exit seals: (5,6) walled alone leaves (6,5) open."""
    assert audit_foreign.unconceded_capture(
        [rec(11, [6, 6]), rec(12, [6, 6])], [(5, 6)], 7) is None


def test_honest_game_reports_nothing() -> None:
    walk = [rec(1, [3, 3]), rec(2, [3, 4]), rec(3, [4, 4])]
    assert audit_foreign.unconceded_capture(walk, [(0, 1), (1, 0)], 7) is None


def test_records_without_positions_derive_nothing() -> None:
    assert audit_foreign.unconceded_capture(
        [{"payload": {"step": 1}}, {"commit": "c"}], [(5, 6), (6, 5)], 7) is None


def test_the_earliest_breach_is_the_one_reported() -> None:
    walk = [rec(9, [0, 0]), rec(11, [6, 6]), rec(12, [6, 6])]
    breach = audit_foreign.unconceded_capture(walk, [(5, 6), (6, 5), (0, 1), (1, 0)], 7)
    assert breach["step"] == 9 and breach["cell"] == [0, 0]  # corner sealed first
