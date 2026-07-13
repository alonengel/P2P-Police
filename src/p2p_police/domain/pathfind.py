"""BFS distances on the barrier-aware board (parity-locked).

Manhattan distance lies once barriers exist; both brains reason over TRUE
shortest paths, and both repos must compute them identically.
"""

from collections import deque

from p2p_police.domain.board import Board
from p2p_police.domain.primitives import Cell, Move

UNREACHABLE = -1


def bfs_distances(board: Board, source: Cell) -> dict[Cell, int]:
    """Shortest-path step counts from `source` to every passable cell.

    Input: a board and a passable source. Output: cell -> distance map;
    cells cut off by barriers are absent (treat as UNREACHABLE).
    """
    distances: dict[Cell, int] = {source: 0}
    frontier: deque[Cell] = deque([source])
    while frontier:
        cell = frontier.popleft()
        for move in (Move.N, Move.S, Move.E, Move.W):
            neighbor = move.applied_to(cell)
            if board.is_passable(neighbor) and neighbor not in distances:
                distances[neighbor] = distances[cell] + 1
                frontier.append(neighbor)
    return distances


def distance_between(board: Board, source: Cell, target: Cell) -> int:
    """BFS distance source->target, or UNREACHABLE when barriers cut them off."""
    return bfs_distances(board, source).get(target, UNREACHABLE)
