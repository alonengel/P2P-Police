"""Directional-claim regions + the scent-grounded lie check (ch. 4 p. 30).

Split from belief.py for the 150-code-line cap: cells consistent with a
verbal claim, and the trail-evidence test that exposes a lying region —
the scent map cannot lie, so a region with no fresh trail betrays the hint.
"""

from p2p_police.domain.primitives import Cell
from p2p_police.domain.scent import ScentField

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


def region_is_lie(region: set[Cell], scent) -> bool:
    """The scent map cannot lie: a region with no fresh trail exposes the
    verbal hint (deviation from (1-rho)-decay expectations)."""
    freshest = max((scent.value_at(cell) for cell in region), default=0.0)
    return freshest < LIE_EVIDENCE_FLOOR


def claim_is_lie(claim: str, scent: ScentField, grid_size: int) -> bool:
    """Directional-claim form of the region lie check (ch. 4 p. 30)."""
    return region_is_lie(claimed_region(claim, grid_size), scent)
