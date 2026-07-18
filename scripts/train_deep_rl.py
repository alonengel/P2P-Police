"""Double-DQN pursuit training v3: ENSEMBLE adversaries + belief-noise.

Arms-race round 2. The twin's counter-evader fully neutralized the v2 trap
cop (survival 1.00), so v3 retrains against an ENSEMBLE - the perfect
BFS-evader, the twin's learned counter-evader (DeepEvader, replayed from
copied weight data), and a random walker - so the policy cannot overfit one
fixed rival. Additionally, BELIEF-NOISE domain randomization: part of the
time the cop is shown a jittered thief position (simulating belief error in
blind/hidden-move games) instead of the true cell, so the policy survives
partial observability. Experience replay + frozen target + best checkpoint.
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
from p2p_police.strategy.arena_thief import DeepEvader, PerfectEvader
from p2p_police.strategy.brain_base import RandomBrain
from p2p_police.strategy.rl_deep import WEIGHTS_PATH, DeepQBrain, Mlp, candidate_actions, features

RULES = RuleSet(max_barriers=14, max_moves=35, survival_threshold=35)
GAMMA, LR, BATCH, SYNC_EPISODES, BUFFER = 0.97, 0.01, 32, 10, 5000
ENSEMBLE = (PerfectEvader, DeepEvader, RandomBrain)
NOISE_P, NOISE_R = 0.4, 2  # belief-noise: prob + Chebyshev jitter radius


def _observed(engine, rng, noisy: bool):
    true = engine.positions[Role.THIEF]
    if not noisy or rng.random() >= NOISE_P:
        return true
    grid = engine.board.grid_size
    return (min(grid - 1, max(0, true[0] + rng.randint(-NOISE_R, NOISE_R))),
            min(grid - 1, max(0, true[1] + rng.randint(-NOISE_R, NOISE_R))))


def run_episode(brain, seed: int, buffer=None, opponent=PerfectEvader, noisy=False):
    engine = GameEngine(7, (0, 0), (3, 3), RULES)
    thief = opponent(Role.THIEF, random.Random(seed + 9000))
    noise_rng = random.Random(seed + 5000)
    while engine.outcome is Outcome.ONGOING:
        target = _observed(engine, noise_rng, noisy)
        shim = type("T", (), {"argmax_cell": lambda self, c=target: c})()
        action = brain.decide(engine, belief=shim)  # sees the jittered cell
        phi = features(engine, action, thief=target) if buffer is not None else None
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
            reward = -0.02 * (d / grid) + 0.1 * containment
            nxt = _observed(engine, noise_rng, noisy)
            next_phis = [features(engine, a, thief=nxt)
                         for a in candidate_actions(engine)]
        buffer.append((phi, reward, next_phis))
    return engine.outcome


def replay_step(net, target_net, buffer, rng) -> None:
    for phi, reward, next_phis in rng.sample(list(buffer), k=min(BATCH, len(buffer))):
        if next_phis:  # Double-DQN: online selects, frozen evaluates
            best = max(next_phis, key=lambda p: net.forward(p)[0])
            target = reward + GAMMA * target_net.forward(best)[0]
        else:
            target = reward
        q, hidden = net.forward(phi)
        net.sgd(phi, hidden, target - q, LR)


def _clone(net: Mlp) -> Mlp:
    frozen = Mlp(random.Random(8))
    frozen.load_state(json.loads(json.dumps(net.state())))
    return frozen


def evaluate(net, base_seed: int, games: int, opponent, noisy=False) -> float:
    brain = DeepQBrain(Role.POLICE, random.Random(base_seed - 1), net=net)
    wins = sum(run_episode(brain, base_seed + i, opponent=opponent, noisy=noisy)
               is Outcome.CAPTURE for i in range(games))
    return wins / games


def main(episodes: int = 4000) -> None:
    rng = random.Random(7)
    net = Mlp(rng)
    target_net = _clone(net)
    brain = DeepQBrain(Role.POLICE, rng, net=net)
    buffer: deque = deque(maxlen=BUFFER)
    curve, best_eval, best_state = [], -1.0, net.state()
    for episode in range(episodes):
        brain.epsilon = max(0.05, 1.0 * (1 - episode / (0.9 * episodes)))
        opponent = ENSEMBLE[episode % len(ENSEMBLE)]
        run_episode(brain, 10_000 + episode, buffer=buffer, opponent=opponent,
                    noisy=True)
        if len(buffer) >= BATCH:
            for _ in range(4):
                replay_step(net, target_net, buffer, rng)
        if (episode + 1) % SYNC_EPISODES == 0:
            target_net = _clone(net)
        if episode % 100 == 0 or episode == episodes - 1:
            vs_perfect = evaluate(net, 50_000, 25, PerfectEvader)
            vs_deep = evaluate(net, 60_000, 25, DeepEvader)
            score = vs_perfect + vs_deep
            if score > best_eval:
                best_eval, best_state = score, json.loads(json.dumps(net.state()))
            curve.append({"episode": episode, "capture_vs_perfect": vs_perfect,
                          "capture_vs_counter_evader": vs_deep})
            print(f"ep {episode:5d}  vs_perfect={vs_perfect:.2f} vs_counter={vs_deep:.2f}")
    net.load_state(best_state)
    finals = {
        "vs_perfect_evader": evaluate(net, 90_000, 100, PerfectEvader),
        "vs_counter_evader": evaluate(net, 91_000, 100, DeepEvader),
        "vs_random": evaluate(net, 92_000, 100, RandomBrain),
        "vs_perfect_with_belief_noise": evaluate(net, 93_000, 100, PerfectEvader,
                                                 noisy=True),
    }
    print("FINAL:", {k: round(v, 2) for k, v in finals.items()})
    WEIGHTS_PATH.write_text(json.dumps(
        {"net": net.state(), "episodes": episodes, "gamma": GAMMA, "lr": LR,
         "double_dqn": True, "checkpoint": "best-eval", "version": "v3-ensemble",
         "ensemble": [c.__name__ for c in ENSEMBLE],
         "belief_noise": {"p": NOISE_P, "radius": NOISE_R}}, indent=2),
        encoding="utf-8")
    Path("results/experiments/deep_rl_training.json").write_text(json.dumps({
        "curve": curve, "base_seed": 7, "eval_games_per_point": 25,
        "final_100_game_evals": finals,
        "regime": "ensemble adversaries + belief-noise domain randomization "
                  "(p=0.4, Chebyshev radius 2) - trains under partial "
                  "observability so the policy survives blind games",
    }, indent=2), encoding="utf-8")
    figure, ax = plt.subplots(figsize=(7, 4))
    for key, color, label in (("capture_vs_perfect", "#1f6feb", "vs perfect evader"),
                              ("capture_vs_counter_evader", "#d29922",
                               "vs learned counter-evader")):
        ax.plot([p["episode"] for p in curve], [p[key] for p in curve],
                marker="o", color=color, label=label)
    ax.legend(fontsize=8)
    ax.set(xlabel="training episode", ylabel="greedy capture rate",
           title="Double-DQN cop v3: ensemble + belief-noise")
    figure.tight_layout()
    figure.savefig("assets/deep_rl_curve.png", dpi=120)


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 4000)
