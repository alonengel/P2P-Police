"""Interception targeting: meet the runner, never follow it.

A same-speed pursuer that chases the believed cell can hold the gap but
never close it — a perimeter cycler simply outruns the clock (league
2026-08-11: two live survivals at constant distance-4 tail chase). With the
trail-head pin the belief peak tracks the runner at lag 0-1, so consecutive
peaks give its HEADING — and the winning move is to aim at the first cell
along that heading that WE reach no later than it does. Cutting the lane
forces the runner to turn into shrinking board, where the wall/trap logic
converts.
"""

from p2p_police.domain.pathfind import bfs_distances
from p2p_police.domain.primitives import Cell


def unit_velocity(prev: Cell | None, peak: Cell):
    """The peak's last step, when it moved exactly one cell; else None."""
    if prev is None:
        return None
    delta = (peak[0] - prev[0], peak[1] - prev[1])
    return delta if abs(delta[0]) + abs(delta[1]) == 1 else None


HORIZON = 10  # project the runner this many steps ahead at most


def _project(board, mine, peak: Cell, velocity) -> list:
    """The runner's likely path: straight while passable; at a wall it turns
    like a flee-er — to the passable neighbor FARTHEST from the cop (mine =
    our BFS map doubles as its threat map). Never doubles back."""
    path, cell, vel, prev = [], peak, velocity, peak
    for _ in range(HORIZON):
        nxt = (cell[0] + vel[0], cell[1] + vel[1])
        if not board.is_passable(nxt):
            options = [
                ((cell[0] + d[0], cell[1] + d[1]), d)
                for d in ((-1, 0), (1, 0), (0, -1), (0, 1))
                if board.is_passable((cell[0] + d[0], cell[1] + d[1]))
                and (cell[0] + d[0], cell[1] + d[1]) != prev
            ]
            if not options:
                break
            nxt, vel = max(options, key=lambda o: mine.get(o[0], 0))
        path.append(nxt)
        prev, cell = cell, nxt
    return path


def intercept_target(board, me: Cell, peak: Cell, velocity) -> Cell | None:
    """First cell on the runner's projected path (straight legs + flee-side
    corner turns) that we reach no later than it does (it needs k steps to
    the k-th cell; we commit when our barrier-aware BFS distance is <= k).
    None when no cut exists — then following is all there is."""
    mine = bfs_distances(board, me)
    for k, cell in enumerate(_project(board, mine, peak, velocity), start=1):
        if mine.get(cell, 10**6) <= k:
            return cell
    return None
