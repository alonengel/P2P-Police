"""Is a TRANSMITTED trail one an agent could actually have produced?

Split from evidence.py, which decodes what a reading MEANS; this module asks
the prior question of whether to believe it at all. It exists because the
guarantee the rulebook leans on is a property of the WIRE SHAPE: under the
replicated-engine wire the trail is derived from applied moves and cannot lie,
but under the reference wire it is transmitted beside `commit` and never
inside it, so no hash audit can reach it (ADR-0010).

Two checks, weakest first. `incredible_saturation` bounds WHERE a deposit may
appear given the movement model - all that a single frame can support.
`transition_emitters` uses the far tighter constraint between CONSECUTIVE
frames: the update law is arithmetic, so a deposit is non-negative and no cell
may fall below `(1-rho)` times its own previous value. A forgery can respect
the movement model, but it cannot move its own HISTORY.
"""

from p2p_police.domain.board import Board
from p2p_police.domain.evidence import TRAIL_CENTER, TRAIL_KEEP, saturated_cells
from p2p_police.domain.primitives import Cell
from p2p_police.domain.scent import EMISSION_KERNEL, KERNEL_RADIUS

# Frame-to-frame law match. Honest frames from a FOREIGN implementation matched
# bit-exactly (0 misses / 396), and detection held identically from 1e-9 to
# 1e-2, so the loose end of that range is taken: the margin costs nothing and
# absorbs a peer that rounds its field on the way to JSON.
TRANSITION_TOLERANCE = 1e-3


def credible_cells(board: Board, anchor, elapsed: int, grid_size: int) -> set:
    """Cells an emitter last known at `anchor`, `elapsed` turns ago, could
    legally have deposited on NOW: the kernel dilation of everything reachable
    in that many steps. `anchor=None` (or a stale one) yields the whole board,
    which is the graceful degradation - the check only ever tightens."""
    board_cells = {(r, c) for r in range(grid_size) for c in range(grid_size)}
    if anchor is None:
        return board_cells
    # Reachability deliberately IGNORES barriers. Walls appear DURING the game,
    # so a barrier-aware BFS asks "could it reach there on today's board" when
    # the honest answer is "it walked there before the wall existed" - measured
    # as a 22.5% false-refusal rate once a late board filled with walls. Every
    # barrier only ever shrinks the true reachable set, so the wall-free ball
    # is a sound superset: it can miss a forgery, never invent one.
    reachable = {cell for cell in board_cells
                 if abs(cell[0] - anchor[0]) + abs(cell[1] - anchor[1]) <= elapsed}
    return {
        (cell[0] + dr, cell[1] + dc)
        for cell in reachable
        for dr in range(-KERNEL_RADIUS, KERNEL_RADIUS + 1)
        for dc in range(-KERNEL_RADIUS, KERNEL_RADIUS + 1)
    } & board_cells


def transition_emitters(previous: list, current: list, board: Board,
                        grid_size: int, tolerance: float = TRANSITION_TOLERANCE) -> list:
    """Emitter cells whose SINGLE deposit turns `previous` into `current`.

    Input: two consecutive readings of the same rival's field. Output: every
    cell consistent with the book's update law, `[]` when none is - which is
    proof the sender did not produce these two frames by playing.

    This is the constraint the reachability envelope throws away. The law
    `F' = clamp((1-rho)F + delta(c - e), 0, center)` is arithmetic, not an
    approximation, and it binds the WHOLE board every turn: a deposit is
    non-negative, so no cell may fall below `(1-rho)` times its own previous
    value no matter where the sender claims to stand. A forged trail that
    respects the movement model still has to move its HISTORY, and history
    cannot be moved - which is what closes the gap the envelope leaves open.
    """
    candidates = []
    for row in range(grid_size):
        for col in range(grid_size):
            emitter = (row, col)
            # NO barrier filter on the candidate. It looks like a free
            # refinement and is not: the law of barriers lets the cop wall its
            # OWN cell, and it still emits from there that turn, so filtering
            # walls discarded the true emitter and refused an honest frame
            # (measured: 50% of games on the twin's side).
            if all(
                abs(min(TRAIL_CENTER, max(0.0, TRAIL_KEEP * previous[r][c]
                                          + _deposit_at((r, c), emitter)))
                    - current[r][c]) <= tolerance
                for r in range(grid_size)
                for c in range(grid_size)
            ):
                candidates.append(emitter)
    return candidates


def _deposit_at(cell: Cell, emitter: Cell) -> float:
    """This turn's kernel contribution at `cell` from an emitter (0 outside)."""
    row = cell[0] - emitter[0] + KERNEL_RADIUS
    col = cell[1] - emitter[1] + KERNEL_RADIUS
    if 0 <= row < len(EMISSION_KERNEL) and 0 <= col < len(EMISSION_KERNEL):
        return EMISSION_KERNEL[row][col]
    return 0.0


def incredible_saturation(scent, board: Board, grid_size: int, allowed: set) -> bool:
    """Does the reading claim a clamp-level deposit somewhere no emitter obeying
    the movement model could have reached? On the reference wire the trail
    arrives as an ASSERTION (`smell_grid` rides beside `commit`, never inside
    it, so no hash audit can ever check it) - physics is the only check left,
    and a forgery that ignores it is refused whole rather than partly believed.
    """
    return bool(saturated_cells(scent, board, grid_size) - allowed)
