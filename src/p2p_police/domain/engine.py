"""Single-process game engine: the authoritative turn loop of the physics.

Round structure (PRD 01; the intra-round order is formally re-agreed per game
in negotiation — this cop-first cadence is the BOOKLETTER wire's; the
reference-v3 hidden wire we play cross-team is thief-first, see
wire/own_state.py): the COP acts first — a move OR a barrier placement (placing
forgoes the move) — then the THIEF moves, then the full-turn boundary fires:
both scent fields update at the agents' current cells and the outcome is
evaluated. Capture conditions are also checked mid-round the moment they
occur (barrier-on-thief, surrounded thief, landing).

Parity-locked with the twin repo.
"""

from p2p_police.domain.board import Board
from p2p_police.domain.errors import GameRuleError
from p2p_police.domain.primitives import Cell, Move, Outcome, Role
from p2p_police.domain.rules import (
    RuleSet,
    outcome_after_full_turn,
    validate_barrier_placement,
)
from p2p_police.domain.scent import ScentField


class GameEngine:
    """Runs one sub-game's physics from start positions to an outcome.

    Input: agent actions in strict cop-then-thief order.
    Output: positions, scent fields, turns_completed, outcome.
    Setup: grid_size, start cells, RuleSet (from the signed config).
    """

    def __init__(
        self,
        grid_size: int,
        cop_start: Cell,
        thief_start: Cell,
        rules: RuleSet,
        center_intensity: float = 0.9,
        decay: float = 0.10,
        kernel_size: int = 5,
    ) -> None:
        self.board = Board(grid_size)
        if not self.board.is_passable(cop_start) or not self.board.is_passable(thief_start):
            raise ValueError("start cells must be on the board and passable")
        self.positions: dict[Role, Cell] = {Role.POLICE: cop_start, Role.THIEF: thief_start}
        self.rules = rules
        # Pheromone params flow from the signed config so a malformed config is
        # rejected here, at construction, by ScentField's fixed-model guard.
        self.scent: dict[Role, ScentField] = {
            Role.POLICE: ScentField(grid_size, center_intensity, decay, kernel_size),
            Role.THIEF: ScentField(grid_size, center_intensity, decay, kernel_size),
        }
        self.turns_completed = 0
        self.outcome = Outcome.ONGOING
        self._next_actor = Role.POLICE

    @property
    def next_actor(self) -> Role:
        """Whose action the engine expects next (police opens every round)."""
        return self._next_actor

    def _require_turn(self, role: Role) -> None:
        if self.outcome is not Outcome.ONGOING:
            raise GameRuleError(f"game is over ({self.outcome.value}); no further actions")
        if self._next_actor is not role:
            raise GameRuleError(f"not {role.value}'s turn; {self._next_actor.value} acts now")

    def _check_captures_mid_round(self) -> None:
        thief_cell = self.positions[Role.THIEF]
        if self.positions[Role.POLICE] == thief_cell or self.board.is_surrounded(thief_cell):
            self.outcome = Outcome.CAPTURE

    def police_move(self, move: Move) -> Cell:
        """Cop's action variant A: a legal orthogonal step or STAY."""
        self._require_turn(Role.POLICE)
        self.positions[Role.POLICE] = self.board.apply_move(self.positions[Role.POLICE], move)
        self._next_actor = Role.THIEF
        self._check_captures_mid_round()
        return self.positions[Role.POLICE]

    def police_place_barrier(self, target: Cell) -> None:
        """Cop's action variant B: place a barrier, forgoing the move (ch. 3)."""
        self._require_turn(Role.POLICE)
        validate_barrier_placement(self.board, self.rules, self.positions[Role.POLICE], target)
        self.board.add_barrier(target)
        self._next_actor = Role.THIEF
        if target == self.positions[Role.THIEF]:
            self.outcome = Outcome.CAPTURE
            return
        self._check_captures_mid_round()

    def thief_move(self, move: Move) -> Cell:
        """Thief's move; a completed thief action closes the full turn."""
        self._require_turn(Role.THIEF)
        self.positions[Role.THIEF] = self.board.apply_move(self.positions[Role.THIEF], move)
        self._next_actor = Role.POLICE
        self._check_captures_mid_round()
        if self.outcome is Outcome.ONGOING:
            self._close_full_turn()
        return self.positions[Role.THIEF]

    def _close_full_turn(self) -> None:
        """Full-turn boundary: both fields decay+emit ONCE, then verdict."""
        for role in (Role.POLICE, Role.THIEF):
            self.scent[role].update(self.positions[role])
        self.turns_completed += 1
        self.outcome = outcome_after_full_turn(
            self.board,
            self.rules,
            self.positions[Role.POLICE],
            self.positions[Role.THIEF],
            self.turns_completed,
        )
