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

import json
from pathlib import Path

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


_LOCK_DOC_PATH = Path(__file__).resolve().parents[3] / "config" / "scent_model_lock.json"
_lock_doc_cache: dict | None = None


def scent_model_spec() -> dict:
    """The locked emission-model document BOTH sides hash (rule 23).

    Since 2026-07-20 this is the LEAGUE-envelope form ({family, name,
    params, example} for `multiplicative_book_v1`), loaded from
    config/scent_model_lock.json so the declared scent_model_sha256 is
    comparable across teams (one shared doc schema, three families). The
    hash equals the registry's pinned value; a bare ad-hoc dict would make
    two correct implementations of the same model refuse each other."""
    global _lock_doc_cache
    if _lock_doc_cache is None:
        _lock_doc_cache = json.loads(_LOCK_DOC_PATH.read_text(encoding="utf-8"))
    return _lock_doc_cache


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
