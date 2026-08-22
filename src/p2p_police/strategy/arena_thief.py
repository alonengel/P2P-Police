"""Training-arena thief adversaries (police-side, self-contained).

Sparring evaders for pursuit training - implemented HERE because the
mirrored-twin rule forbids cross-repo imports (duplicated static code is
legal; shared live state is not):

- PerfectEvader: deterministic upper bound, maximize BFS distance.
- DeepEvader: replays the twin repo's LEARNED counter-evader (the Double-DQN
  thief that fully neutralized our v2 trap cop). Its weights file
  (data/arena_thief_weights.json) is copied DATA from our own team's twin
  training run; the thief-side feature code is duplicated below.
"""

import json
import random
from pathlib import Path

from p2p_police.domain import protocol
from p2p_police.domain.engine import GameEngine
from p2p_police.domain.pathfind import UNREACHABLE, bfs_distances
from p2p_police.domain.primitives import Move, Role
from p2p_police.strategy.brain_base import BrainBase
from p2p_police.strategy.rl_deep import Mlp

ARENA_WEIGHTS = Path(__file__).resolve().parents[3] / "data" / "arena_thief_weights.json"


class ThiefForArena(BrainBase):
    """Evasion sparring partner for OUR self-play arena only (the real thief
    brain lives in the P2P-Thief repo): maximize BFS distance from the cop.
    Home moved from police_brain.py for the 150-line cap (re-exported there)."""

    def decide(self, engine: GameEngine, belief=None) -> dict:
        cop = belief.argmax_cell() if belief is not None else engine.positions[Role.POLICE]
        me = engine.positions[Role.THIEF]
        distances = bfs_distances(engine.board, cop)
        best_move, best = Move.STAY, distances.get(me, 0)
        for move in self.rng.sample(list(Move), k=len(Move)):
            target = move.applied_to(me)
            if move is Move.STAY or not engine.board.is_passable(target):
                continue
            distance = distances.get(target, 0)
            if distance > best:
                best_move, best = move, distance
        return protocol.move_action(best_move)


class PerfectEvader:
    """Deterministic upper-bound thief: always maximize BFS distance."""

    def __init__(self, role: Role, rng: random.Random) -> None:
        self.role = role

    def decide(self, engine: GameEngine, belief=None) -> dict:
        me = engine.positions[Role.THIEF]
        distances = bfs_distances(engine.board, engine.positions[Role.POLICE])
        best = max(engine.board.legal_moves(me),
                   key=lambda m: distances.get(m.applied_to(me), 0))
        return protocol.move_action(best)


def evader_features(engine: GameEngine, move: Move) -> list[float]:
    """The twin thief's 9 after-move features, duplicated in spirit."""
    me, cop = engine.positions[Role.THIEF], engine.positions[Role.POLICE]
    landing = move.applied_to(me)
    if move is not Move.STAY and not engine.board.is_passable(landing):
        landing = me
    from_cop = bfs_distances(engine.board, cop)
    grid, horizon = engine.board.grid_size, 2.0 * engine.board.grid_size
    d_after = from_cop.get(landing, UNREACHABLE)
    d_after = 1.0 if d_after == UNREACHABLE else d_after / horizon
    d_before = from_cop.get(me, UNREACHABLE)
    d_before = 1.0 if d_before == UNREACHABLE else d_before / horizon
    escapes = sum(
        1 for m in (Move.N, Move.S, Move.E, Move.W)
        if engine.board.is_passable(m.applied_to(landing))
    )
    my_region = bfs_distances(engine.board, landing)
    wall = min(landing[0], landing[1], grid - 1 - landing[0], grid - 1 - landing[1])
    return [
        1.0, d_after, d_after - d_before, escapes / 4.0,
        len(my_region) / float(grid * grid),
        wall / (grid / 2.0),
        len(engine.board.barriers) / max(1, engine.rules.max_barriers),
        float(move is Move.STAY),
        float((landing[0] + landing[1] + cop[0] + cop[1]) % 2),
    ]


class DeepEvader:
    """The twin's trained counter-evader, replayed from copied weight DATA."""

    def __init__(self, role: Role, rng: random.Random) -> None:
        self.role, self.rng = role, rng
        self.net = Mlp(rng)
        self.net.load_state(
            json.loads(ARENA_WEIGHTS.read_text(encoding="utf-8"))["net"])

    def decide(self, engine: GameEngine, belief=None) -> dict:
        me = engine.positions[Role.THIEF]
        legal = self.rng.sample(engine.board.legal_moves(me),
                                k=len(engine.board.legal_moves(me)))
        best = max(legal, key=lambda m: self.net.forward(evader_features(engine, m))[0])
        return protocol.move_action(best)
