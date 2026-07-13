"""Board tests encode rulebook rules 13-16 and the surrounded-thief geometry
(rule 47): orthogonal+STAY only, barriers permanent and impassable, illegal
targets rejected loudly."""

import pytest

from p2p_police.domain.board import Board
from p2p_police.domain.errors import IllegalBarrierError, IllegalMoveError
from p2p_police.domain.primitives import Move


@pytest.fixture
def board() -> Board:
    return Board(7)


def test_grid_size_below_two_is_rejected() -> None:
    with pytest.raises(ValueError):
        Board(1)


def test_non_int_grid_size_is_rejected() -> None:
    with pytest.raises(ValueError):
        Board("7")  # type: ignore[arg-type]


def test_bounds_cover_the_full_grid(board: Board) -> None:
    assert board.in_bounds((0, 0))
    assert board.in_bounds((6, 6))
    assert not board.in_bounds((-1, 0))
    assert not board.in_bounds((0, 7))


def test_move_off_the_board_is_rejected(board: Board) -> None:
    with pytest.raises(IllegalMoveError):
        board.apply_move((0, 0), Move.N)


def test_move_into_barrier_is_rejected(board: Board) -> None:
    board.add_barrier((0, 1))
    with pytest.raises(IllegalMoveError):
        board.apply_move((0, 0), Move.E)


def test_legal_move_returns_target(board: Board) -> None:
    assert board.apply_move((3, 3), Move.W) == (3, 2)


def test_stay_is_always_returned_even_at_a_corner(board: Board) -> None:
    assert board.apply_move((0, 0), Move.STAY) == (0, 0)


def test_barrier_off_board_is_rejected(board: Board) -> None:
    with pytest.raises(IllegalBarrierError):
        board.add_barrier((7, 0))


def test_duplicate_barrier_is_rejected(board: Board) -> None:
    board.add_barrier((2, 2))
    with pytest.raises(IllegalBarrierError):
        board.add_barrier((2, 2))


def test_barriers_are_permanent_and_reported(board: Board) -> None:
    board.add_barrier((2, 2))
    assert board.is_barrier((2, 2))
    assert board.barriers == frozenset({(2, 2)})


def test_legal_moves_at_open_center(board: Board) -> None:
    assert set(board.legal_moves((3, 3))) == {Move.N, Move.S, Move.E, Move.W, Move.STAY}


def test_legal_moves_at_corner(board: Board) -> None:
    assert set(board.legal_moves((0, 0))) == {Move.S, Move.E, Move.STAY}


def test_surrounded_needs_all_four_neighbors_blocked(board: Board) -> None:
    for cell in [(2, 3), (4, 3), (3, 2)]:
        board.add_barrier(cell)
    assert not board.is_surrounded((3, 3))
    board.add_barrier((3, 4))
    assert board.is_surrounded((3, 3))


def test_corner_cell_is_surrounded_by_two_barriers(board: Board) -> None:
    """Board edges count as impassable, so a corner needs only two barriers."""
    board.add_barrier((0, 1))
    board.add_barrier((1, 0))
    assert board.is_surrounded((0, 0))


def test_stay_does_not_rescue_a_surrounded_cell(board: Board) -> None:
    board.add_barrier((0, 1))
    board.add_barrier((1, 0))
    assert Move.STAY in board.legal_moves((0, 0))
    assert board.is_surrounded((0, 0))
