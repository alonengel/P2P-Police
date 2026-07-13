"""State-machine tests encode the book's exact transition table (ch. 8):
the normal turn cycle, the three emergency exits, and terminal TECHNICAL_LOSS."""

import pytest

from p2p_police.domain.errors import IllegalTransitionError
from p2p_police.domain.primitives import GamePhase
from p2p_police.domain.state_machine import GamePhaseMachine


def test_starts_waiting_for_opponent() -> None:
    assert GamePhaseMachine().state is GamePhase.WAITING_FOR_OPPONENT


def test_full_normal_cycle_returns_to_waiting() -> None:
    machine = GamePhaseMachine()
    for phase in [
        GamePhase.COMPUTING_MOVE,
        GamePhase.COMMITTING,
        GamePhase.AWAITING_REVEAL,
        GamePhase.VERIFYING,
        GamePhase.WAITING_FOR_OPPONENT,
    ]:
        machine.transition(phase)
    assert machine.state is GamePhase.WAITING_FOR_OPPONENT


@pytest.mark.parametrize("origin", [GamePhase.COMPUTING_MOVE, GamePhase.AWAITING_REVEAL])
def test_emergency_exit_to_technical_loss(origin: GamePhase) -> None:
    machine = GamePhaseMachine()
    machine.transition(GamePhase.COMPUTING_MOVE)
    if origin is GamePhase.AWAITING_REVEAL:
        machine.transition(GamePhase.COMMITTING)
        machine.transition(GamePhase.AWAITING_REVEAL)
    machine.transition(GamePhase.TECHNICAL_LOSS)
    assert machine.is_terminal


def test_technical_loss_is_terminal() -> None:
    machine = GamePhaseMachine()
    machine.transition(GamePhase.COMPUTING_MOVE)
    machine.transition(GamePhase.TECHNICAL_LOSS)
    with pytest.raises(IllegalTransitionError):
        machine.transition(GamePhase.WAITING_FOR_OPPONENT)


def test_skipping_commit_is_illegal() -> None:
    machine = GamePhaseMachine()
    machine.transition(GamePhase.COMPUTING_MOVE)
    with pytest.raises(IllegalTransitionError):
        machine.transition(GamePhase.AWAITING_REVEAL)


def test_committing_cannot_bail_to_technical_loss_directly() -> None:
    """COMMITTING's only legal successor is AWAITING_REVEAL (book table)."""
    machine = GamePhaseMachine()
    machine.transition(GamePhase.COMPUTING_MOVE)
    machine.transition(GamePhase.COMMITTING)
    with pytest.raises(IllegalTransitionError):
        machine.transition(GamePhase.TECHNICAL_LOSS)


def test_can_transition_predicts_without_mutating() -> None:
    machine = GamePhaseMachine()
    assert machine.can_transition(GamePhase.COMPUTING_MOVE)
    assert not machine.can_transition(GamePhase.VERIFYING)
    assert machine.state is GamePhase.WAITING_FOR_OPPONENT
