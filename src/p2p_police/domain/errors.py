"""Typed domain exceptions (parity-locked with the twin repo).

The physics engine rejects illegal actions by raising, never by silently
correcting — an illegal move by the opponent is grounds for technical loss,
so the distinction must surface loudly (rulebook rules 13-16).
"""


class GameRuleError(Exception):
    """Base class for violations of the game physics."""


class IllegalMoveError(GameRuleError):
    """Move target is off-board or blocked by a barrier."""


class IllegalBarrierError(GameRuleError):
    """Barrier placement violates distance, quota, or duplication rules."""


class IllegalTransitionError(GameRuleError):
    """State machine asked to perform a transition its table forbids."""


class RivalBreachError(GameRuleError):
    """A rule breach PROVEN from the rival's own message (e.g. a declared
    barrier beyond the quota). The technical loss still scores 0/0 (App ו),
    but the report must attribute the breach to the OPPONENT — our own
    report must never name a cheater as winner_group. Raised only where the
    breach is unambiguously theirs, never for local failures."""
