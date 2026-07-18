"""Train the LinearQBrain cop vs a scripted random-walker thief (the catchable
baseline), then evaluate the SAME trained policy vs a perfect BFS-distance
evader - the theory-confirming negative result (uncatchable by movement alone,
see README RL section) is recorded as a first-class artifact, not just prose.

Rewards: capture +1, thief survival -1, per-turn shaping -0.02*(distance/grid)
(patience is fine, drifting away is not). Epsilon decays 0.30 -> 0.05.
Outputs: results/rl_weights.json, results/experiments/rl_training.json,
assets/rl_learning_curve.png. Reproducible: fixed base seed; eval uses its own
RNG stream so measurement never perturbs training.
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


def run_episode(brain: LinearQBrain, seed: int, learn: bool,
                opponent=RandomBrain) -> tuple[Outcome, float]:
    engine = GameEngine(7, (0, 0), (3, 3), RULES)
    thief = opponent(Role.THIEF, random.Random(seed + 9000))
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


def evaluate(brain: LinearQBrain, base_seed: int, games: int = 50,
             opponent=RandomBrain) -> float:
    saved, brain.epsilon = brain.epsilon, 0.0
    eval_rng, brain.rng = brain.rng, random.Random(base_seed - 1)  # own stream
    wins = sum(
        run_episode(brain, base_seed + i, learn=False, opponent=opponent)[0]
        is Outcome.CAPTURE
        for i in range(games)
    )
    brain.epsilon, brain.rng = saved, eval_rng
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
    vs_perfect = evaluate(brain, 90_000, games=100, opponent=PerfectEvader)
    print(f"trained policy vs PERFECT evader: {vs_perfect:.2f} (theory: uncatchable)")
    WEIGHTS_PATH.parent.mkdir(exist_ok=True)
    WEIGHTS_PATH.write_text(json.dumps(
        {"weights": brain.weights, "episodes": episodes, "alpha": ALPHA, "gamma": GAMMA},
        indent=2), encoding="utf-8")
    out = Path("results/experiments/rl_training.json")
    out.write_text(json.dumps({
        "curve": curve, "final_weights": brain.weights,
        "eval_games_per_point": 50, "base_seed": 7,
        "negative_result_vs_perfect_evader": {
            "win_rate": vs_perfect, "games": 100,
            "note": "same trained policy; a perfect BFS-distance evader is "
                    "provably uncatchable by movement alone on an open board",
        }}, indent=2), encoding="utf-8")
    figure, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
    ax1.plot([p["episode"] for p in curve], [p["eval_win_rate"] for p in curve],
             marker="o", color="#1f6feb", label="vs random walker")
    ax1.axhline(vs_perfect, color="#cf222e", linestyle="--",
                label=f"vs perfect evader ({vs_perfect:.2f})")
    ax1.legend(loc="center right", fontsize=8)
    ax1.set(xlabel="training episode", ylabel="greedy eval win rate",
            title="Linear-FA Q-learning cop")
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
