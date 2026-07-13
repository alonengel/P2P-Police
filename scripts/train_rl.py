"""Train the LinearQBrain cop by self-play vs the random-walker thief (the catchable baseline; a PERFECT evader is provably uncatchable by movement alone - see README RL section).

Rewards: capture +1, thief survival -1, per-turn shaping -0.02*(distance/grid)
(patience is fine, drifting away is not). Epsilon decays 0.30 -> 0.05.
Outputs: results/rl_weights.json, results/experiments/rl_training.json,
assets/rl_learning_curve.png. Reproducible: fixed base seed.
Run: uv run python scripts/train_rl.py [episodes]
"""

import json
import random
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from p2p_police.domain import protocol
from p2p_police.domain.engine import GameEngine
from p2p_police.domain.pathfind import bfs_distances
from p2p_police.domain.primitives import Move, Outcome, Role
from p2p_police.domain.rules import RuleSet
from p2p_police.strategy.brain_base import RandomBrain
from p2p_police.strategy.rl_brain import WEIGHTS_PATH, LinearQBrain

RULES = RuleSet(max_barriers=14, max_moves=35, survival_threshold=35)
ALPHA, GAMMA = 0.05, 0.95


def run_episode(brain: LinearQBrain, seed: int, learn: bool) -> tuple[Outcome, float]:
    engine = GameEngine(7, (0, 0), (3, 3), RULES)
    thief = RandomBrain(Role.THIEF, random.Random(seed + 9000))
    td_total = 0.0
    while engine.outcome is Outcome.ONGOING:
        me, target = engine.positions[Role.POLICE], engine.positions[Role.THIEF]
        action = brain.decide(engine)
        move = Move[action["move"]]
        protocol.apply_action(engine, Role.POLICE, action)
        if engine.outcome is Outcome.ONGOING:
            protocol.apply_action(engine, Role.THIEF, thief.decide(engine))
        if learn:
            grid = engine.board.grid_size
            distance = bfs_distances(engine.board, engine.positions[Role.THIEF]).get(
                engine.positions[Role.POLICE], 2 * grid
            )
            if engine.outcome is Outcome.CAPTURE:
                reward, next_q = 1.0, 0.0
            elif engine.outcome is Outcome.SURVIVAL:
                reward, next_q = -1.0, 0.0
            else:
                reward = -0.02 * (distance / grid)
                new_me = engine.positions[Role.POLICE]
                new_target = engine.positions[Role.THIEF]
                next_q = max(
                    brain.q(engine, new_me, new_target, m)
                    for m in engine.board.legal_moves(new_me)
                )
            td_total += abs(brain.td_update(engine, me, target, move, reward, next_q,
                                            ALPHA, GAMMA))
    return engine.outcome, td_total


def evaluate(brain: LinearQBrain, base_seed: int, games: int = 20) -> float:
    saved, brain.epsilon = brain.epsilon, 0.0
    wins = sum(run_episode(brain, base_seed + i, learn=False)[0] is Outcome.CAPTURE
               for i in range(games))
    brain.epsilon = saved
    return wins / games


def main(episodes: int = 600) -> None:
    brain = LinearQBrain(Role.POLICE, random.Random(7), weights=[0.0] * 5)
    curve, td_curve = [], []
    for episode in range(episodes):
        brain.epsilon = max(0.05, 0.30 * (1 - episode / episodes))
        _, td = run_episode(brain, 10_000 + episode, learn=True)
        td_curve.append(td)
        if episode % 50 == 0 or episode == episodes - 1:
            win_rate = evaluate(brain, 50_000)
            curve.append({"episode": episode, "eval_win_rate": win_rate,
                          "epsilon": round(brain.epsilon, 3)})
            print(f"ep {episode:4d}  win_rate={win_rate:.2f}  eps={brain.epsilon:.2f}")
    WEIGHTS_PATH.parent.mkdir(exist_ok=True)
    WEIGHTS_PATH.write_text(json.dumps(
        {"weights": brain.weights, "episodes": episodes, "alpha": ALPHA, "gamma": GAMMA},
        indent=2), encoding="utf-8")
    out = Path("results/experiments/rl_training.json")
    out.write_text(json.dumps({"curve": curve, "final_weights": brain.weights},
                              indent=2), encoding="utf-8")
    figure, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
    ax1.plot([p["episode"] for p in curve], [p["eval_win_rate"] for p in curve],
             marker="o", color="#1f6feb")
    ax1.set(xlabel="training episode", ylabel="greedy eval win rate",
            title="Linear-FA Q-learning cop vs random thief")
    window = 25
    smoothed = [sum(td_curve[max(0, i - window):i + 1]) / len(td_curve[max(0, i - window):i + 1])
                for i in range(len(td_curve))]
    ax2.plot(smoothed, color="#d29922")
    ax2.set(xlabel="training episode", ylabel="|TD error| (moving avg)",
            title="Convergence")
    figure.tight_layout()
    figure.savefig("assets/rl_learning_curve.png", dpi=120)
    print("weights:", [round(w, 3) for w in brain.weights])


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 600)
