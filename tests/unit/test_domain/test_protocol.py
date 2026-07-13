"""Protocol tests: message round-trip, malformed payloads rejected loudly,
single application path, deterministic end-state digest."""

import pytest

from p2p_police.domain import protocol
from p2p_police.domain.engine import GameEngine
from p2p_police.domain.errors import GameRuleError
from p2p_police.domain.primitives import Move, Role
from p2p_police.domain.rules import RuleSet

RULES = RuleSet(max_barriers=14, max_moves=35, survival_threshold=35)


def make_engine() -> GameEngine:
    return GameEngine(7, (0, 0), (3, 3), RULES)


def test_move_message_round_trip() -> None:
    message = protocol.turn_message(1, Role.POLICE, protocol.move_action(Move.E))
    turn, actor, action = protocol.parse_turn_message(message)
    assert (turn, actor) == (1, Role.POLICE)
    assert action == {"type": "move", "move": "E"}


def test_barrier_message_round_trip() -> None:
    message = protocol.turn_message(4, Role.POLICE, protocol.barrier_action((2, 3)))
    _, _, action = protocol.parse_turn_message(message)
    assert action == {"type": "barrier", "cell": [2, 3]}


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"turn": 1, "actor": "judge", "action": {"type": "move", "move": "E"}},
        {"turn": 1, "actor": "police", "action": {"type": "move", "move": "NE"}},
        {"turn": 1, "actor": "police", "action": {"type": "teleport"}},
        {"turn": 1, "actor": "police", "action": {"type": "barrier", "cell": [1]}},
    ],
)
def test_malformed_messages_are_rejected(payload: dict) -> None:
    with pytest.raises(GameRuleError):
        protocol.parse_turn_message(payload)


def test_apply_action_moves_the_right_agent() -> None:
    engine = make_engine()
    protocol.apply_action(engine, Role.POLICE, {"type": "move", "move": "E"})
    assert engine.positions[Role.POLICE] == (0, 1)
    protocol.apply_action(engine, Role.THIEF, {"type": "move", "move": "N"})
    assert engine.positions[Role.THIEF] == (2, 3)


def test_thief_barrier_action_is_rejected() -> None:
    engine = make_engine()
    engine.police_move(Move.STAY)
    with pytest.raises(GameRuleError, match="only the police"):
        protocol.apply_action(engine, Role.THIEF, {"type": "barrier", "cell": [3, 3]})


def test_end_state_digest_is_deterministic_and_state_sensitive() -> None:
    one, two = make_engine(), make_engine()
    for engine in (one, two):
        protocol.apply_action(engine, Role.POLICE, {"type": "move", "move": "E"})
        protocol.apply_action(engine, Role.THIEF, {"type": "move", "move": "W"})
    assert protocol.end_state_digest(one) == protocol.end_state_digest(two)
    protocol.apply_action(one, Role.POLICE, {"type": "move", "move": "S"})
    protocol.apply_action(one, Role.THIEF, {"type": "move", "move": "S"})
    assert protocol.end_state_digest(one) != protocol.end_state_digest(two)
