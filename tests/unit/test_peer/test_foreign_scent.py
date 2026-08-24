"""The other branch's law, solved: their published subtractive_chebyshev_v1.

Frames are generated here by THEIR algorithm as their own source states it
(SMNGRP05 peer/turn_sender.py: deposit merging by MAXIMUM, then a flat
subtractive decay, once per own turn) - not by ours with a knob flipped. If
our reading of their physics is wrong, these fail.
"""

import pytest

from p2p_police.peer.foreign_scent import DROP, RHO, foreign_emitters, kernel_at

GRID = 7


def _their_step(previous: list, emitter) -> list:
    """One turn of their law: deposit by max, then fade, then drop dust."""
    out = [[0.0] * GRID for _ in range(GRID)]
    for r in range(GRID):
        for c in range(GRID):
            merged = max(previous[r][c], kernel_at((r, c), emitter, GRID))
            faded = round(max(0.0, merged - RHO), 4)
            out[r][c] = 0.0 if faded <= DROP else faded
    return out


def _walk(cells):
    field, frames = [[0.0] * GRID for _ in range(GRID)], []
    for cell in cells:
        field = _their_step(field, cell)
        frames.append([row[:] for row in field])
    return frames


def test_their_kernel_is_linear_chebyshev_not_a_gaussian_table() -> None:
    """0.9 / 0.6 / 0.3, and NO orthogonal-vs-diagonal split (ours has one)."""
    assert kernel_at((3, 3), (3, 3), GRID) == 0.9
    assert kernel_at((3, 4), (3, 3), GRID) == 0.6   # orthogonal
    assert kernel_at((4, 4), (3, 3), GRID) == 0.6   # diagonal - SAME
    assert kernel_at((3, 5), (3, 3), GRID) == 0.3
    assert kernel_at((3, 6), (3, 3), GRID) == 0.0   # outside the 5x5 window


@pytest.mark.parametrize("walk", [
    [(3, 3), (3, 4), (4, 4), (4, 5)],
    [(0, 0), (0, 1), (1, 1)],
    [(6, 6), (6, 5), (5, 5), (5, 4), (4, 4)],
])
def test_emitter_is_recovered_from_consecutive_frames(walk) -> None:
    frames = _walk(walk)
    for index in range(1, len(frames)):
        found = foreign_emitters(frames[index - 1], frames[index], GRID)
        assert walk[index] in found, f"turn {index}: {walk[index]} not in {found}"


def test_a_frame_our_own_law_would_refuse_is_solved_here() -> None:
    """The regression: their honest frames break the book law on every cell."""
    from p2p_police.domain.board import Board
    from p2p_police.domain.trail_forensics import transition_emitters
    frames = _walk([(3, 3), (3, 4), (4, 4)])
    ours = transition_emitters(frames[0], frames[1], Board(GRID), GRID)
    theirs = foreign_emitters(frames[0], frames[1], GRID)
    assert ours == []          # our law cannot explain their honest frame
    assert (3, 4) in theirs    # their law can


def test_noise_yields_no_pin_rather_than_a_wrong_one() -> None:
    frames = _walk([(3, 3), (3, 4)])
    garbage = [[0.42] * GRID for _ in range(GRID)]
    assert foreign_emitters(frames[0], garbage, GRID) == []
