"""A rival on the league's OTHER scent branch must not blind us.

The league forked: we run the book's `multiplicative_book_v1`, the course
reference and several teams run `subtractive_chebyshev_v1` (SMNGRP05
2026-08-24, ali-ahm1 2026-08-23). Under subtraction a cell legally falls
below (1-rho) times its previous value, so our law solver finds NO emitter
in ANY honest frame: three frames latch `scent_trusted` off and we play the
rest of the sub-game blind against an honest peer. Their own tracker calls
this out — "one disagreement is far likelier to be a dialect than a
forgery" — and tolerates it.

`rival_scent_law = "foreign"` consumes the field as belief evidence and
verifies no decay law. What it does NOT relax is geometry: the saturation
envelope still latches on a deposit nowhere reachable, so a forgery is
still refused.
"""

import pytest

from p2p_police.domain.board import Board
from p2p_police.domain.primitives import Role
from p2p_police.peer.floor_tolerance import law_verdict
from p2p_police.peer.perception import Perception

BOARD = Board(7)


class _Field:
    """A rival field faded SUBTRACTIVELY — the other branch's law."""

    def __init__(self, grid):
        self._grid = grid

    def values(self):
        return self._grid


def _subtractive_frames(turns: int) -> list:
    """Deposit 0.9 at a fixed cell, fade every cell by a flat 0.1."""
    grid = [[0.0] * 7 for _ in range(7)]
    frames = []
    for _ in range(turns):
        grid = [[max(0.0, v - 0.1) for v in row] for row in grid]
        grid[3][3] = 0.9
        grid[3][4] = grid[4][3] = 0.6
        frames.append([row[:] for row in grid])
    return frames


def _percep(law: str) -> Perception:
    return Perception(Role.POLICE, 7, rival_start=(3, 3), rival_scent_law=law)


def test_book_law_latches_off_against_the_other_branch() -> None:
    """The regression this guards: honest subtractive frames blind us."""
    percep = _percep("book")
    for frame in _subtractive_frames(5):
        law_verdict(percep, _Field(frame), BOARD)
        percep._previous_field = frame
    assert percep.scent_trusted is False  # blinded by an HONEST peer


def test_foreign_law_keeps_the_field_usable() -> None:
    percep = _percep("foreign")
    for frame in _subtractive_frames(5):
        assert law_verdict(percep, _Field(frame), BOARD) is False
        percep._previous_field = frame
    assert percep.scent_trusted is True
    assert percep.scent_frames_seen == 5
    assert percep._last_emitter is None  # no trail head is claimed


def test_foreign_law_still_books_an_empty_frame() -> None:
    percep = _percep("foreign")
    empty = [[0.0] * 7 for _ in range(7)]
    assert law_verdict(percep, _Field(empty), BOARD) is False
    assert (percep.scent_frames_empty, percep.scent_frames_seen) == (1, 0)


@pytest.mark.parametrize("law", ["book", "foreign"])
def test_default_is_the_book_law(law: str) -> None:
    assert Perception(Role.POLICE, 7).rival_scent_law == "book"
    assert _percep(law).rival_scent_law == law
