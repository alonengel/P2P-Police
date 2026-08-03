"""Rules 46/47 adjudicated from a FOREIGN rival's own revealed positions.

Live finding 2026-08-01: our cop sealed their thief into the SE corner in
three games (barriers (5,6) then (6,5), thief at (6,6)); their peer never ran
its own imprisonment check, played 23 more steps and claimed survival. A
barrier capture is self-declared under hidden information, so the REVEAL is
the only place we can prove it — and the foreign-schema tier was not looking.
"""

from p2p_police.wire import dispute


def rec(step: int, cell: list) -> dict:
    return {"payload": {"step": step, "position": cell}}


SEAL = [(11, (5, 6)), (12, (6, 5))]  # (step placed, cell)


def test_sealed_corner_is_named_with_its_evidence() -> None:
    walk = [rec(12, [6, 6]), rec(13, [6, 6]), rec(14, [6, 6])]
    breach = dispute.unconceded_capture(walk, SEAL, 7)
    assert breach is not None
    assert breach["cell"] == [6, 6] and breach["step"] == 12
    assert "47" in breach["rule"]
    assert breach["barriers"] == [[5, 6], [6, 5]]


def test_a_wall_does_not_constrain_before_it_exists() -> None:
    """The 2026-08-03 false positive: their thief legally stood on (6,5) at
    step 7; we walled that cell at step 12. A final-set comparison called it
    a rule-46 capture five steps before the wall existed."""
    walk = [rec(7, [6, 5]), rec(8, [5, 5]), rec(9, [4, 5])]
    assert dispute.unconceded_capture(walk, SEAL, 7) is None


def test_barrier_on_the_thief_is_rule_46() -> None:
    breach = dispute.unconceded_capture([rec(4, [3, 3])], [(4, (3, 3))], 7)
    assert breach is not None and "46" in breach["rule"]


def test_a_capture_ending_is_never_disputed() -> None:
    """The duty was honoured, whatever route it took."""
    walk = [rec(12, [6, 6]), rec(13, [6, 6])]
    assert dispute.unconceded_capture(walk, SEAL, 7, "capture") is None
    assert dispute.unconceded_capture(walk, SEAL, 7, "survival") is not None


def test_one_open_neighbour_is_not_a_capture() -> None:
    """Only the LAST exit seals: (5,6) walled alone leaves (6,5) open."""
    assert dispute.unconceded_capture(
        [rec(12, [6, 6]), rec(13, [6, 6])], [(11, (5, 6))], 7) is None


def test_honest_game_reports_nothing() -> None:
    walk = [rec(1, [3, 3]), rec(2, [3, 4]), rec(3, [4, 4])]
    assert dispute.unconceded_capture(
        walk, [(1, (0, 1)), (2, (1, 0))], 7) is None


def test_records_without_positions_derive_nothing() -> None:
    assert dispute.unconceded_capture(
        [{"payload": {"step": 1}}, {"commit": "c"}], SEAL, 7) is None


def test_the_timeline_is_read_from_our_own_records() -> None:
    own = [{"payload": {"step": 11, "action": {"type": "barrier", "cell": [5, 6]}}},
           {"payload": {"step": 12, "action": {"type": "move", "move": "N"}}}]
    assert dispute.own_barrier_timeline(own) == [(11, (5, 6))]
