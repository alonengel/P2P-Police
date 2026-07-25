"""Trail-evidence decode (rulebook ch. 4, Appendix VI) — parity-locked.

A reading of a transmitted scent field is a CLOCK, not a beacon: under the
fixed book model every value is some kernel deposit K_d (placed at Manhattan
ring d of the emitter) decayed ×(1-rho)=0.9 per full turn. A value therefore
decodes to a REACH radius d + age — the Manhattan ball the emitter must
occupy NOW — and its evidence weight spreads over that ball, so an aged
plateau thins out while fresh evidence stays sharp.
"""

import math

from p2p_police.domain.board import Board
from p2p_police.domain.scent import EMISSION_KERNEL, KERNEL_RADIUS

TRAIL_CENTER = EMISSION_KERNEL[KERNEL_RADIUS][KERNEL_RADIUS]  # 0.9, Appendix VI
TRAIL_KEEP = 0.9  # (1 - rho); rho fixed at 0.10 (Appendix VI)
REACH_HORIZON = 8  # readings decoding farther than this carry no evidence
# The kernel's (Manhattan ring, fresh deposit) rungs — every legal fresh value.
_KERNEL_RUNGS: tuple[tuple[int, float], ...] = tuple(sorted({
    (abs(dr) + abs(dc), EMISSION_KERNEL[dr + KERNEL_RADIUS][dc + KERNEL_RADIUS])
    for dr in range(-KERNEL_RADIUS, KERNEL_RADIUS + 1)
    for dc in range(-KERNEL_RADIUS, KERNEL_RADIUS + 1)
}))


def decoded_reach(value: float) -> int | None:
    """Radius of the Manhattan ball the rival must occupy NOW, given one
    reading: the tightest kernel hypothesis min over rungs (d, K) of
    d + age(value | K). Ring rungs (d > 0) are accepted only at age 0 — a
    surviving ring value from an older visit would have been overwritten or
    out-decayed, so aged readings fall back to the center-decay clock.
    None when silent or beyond the horizon."""
    if value <= 0.0:
        return None
    value = min(value, TRAIL_CENTER)
    best = None
    for distance, fresh in _KERNEL_RUNGS:
        if value > fresh + 1e-9:
            continue  # decay only lowers a deposit: hypothesis inconsistent
        age = round(math.log(value / fresh) / math.log(TRAIL_KEEP))
        if distance > 0 and age > 0:
            continue  # ring evidence counts only while it is fresh
        reach = distance + age
        if best is None or reach < best:
            best = reach
    return best if best is not None and best <= REACH_HORIZON else None


def scent_evidence(scent, board: Board, grid_size: int) -> list[list[float]]:
    """Per-cell evidence weights: each decodable reading spreads its value
    over the (passable) cells of its reach ball (reach 0 = a fresh spike)."""
    evidence = [[0.0] * grid_size for _ in range(grid_size)]
    for row in range(grid_size):
        for col in range(grid_size):
            reach = decoded_reach(scent.value_at((row, col)))
            if reach is None:
                continue
            ball = [
                (r, c)
                for r in range(max(0, row - reach), min(grid_size, row + reach + 1))
                for c in range(max(0, col - reach), min(grid_size, col + reach + 1))
                if abs(r - row) + abs(c - col) <= reach and not board.is_barrier((r, c))
            ]
            for r, c in ball:
                evidence[r][c] += scent.value_at((row, col)) / len(ball)
    return evidence
