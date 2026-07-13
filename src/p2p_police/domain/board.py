"""The game board: grid bounds, permanent barriers, movement legality.

Input: grid_size (side of the square grid, config `board_and_agents.grid_size`).
Output: legality answers and applied moves. Setup: barriers accumulate over the
game and are irreversible (rulebook "law of barriers").

Parity-locked with the twin repo; behavior pinned by golden vectors.
"""

from p2p_police.domain.errors import IllegalBarrierError, IllegalMoveError
from p2p_police.domain.primitives import Cell, Move

ORTHOGONAL_MOVES = (Move.N, Move.S, Move.E, Move.W)


class Board:
    """Square grid with permanent barriers.

    Input: cells as (row, col). Output: bool legality / applied cells.
    Setup: grid_size >= 2 (validated); barriers start empty.
    """

    def __init__(self, grid_size: int) -> None:
        if not isinstance(grid_size, int) or grid_size < 2:
            raise ValueError(f"grid_size must be an int >= 2, got {grid_size!r}")
        self.grid_size = grid_size
        self._barriers: set[Cell] = set()

    @property
    def barriers(self) -> frozenset[Cell]:
        return frozenset(self._barriers)

    def in_bounds(self, cell: Cell) -> bool:
        row, col = cell
        return 0 <= row < self.grid_size and 0 <= col < self.grid_size

    def is_barrier(self, cell: Cell) -> bool:
        return cell in self._barriers

    def is_passable(self, cell: Cell) -> bool:
        """A cell an agent may occupy: on the board and not a barrier."""
        return self.in_bounds(cell) and not self.is_barrier(cell)

    def add_barrier(self, cell: Cell) -> None:
        """Place a permanent barrier. Raises IllegalBarrierError off-board or on
        an existing barrier (placements are declared, so duplicates are bugs)."""
        if not self.in_bounds(cell):
            raise IllegalBarrierError(f"barrier target {cell} is off the board")
        if cell in self._barriers:
            raise IllegalBarrierError(f"cell {cell} already holds a barrier")
        self._barriers.add(cell)

    def legal_moves(self, cell: Cell) -> list[Move]:
        """All legal moves from `cell`. STAY is always legal for an occupant
        (even one standing where a barrier was later placed under it —
        that situation is capture for the thief and transient for the cop)."""
        moves = [Move.STAY]
        moves.extend(m for m in ORTHOGONAL_MOVES if self.is_passable(m.applied_to(cell)))
        return moves

    def apply_move(self, cell: Cell, move: Move) -> Cell:
        """Return the destination of `move` from `cell`, enforcing legality.

        Raises IllegalMoveError when the target is off-board or a barrier —
        the physics rejects, never corrects (rules 13-14).
        """
        target = move.applied_to(cell)
        if move is Move.STAY:
            return target
        if not self.in_bounds(target):
            raise IllegalMoveError(f"move {move.name} from {cell} leaves the board")
        if self.is_barrier(target):
            raise IllegalMoveError(f"move {move.name} from {cell} hits a barrier at {target}")
        return target

    def is_surrounded(self, cell: Cell) -> bool:
        """True when all four orthogonal neighbors are impassable.

        A fully surrounded thief counts as captured (rule 47); STAY does not
        rescue it — the check deliberately ignores STAY.
        """
        return all(
            not self.is_passable(m.applied_to(cell)) for m in ORTHOGONAL_MOVES
        )
