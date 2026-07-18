"""Arena evaders: legality, determinism, and genuine threat level."""

import random

from p2p_police.domain import protocol
from p2p_police.domain.engine import GameEngine
from p2p_police.domain.primitives import Move, Outcome, Role
from p2p_police.domain.rules import RuleSet
from p2p_police.strategy.arena_thief import DeepEvader, PerfectEvader, evader_features

RULES = RuleSet(max_barriers=14, max_moves=35, survival_threshold=35)


def _engine() -> GameEngine:
    return GameEngine(7, (0, 0), (3, 3), RULES)


def test_evaders_emit_only_legal_moves() -> None:
    engine = _engine()
    for cls in (PerfectEvader, DeepEvader):
        action = cls(Role.THIEF, random.Random(1)).decide(engine)
        assert action["type"] == "move"
        assert Move[action["move"]] in engine.board.legal_moves((3, 3))


def test_evader_features_are_bounded() -> None:
    engine = _engine()
    for move in engine.board.legal_moves((3, 3)):
        phi = evader_features(engine, move)
        assert len(phi) == 9 and all(-1.5 <= f <= 1.5 for f in phi)


def test_perfect_evader_survives_a_movement_only_chaser() -> None:
    """The theorem the whole RL story leans on, reproduced as a test."""
    engine = _engine()
    evader = PerfectEvader(Role.THIEF, random.Random(2))
    while engine.outcome is Outcome.ONGOING:
        me, thief = engine.positions[Role.POLICE], engine.positions[Role.THIEF]
        from p2p_police.domain.pathfind import bfs_distances

        d = bfs_distances(engine.board, thief)
        chase = min(engine.board.legal_moves(me),
                    key=lambda m: d.get(m.applied_to(me), 99))
        protocol.apply_action(engine, Role.POLICE, protocol.move_action(chase))
        if engine.outcome is Outcome.ONGOING:
            protocol.apply_action(engine, Role.THIEF, evader.decide(engine))
    assert engine.outcome is Outcome.SURVIVAL
