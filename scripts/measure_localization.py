"""Sensitivity of the dwell-plateau fit gate (PRD 10), on in-repo evaders.

Sweeps `PLATEAU_MIN_FIT` and reports the precision/coverage trade-off the gate
buys: how often a pin fires, how often it is exactly right, and the mean error
when it fires - against the posterior argmax on the SAME turns as the control.

Ground truth is the arena's true thief cell; the cop stays blind and observes
through the shipped Perception pipeline.

Run: uv run python scripts/measure_localization.py [games_per_evader]
Output: results/experiments/plateau_localization.json
"""

import json
import random
import sys
from pathlib import Path

from p2p_police.domain import evidence, protocol
from p2p_police.domain.belief import BeliefMap
from p2p_police.domain.engine import GameEngine
from p2p_police.domain.primitives import Outcome, Role
from p2p_police.peer.perception import Perception
from p2p_police.shared.config import Config
from p2p_police.strategy.arena_thief import PerfectEvader
from p2p_police.strategy.brain_base import RandomBrain
from p2p_police.strategy.police_brain import PoliceBrain, ThiefForArena

RESULT_PATH = Path("results/experiments/plateau_localization.json")
DEFAULT_GAMES = 20
EVADERS = {"heuristic": ThiefForArena, "random": RandomBrain, "perfect": PerfectEvader}
BLIND_EVADERS = {"heuristic", "random"}
FITS = (0.5, 0.6, 0.7, 0.8, 0.9, 0.95)


def collect(seed: int, config: Config, evader_name: str) -> list[dict]:
    """One arena game; per turn, the truth, the pin and the argmax."""
    engine = GameEngine(config.grid_size, config.cop_start, config.thief_start,
                        config.rule_set())
    cop = PoliceBrain(Role.POLICE, random.Random(seed))
    evader = EVADERS[evader_name](Role.THIEF, random.Random(seed + 999))
    perception = Perception.for_peer(Role.POLICE, config)
    evader_belief = BeliefMap(config.grid_size)
    rows = []
    while engine.outcome is Outcome.ONGOING:
        action = cop.decide(engine, perception.belief)
        wall = tuple(action["cell"]) if action["type"] == "barrier" else None
        protocol.apply_action(engine, Role.POLICE, action)
        if engine.outcome is not Outcome.ONGOING:
            break
        evader_belief.diffuse(engine.board)
        evader_belief.observe_scent(engine.scent[Role.POLICE], engine.board)
        view = evader_belief if evader_name in BLIND_EVADERS else None
        protocol.apply_action(engine, Role.THIEF, evader.decide(engine, view))
        perception.observe(engine, Role.THIEF, None, barrier_cell=wall)
        truth = engine.positions[Role.THIEF]
        pins = {}
        for fit in FITS:
            evidence.PLATEAU_MIN_FIT = fit
            pin = evidence.plateau_origin(engine.scent[Role.THIEF], engine.board,
                                          config.grid_size)
            pins[str(fit)] = list(pin) if pin else None
        evidence.PLATEAU_MIN_FIT = 0.9  # restore the shipped gate
        peak = perception.belief.argmax_cell()
        rows.append({"truth": list(truth), "pins": pins,
                     "argmax_error": abs(peak[0] - truth[0]) + abs(peak[1] - truth[1])})
    return rows


def summarize(rows: list[dict]) -> dict:
    turns = len(rows)
    table = {}
    for fit in FITS:
        fired = [r for r in rows if r["pins"][str(fit)] is not None]
        errors = [abs(r["pins"][str(fit)][0] - r["truth"][0])
                  + abs(r["pins"][str(fit)][1] - r["truth"][1]) for r in fired]
        table[str(fit)] = {
            "fire_rate": round(len(fired) / turns, 4) if turns else 0.0,
            "exact_when_fired": round(
                sum(1 for e in errors if e == 0) / len(errors), 4) if errors else None,
            "mean_error_when_fired": round(sum(errors) / len(errors), 3) if errors else None,
        }
    return {
        "turns": turns,
        "argmax_exact_rate": round(
            sum(1 for r in rows if r["argmax_error"] == 0) / turns, 4) if turns else 0.0,
        "argmax_mean_error": round(
            sum(r["argmax_error"] for r in rows) / turns, 3) if turns else None,
        "by_fit_threshold": table,
    }


def main() -> None:
    games = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_GAMES
    config = Config.load("config")
    rows = [row for name in EVADERS for seed in range(games)
            for row in collect(seed, config, name)]
    report = {
        "description": "dwell-plateau fit-gate sweep vs the posterior argmax, "
                       "blind cop, shipped Perception pipeline",
        "games_per_evader": games,
        "shipped_fit_threshold": 0.9,
        **summarize(rows),
    }
    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
