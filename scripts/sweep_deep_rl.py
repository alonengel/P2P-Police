"""Hyperparameter sweep for the DQN cop - is 0.74 a tuning artifact?

Six configs at an equal 1200-episode budget, each evaluated vs the perfect
evader (50 games) and vs random (25). Writes results/experiments/
deep_rl_sweep.json and prints a ranked table. Does NOT touch the shipped
weights - a winning config earns a full 4000-episode run separately, gated
on beating the incumbent's 0.74/100.
Run: uv run python scripts/sweep_deep_rl.py [episodes_per_config]
"""

import json
import random
import sys
from collections import deque
from pathlib import Path

import train_deep_rl as t

from p2p_police.domain.primitives import Role
from p2p_police.strategy import rl_deep
from p2p_police.strategy.arena_thief import PerfectEvader
from p2p_police.strategy.brain_base import RandomBrain
from p2p_police.strategy.rl_deep import DeepQBrain, Mlp

CONFIGS = [
    {"name": "baseline", "lr": 0.01, "hidden": 12, "sweeps": 4, "eps_lo": 0.05},
    {"name": "lr-hot", "lr": 0.02, "hidden": 12, "sweeps": 4, "eps_lo": 0.05},
    {"name": "lr-cool", "lr": 0.005, "hidden": 12, "sweeps": 4, "eps_lo": 0.05},
    {"name": "wide-20", "lr": 0.01, "hidden": 20, "sweeps": 4, "eps_lo": 0.05},
    {"name": "replay-8", "lr": 0.01, "hidden": 12, "sweeps": 8, "eps_lo": 0.05},
    {"name": "explore-16", "lr": 0.01, "hidden": 16, "sweeps": 4, "eps_lo": 0.10},
]


def train_one(cfg: dict, episodes: int) -> dict:
    saved_lr, saved_hidden = t.LR, rl_deep.HIDDEN
    t.LR, rl_deep.HIDDEN = cfg["lr"], cfg["hidden"]
    try:
        net = Mlp(rng := random.Random(7))
        target_net = t._clone(net)
        brain = DeepQBrain(Role.POLICE, rng, net=net)
        buffer: deque = deque(maxlen=t.BUFFER)
        best_state, best_eval = json.loads(json.dumps(net.state())), -1.0
        for episode in range(episodes):
            brain.epsilon = max(cfg["eps_lo"], 1.0 * (1 - episode / (0.9 * episodes)))
            t.run_episode(brain, 10_000 + episode, buffer=buffer,
                          opponent=t.ENSEMBLE[episode % len(t.ENSEMBLE)], noisy=True)
            if len(buffer) >= t.BATCH:
                for _ in range(cfg["sweeps"]):
                    t.replay_step(net, target_net, buffer, rng)
            if (episode + 1) % t.SYNC_EPISODES == 0:
                target_net = t._clone(net)
            if episode % 150 == 0 or episode == episodes - 1:
                vs_perfect = t.evaluate(net, 50_000, 25, PerfectEvader)
                if vs_perfect > best_eval:
                    best_eval = vs_perfect
                    best_state = json.loads(json.dumps(net.state()))
        net.load_state(best_state)
        result = {
            "vs_perfect_50": t.evaluate(net, 90_000, 50, PerfectEvader),
            "vs_random_25": t.evaluate(net, 92_000, 25, RandomBrain),
            "best_checkpoint_25": best_eval,
        }
        print(f"{cfg['name']:>10}: {result}")
        return result
    finally:
        t.LR, rl_deep.HIDDEN = saved_lr, saved_hidden


def main(episodes: int = 1200) -> None:
    table = {}
    for cfg in CONFIGS:
        table[cfg["name"]] = {"config": cfg, **train_one(cfg, episodes)}
    ranked = sorted(table.items(), key=lambda kv: -kv[1]["vs_perfect_50"])
    out = Path("results/experiments/deep_rl_sweep.json")
    out.write_text(json.dumps({
        "episodes_per_config": episodes, "base_seed": 7,
        "ranked": [name for name, _ in ranked], "table": table,
        "incumbent": "v3 shipped weights: 0.74 vs perfect over 100 games",
    }, indent=2), encoding="utf-8")
    print("RANKED:", [(n, round(r["vs_perfect_50"], 2)) for n, r in ranked])


if __name__ == "__main__":
    sys.path.insert(0, "scripts")
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 1200)
