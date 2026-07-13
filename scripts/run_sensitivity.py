"""Sensitivity experiments (guidelines section 9): OAT parameter sweeps.

Axes: (1) scent decay rate vs trail readability (analytic); (2) hint honesty
vs blind capture rate (simulation); (3) board size vs capture speed
(simulation). Outputs: PNGs to assets/ + raw JSON to results/experiments/.
Run: uv run python scripts/run_sensitivity.py
"""

import json
import random
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from p2p_police.domain import protocol
from p2p_police.domain.belief import BeliefMap
from p2p_police.domain.engine import GameEngine
from p2p_police.domain.primitives import Move, Outcome, Role
from p2p_police.domain.rules import RuleSet
from p2p_police.strategy.brain_base import RandomBrain
from p2p_police.strategy.hints import build_hint, parse_claim
from p2p_police.strategy.police_brain import PoliceBrain

ASSETS, OUT = Path("assets"), Path("results/experiments")
SEEDS = range(15)


def decay_curves() -> dict:
    """tau_t = 0.9*(1-rho)^t - turns until the trail fades below 0.4."""
    curves = {}
    for rho in (0.05, 0.10, 0.20, 0.30):
        series = [round(0.9 * (1 - rho) ** t, 4) for t in range(12)]
        curves[str(rho)] = series
    plt.figure(figsize=(6, 4))
    for rho, series in curves.items():
        plt.plot(series, marker="o", label=f"rho={rho}")
    plt.axhline(0.4, ls="--", c="gray", label="lie-evidence floor")
    plt.xlabel("turns since deposit")
    plt.ylabel("scent intensity")
    plt.title("Trail readability vs decay rate (fixed: rho=0.10)")
    plt.legend()
    plt.tight_layout()
    plt.savefig(ASSETS / "sens_decay.png", dpi=120)
    return curves


def blind_game(seed: int, truth_p: float, grid: int = 7) -> Outcome:
    rng = random.Random(seed)
    rules = RuleSet(max_barriers=14, max_moves=35, survival_threshold=35)
    engine = GameEngine(grid, (0, 0), (grid // 2, grid // 2), rules)
    cop = PoliceBrain(Role.POLICE, rng)
    thief = RandomBrain(Role.THIEF, random.Random(seed + 500))
    belief = BeliefMap(grid)
    while engine.outcome is Outcome.ONGOING:
        protocol.apply_action(engine, Role.POLICE, cop.decide(engine, belief))
        if engine.outcome is not Outcome.ONGOING:
            break
        action = thief.decide(engine)
        protocol.apply_action(engine, Role.THIEF, action)
        text, _, _ = build_hint(Move[action["move"]], rng.random() < truth_p, 15, rng)
        belief.diffuse(engine.board)
        belief.observe_scent(engine.scent[Role.THIEF], engine.board)
        claim = parse_claim(text)
        if claim:
            belief.observe_hint(claim, engine.scent[Role.THIEF])
    return engine.outcome


def honesty_sweep() -> dict:
    rates = {}
    for truth_p in (0.0, 0.25, 0.5, 0.75, 1.0):
        captures = sum(blind_game(s, truth_p) is Outcome.CAPTURE for s in SEEDS)
        rates[str(truth_p)] = captures / len(SEEDS)
    plt.figure(figsize=(6, 4))
    plt.bar(list(rates), list(rates.values()), color="#1f6feb")
    plt.xlabel("thief hint honesty P(truth)")
    plt.ylabel("blind cop capture rate")
    plt.title("Lie detection neutralizes dishonesty (15 seeds/point)")
    plt.tight_layout()
    plt.savefig(ASSETS / "sens_honesty.png", dpi=120)
    return rates


def board_sweep() -> dict:
    turns = {}
    for grid in (7, 9, 11):
        captured = [t for t in (
            _full_info_turns(s, grid) for s in SEEDS) if t is not None]
        turns[str(grid)] = round(sum(captured) / len(captured), 1) if captured else None
    plt.figure(figsize=(6, 4))
    keys = [k for k in turns if turns[k] is not None]
    plt.plot(keys, [turns[k] for k in keys], marker="s", color="#d29922")
    plt.xlabel("board size")
    plt.ylabel("mean turns to capture (full info)")
    plt.title("Bigger boards favor the thief")
    plt.tight_layout()
    plt.savefig(ASSETS / "sens_board.png", dpi=120)
    return turns


def _full_info_turns(seed: int, grid: int) -> int | None:
    rng = random.Random(seed)
    rules = RuleSet(max_barriers=14, max_moves=35, survival_threshold=35)
    engine = GameEngine(grid, (0, 0), (grid // 2, grid // 2), rules)
    cop = PoliceBrain(Role.POLICE, rng)
    thief = RandomBrain(Role.THIEF, random.Random(seed + 500))
    while engine.outcome is Outcome.ONGOING:
        actor = engine.next_actor
        brain = cop if actor is Role.POLICE else thief
        protocol.apply_action(engine, actor, brain.decide(engine))
    return engine.turns_completed if engine.outcome is Outcome.CAPTURE else None


if __name__ == "__main__":
    ASSETS.mkdir(exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    results = {"decay_curves": decay_curves(), "honesty_capture_rate": honesty_sweep(),
               "board_capture_turns": board_sweep()}
    (OUT / "sensitivity.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results["honesty_capture_rate"], indent=2))
    print("board:", results["board_capture_turns"])
