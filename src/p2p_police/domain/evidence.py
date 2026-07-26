"""Trail-evidence decode (rulebook ch. 4, Appendix VI) — parity-locked.

A reading of a transmitted scent field is a CLOCK, not a beacon: under the
fixed book model every value is some kernel deposit K_d (placed at Manhattan
ring d of the emitter) decayed ×(1-rho)=0.9 per full turn. A value therefore
decodes to a REACH radius d + age — the Manhattan ball the emitter must
occupy NOW — and its evidence weight spreads over that ball, so an aged
plateau thins out while fresh evidence stays sharp.

Second decode (plateau_origin): under re-emission the update rule drives a
kernel cell toward delta/rho, so every offset with delta >= rho*center
SATURATES at the clamp while the far corners never do. A dweller therefore
stamps its own kernel window onto the board at max intensity — and fitting
that SHAPE back inverts to the emitter's own cell, board clipping included.
Reach-decoding alone cannot: every saturated cell reads reach 0, so the
evidence ties flat across the whole plateau. Camping is self-reporting.
"""

import math

from p2p_police.domain.board import Board
from p2p_police.domain.primitives import Cell
from p2p_police.domain.scent import EMISSION_KERNEL, KERNEL_RADIUS

TRAIL_CENTER = EMISSION_KERNEL[KERNEL_RADIUS][KERNEL_RADIUS]  # 0.9, Appendix VI
TRAIL_KEEP = 0.9  # (1 - rho); rho fixed at 0.10 (Appendix VI)
REACH_HORIZON = 8  # readings decoding farther than this carry no evidence
PLATEAU_MIN_CELLS = 4  # fewer saturated cells carry no SHAPE to fit
PLATEAU_MIN_FIT = 0.9  # Jaccard(saturated, hypothesis window) to accept a pin
PLATEAU_MARGIN = 0.05  # ...and the lead the winner must hold over the runner-up
# Offsets whose repeated deposit reaches the clamp: fixed point delta/rho >=
# center <=> delta >= rho * center. The kernel's far corners never get there,
# which is exactly what makes the saturated shape identify its emitter.
SATURATING_OFFSETS: tuple[tuple[int, int], ...] = tuple(
    (dr, dc)
    for dr in range(-KERNEL_RADIUS, KERNEL_RADIUS + 1)
    for dc in range(-KERNEL_RADIUS, KERNEL_RADIUS + 1)
    if EMISSION_KERNEL[dr + KERNEL_RADIUS][dc + KERNEL_RADIUS]
    >= (1.0 - TRAIL_KEEP) * TRAIL_CENTER
)
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


def saturated_cells(scent, board: Board, grid_size: int) -> set:
    """Passable cells reading at the clamp (reach 0) — the plateau's shape."""
    return {
        (row, col)
        for row in range(grid_size)
        for col in range(grid_size)
        if not board.is_barrier((row, col))
        and decoded_reach(scent.value_at((row, col))) == 0
    }


def _saturating_window(cell: Cell, board: Board, grid_size: int) -> set:
    """The cells a dweller at `cell` would drive to the clamp (board-clipped)."""
    return {
        (cell[0] + dr, cell[1] + dc)
        for dr, dc in SATURATING_OFFSETS
        if 0 <= cell[0] + dr < grid_size and 0 <= cell[1] + dc < grid_size
        and not board.is_barrier((cell[0] + dr, cell[1] + dc))
    }


def plateau_origin(scent, board: Board, grid_size: int) -> Cell | None:
    """The cell whose saturating window best FITS the saturated plateau.

    Input: a scent reading + the board. Output: the emitter's own cell, or
    None when no dweller is evidenced. Setup: the module's fit thresholds.
    Fit is Jaccard(plateau, window) — symmetric on purpose: unexplained
    saturation rules a hypothesis out, and so does a window the plateau has
    not filled, which is what keeps a big window from swallowing a small
    plateau. A pin needs both a high fit and a clear lead over the runner-up,
    so a walker's smeared trail (fitting no single window) stays silent.
    """
    plateau = saturated_cells(scent, board, grid_size)
    if len(plateau) < PLATEAU_MIN_CELLS:
        return None
    ranked = sorted(
        (
            (
                len(plateau & window) / len(plateau | window),
                cell,
            )
            for cell in plateau
            for window in (_saturating_window(cell, board, grid_size),)
            if window
        ),
        key=lambda scored: (-scored[0], scored[1]),
    )
    if not ranked or ranked[0][0] < PLATEAU_MIN_FIT:
        return None
    if len(ranked) > 1 and ranked[0][0] - ranked[1][0] < PLATEAU_MARGIN:
        return None
    return ranked[0][1]


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
