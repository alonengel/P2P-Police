"""Deep-RL brain: MLP math, legality of the extended action space, seam."""

import random
import types

from p2p_police.domain.engine import GameEngine
from p2p_police.domain.primitives import Move, Role
from p2p_police.domain.rules import RuleSet, validate_barrier_placement
from p2p_police.strategy.brain_base import resolve_brain
from p2p_police.strategy.rl_deep import DeepQBrain, Mlp, candidate_actions, features

RULES = RuleSet(max_barriers=14, max_moves=35, survival_threshold=35)
SEAM_SPEC = "p2p_police.strategy.rl_deep:DeepQBrain"


def _engine() -> GameEngine:
    return GameEngine(7, (0, 0), (3, 3), RULES)


def test_candidate_actions_are_moves_plus_legal_barriers() -> None:
    engine = _engine()
    actions = candidate_actions(engine)
    moves = [a for a in actions if a["type"] == "move"]
    barriers = [a for a in actions if a["type"] == "barrier"]
    assert {Move[a["move"]] for a in moves} == set(engine.board.legal_moves((0, 0)))
    assert barriers  # corner cop still has placements within distance <= 1
    for action in barriers:
        validate_barrier_placement(engine.board, RULES, (0, 0), tuple(action["cell"]))


def test_features_are_bounded_and_trap_aware() -> None:
    engine = _engine()
    for action in candidate_actions(engine):
        phi = features(engine, action)
        assert len(phi) == 8 and all(-1.5 <= f <= 1.5 for f in phi)
    barrier = next(a for a in candidate_actions(engine) if a["type"] == "barrier")
    assert features(engine, barrier)[5] == 1.0  # is_barrier flag set


def test_mlp_forward_deterministic_and_sgd_reduces_error() -> None:
    net = Mlp(random.Random(3))
    phi = [1.0, 0.5, -0.1, 0.75, 0.9, 0.0, 1.0, 0.0]
    q0, hidden = net.forward(phi)
    assert net.forward(phi)[0] == q0  # deterministic
    target = q0 + 1.0
    for _ in range(200):
        q, hidden = net.forward(phi)
        net.sgd(phi, hidden, target - q, 0.05)
    assert abs(net.forward(phi)[0] - target) < abs(q0 - target)


def test_decide_returns_only_legal_actions_both_modes() -> None:
    engine = _engine()
    brain = DeepQBrain(Role.POLICE, random.Random(1), net=Mlp(random.Random(2)))
    legal = candidate_actions(engine)
    assert brain.decide(engine) in legal  # greedy
    brain.epsilon = 1.0
    for _ in range(20):
        assert brain.decide(engine) in legal  # exploration


def test_seam_spec_loads_and_uses_belief_target() -> None:
    config = types.SimpleNamespace(private={"strategy": {"police_class": SEAM_SPEC}})
    brain = resolve_brain(config, Role.POLICE, random.Random(3))
    assert isinstance(brain, DeepQBrain) and brain.epsilon == 0.0

    class FixedBelief:
        def argmax_cell(self):
            return (6, 6)

    action = brain.decide(_engine(), belief=FixedBelief())
    assert action["type"] in ("move", "barrier")
