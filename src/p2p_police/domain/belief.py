"""Bayesian belief over the rival's location (rulebook ch. 6) — parity-locked.

Per full turn: diffuse (the rival moved one orthogonal step or stayed) ×
scent likelihood (reach-decoded trail evidence, domain/evidence.py: fresh
readings spike, aged plateaus thin out) × hint likelihood (claims weighted
by a lie detector grounded in the scent evidence, ch. 4 p. 30) × barrier-
origin likelihood (a declared placement pins the placer — law of barriers).
"""

from p2p_police.domain.board import Board
from p2p_police.domain.evidence import plateau_origin, scent_evidence
from p2p_police.domain.primitives import Cell, Move
from p2p_police.domain.scent import ScentField

SCENT_LIKELIHOOD_FLOOR = 0.05  # silent cell is missing info, not impossible
TRUE_CLAIM_WEIGHT = 3.0
FALSE_CLAIM_WEIGHT = 0.4
# Book p.30: a truthful fresh trail reads (1-rho)*0.9 ~= 0.81; claims backed by
# far weaker evidence are treated as lies.
LIE_EVIDENCE_FLOOR = 0.4
BARRIER_ORIGIN_BOOST = 25.0  # placement-origin cells: near-certain evidence
PLATEAU_ORIGIN_BOOST = 25.0  # a fitted dwell plateau: the same evidence grade


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


def region_is_lie(region: set[Cell], scent) -> bool:
    """The scent map cannot lie: a region with no fresh trail exposes the
    verbal hint (deviation from (1-rho)-decay expectations)."""
    freshest = max((scent.value_at(cell) for cell in region), default=0.0)
    return freshest < LIE_EVIDENCE_FLOOR


def claim_is_lie(claim: str, scent: ScentField, grid_size: int) -> bool:
    """Directional-claim form of the region lie check (ch. 4 p. 30)."""
    return region_is_lie(claimed_region(claim, grid_size), scent)


class BeliefMap:
    """Posterior P(rival at cell) maintained by one peer about its rival.

    Input: per-turn scent reading + optional hint claim / barrier event.
    Output: normalized grid + argmax cell. Setup: uniform prior.
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
        """Weight by reach-decoded trail evidence; barriers hold zero mass."""
        evidence = scent_evidence(scent, board, self.grid_size)
        for row in range(self.grid_size):
            for col in range(self.grid_size):
                if board.is_barrier((row, col)):
                    self._p[row][col] = 0.0
                else:
                    self._p[row][col] *= SCENT_LIKELIHOOD_FLOOR + evidence[row][col]
        self._normalize()

    def observe_region(
        self, region: set[Cell], scent, weights: tuple[float, float] | None = None
    ) -> None:
        """Weight any claimed region — inverted when the scent exposes a lie.

        Optional profiler-advised (inside, outside) weights replace the
        defaults; the per-observation scent check still flips them on a lie —
        evidence always outranks reputation."""
        lie = region_is_lie(region, scent)
        true_w, false_w = weights if weights else (TRUE_CLAIM_WEIGHT, FALSE_CLAIM_WEIGHT)
        inside = false_w if lie else true_w
        outside = true_w if lie else false_w
        for row in range(self.grid_size):
            for col in range(self.grid_size):
                self._p[row][col] *= inside if (row, col) in region else outside
        self._normalize()

    def observe_hint(
        self, claim: str, scent: ScentField,
        weights: tuple[float, float] | None = None,
    ) -> None:
        """Directional claim -> board-half region observation."""
        self.observe_region(claimed_region(claim, self.grid_size), scent, weights)

    def observe_plateau(self, scent: ScentField, board: Board) -> Cell | None:
        """Pin a dwelling rival to the cell its saturated plateau fits.

        Reach-decoding ties flat across a plateau (every cell reads reach 0),
        so a dweller hides inside its own trail; the shape fit breaks that tie
        exactly. Applied as a boost rather than a collapse: a wrong pin must
        stay recoverable by the next turn's evidence. No fit, no observation.
        Returns the pinned cell so the caller can re-anchor its movement model."""
        origin = plateau_origin(scent, board, self.grid_size)
        if origin is None:
            return None
        self._p[origin[0]][origin[1]] *= PLATEAU_ORIGIN_BOOST
        self._normalize()
        return origin

    def observe_barrier(self, barrier: Cell, board: Board) -> None:
        """A declared placement localizes the placer: the target lies on the
        placer's own cell or an orthogonal neighbor (law of barriers), so the
        passable neighbors of the new wall carry near-certain origin mass.
        The wall itself holds none; no passable origin leaves the map as-is."""
        origins = [
            m.applied_to(barrier)
            for m in (Move.N, Move.S, Move.E, Move.W)
            if board.is_passable(m.applied_to(barrier))
        ]
        if not origins:
            return
        self._p[barrier[0]][barrier[1]] = 0.0
        for r, c in origins:
            self._p[r][c] *= BARRIER_ORIGIN_BOOST
        self._normalize()
