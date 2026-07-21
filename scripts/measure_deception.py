"""Policy-vs-coin measurement: does the cop's masked approach buy captures?

Self-play harness (static-duplicated arena, never cross-repo imports): OUR
PoliceBrain hunts the arena evader; the thief evades through a BeliefMap fed
by the cop's scent and hint claims (the receiving side's own pipeline, read
pre-boundary exactly as in the real round order). Arm "coin" hints by the
config baseline_truth_probability; arm "policy" by the Deceiver. Same seeds
per arm — only the hint policy varies.

Run: uv run python scripts/measure_deception.py [games]
Output: results/experiments/deception_policy.json
"""

import json
import random
import sys
from pathlib import Path
from types import SimpleNamespace

from p2p_police.domain import protocol
from p2p_police.domain.belief import BeliefMap
from p2p_police.domain.engine import GameEngine
from p2p_police.domain.primitives import Move, Outcome, Role
from p2p_police.shared.config import Config
from p2p_police.strategy.deception import Deceiver
from p2p_police.strategy.hints import build_hint
from p2p_police.strategy.police_brain import PoliceBrain, ThiefForArena

RESULT_PATH = Path("results/experiments/deception_policy.json")
DEFAULT_GAMES = 60


def play(seed: int, config: Config, use_policy: bool) -> dict:
    rng = random.Random(seed)
    engine = GameEngine(config.grid_size, config.cop_start, config.thief_start,
                        config.rule_set())
    cop = PoliceBrain(Role.POLICE, rng)
    thief = ThiefForArena(Role.THIEF, random.Random(seed + 999))
    cop_belief = BeliefMap(config.grid_size)    # our picture of the evader
    thief_belief = BeliefMap(config.grid_size)  # the evader's picture of us
    deceiver = Deceiver(Role.POLICE, config, rng)
    coin = config.deception()["baseline_truth_probability"]
    max_words = int(config.shared["world"]["hint_max_words"])
    turn, lies, track_errors = 0, 0, []
    while engine.outcome is Outcome.ONGOING:
        turn += 1
        action = cop.decide(engine, cop_belief)
        moved = action["move"] if action["type"] == "move" else "STAY"
        if use_policy:
            claim, truth = deceiver.plan_hint(
                engine, SimpleNamespace(belief=cop_belief), Move[moved], turn)
        else:
            _, claim, truth = build_hint(Move[moved], rng.random() < coin, max_words, rng)
        lies += not truth
        protocol.apply_action(engine, Role.POLICE, action)
        if use_policy:
            deceiver.observe_own(engine, claim)
        thief_belief.diffuse(engine.board)  # rival reads us PRE-boundary
        thief_belief.observe_scent(engine.scent[Role.POLICE], engine.board)
        thief_belief.observe_hint(claim, engine.scent[Role.POLICE])
        guess, me = thief_belief.argmax_cell(), engine.positions[Role.POLICE]
        track_errors.append(abs(guess[0] - me[0]) + abs(guess[1] - me[1]))
        if engine.outcome is not Outcome.ONGOING:
            break
        protocol.apply_action(engine, Role.THIEF, thief.decide(engine, thief_belief))
        cop_belief.diffuse(engine.board)
        cop_belief.observe_scent(engine.scent[Role.THIEF], engine.board)
    return {"outcome": engine.outcome, "lies": lies,
            "track_error": sum(track_errors) / max(1, len(track_errors))}


def run_arm(config: Config, use_policy: bool, games: int) -> dict:
    played = [play(seed, config, use_policy) for seed in range(games)]
    captured = sum(game["outcome"] is Outcome.CAPTURE for game in played)
    return {"games": games, "capture": captured, "survival": games - captured,
            "capture_rate": round(captured / games, 3),
            "mean_lies_per_game": round(sum(g["lies"] for g in played) / games, 2),
            "mean_thief_tracking_error": round(
                sum(g["track_error"] for g in played) / games, 3)}


def main() -> None:
    games = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_GAMES
    config = Config.load("config")
    report = {
        "description": "cop capture vs belief-driven arena evader, per hint policy",
        "deception_config": config.deception(),
        "coin": run_arm(config, use_policy=False, games=games),
        "policy": run_arm(config, use_policy=True, games=games),
    }
    report["capture_delta"] = round(
        report["policy"]["capture_rate"] - report["coin"]["capture_rate"], 3)
    report["lies_saved_per_game"] = round(
        report["coin"]["mean_lies_per_game"] - report["policy"]["mean_lies_per_game"], 2)
    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
