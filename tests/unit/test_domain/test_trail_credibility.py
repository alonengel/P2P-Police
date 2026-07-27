"""Credibility of an ASSERTED trail (reference wire, rules 8-9 boundary).

`smell_grid` rides beside `commit`, never inside it, so no end-of-game hash
audit can check it: a hostile peer may transmit any field at all. Physics is
the only check left - a reading must be explainable by ONE emitter moving a
step per turn. Soundness comes first here: a false refusal is a self-inflicted
denial of service, so the anchor is the AGREED start, never a later estimate.
"""

import pytest

from p2p_police.domain.board import Board
from p2p_police.domain.evidence import TRAIL_CENTER
from p2p_police.domain.scent import ScentField
from p2p_police.domain.trail_forensics import (
    credible_cells,
    incredible_saturation,
    transition_emitters,
)


@pytest.fixture
def board() -> Board:
    return Board(7)


def test_credible_cells_grow_with_the_movement_model(board: Board) -> None:
    """An emitter obeying the movement model can only deposit within kernel
    range of somewhere it could actually BE. From a known anchor, that set is
    the kernel dilation of the cells reachable in `elapsed` steps - the whole
    board once the anchor goes stale, which is the graceful degradation."""
    tight = credible_cells(board, (3, 3), 0, 7)
    assert (3, 3) in tight and (5, 5) in tight  # kernel reach is Chebyshev 2
    assert (6, 6) not in tight and (0, 0) not in tight
    assert credible_cells(board, (3, 3), 1, 7) > tight  # one step of slack
    assert credible_cells(board, (3, 3), 99, 7) == credible_cells(board, None, 0, 7)


def test_forged_readings_outside_the_movement_model_are_incredible(board: Board) -> None:
    """The security property. On the reference wire `smell_grid` is a plaintext
    sibling of `commit` - never sealed - so a hostile peer can transmit any
    field and no end-of-game hash audit can see it. What it CANNOT do is make
    a forgery obey physics: a plateau stamped across the board, or a field
    saturating everything at once, is unexplainable by one emitter that moves
    a step per turn."""
    allowed = credible_cells(board, (3, 3), 1, 7)
    honest = ScentField(7)
    honest.update((3, 4))  # a real, legal step from the anchor
    assert not incredible_saturation(honest, board, 7, allowed)

    decoy = ScentField(7)
    for _ in range(12):
        decoy.update((0, 6))  # a plateau nowhere near a reachable cell
    assert incredible_saturation(decoy, board, 7, allowed)

    flood = ScentField(7)
    flood._grid = [[TRAIL_CENTER] * 7 for _ in range(7)]  # every cell clamped
    assert incredible_saturation(flood, board, 7, allowed)


def test_credibility_never_rejects_an_honest_walk(board: Board) -> None:
    """No false alarms: a real trail stays credible against an anchor that is
    `elapsed` turns stale, because every cell it ever deposited on sits within
    kernel range of a position reachable in that many steps."""
    scent = ScentField(7)
    walk = [(3, 3), (3, 4), (4, 4), (4, 5), (5, 5), (5, 6), (6, 6)]
    for step, cell in enumerate(walk):
        scent.update(cell)
        allowed = credible_cells(board, (3, 3), step, 7)
        assert not incredible_saturation(scent, board, 7, allowed)


def test_an_honest_transition_admits_exactly_one_emitter(board: Board) -> None:
    """The far tighter constraint the reachability envelope throws away: an
    honest field satisfies the update law EXACTLY, frame to frame, for a
    SINGLE emitter. Measured over 396 frames produced by a foreign
    implementation, every honest transition admitted exactly one emitter and
    none were unexplained - the law is arithmetic, not an approximation."""
    scent = ScentField(7)
    scent.update((3, 3))
    for cell in ((3, 4), (4, 4), (4, 5)):
        previous = scent.values()
        scent.update(cell)
        assert transition_emitters(previous, scent.values(), board, 7) == [cell]


def test_a_value_may_never_fall_faster_than_decay(board: Board) -> None:
    """Why a drifting decoy cannot escape: it moves its plateau, so cells that
    read the clamp last frame read zero this one. The law forbids it outright -
    a deposit is non-negative, so no cell may drop below 0.9x its own previous
    value, whatever the sender claims about where it now stands."""
    scent = ScentField(7)
    for _ in range(12):
        scent.update((3, 3))
    previous = scent.values()
    drifted = ScentField(7)
    for _ in range(12):
        drifted.update((3, 4))  # a legal STEP, but a teleported HISTORY
    assert not transition_emitters(previous, drifted.values(), board, 7)


def test_a_saturated_camp_stays_explainable(board: Board) -> None:
    """No false alarm where information is genuinely lost: under a dweller the
    clamp erases the difference between frames, so the transition is satisfied
    (by more than one candidate) rather than violated."""
    scent = ScentField(7)
    for _ in range(12):
        scent.update((3, 3))
    previous = scent.values()
    scent.update((3, 3))
    assert (3, 3) in transition_emitters(previous, scent.values(), board, 7)
