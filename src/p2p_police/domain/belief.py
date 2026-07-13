"""Bayesian belief over the rival's location (rulebook ch. 6) — parity-locked.

Per full turn: diffuse (the rival moved one orthogonal step or stayed) ×
scent likelihood (fresh trail = probable presence) × hint likelihood (claims
weighted by a lie detector grounded in the scent evidence, ch. 4 p. 30).
"""

from p2p_police.domain.board import Board
from p2p_police.domain.primitives import Cell, Move
from p2p_police.domain.scent import ScentField

SCENT_LIKELIHOOD_FLOOR = 0.05  # silent cell is missing info, not impossible
TRUE_CLAIM_WEIGHT = 3.0
FALSE_CLAIM_WEIGHT = 0.4
# Book p.30: a truthful fresh trail reads (1-rho)*0.9 ~= 0.81; claims backed by
# far weaker evidence are treated as lies.
LIE_EVIDENCE_FLOOR = 0.4


def claimed_region(claim: str, grid_size: int) -> set[Cell]:
    """Cells consistent with a directional claim (board halves; STAY = all)."""
    half = grid_size / 2
    cells = set()
    for row in range(grid_size):
        for col in range(grid_size):
            if (
                claim == "STAY"
                or (claim == "N" and row < half)
                or (claim == "S" and row >= half)
                or (claim == "W" and col < half)
                or (claim == "E" and col >= half)
            ):
                cells.add((row, col))
    return cells


def claim_is_lie(claim: str, scent: ScentField, grid_size: int) -> bool:
    """The scent map cannot lie: a claimed region with no fresh trail exposes
    the verbal hint (deviation from (1-rho)-decay expectations)."""
    region = claimed_region(claim, grid_size)
    freshest = max((scent.value_at(cell) for cell in region), default=0.0)
    return freshest < LIE_EVIDENCE_FLOOR


class BeliefMap:
    """Posterior P(rival at cell) maintained by one peer about its rival.

    Input: per-turn scent reading + optional hint claim. Output: normalized
    grid + argmax cell. Setup: uniform prior over passable cells.
    """

    def __init__(self, grid_size: int) -> None:
        self.grid_size = grid_size
        uniform = 1.0 / (grid_size * grid_size)
        self._p = [[uniform] * grid_size for _ in range(grid_size)]

    def value_at(self, cell: Cell) -> float:
        return self._p[cell[0]][cell[1]]

    def values(self) -> list[list[float]]:
        return [row.copy() for row in self._p]

    def argmax_cell(self) -> Cell:
        return max(
            ((r, c) for r in range(self.grid_size) for c in range(self.grid_size)),
            key=lambda cell: self._p[cell[0]][cell[1]],
        )

    def _normalize(self) -> None:
        total = sum(sum(row) for row in self._p)
        if total <= 0.0:  # evidence annihilated everything: reset to uniform
            uniform = 1.0 / (self.grid_size * self.grid_size)
            self._p = [[uniform] * self.grid_size for _ in range(self.grid_size)]
            return
        self._p = [[value / total for value in row] for row in self._p]

    def diffuse(self, board: Board) -> None:
        """Movement model: the rival took one orthogonal step or stayed."""
        fresh = [[0.0] * self.grid_size for _ in range(self.grid_size)]
        for row in range(self.grid_size):
            for col in range(self.grid_size):
                mass = self._p[row][col]
                if mass == 0.0 or board.is_barrier((row, col)):
                    continue
                targets = [(row, col)] + [
                    m.applied_to((row, col))
                    for m in (Move.N, Move.S, Move.E, Move.W)
                    if board.is_passable(m.applied_to((row, col)))
                ]
                share = mass / len(targets)
                for r, c in targets:
                    fresh[r][c] += share
        self._p = fresh
        self._normalize()

    def observe_scent(self, scent: ScentField, board: Board) -> None:
        """Weight by trail freshness; barriers hold zero mass."""
        for row in range(self.grid_size):
            for col in range(self.grid_size):
                if board.is_barrier((row, col)):
                    self._p[row][col] = 0.0
                else:
                    likelihood = SCENT_LIKELIHOOD_FLOOR + scent.value_at((row, col))
                    self._p[row][col] *= likelihood
        self._normalize()

    def observe_hint(self, claim: str, scent: ScentField) -> None:
        """Weight the claimed region — inverted when the scent exposes a lie."""
        region = claimed_region(claim, self.grid_size)
        lie = claim_is_lie(claim, scent, self.grid_size)
        inside = FALSE_CLAIM_WEIGHT if lie else TRUE_CLAIM_WEIGHT
        outside = TRUE_CLAIM_WEIGHT if lie else FALSE_CLAIM_WEIGHT
        for row in range(self.grid_size):
            for col in range(self.grid_size):
                self._p[row][col] *= inside if (row, col) in region else outside
        self._normalize()
