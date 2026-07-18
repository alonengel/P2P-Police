"""Linear function-approximation Q-learning pursuit brain (rulebook ch. 6.3).

RL is the book's optional third path: Q(s,a) = w . phi(s,a) with TD(0)
updates and epsilon-greedy exploration. Features are barrier-aware BFS
quantities, so the policy generalizes across board layouts instead of
memorizing cells (a 7x7 tabular Q would not survive barriers). Trained by
a scripted evader (scripts/train_rl.py); weights load through the seam:
    [strategy] police_class = "p2p_police.strategy.rl_brain:LinearQBrain"
The MOVE stays pure Python - this is an algorithm, not an LLM (rule 25).
"""

import json
import random
from pathlib import Path

from p2p_police.domain import protocol
from p2p_police.domain.engine import GameEngine
from p2p_police.domain.pathfind import UNREACHABLE, bfs_distances
from p2p_police.domain.primitives import Cell, Move, Role

REPO_ROOT = Path(__file__).resolve().parents[3]  # anchor: cwd-independent load
WEIGHTS_PATH = REPO_ROOT / "results" / "rl_weights.json"
FEATURE_NAMES = ("bias", "distance", "distance_delta", "openness", "stay")


def features(engine: GameEngine, me: Cell, target: Cell, move: Move) -> list[float]:
    """phi(s,a): normalized BFS geometry AFTER taking `move` from `me`."""
    landing = move.applied_to(me)
    if move is not Move.STAY and not engine.board.is_passable(landing):
        landing = me  # illegal probes are never chosen; keep phi defined
    distances = bfs_distances(engine.board, target)
    grid = engine.board.grid_size
    before = distances.get(me, UNREACHABLE)
    after = distances.get(landing, UNREACHABLE)
    horizon = 2.0 * grid
    d_after = 1.0 if after == UNREACHABLE else after / horizon
    d_before = 1.0 if before == UNREACHABLE else before / horizon
    openness = sum(
        1 for m in (Move.N, Move.S, Move.E, Move.W)
        if engine.board.is_passable(m.applied_to(landing))
    )
    return [1.0, d_after, d_after - d_before, openness / 4.0, float(move is Move.STAY)]


class LinearQBrain:
    """Q(s,a)=w.phi; greedy at play time, epsilon-greedy while training."""

    def __init__(self, role: Role, rng: random.Random, weights: list[float] | None = None) -> None:
        self.role = role
        self.rng = rng
        self.epsilon = 0.0  # play-time default: pure exploitation
        self.weights = weights if weights is not None else self._load()

    def _load(self) -> list[float]:
        if WEIGHTS_PATH.is_file():
            return json.loads(WEIGHTS_PATH.read_text(encoding="utf-8"))["weights"]
        return [0.0, -1.0, -1.0, 0.0, 0.0]  # sane prior: shrink the distance

    def q(self, engine: GameEngine, me: Cell, target: Cell, move: Move) -> float:
        phi = features(engine, me, target, move)
        return sum(w * f for w, f in zip(self.weights, phi, strict=True))

    def _target(self, engine: GameEngine, belief) -> Cell:
        if belief is not None:
            return belief.argmax_cell()
        return engine.positions[self.role.rival]

    def decide(self, engine: GameEngine, belief=None) -> dict:
        me = engine.positions[self.role]
        target = self._target(engine, belief)
        legal = engine.board.legal_moves(me)
        if self.rng.random() < self.epsilon:
            return protocol.move_action(self.rng.choice(legal))
        shuffled = self.rng.sample(legal, k=len(legal))  # random tie-break
        best = max(shuffled, key=lambda m: self.q(engine, me, target, m))
        return protocol.move_action(best)

    def td_update(
        self, engine: GameEngine, me: Cell, target: Cell, move: Move,
        reward: float, next_best_q: float, alpha: float, gamma: float,
    ) -> float:
        """w += alpha * delta * phi; returns the TD error for the curve."""
        phi = features(engine, me, target, move)
        delta = reward + gamma * next_best_q - self.q(engine, me, target, move)
        self.weights = [w + alpha * delta * f for w, f in zip(self.weights, phi, strict=True)]
        return delta
