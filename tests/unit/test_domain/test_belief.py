"""Belief tests encode ch. 6 (Bayesian posterior) + the ch. 4 p.30 worked
lie-detection example: dead-silent claimed region + hot opposite region."""

import pytest

from p2p_police.domain.belief import BeliefMap, claim_is_lie
from p2p_police.domain.board import Board
from p2p_police.domain.scent import ScentField


def total(belief: BeliefMap) -> float:
    return sum(sum(row) for row in belief.values())


@pytest.fixture
def board() -> Board:
    return Board(7)


def test_prior_is_uniform_and_normalized() -> None:
    belief = BeliefMap(7)
    assert total(belief) == pytest.approx(1.0)
    assert belief.value_at((0, 0)) == pytest.approx(1 / 49)


def test_scent_concentrates_mass_near_fresh_trail(board: Board) -> None:
    scent = ScentField(7)
    scent.update((5, 5))
    belief = BeliefMap(7)
    belief.observe_scent(scent, board)
    assert belief.argmax_cell() == (5, 5)
    assert total(belief) == pytest.approx(1.0)


def test_barriers_hold_zero_mass(board: Board) -> None:
    board.add_barrier((3, 3))
    belief = BeliefMap(7)
    belief.observe_scent(ScentField(7), board)
    assert belief.value_at((3, 3)) == 0.0


def test_diffusion_spreads_and_stays_normalized(board: Board) -> None:
    scent = ScentField(7)
    scent.update((3, 3))
    belief = BeliefMap(7)
    belief.observe_scent(scent, board)
    peak_before = belief.value_at(belief.argmax_cell())
    belief.diffuse(board)
    assert belief.value_at(belief.argmax_cell()) < peak_before
    assert total(belief) == pytest.approx(1.0)


def test_silent_north_exposes_the_lie() -> None:
    """Book p.30: thief claims 'moved north' but the north is dead silent
    while the south-east burns — the claim is a lie."""
    scent = ScentField(7)
    scent.update((5, 5))  # hot SE, silent north
    assert claim_is_lie("N", scent, 7)
    assert not claim_is_lie("S", scent, 7)


def test_lying_hint_re_aims_belief_at_the_scent_source(board: Board) -> None:
    scent = ScentField(7)
    scent.update((5, 5))
    belief = BeliefMap(7)
    belief.observe_scent(scent, board)
    belief.observe_hint("N", scent)  # lie: evidence stays in the south
    row, _ = belief.argmax_cell()
    assert row >= 4


def test_truthful_hint_sharpens_toward_claimed_region(board: Board) -> None:
    scent = ScentField(7)
    scent.update((5, 5))
    belief = BeliefMap(7)
    north_mass_before = sum(belief.value_at((r, c)) for r in range(3) for c in range(7))
    belief.observe_hint("S", scent)  # truthful: south really is hot
    north_mass_after = sum(belief.value_at((r, c)) for r in range(3) for c in range(7))
    assert north_mass_after < north_mass_before
    assert total(belief) == pytest.approx(1.0)


def test_annihilated_posterior_resets_to_uniform(board: Board) -> None:
    for cell in [(0, 1), (1, 0), (1, 1)]:
        board.add_barrier(cell)
    belief = BeliefMap(2)  # tiny board: barriers can zero everything
    tiny_board = Board(2)
    for cell in [(0, 0), (0, 1), (1, 0), (1, 1)]:
        tiny_board.add_barrier(cell)
    belief.observe_scent(ScentField(2, kernel_size=5), tiny_board)
    assert total(belief) == pytest.approx(1.0)
