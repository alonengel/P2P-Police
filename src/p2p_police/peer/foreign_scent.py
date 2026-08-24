"""Solve the OTHER branch's scent law: `subtractive_chebyshev_v1`.

Our own law (multiplicative kernel, domain/trail_forensics.py) cannot verify a
peer on the reference branch, so `rival_scent_law = "foreign"` consumed their
field without solving it — which cost the emitter pin and left the rule-36
`rival_trail_track` empty against them (SMNGRP05 friendly, 2026-08-24: 35 nulls).

Their law is public and exact (SMNGRP05 `peer/turn_sender.py`: deposit then
decay, once per own turn, and the snapshot transmitted is post-update):

    tmp[c] = max(prev[c], kernel(c, emitter))     # merge by MAXIMUM, not sum
    cur[c] = round(max(0, tmp[c] - rho), 4)       # dropped when <= 0.0005

with `kernel = round(max(0, I - (I / (half + 1)) * chebyshev), 3)` over the
5x5 window — 0.9 / 0.6 / 0.3, no orthogonal-vs-diagonal split.

STRICTLY ADDITIVE by design: a solved frame yields a pin, an unsolved one
yields nothing. It never refuses and never latches trust off, because a
modelling error in OUR reading of THEIR physics must not be able to blind us
against an honest peer — the failure this whole path exists to prevent.
"""

CENTER = 0.9
RHO = 0.1
DROP = 0.0005
TOLERANCE = 1e-3


def kernel_at(cell, emitter, grid_size: int) -> float:
    """Their deposit at `cell` from `emitter` (0 outside the 5x5 window)."""
    half = grid_size // 2 if grid_size < 5 else 2
    d_row, d_col = cell[0] - emitter[0], cell[1] - emitter[1]
    if max(abs(d_row), abs(d_col)) > half:
        return 0.0
    step = CENTER / (half + 1)
    return round(max(0.0, CENTER - step * max(abs(d_row), abs(d_col))), 3)


def _predict(previous: list, emitter, grid_size: int) -> dict:
    """The frame their law produces from `previous` with this emitter."""
    out = {}
    for row in range(grid_size):
        for col in range(grid_size):
            merged = max(previous[row][col], kernel_at((row, col), emitter, grid_size))
            faded = round(max(0.0, merged - RHO), 4)
            out[(row, col)] = 0.0 if faded <= DROP else faded
    return out


def foreign_emitters(previous: list, current: list, grid_size: int) -> list:
    """Every cell whose deposit turns `previous` into `current` under their law.

    Returns [] when no cell explains the transition — which is NOT treated as a
    violation here (see the module docstring): we simply claim no pin.
    """
    candidates = []
    for row in range(grid_size):
        for col in range(grid_size):
            predicted = _predict(previous, (row, col), grid_size)
            if all(abs(predicted[(r, c)] - current[r][c]) <= TOLERANCE
                   for r in range(grid_size) for c in range(grid_size)):
                candidates.append((row, col))
    return candidates
