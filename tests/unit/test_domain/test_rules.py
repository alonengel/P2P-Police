"""Rules tests encode rulebook rules 15-16 (barrier law) and 46-48 (captures,
survival, every-scenario scoring)."""

import pytest

from p2p_police.domain.board import Board
from p2p_police.domain.errors import IllegalBarrierError
from p2p_police.domain.primitives import Outcome
from p2p_police.domain.rules import (
    RuleSet,
    barrier_capture,
    landing_capture,
    outcome_after_full_turn,
    surrounded_capture,
    validate_barrier_placement,
)

RULES = RuleSet(max_barriers=14, max_moves=35, survival_threshold=35)


@pytest.fixture
def board() -> Board:
    return Board(7)


def test_ruleset_rejects_nonsense_limits() -> None:
    with pytest.raises(ValueError):
        RuleSet(max_barriers=-1, max_moves=35, survival_threshold=35)
    with pytest.raises(ValueError):
        RuleSet(max_barriers=14, max_moves=0, survival_threshold=35)


def test_barrier_on_own_cell_is_legal(board: Board) -> None:
    validate_barrier_placement(board, RULES, (3, 3), (3, 3))


def test_barrier_on_orthogonal_neighbor_is_legal(board: Board) -> None:
    validate_barrier_placement(board, RULES, (3, 3), (2, 3))


def test_barrier_beyond_distance_one_is_rejected(board: Board) -> None:
    with pytest.raises(IllegalBarrierError):
        validate_barrier_placement(board, RULES, (3, 3), (1, 3))


def test_barrier_on_diagonal_neighbor_is_rejected(board: Board) -> None:
    """Diagonal distance is 2 in Manhattan terms — outside the barrier reach."""
    with pytest.raises(IllegalBarrierError):
        validate_barrier_placement(board, RULES, (3, 3), (2, 2))


def test_barrier_beyond_quota_is_rejected(board: Board) -> None:
    tight = RuleSet(max_barriers=1, max_moves=35, survival_threshold=35)
    board.add_barrier((0, 6))
    with pytest.raises(IllegalBarrierError):
        validate_barrier_placement(board, tight, (3, 3), (3, 4))


def test_barrier_on_existing_barrier_is_rejected(board: Board) -> None:
    board.add_barrier((3, 4))
    with pytest.raises(IllegalBarrierError):
        validate_barrier_placement(board, RULES, (3, 3), (3, 4))


def test_landing_capture_is_cell_equality() -> None:
    assert landing_capture((2, 2), (2, 2))
    assert not landing_capture((2, 2), (2, 3))


def test_barrier_on_thief_cell_captures(board: Board) -> None:
    assert barrier_capture((5, 5), (5, 5))
    assert not barrier_capture((5, 5), (5, 4))


def test_surrounded_thief_is_captured(board: Board) -> None:
    for cell in [(0, 1), (1, 0)]:
        board.add_barrier(cell)
    assert surrounded_capture(board, (0, 0))


def test_outcome_capture_beats_survival_on_final_turn(board: Board) -> None:
    outcome = outcome_after_full_turn(board, RULES, (4, 4), (4, 4), turns_completed=35)
    assert outcome is Outcome.CAPTURE


def test_outcome_survival_at_threshold(board: Board) -> None:
    outcome = outcome_after_full_turn(board, RULES, (0, 0), (6, 6), turns_completed=35)
    assert outcome is Outcome.SURVIVAL


def test_outcome_ongoing_before_threshold(board: Board) -> None:
    outcome = outcome_after_full_turn(board, RULES, (0, 0), (6, 6), turns_completed=34)
    assert outcome is Outcome.ONGOING


def test_outcome_survival_at_move_cap_even_if_threshold_higher(board: Board) -> None:
    """Documented PRD-01 assumption: hitting max_moves uncaptured = survival."""
    rules = RuleSet(max_barriers=14, max_moves=10, survival_threshold=99)
    outcome = outcome_after_full_turn(board, rules, (0, 0), (6, 6), turns_completed=10)
    assert outcome is Outcome.SURVIVAL
