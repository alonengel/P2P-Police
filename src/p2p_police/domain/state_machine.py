"""Strict turn state machine (rulebook ch. 8, rules 4-5).

Only the transitions in the book's table are legal; anything else raises
immediately — a loud dev-time bug instead of a silent play-time deadlock.
TECHNICAL_LOSS is terminal. Parity-locked with the twin repo.
"""

from p2p_police.domain.errors import IllegalTransitionError
from p2p_police.domain.primitives import GamePhase

_TRANSITIONS: dict[GamePhase, frozenset[GamePhase]] = {
    GamePhase.WAITING_FOR_OPPONENT: frozenset({GamePhase.COMPUTING_MOVE}),
    GamePhase.COMPUTING_MOVE: frozenset(
        {GamePhase.COMMITTING, GamePhase.TECHNICAL_LOSS}
    ),
    GamePhase.COMMITTING: frozenset({GamePhase.AWAITING_REVEAL}),
    GamePhase.AWAITING_REVEAL: frozenset(
        {GamePhase.VERIFYING, GamePhase.TECHNICAL_LOSS}
    ),
    GamePhase.VERIFYING: frozenset({GamePhase.WAITING_FOR_OPPONENT}),
    GamePhase.TECHNICAL_LOSS: frozenset(),
}


class GamePhaseMachine:
    """Guards the turn lifecycle of one peer.

    Input: requested target phases. Output: the new phase, or
    IllegalTransitionError. Setup: starts at WAITING_FOR_OPPONENT.
    """

    def __init__(self) -> None:
        self._state = GamePhase.WAITING_FOR_OPPONENT

    @property
    def state(self) -> GamePhase:
        return self._state

    @property
    def is_terminal(self) -> bool:
        return not _TRANSITIONS[self._state]

    def can_transition(self, target: GamePhase) -> bool:
        return target in _TRANSITIONS[self._state]

    def transition(self, target: GamePhase) -> GamePhase:
        """Move to `target` or raise. Raising beats deadlock (ch. 8)."""
        if not self.can_transition(target):
            raise IllegalTransitionError(
                f"illegal transition: {self._state.value} -> {target.value}"
            )
        self._state = target
        return self._state
