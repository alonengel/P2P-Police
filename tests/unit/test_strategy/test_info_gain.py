"""Info-gain term: entropy math, the move-value ordering it induces, and the
promise that it only ever works on belief SNAPSHOTS - never live state."""

import math

from p2p_police.domain.belief import BeliefMap
from p2p_police.shared.tuning import INFO_GAIN_DEFAULTS
from p2p_police.strategy.info_gain import entropy, expected_gain, kernel_reading


class SplitBelief:
    """Half the mass on each of two cells - maximal two-way ambiguity."""

    def __init__(self, grid_size: int, first, second) -> None:
        self.grid_size, self._cells = grid_size, (first, second)

    def values(self) -> list[list[float]]:
        grid = [[0.0] * self.grid_size for _ in range(self.grid_size)]
        for row, col in self._cells:
            grid[row][col] = 0.5
        return grid


def test_kernel_reading_matches_the_fixed_emission_model() -> None:
    assert kernel_reading((3, 3), (3, 3)) == 0.9  # center
    assert kernel_reading((3, 4), (3, 3)) == 0.62  # one step off
    assert kernel_reading((0, 0), (3, 3)) == 0.0  # outside the 5x5 kernel


def test_entropy_basics() -> None:
    assert entropy([1.0]) == 0.0
    assert math.isclose(entropy([0.5, 0.5]), math.log(2))
    assert entropy([]) == 0.0


def test_settled_belief_has_nothing_to_learn() -> None:
    class Point:
        def values(self):
            grid = [[0.0] * 7 for _ in range(7)]
            grid[2][2] = 1.0
            return grid

    assert expected_gain(Point(), (2, 3), INFO_GAIN_DEFAULTS) == 0.0


def test_landing_that_separates_hypotheses_beats_a_deaf_one() -> None:
    """(0,1) reads 0.62 if the thief sits at (0,0) and 0.0 if at (6,6); (3,3)
    reads 0.0 either way. Information lives where predictions differ."""
    belief = SplitBelief(7, (0, 0), (6, 6))
    near = expected_gain(belief, (0, 1), INFO_GAIN_DEFAULTS)
    deaf = expected_gain(belief, (3, 3), INFO_GAIN_DEFAULTS)
    assert near > deaf
    assert deaf == 0.0  # identical predictions -> posterior == prior
    assert near <= math.log(2) + 1e-9  # can never learn more than the ambiguity


def test_expected_gain_never_mutates_the_live_belief() -> None:
    belief = BeliefMap(7)
    before = belief.values()
    expected_gain(belief, (3, 3), INFO_GAIN_DEFAULTS)
    assert belief.values() == before
