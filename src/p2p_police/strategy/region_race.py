"""The two-front BFS race: the believed thief's SAFE REGION — cells it
reaches strictly before the cop (ties go to the cop: arriving together
is a capture, not an escape).

Mechanism studied from imreeyal's repos (read with the owner's
permission; re-implemented independently, no code copied — returning the
convention their endgame layer applies to our doctrine). Their measured
lesson: a pursuit score that only prices distance chases the peak and a
competent evader circles it forever; pricing the thief's shrinking safe
ground makes the cop pick, among equal-distance approaches, the one
that removes exits — corner compression at zero barrier cost (their
counted conversions run t7-14 on this where distance-only runs t18+).
Wired as a pursuit term behind [strategy.pursuit] w_safe_region,
default 0.0 — the decision stream stays byte-identical until a sweep
arms it (house keep-gate discipline, docs/evidence/cop-strength.md).
"""

from p2p_police.domain.pathfind import bfs_distances
from p2p_police.domain.primitives import Cell


def safe_region_size(board, thief: Cell, cop: Cell) -> int:
    """How many cells the thief reaches strictly before the cop."""
    theirs = bfs_distances(board, thief)
    ours = bfs_distances(board, cop)
    return sum(
        1 for cell, steps in theirs.items()
        if steps < ours.get(cell, board.grid_size * board.grid_size)
    )
