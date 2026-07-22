"""Own-state engine for the hidden-information wire (rules 8-9 structural).

Tracks ONLY what this peer truly knows: its own cell, the public barrier
record (own placements plus every absorbed barrier_placed declaration), its
own scent field under the locked multiplicative_book_v1 model, and the turn
clock. The rival's position is STRUCTURALLY absent — `positions` holds a
single key, so any code that asks for the rival's cell fails loudly instead
of silently peeking. Duck-types the engine surface that Perception, the
Deceiver and the brains read, which is exactly what makes belief-only play
enforceable by shape rather than by discipline.
"""

import hashlib

from p2p_police.domain.board import Board
from p2p_police.domain.crypto import canonical
from p2p_police.domain.errors import GameRuleError
from p2p_police.domain.primitives import Cell, Move, Outcome, Role
from p2p_police.domain.rules import RuleSet, validate_barrier_placement
from p2p_police.domain.scent import ScentField


class ReceivedScent:
    """The rival's transmitted field, absorbed as-is (no receiver-side pass:
    the sender already ran the book-model update before serializing)."""

    def __init__(self, grid_size: int) -> None:
        self.grid_size = grid_size
        self._grid = [[0.0] * grid_size for _ in range(grid_size)]

    def value_at(self, cell: Cell) -> float:
        return self._grid[cell[0]][cell[1]]

    def values(self) -> list[list[float]]:
        return [row.copy() for row in self._grid]

    def absorb(self, smell_grid: dict) -> None:
        """Replace with the latest sparse {"r,c": intensity} snapshot."""
        fresh = [[0.0] * self.grid_size for _ in range(self.grid_size)]
        for key, value in smell_grid.items():
            row, col = (int(part) for part in str(key).split(","))
            if 0 <= row < self.grid_size and 0 <= col < self.grid_size:
                fresh[row][col] = float(value)
        self._grid = fresh


class OwnState:
    """One peer's local truth under the hidden wire.

    Input: own actions + the rival's public declarations. Output: engine-
    shaped reads (positions/board/scent/rules/outcome) minus the rival's
    cell. Setup: role, grid, own start cell, RuleSet, locked scent params.
    """

    def __init__(
        self,
        role: Role,
        grid_size: int,
        start: Cell,
        rules: RuleSet,
        center_intensity: float = 0.9,
        decay: float = 0.10,
        kernel_size: int = 5,
    ) -> None:
        self.role = role
        self.board = Board(grid_size)
        if not self.board.is_passable(start):
            raise ValueError("own start cell must be on the board and passable")
        self.rules = rules
        self.positions: dict[Role, Cell] = {role: start}  # rival key ABSENT
        self.scent = {
            role: ScentField(grid_size, center_intensity, decay, kernel_size),
            role.rival: ReceivedScent(grid_size),
        }
        self.turns_completed = 0
        self.outcome = Outcome.ONGOING
        self.next_actor = Role.POLICE  # police opens every round (PRD 01)

    @property
    def cell(self) -> Cell:
        return self.positions[self.role]

    def apply_own_action(self, action: dict) -> Cell | None:
        """Apply my own move or barrier; returns the barrier cell if placed.

        Legality flows through the SAME domain physics the engine uses
        (board.apply_move / validate_barrier_placement) — reject, never fix.
        """
        if self.next_actor is not self.role:
            raise GameRuleError(f"not {self.role.value}'s half-turn")
        if action["type"] == "barrier":
            if self.role is not Role.POLICE:
                raise GameRuleError("only the police may place barriers")
            target = (action["cell"][0], action["cell"][1])
            validate_barrier_placement(self.board, self.rules, self.cell, target)
            self.board.add_barrier(target)
            self.next_actor = self.role.rival
            return target
        self.positions[self.role] = self.board.apply_move(self.cell, Move[action["move"]])
        self.next_actor = self.role.rival
        return None

    def note_rival_half_turn(self) -> None:
        """The rival's wire message IS its half-turn: pass the token back."""
        if self.next_actor is self.role:
            raise GameRuleError("rival acted while holding no turn token")
        self.next_actor = self.role

    def note_rival_barrier(self, cell) -> None:
        """Absorb a barrier_placed declaration (public, binding for both);
        duplicates are at-least-once transport noise, not errors."""
        target = (cell[0], cell[1])
        if not self.board.in_bounds(target):
            raise GameRuleError(f"declared barrier {target} is off the board")
        if not self.board.is_barrier(target):
            self.board.add_barrier(target)

    def close_full_turn(self) -> None:
        """Full-turn boundary: MY field updates at MY cell (the rival runs
        its own update and transmits the snapshot); the clock advances."""
        self.scent[self.role].update(self.cell)
        self.turns_completed += 1

    def survival_reached(self) -> bool:
        return (
            self.turns_completed >= self.rules.survival_threshold
            or self.turns_completed >= self.rules.max_moves
        )

    def i_am_captured(self) -> bool:
        """The automatic capture families computable from local truth alone:
        a barrier on my cell, or fully surrounded (rule 47) — the book
        resolves both without any claim exchange."""
        return self.board.is_barrier(self.cell) or self.board.is_surrounded(self.cell)

    def digest(self) -> str:
        """Self-only state digest sealed into each record — my cell and the
        public barriers, never any rival data (no shared board frame)."""
        state = {
            "grid_size": self.board.grid_size,
            "self": list(self.cell),
            "barriers": sorted([list(c) for c in self.board.barriers]),
        }
        return hashlib.sha256(canonical(state).encode("utf-8")).hexdigest()
