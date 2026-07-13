"""Pheromone (scent) physics — rulebook ch. 4, Appendix VI (all params FIXED).

Update rule, applied exactly ONCE per FULL turn (after both agents acted):
    tau'(c) = clamp((1 - rho) * tau(c) + delta(c), 0, center_intensity)
where delta comes from the 5x5 radial kernel centered on the emitting agent
(the book's reference matrix, Figure 4), clipped at board borders. A cell the
kernel never reached reads 0.0 — silence is missing info, not negative info.

The upper clamp encodes the book's stated range tau in [0, 0.9] under
re-emission (PRD 01 documented assumption). This whole module is part of the
scent model that gets SHA-256-locked with the opponent before a series
(rule 23) and is parity-locked with the twin repo.
"""

from p2p_police.domain.primitives import Cell

# The book's reference emission field (Figure 4): radial Gaussian falloff,
# center 0.9. Literal values, NOT recomputed - both peers must add identical
# deltas byte-for-byte.
EMISSION_KERNEL: tuple[tuple[float, ...], ...] = (
    (0.04, 0.14, 0.20, 0.14, 0.04),
    (0.14, 0.42, 0.62, 0.42, 0.14),
    (0.20, 0.62, 0.90, 0.62, 0.20),
    (0.14, 0.42, 0.62, 0.42, 0.14),
    (0.04, 0.14, 0.20, 0.14, 0.04),
)
KERNEL_RADIUS = 2  # 5x5 kernel => center offset 2


def scent_model_spec() -> dict:
    """The human+machine-readable emission model BOTH sides must lock
    (rule 23) - includes the numeric example and the re-emission CLAMP,
    which extends the book's literal formula (PRD-01 disclosure)."""
    return {
        "formula": "tau' = clamp((1-rho)*tau + delta, 0, center_intensity)",
        "center_intensity": 0.9,
        "decay_rho": 0.10,
        "kernel_5x5": [list(row) for row in EMISSION_KERNEL],
        "clamp_note": "re-emission capped at center_intensity (0.9)",
        "numeric_example": "single deposit at center: 0.9 -> 0.81 -> 0.729",
        "decay_boundary": "once per FULL turn, after both agents acted",
    }


class ScentField:
    """One agent's scent trail as read by its rival.

    Input: emitter cell per full turn. Output: per-cell intensities.
    Setup: grid_size; center_intensity / decay / kernel size from the signed
    config's `pheromones` block (validated against the fixed kernel).
    """

    def __init__(
        self,
        grid_size: int,
        center_intensity: float = 0.9,
        decay: float = 0.10,
        kernel_size: int = 5,
    ) -> None:
        if kernel_size != len(EMISSION_KERNEL):
            raise ValueError(f"kernel size {kernel_size} unsupported; model fixes 5")
        if center_intensity != EMISSION_KERNEL[KERNEL_RADIUS][KERNEL_RADIUS]:
            raise ValueError(
                f"center intensity {center_intensity} must equal the kernel center "
                f"{EMISSION_KERNEL[KERNEL_RADIUS][KERNEL_RADIUS]}"
            )
        if not 0.0 < decay < 1.0:
            raise ValueError(f"decay must be in (0,1), got {decay}")
        self.grid_size = grid_size
        self.center_intensity = center_intensity
        self.decay = decay
        self._grid = [[0.0] * grid_size for _ in range(grid_size)]

    def value_at(self, cell: Cell) -> float:
        return self._grid[cell[0]][cell[1]]

    def values(self) -> list[list[float]]:
        """Snapshot copy (callers must never mutate physics state directly)."""
        return [row.copy() for row in self._grid]

    def _delta_at(self, cell: Cell, emitter: Cell) -> float:
        kernel_row = cell[0] - emitter[0] + KERNEL_RADIUS
        kernel_col = cell[1] - emitter[1] + KERNEL_RADIUS
        if 0 <= kernel_row < len(EMISSION_KERNEL) and 0 <= kernel_col < len(EMISSION_KERNEL):
            return EMISSION_KERNEL[kernel_row][kernel_col]
        return 0.0

    def update(self, emitter: Cell) -> None:
        """Apply one full-turn update: decay everything, add this turn's emission.

        Called exactly once per full turn, after BOTH agents acted (the decay
        boundary the golden vectors pin). Clamps to [0, center_intensity].
        """
        keep = 1.0 - self.decay
        for row in range(self.grid_size):
            for col in range(self.grid_size):
                raw = keep * self._grid[row][col] + self._delta_at((row, col), emitter)
                self._grid[row][col] = min(self.center_intensity, max(0.0, raw))
