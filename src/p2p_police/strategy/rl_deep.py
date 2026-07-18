"""Deep-RL pursuit brain: a tiny MLP Q-network WITH barrier actions.

The linear brain's recorded negative result (0% vs a perfect evader) is a
theorem about MOVEMENT-ONLY pursuit; barriers are what break it. This module
extends the RL action space to barrier placement and swaps the linear value
function for a small tanh MLP (pure Python - no new dependencies), trained
DQN-style (experience replay + target network, scripts/train_deep_rl.py).
Moves stay pure Python (rule 25); legality is enforced twice (here + engine).
Seam: [strategy] police_class = "p2p_police.strategy.rl_deep:DeepQBrain".
"""

import json
import logging
import math
import random
from pathlib import Path

from p2p_police.domain import protocol
from p2p_police.domain.engine import GameEngine
from p2p_police.domain.errors import IllegalBarrierError
from p2p_police.domain.pathfind import UNREACHABLE, bfs_distances
from p2p_police.domain.primitives import Move, Role
from p2p_police.domain.rules import validate_barrier_placement

_LOG = logging.getLogger(__name__)
REPO_ROOT = Path(__file__).resolve().parents[3]
WEIGHTS_PATH = REPO_ROOT / "results" / "deep_rl_weights.json"
N_FEATURES, HIDDEN = 10, 12


class _Hypothetical:
    """Board view with one extra barrier - features peek at after-states."""

    def __init__(self, board, extra) -> None:
        self._board, self._extra, self.grid_size = board, extra, board.grid_size

    def is_passable(self, cell) -> bool:
        return cell != self._extra and self._board.is_passable(cell)


def candidate_actions(engine: GameEngine) -> list[dict]:
    """Every legal cop action this turn: orthogonal moves + barrier placements."""
    me = engine.positions[Role.POLICE]
    actions = [protocol.move_action(m) for m in engine.board.legal_moves(me)]
    for cell in [me] + [m.applied_to(me) for m in (Move.N, Move.S, Move.E, Move.W)]:
        try:
            validate_barrier_placement(engine.board, engine.rules, me, cell)
            actions.append(protocol.barrier_action(cell))
        except IllegalBarrierError:
            continue
    return actions


def features(engine: GameEngine, action: dict, thief=None) -> list[float]:
    """phi(s,a) on the SIMULATED after-state (trap-progress aware).
    `thief` overrides the target cell (belief argmax in blind games)."""
    me = engine.positions[Role.POLICE]
    thief = thief or engine.positions[Role.THIEF]
    if action["type"] == "barrier":
        board, landing = _Hypothetical(engine.board, tuple(action["cell"])), me
    else:
        board, landing = engine.board, Move[action["move"]].applied_to(me)
    from_thief = bfs_distances(board, thief)
    grid, horizon = engine.board.grid_size, 2.0 * engine.board.grid_size
    before = from_thief.get(me, UNREACHABLE)
    after = from_thief.get(landing, UNREACHABLE)
    d_after = 1.0 if after == UNREACHABLE else after / horizon
    d_before = 1.0 if before == UNREACHABLE else before / horizon
    thief_escapes = sum(
        1 for m in (Move.N, Move.S, Move.E, Move.W) if board.is_passable(m.applied_to(thief))
    )
    wall = min(thief[0], thief[1], grid - 1 - thief[0], grid - 1 - thief[1])
    return [
        1.0, d_after, d_after - d_before, thief_escapes / 4.0,
        len(from_thief) / float(grid * grid),          # thief's reachable region
        1.0 if action["type"] == "barrier" else 0.0,
        (engine.rules.max_barriers - len(engine.board.barriers)) / engine.rules.max_barriers,
        1.0 if thief_escapes <= 1 else 0.0,            # one exit left: the trap
        wall / (grid / 2.0),                           # traps close near walls
        float((landing[0] + landing[1] + thief[0] + thief[1]) % 2),  # chase parity
    ]


class Mlp:
    """8 -> tanh(10) -> 1, hand-rolled: forward, gradients, SGD step."""

    def __init__(self, rng: random.Random) -> None:
        scale = 1.0 / math.sqrt(N_FEATURES)
        self.w1 = [[rng.uniform(-scale, scale) for _ in range(N_FEATURES)]
                   for _ in range(HIDDEN)]
        self.b1 = [0.0] * HIDDEN
        self.w2 = [rng.uniform(-scale, scale) for _ in range(HIDDEN)]
        self.b2 = 0.0

    def forward(self, phi: list[float]) -> tuple[float, list[float]]:
        hidden = [math.tanh(sum(w * f for w, f in zip(row, phi, strict=True)) + b)
                  for row, b in zip(self.w1, self.b1, strict=True)]
        q = sum(w * h for w, h in zip(self.w2, hidden, strict=True)) + self.b2
        return q, hidden

    def sgd(self, phi: list[float], hidden: list[float], delta: float, lr: float) -> None:
        """One gradient step pushing Q(phi) by delta (TD error), lr-scaled."""
        for j, h in enumerate(hidden):
            grad_h = delta * self.w2[j] * (1.0 - h * h)
            self.w2[j] += lr * delta * h
            for i, f in enumerate(phi):
                self.w1[j][i] += lr * grad_h * f
            self.b1[j] += lr * grad_h
        self.b2 += lr * delta

    def state(self) -> dict:
        return {"w1": self.w1, "b1": self.b1, "w2": self.w2, "b2": self.b2}

    def load_state(self, state: dict) -> None:
        self.w1, self.b1 = state["w1"], state["b1"]
        self.w2, self.b2 = state["w2"], state["b2"]


class DeepQBrain:
    """Greedy over ALL legal actions (moves + barriers) at play time."""

    def __init__(self, role: Role, rng: random.Random, net: Mlp | None = None) -> None:
        self.role, self.rng, self.epsilon = role, rng, 0.0
        self.net = net or self._load(rng)

    def _load(self, rng: random.Random) -> Mlp:
        net = Mlp(rng)
        if WEIGHTS_PATH.is_file():
            net.load_state(json.loads(WEIGHTS_PATH.read_text(encoding="utf-8"))["net"])
        else:  # loud, not silent: an untrained net is a valid but weak brain
            _LOG.warning("deep-RL weights missing at %s - random init", WEIGHTS_PATH)
        return net

    def q(self, engine: GameEngine, action: dict, thief=None) -> float:
        return self.net.forward(features(engine, action, thief))[0]

    def decide(self, engine: GameEngine, belief=None) -> dict:
        target = belief.argmax_cell() if belief is not None else None
        actions = candidate_actions(engine)
        if self.rng.random() < self.epsilon:
            return self.rng.choice(actions)
        shuffled = self.rng.sample(actions, k=len(actions))  # random tie-break
        return max(shuffled, key=lambda a: self.q(engine, a, target))
