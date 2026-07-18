"""DQN-style training: MLP Q-network cop WITH barrier actions, trained
directly against the PERFECT evader - the opponent the linear movement-only
policy provably cannot beat (0% recorded). Experience replay + frozen target
network + epsilon 1.0->0.05. Every eval is greedy on a dedicated RNG stream.
Outputs: results/deep_rl_weights.json, results/experiments/deep_rl_training.json,
assets/deep_rl_curve.png. Run: uv run python scripts/train_deep_rl.py [episodes]
"""

import json
import random
import sys
from collections import deque
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from p2p_police.domain import protocol
from p2p_police.domain.engine import GameEngine
from p2p_police.domain.pathfind import bfs_distances
from p2p_police.domain.primitives import Outcome, Role
from p2p_police.domain.rules import RuleSet
from p2p_police.strategy.brain_base import RandomBrain
from p2p_police.strategy.rl_deep import WEIGHTS_PATH, DeepQBrain, Mlp, candidate_actions, features

RULES = RuleSet(max_barriers=14, max_moves=35, survival_threshold=35)
GAMMA, LR, BATCH, SYNC_EVERY, BUFFER = 0.97, 0.01, 32, 250, 5000


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


def _clone(net: Mlp, rng: random.Random) -> Mlp:
    frozen = Mlp(rng)
    frozen.load_state(json.loads(json.dumps(net.state())))
    return frozen


def run_episode(brain, seed: int, buffer=None, opponent=PerfectEvader):
    engine = GameEngine(7, (0, 0), (3, 3), RULES)
    thief = opponent(Role.THIEF, random.Random(seed + 9000))
    while engine.outcome is Outcome.ONGOING:
        action = brain.decide(engine)
        phi = features(engine, action)
        protocol.apply_action(engine, Role.POLICE, action)
        if engine.outcome is Outcome.ONGOING:
            protocol.apply_action(engine, Role.THIEF, thief.decide(engine))
        if buffer is None:
            continue
        grid = engine.board.grid_size
        if engine.outcome is Outcome.CAPTURE:
            reward, next_phis = 1.0, []
        elif engine.outcome is not Outcome.ONGOING:
            reward, next_phis = -1.0, []
        else:
            from_thief = bfs_distances(engine.board, engine.positions[Role.THIEF])
            d = from_thief.get(engine.positions[Role.POLICE], 2 * grid)
            containment = 1.0 - len(from_thief) / float(grid * grid)
            reward = -0.02 * (d / grid) + 0.1 * containment  # traps pay rent
            next_phis = [features(engine, a) for a in candidate_actions(engine)]
        buffer.append((phi, reward, next_phis))
    return engine.outcome


def replay_step(net: Mlp, target_net: Mlp, buffer, rng: random.Random) -> None:
    for phi, reward, next_phis in rng.sample(list(buffer), k=min(BATCH, len(buffer))):
        target = reward + (GAMMA * max(target_net.forward(p)[0] for p in next_phis)
                           if next_phis else 0.0)
        q, hidden = net.forward(phi)
        net.sgd(phi, hidden, target - q, LR)


def evaluate(net: Mlp, base_seed: int, games: int, opponent) -> float:
    brain = DeepQBrain(Role.POLICE, random.Random(base_seed - 1), net=net)
    wins = sum(run_episode(brain, base_seed + i, opponent=opponent) is Outcome.CAPTURE
               for i in range(games))
    return wins / games


def main(episodes: int = 1500) -> None:
    rng = random.Random(7)
    net = Mlp(rng)
    target_net = _clone(net, random.Random(8))
    brain = DeepQBrain(Role.POLICE, rng, net=net)
    buffer: deque = deque(maxlen=BUFFER)
    curve = []
    for episode in range(episodes):
        brain.epsilon = max(0.05, 1.0 * (1 - episode / (0.8 * episodes)))
        run_episode(brain, 10_000 + episode, buffer=buffer)
        if len(buffer) >= BATCH:
            for _ in range(4):  # several replay sweeps per episode
                replay_step(net, target_net, buffer, rng)
        if (episode + 1) % (SYNC_EVERY // 25) == 0:  # sync target ~every 10 eps
            target_net = _clone(net, random.Random(8))
        if episode % 100 == 0 or episode == episodes - 1:
            vs_perfect = evaluate(net, 50_000, 25, PerfectEvader)
            vs_random = evaluate(net, 70_000, 25, RandomBrain)
            curve.append({"episode": episode, "capture_vs_perfect": vs_perfect,
                          "capture_vs_random": vs_random,
                          "epsilon": round(brain.epsilon, 3)})
            print(f"ep {episode:5d}  vs_perfect={vs_perfect:.2f} "
                  f"vs_random={vs_random:.2f}  eps={brain.epsilon:.2f}")
    final_perfect = evaluate(net, 90_000, 100, PerfectEvader)
    print(f"FINAL: capture rate vs perfect evader over 100 games: {final_perfect:.2f}")
    WEIGHTS_PATH.write_text(json.dumps(
        {"net": net.state(), "episodes": episodes, "gamma": GAMMA, "lr": LR,
         "batch": BATCH, "sync_every": SYNC_EVERY}, indent=2), encoding="utf-8")
    out = Path("results/experiments/deep_rl_training.json")
    out.write_text(json.dumps({
        "curve": curve, "base_seed": 7, "eval_games_per_point": 25,
        "final_capture_vs_perfect_evader": {"win_rate": final_perfect, "games": 100},
        "comparison": "linear movement-only policy: 0.00 vs the same evader "
                      "(results/experiments/rl_training.json)",
    }, indent=2), encoding="utf-8")
    figure, ax = plt.subplots(figsize=(7, 4))
    ax.plot([p["episode"] for p in curve], [p["capture_vs_perfect"] for p in curve],
            marker="o", color="#1f6feb", label="vs perfect evader (barriers learned)")
    ax.plot([p["episode"] for p in curve], [p["capture_vs_random"] for p in curve],
            marker=".", color="#8b949e", label="vs random walker")
    ax.axhline(0.0, color="#cf222e", linestyle="--",
               label="linear movement-only policy vs perfect (0.00)")
    ax.legend(fontsize=8)
    ax.set(xlabel="training episode", ylabel="greedy capture rate",
           title="DQN cop with barrier actions")
    figure.tight_layout()
    figure.savefig("assets/deep_rl_curve.png", dpi=120)


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 1500)
