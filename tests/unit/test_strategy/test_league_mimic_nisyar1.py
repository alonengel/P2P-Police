"""Adaptive nis-yar1 thief mimics — the live bar for the intercepting cop.

Their thief's fitted shape (imreeyal's single-game model, corroborated by
our g05 live capture at 23): flee the cop, then PERCH — long STAY runs,
waking only at adjacency. Two arms: the pure percher, and their newest
runner-then-percher (corner-averse opening walk first). Measured at ship
time: 30/30 captures on both, turns 13-15.
"""

import random

from p2p_police.domain import protocol
from p2p_police.domain.engine import GameEngine
from p2p_police.domain.pathfind import bfs_distances
from p2p_police.domain.primitives import Move, Outcome, Role
from p2p_police.domain.rules import RuleSet
from p2p_police.peer.perception import Perception
from p2p_police.shared.config import Config
from p2p_police.strategy.police_brain import PoliceBrain

RULES = RuleSet(max_barriers=14, max_moves=35, survival_threshold=35)
LIES = ["I am wherever the lamplight fails you.",
        "Still breathing, still moving; catch me if you can.",
        "The streets remember me; your boots they only tolerate.",
        "Your footsteps echo; mine never do."]


class PercherMimic:
    """Perch while the gap exceeds 1; wake to the max-distance step."""

    def __init__(self, rng: random.Random) -> None:
        self.rng = rng

    def act(self, engine) -> dict:
        me = engine.positions[Role.THIEF]
        cop = engine.positions[Role.POLICE]
        if abs(me[0] - cop[0]) + abs(me[1] - cop[1]) > 1:
            return {"type": "move", "move": "STAY"}
        dist = bfs_distances(engine.board, cop)
        moves = [m for m in (Move.N, Move.S, Move.E, Move.W)
                 if engine.board.is_passable(m.applied_to(me))]
        self.rng.shuffle(moves)
        if not moves:
            return {"type": "move", "move": "STAY"}
        return {"type": "move",
                "move": max(moves, key=lambda m: dist.get(m.applied_to(me), 0)).name}


class RunnerPercher(PercherMimic):
    """Their newest shape: a corner-averse opening walk, then the perch."""

    def __init__(self, rng: random.Random) -> None:
        super().__init__(rng)
        self.opening = 8

    def act(self, engine) -> dict:
        if self.opening > 0:
            self.opening -= 1
            me = engine.positions[Role.THIEF]
            cop = engine.positions[Role.POLICE]
            dist = bfs_distances(engine.board, cop)
            moves = [m for m in (Move.N, Move.S, Move.E, Move.W)
                     if engine.board.is_passable(m.applied_to(me))]
            self.rng.shuffle(moves)
            if moves:
                def key(move):
                    cell = move.applied_to(me)
                    exits = sum(1 for x in (Move.N, Move.S, Move.E, Move.W)
                                if engine.board.is_passable(x.applied_to(cell)))
                    return (min(exits, 3), dist.get(cell, 0))
                return {"type": "move", "move": max(moves, key=key).name}
        return super().act(engine)


def _play(seed: int, cls) -> Outcome:
    engine = GameEngine(7, (0, 0), (3, 3), RULES)
    cop = PoliceBrain(Role.POLICE, random.Random(seed), Config.load("config"))
    percep = Perception.for_peer(Role.POLICE, Config.load("config"))
    thief, turn = cls(random.Random(seed + 900)), 0
    while engine.outcome is Outcome.ONGOING and turn < RULES.max_moves:
        turn += 1
        try:
            protocol.apply_action(engine, Role.POLICE, cop.decide(engine, percep.belief))
        except Exception:
            protocol.apply_action(engine, Role.POLICE, {"type": "move", "move": "STAY"})
        if engine.outcome is not Outcome.ONGOING:
            break
        try:
            protocol.apply_action(engine, Role.THIEF, thief.act(engine))
        except Exception:
            protocol.apply_action(engine, Role.THIEF, {"type": "move", "move": "STAY"})
        if engine.outcome is not Outcome.ONGOING:
            break
        percep.observe(engine, Role.THIEF, LIES[turn % len(LIES)])
    return engine.outcome


def test_intercepting_cop_converts_both_percher_shapes() -> None:
    for cls in (PercherMimic, RunnerPercher):
        captures = sum(_play(seed, cls) is Outcome.CAPTURE for seed in range(10))
        assert captures >= 9, f"{cls.__name__}: only {captures}/10 captured"
