"""Floored-residue tolerance: a peer that zeroes sub-epsilon residues at
serialization breaks the update law by NOISE, not by motion (najamjad
2026-08-22: smallest value they ever transmit is 0.005341; four refused
frames were single remote cells crossing their ~0.005 floor, prev 0.0054
-> lawful 0.00486 -> transmitted 0). Refusing such frames is correct
evidence but a latch hazard: cells laid on adjacent turns cross the
floor on adjacent turns, and three consecutive breaks latch scent off
for the whole game — a self-inflicted blinding against an honest-but-
sloppy emitter. The tolerance re-solves the transition with the floored
cells restored to their lawful decay; acceptance is recorded separately
(floored evidence, not refusal) so rule-36 reporting keeps the trail.
"""

from p2p_police.domain.board import Board
from p2p_police.domain.scent import ScentField
from p2p_police.peer.floor_tolerance import solve_with_tolerance

BOARD = Board(7)
EPS = 0.006


def _walk(cells):
    field = ScentField(grid_size=7, center_intensity=0.9, decay=0.1)
    frames = []
    for cell in cells:
        field.update(cell)
        frames.append([row[:] for row in field.values()])
    return frames


def test_lawful_transition_passes_through_untouched() -> None:
    frames = _walk([(3, 3), (3, 4), (3, 5)])
    emitters, floored = solve_with_tolerance(frames[1], frames[2],
                                             BOARD, 7, EPS)
    assert emitters and floored == []


def test_najamjad_floor_single_cell_is_tolerated_and_recorded() -> None:
    # Real shape of the 2026-08-22 refusals: a long walk decays one remote
    # cell to ~0.0054; the next frame is lawful EXCEPT that cell reads 0.
    frames = _walk([(6, 1)] + [(3, 3)] * 47 + [(3, 4)])
    prev, cur = frames[-2], frames[-1]
    residue = prev[6][1]
    assert 0 < 0.9 * residue <= EPS  # the fixture really sits at the floor
    floored_cur = [row[:] for row in cur]
    floored_cur[6][1] = 0.0  # their serializer's zeroing
    emitters, floored = solve_with_tolerance(prev, floored_cur, BOARD, 7, EPS)
    assert emitters  # the frame tracks again
    assert floored == [(6, 1)]  # and the event is evidence, not silence


def test_large_cell_zeroing_is_still_refused() -> None:
    # Zeroing a cell whose lawful next value EXCEEDS the epsilon is real
    # physics violation — the tolerance must not launder it.
    frames = _walk([(3, 3), (3, 4), (3, 5)])
    prev, cur = frames[1], frames[2]
    forged = [row[:] for row in cur]
    forged[3][3] = 0.0  # fresh strong history erased
    emitters, floored = solve_with_tolerance(prev, forged, BOARD, 7, EPS)
    assert not emitters and floored == []
