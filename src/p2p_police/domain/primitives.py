"""Core value types of the game physics (parity-locked with the twin repo).

Coordinate convention (rulebook ch. 3, pinned by golden vectors): cells are
(row, col), origin at the TOP-LEFT corner, zero-indexed, rows grow DOWNWARD —
so N decreases the row and S increases it.
"""

from enum import Enum

type Cell = tuple[int, int]


class Move(Enum):
    """The five legal move directions — orthogonal steps or stay, never diagonal.

    Input: none (enum). Output: (row_delta, col_delta) via `delta`.
    """

    N = (-1, 0)
    S = (1, 0)
    E = (0, 1)
    W = (0, -1)
    STAY = (0, 0)

    @property
    def delta(self) -> Cell:
        return self.value

    def applied_to(self, cell: Cell) -> Cell:
        """Return the target cell of this move from `cell` (no legality check)."""
        return (cell[0] + self.value[0], cell[1] + self.value[1])


class Role(Enum):
    """The two game roles; values match the config/CLI vocabulary."""

    POLICE = "police"
    THIEF = "thief"

    @property
    def rival(self) -> "Role":
        return Role.THIEF if self is Role.POLICE else Role.POLICE


class GamePhase(Enum):
    """Legal states of the turn state machine (rulebook ch. 8)."""

    WAITING_FOR_OPPONENT = "WAITING_FOR_OPPONENT"
    COMPUTING_MOVE = "COMPUTING_MOVE"
    COMMITTING = "COMMITTING"
    AWAITING_REVEAL = "AWAITING_REVEAL"
    VERIFYING = "VERIFYING"
    TECHNICAL_LOSS = "TECHNICAL_LOSS"


class Outcome(Enum):
    """How a sub-game ends (rulebook ch. 3 win-conditions table)."""

    ONGOING = "ongoing"
    CAPTURE = "capture"
    SURVIVAL = "survival"
    TECHNICAL_LOSS = "technical_loss"
