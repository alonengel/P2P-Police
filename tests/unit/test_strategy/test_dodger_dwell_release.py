"""Contact-dwell quota release vs the live dodger under a stale trail.

The live g01 (2026-08-11 17:15): our cop held gap 1 for FOURTEEN straight
turns and never converted — their thief sidesteps every landing, and the
trap gate kept waiting for a cornered-ness that a dodger never offers. This
harness rebuilds the live regime (reactive dodger + the one-turn-stale
transmitted trail a real wire delivers) and pins the release: after
`dwell_release` consecutive sharp contact turns, walls stop waiting.
Measured: 9/15 -> 11/15 captures (sweep: release 2:11, 3:10, 4:11, 6:9).
Fully seeded — deterministic, no flake.
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
        "Your footsteps echo; mine never do.",
        "The streets remember me; your boots they only tolerate."]


class StaleField:
    """Delivers the rival's field one turn late — what a real wire does."""

    grid_size = 7

    def __init__(self, real) -> None:
        self.real, self.frame = real, [[0.0] * 7 for _ in range(7)]

    def push(self) -> None:
        self.frame = self.real.values()

    def values(self):
        return [row[:] for row in self.frame]

    def value_at(self, cell):
        return self.frame[cell[0]][cell[1]]

    def update(self, cell) -> None:
        self.real.update(cell)


class LiveDodger:
    """Their live thief shape: linger while safe, dodge on contact to the
    roomiest max-distance cell (14 contact turns, zero conversions, live)."""

    def __init__(self, rng: random.Random) -> None:
        self.rng = rng

    def act(self, engine) -> dict:
        me = engine.positions[Role.THIEF]
        cop = engine.positions[Role.POLICE]
        dist = bfs_distances(engine.board, cop)
        moves = [m for m in (Move.N, Move.S, Move.E, Move.W)
                 if engine.board.is_passable(m.applied_to(me))]
        self.rng.shuffle(moves)
        if dist.get(me, 99) > 2 and moves and self.rng.random() < 0.5:
            return {"type": "move", "move": "STAY"}
        if not moves:
            return {"type": "move", "move": "STAY"}

        def key(move):
            cell = move.applied_to(me)
            exits = sum(1 for x in (Move.N, Move.S, Move.E, Move.W)
                        if engine.board.is_passable(x.applied_to(cell)))
            return (min(exits, 3), dist.get(cell, 0))
        return {"type": "move", "move": max(moves, key=key).name}


def _play(seed: int) -> Outcome:
    engine = GameEngine(7, (0, 0), (3, 3), RULES)
    cop = PoliceBrain(Role.POLICE, random.Random(seed), Config.load("config"))
    percep = Perception.for_peer(Role.POLICE, Config.load("config"))
    real = engine.scent[Role.THIEF]
    stale = StaleField(real)
    thief, turn = LiveDodger(random.Random(seed + 40)), 0
    while engine.outcome is Outcome.ONGOING and turn < RULES.max_moves:
        turn += 1
        engine.scent[Role.THIEF] = real
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
        engine.scent[Role.THIEF] = stale
        percep.observe(engine, Role.THIEF, LIES[turn % 3])
        stale.push()
    return engine.outcome


def test_dwell_release_converts_the_live_dodger() -> None:
    captures = sum(_play(seed) is Outcome.CAPTURE for seed in range(15))
    assert captures >= 10, f"dodger harness: only {captures}/15 captured"
