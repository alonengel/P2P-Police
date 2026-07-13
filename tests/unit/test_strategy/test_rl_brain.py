"""RL brain: legal actions only, TD update moves Q toward the target."""

import random

from p2p_police.domain.engine import GameEngine
from p2p_police.domain.primitives import Move, Role
from p2p_police.domain.rules import RuleSet
from p2p_police.strategy.rl_brain import LinearQBrain, features

RULES = RuleSet(max_barriers=14, max_moves=35, survival_threshold=35)


def test_decide_returns_only_legal_moves() -> None:
    engine = GameEngine(7, (0, 0), (3, 3), RULES)
    brain = LinearQBrain(Role.POLICE, random.Random(1), weights=[0.0] * 5)
    brain.epsilon = 1.0  # force exploration - still legal
    for _ in range(30):
        move = Move[brain.decide(engine)["action" in {} and "x" or "move"]]
        assert move in engine.board.legal_moves((0, 0))


def test_td_update_moves_q_toward_reward() -> None:
    engine = GameEngine(7, (0, 0), (3, 3), RULES)
    brain = LinearQBrain(Role.POLICE, random.Random(1), weights=[0.0] * 5)
    before = brain.q(engine, (0, 0), (3, 3), Move.E)
    delta = brain.td_update(engine, (0, 0), (3, 3), Move.E, 1.0, 0.0, 0.5, 0.9)
    assert delta > 0
    assert brain.q(engine, (0, 0), (3, 3), Move.E) > before


def test_features_are_bounded_and_named() -> None:
    engine = GameEngine(7, (0, 0), (3, 3), RULES)
    phi = features(engine, (0, 0), (3, 3), Move.E)
    assert len(phi) == 5 and all(-1.5 <= f <= 1.5 for f in phi)
