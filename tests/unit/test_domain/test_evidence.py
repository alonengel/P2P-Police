"""Evidence-decode tests: a trail reading is a CLOCK (kernel deposit x0.9
per decay turn), so evidence lands where the rival can be NOW — the
counter-camping property that turns the transmitted trail into a tracker."""

import pytest

from p2p_police.domain.belief import BeliefMap
from p2p_police.domain.board import Board
from p2p_police.domain.evidence import decoded_reach, plateau_origin
from p2p_police.domain.scent import ScentField


@pytest.fixture
def board() -> Board:
    return Board(7)


def test_decoded_reach_inverts_the_book_decay() -> None:
    """A reading = some kernel deposit K_d decayed x0.9 per turn; the reach
    is the tightest consistent d + age. Centers: 0.9 fresh, 0.81 one turn
    old... Fresh ring deposits pin the rival to their own ring distance."""
    assert decoded_reach(0.9) == 0  # fresh center: the rival is HERE
    assert decoded_reach(0.81) == 1  # center one decay turn ago
    assert decoded_reach(0.729) == 2
    assert decoded_reach(0.62) == 1  # fresh orthogonal ring: rival adjacent
    assert decoded_reach(0.2) == 2  # fresh outer ring
    assert decoded_reach(0.04) == 4  # fresh far corner of the 5x5 kernel
    assert decoded_reach(0.0) is None  # silence is missing info, not evidence
    assert decoded_reach(0.001) is None  # beyond the decodable horizon
    assert decoded_reach(1.5) == 0  # clamp guard: never decodes negative age


def test_posterior_chases_the_fresh_spike_not_the_stale_plateau(board: Board) -> None:
    """The counter-camping property: a long camp saturates a 5x5 plateau at
    max intensity; under the earlier raw-intensity weighting the posterior
    locked onto that stale plateau after the rival left (measured: peak 6
    cells behind an 8-step escapee, still 2 from the camp). Reach-decoding
    spreads stale readings over their reach ball while fresh evidence stays
    sharp, so the peak follows the walker and abandons the camp. The peak
    may trail up to ~3 cells: while the walker's kernel keeps recent trail
    cells clamped at max intensity they are indistinguishable from the true
    center — an ambiguity of the clamp itself, not of the decode."""
    scent = ScentField(7)
    for _ in range(9):
        scent.update((1, 1))  # camp: plateau saturates at 0.9
    belief = BeliefMap(7)
    belief.diffuse(board)
    belief.observe_scent(scent, board)
    walk = [(1, 2), (1, 3), (1, 4), (1, 5), (2, 5), (3, 5), (4, 5), (5, 5)]
    for cell in walk:
        scent.update(cell)
        belief.diffuse(board)
        belief.observe_scent(scent, board)
    peak = belief.argmax_cell()
    d_walker = abs(peak[0] - 5) + abs(peak[1] - 5)
    d_camp = abs(peak[0] - 1) + abs(peak[1] - 1)
    assert d_walker <= 3, f"posterior at {peak} lost the walker at (5, 5)"
    assert d_camp >= 4, f"posterior at {peak} still anchored to the camp"


def test_stale_reading_spreads_thinner_than_fresh_spike(board: Board) -> None:
    """One-shot: a 3-turn-old center must put LESS mass on its own cell than
    a fresh center does — the rival had 3 turns to leave that cell."""
    fresh, stale = ScentField(7), ScentField(7)
    fresh.update((3, 3))
    stale.update((3, 3))
    for _ in range(3):
        stale.update((0, 6))  # decay-only turns for the (3,3) deposit
    peaked, aged = BeliefMap(7), BeliefMap(7)
    peaked.observe_scent(fresh, board)
    aged.observe_scent(stale, board)
    assert aged.value_at((3, 3)) < peaked.value_at((3, 3))


def test_plateau_origin_pins_a_camper_the_argmax_cannot_find(board: Board) -> None:
    """The camper's tell. Dwelling re-deposits until every kernel cell whose
    fixed point (delta / rho) reaches the clamp saturates at max intensity —
    so the SHAPE of the saturated set is the emitter's kernel window, clipped
    by the board. Fitting that shape back inverts to the emitter's own cell,
    while the posterior peak (every plateau cell decodes reach 0, so evidence
    ties across all of them) is left several cells adrift."""
    scent = ScentField(7)
    for _ in range(12):
        scent.update((6, 6))  # corner camp: the plateau is clipped two ways
    belief = BeliefMap(7)
    belief.diffuse(board)
    belief.observe_scent(scent, board)
    assert plateau_origin(scent, board, 7) == (6, 6)
    assert belief.argmax_cell() != (6, 6)  # the tie the fit resolves


def test_plateau_origin_stays_silent_when_the_shape_is_ambiguous(board: Board) -> None:
    """No guessing: silence, a lone fresh spike (one cell — no shape yet) and
    a straight open march (a smear that fits no single window) all abstain.
    Abstention is the whole safety property — a pin is acted on as certainty."""
    assert plateau_origin(ScentField(7), board, 7) is None
    fresh = ScentField(7)
    fresh.update((3, 3))
    assert plateau_origin(fresh, board, 7) is None
    marching = ScentField(7)
    for col in range(7):
        marching.update((3, col))
        assert plateau_origin(marching, board, 7) is None


def test_plateau_origin_ignores_walls_and_never_pins_one(board: Board) -> None:
    """Barrier cells hold no emitter and never count against the fit."""
    board.add_barrier((4, 6))
    scent = ScentField(7)
    for _ in range(12):
        scent.update((6, 6))
    assert plateau_origin(scent, board, 7) == (6, 6)


def test_evidence_spread_respects_barriers(board: Board) -> None:
    """Reach balls never place evidence on walls: after an aged reading the
    posterior still holds zero mass on barrier cells."""
    board.add_barrier((3, 4))
    scent = ScentField(7)
    scent.update((3, 3))
    for _ in range(2):
        scent.update((0, 6))  # age the (3,3) deposit to reach 2
    belief = BeliefMap(7)
    belief.observe_scent(scent, board)
    assert belief.value_at((3, 4)) == 0.0
    assert sum(sum(row) for row in belief.values()) == pytest.approx(1.0)
