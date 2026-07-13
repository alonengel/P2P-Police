"""Win conditions and the law of barriers (rulebook ch. 3, rules 46-48).

Two capture families with different downstream obligations (PRD 01):
- AUTOMATIC captures (no claim, no truth-duty): a barrier placed on the
  thief's cell, or a thief left with all four neighbors impassable.
- LANDING capture: cop occupies the thief's cell — at the protocol layer this
  one carries a cryptographic Capture Claim (Phase 6).

Parity-locked with the twin repo.
"""

from dataclasses import dataclass

from p2p_police.domain.board import Board
from p2p_police.domain.errors import IllegalBarrierError
from p2p_police.domain.primitives import Cell, Outcome


@dataclass(frozen=True)
class RuleSet:
    """The agreed movement/turn limits (config `movement_and_barriers`).

    Input: values from the signed game.json. Output: capture/survival verdicts.
    Setup: validated at construction — these are league-audited minimums.
    """

    max_barriers: int
    max_moves: int
    survival_threshold: int

    def __post_init__(self) -> None:
        if self.max_barriers < 0:
            raise ValueError("max_barriers must be >= 0")
        if self.max_moves < 1 or self.survival_threshold < 1:
            raise ValueError("max_moves and survival_threshold must be >= 1")


def validate_barrier_placement(
    board: Board, rules: RuleSet, cop_cell: Cell, target: Cell
) -> None:
    """Enforce the law of barriers before placement (rules 15-16).

    Legal target: on the board, not already a barrier, and at distance <= 1
    from the cop — his own cell or one of the four orthogonal neighbors.
    Quota (max_barriers) may never be exceeded. Raises IllegalBarrierError.
    """
    if len(board.barriers) >= rules.max_barriers:
        raise IllegalBarrierError(
            f"barrier quota exhausted ({rules.max_barriers}); placement rejected"
        )
    distance = abs(cop_cell[0] - target[0]) + abs(cop_cell[1] - target[1])
    if distance > 1:
        raise IllegalBarrierError(
            f"barrier at {target} is distance {distance} from cop {cop_cell}; max is 1"
        )
    if not board.in_bounds(target):
        raise IllegalBarrierError(f"barrier target {target} is off the board")
    if board.is_barrier(target):
        raise IllegalBarrierError(f"cell {target} already holds a barrier")


def landing_capture(cop_cell: Cell, thief_cell: Cell) -> bool:
    """Cop stands on the thief's cell (requires a Capture Claim upstream)."""
    return cop_cell == thief_cell


def barrier_capture(barrier_cell: Cell, thief_cell: Cell) -> bool:
    """A barrier placed on the thief's current cell captures automatically."""
    return barrier_cell == thief_cell


def surrounded_capture(board: Board, thief_cell: Cell) -> bool:
    """A thief with no orthogonal escape counts as captured (rule 47)."""
    return board.is_surrounded(thief_cell)


def outcome_after_full_turn(
    board: Board, rules: RuleSet, cop_cell: Cell, thief_cell: Cell, turns_completed: int
) -> Outcome:
    """Verdict at a full-turn boundary (both agents acted).

    Capture checks precede survival: a thief captured on the final turn is
    captured. Reaching max_moves uncaptured counts as survival (PRD 01
    documented assumption; defaults make both limits 35).
    """
    if landing_capture(cop_cell, thief_cell) or surrounded_capture(board, thief_cell):
        return Outcome.CAPTURE
    if turns_completed >= rules.survival_threshold or turns_completed >= rules.max_moves:
        return Outcome.SURVIVAL
    return Outcome.ONGOING
