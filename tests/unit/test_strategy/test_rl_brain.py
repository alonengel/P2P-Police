"""RL brain: legal actions only, TD update direction, and the PLAY-TIME paths
(greedy exploitation, belief targeting, weight loading via the real seam)."""

import random
import types

from p2p_police.domain.engine import GameEngine
from p2p_police.domain.primitives import Move, Role
from p2p_police.domain.rules import RuleSet
from p2p_police.strategy import rl_brain
from p2p_police.strategy.brain_base import resolve_brain
from p2p_police.strategy.rl_brain import LinearQBrain, features

RULES = RuleSet(max_barriers=14, max_moves=35, survival_threshold=35)
SEAM_SPEC = "p2p_police.strategy.rl_brain:LinearQBrain"


def _engine() -> GameEngine:
    return GameEngine(7, (0, 0), (3, 3), RULES)


def test_decide_returns_only_legal_moves() -> None:
    engine = _engine()
    brain = LinearQBrain(Role.POLICE, random.Random(1), weights=[0.0] * 5)
    brain.epsilon = 1.0  # force exploration - still legal
    for _ in range(30):
        move = Move[brain.decide(engine)["move"]]
        assert move in engine.board.legal_moves((0, 0))


def test_td_update_moves_q_toward_reward() -> None:
    engine = _engine()
    brain = LinearQBrain(Role.POLICE, random.Random(1), weights=[0.0] * 5)
    before = brain.q(engine, (0, 0), (3, 3), Move.E)
    delta = brain.td_update(engine, (0, 0), (3, 3), Move.E, 1.0, 0.0, 0.5, 0.9)
    assert delta > 0
    assert brain.q(engine, (0, 0), (3, 3), Move.E) > before


def test_features_are_bounded_and_named() -> None:
    engine = _engine()
    phi = features(engine, (0, 0), (3, 3), Move.E)
    assert len(phi) == 5 and all(-1.5 <= f <= 1.5 for f in phi)


def test_seam_spec_loads_and_plays_greedy_with_belief() -> None:
    """The exact league config line, through the real resolve_brain seam."""
    config = types.SimpleNamespace(private={"strategy": {"police_class": SEAM_SPEC}})
    brain = resolve_brain(config, Role.POLICE, random.Random(3))
    assert isinstance(brain, LinearQBrain)
    assert brain.epsilon == 0.0  # play-time default: pure exploitation
    assert len(brain.weights) == 5  # loaded from results/rl_weights.json

    class FixedBelief:
        def argmax_cell(self):
            return (3, 3)

    engine = _engine()
    action = brain.decide(engine, belief=FixedBelief())  # greedy + belief path
    assert Move[action["move"]] in engine.board.legal_moves((0, 0))


def test_missing_weights_file_falls_back_to_prior(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(rl_brain, "WEIGHTS_PATH", tmp_path / "absent.json")
    brain = LinearQBrain(Role.POLICE, random.Random(1))
    assert brain.weights == [0.0, -1.0, -1.0, 0.0, 0.0]  # documented sane prior
