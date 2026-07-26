"""Keep-gate arena: does each booster actually make the COP stronger?

Arms (same seeds each): baseline / +endgame / +info_gain / +both plus the
[strategy.trap] barrier-gate sweep, toggled purely through the [strategy.*]
config tables the live brain reads. Every arm plays the full evader pool: the
belief-driven heuristic evader (blind), the deterministic PerfectEvader and
the twin-trained DeepEvader (both full information - the harshest test). The
cop is always BLIND and observes through the SHIPPED Perception pipeline, so
what is measured here is what plays: diffuse, scent, then the dwell-plateau
pin, with the movement-model credibility check armed as in a real game. Keep rule: a setting stays only if it raises capture rate ACROSS THE
POOL - a gate tuned on one opponent is not a gate that travels; a negative
result flips the config default and is recorded honestly
(docs/evidence/cop-strength.md).

Run: uv run python scripts/measure_cop_strength.py [games_per_evader]
Output: results/experiments/cop_strength.json
"""

import json
import random
import sys
from pathlib import Path
from types import SimpleNamespace

from p2p_police.domain import protocol
from p2p_police.domain.belief import BeliefMap
from p2p_police.domain.engine import GameEngine
from p2p_police.domain.primitives import Outcome, Role
from p2p_police.peer.perception import Perception
from p2p_police.shared.config import Config
from p2p_police.strategy.arena_thief import DeepEvader, PerfectEvader
from p2p_police.strategy.brain_base import RandomBrain
from p2p_police.strategy.police_brain import PoliceBrain, ThiefForArena

RESULT_PATH = Path("results/experiments/cop_strength.json")
DEFAULT_GAMES = 20  # per evader per arm; the 4-evader pool makes 80 games/arm
# Booster arms carry (endgame, info_gain); trap arms re-sweep the barrier
# gate across the whole pool, since it was first tuned against a single rival.
# (endgame, info_gain, trap gate or None = shipped default). The trap gate is
# swept BOTH bare and under the boosters: gates interact, and a gate tuned in
# isolation is a gate tuned for a configuration nobody plays.
ARMS: dict = {
    "baseline": (False, False, None), "endgame": (True, False, None),
    "info_gain": (False, True, None), "both": (True, True, None),
    "trap2": (False, False, 2), "trap4": (False, False, 4),
    "both_trap2": (True, True, 2), "both_trap4": (True, True, 4),
    "both_trap5": (True, True, 5),
}
# random = calibration floor (the strong evaders sit at 0 captures for a blind
# cop - deception_policy.json - so deltas need a beatable rung to register).
EVADERS = {"heuristic": ThiefForArena, "random": RandomBrain,
           "perfect": PerfectEvader, "deep_rl": DeepEvader}
BLIND_EVADERS = {"heuristic", "random"}  # the rest play with full information


def arm_config(config: Config, arm: str) -> SimpleNamespace:
    use_endgame, use_info, trap = ARMS[arm]
    private = json.loads(json.dumps(config.private))  # deep copy - no live sharing
    strategy = private.setdefault("strategy", {})
    strategy.setdefault("endgame", {})["enabled"] = use_endgame
    strategy.setdefault("info_gain", {})["enabled"] = use_info
    if trap is not None:  # sweep both gate dimensions together, as shipped
        strategy.setdefault("trap", {}).update({"escape_limit": trap, "range": trap})
    return SimpleNamespace(private=private)


def play(seed: int, config: Config, arm: str, evader_name: str) -> dict:
    engine = GameEngine(config.grid_size, config.cop_start, config.thief_start,
                        config.rule_set())
    cop = PoliceBrain(Role.POLICE, random.Random(seed), arm_config(config, arm))
    evader = EVADERS[evader_name](Role.THIEF, random.Random(seed + 999))
    # The cop observes through the shipped pipeline (Perception), so the arms
    # measure the belief the live peer actually decides on - plateau pin included.
    perception = Perception.for_peer(Role.POLICE, config)
    evader_belief = BeliefMap(config.grid_size)  # blind evaders' picture of the cop
    while engine.outcome is Outcome.ONGOING:
        action = cop.decide(engine, perception.belief)
        wall = tuple(action["cell"]) if action["type"] == "barrier" else None
        protocol.apply_action(engine, Role.POLICE, action)
        if engine.outcome is not Outcome.ONGOING:
            break
        evader_belief.diffuse(engine.board)  # rivals read us PRE-boundary
        evader_belief.observe_scent(engine.scent[Role.POLICE], engine.board)
        view = evader_belief if evader_name in BLIND_EVADERS else None
        protocol.apply_action(engine, Role.THIEF, evader.decide(engine, view))
        perception.observe(engine, Role.THIEF, None, barrier_cell=wall)
    return {"captured": engine.outcome is Outcome.CAPTURE,
            "turns": engine.turns_completed, "endgame_fired": cop.endgame.fired}


def run_arm(config: Config, arm: str, games: int) -> dict:
    per_evader, all_games = {}, []
    for evader_name in EVADERS:
        played = [play(seed, config, arm, evader_name) for seed in range(games)]
        captures = [g for g in played if g["captured"]]
        per_evader[evader_name] = {
            "games": games, "capture_rate": round(len(captures) / games, 3),
            "mean_turns_to_capture": round(
                sum(g["turns"] for g in captures) / len(captures), 2) if captures else None,
        }
        all_games.extend(played)
    captures = [g for g in all_games if g["captured"]]
    return {"games": len(all_games),
            "capture_rate": round(len(captures) / len(all_games), 3),
            "mean_turns_to_capture": round(
                sum(g["turns"] for g in captures) / len(captures), 2) if captures else None,
            "endgame_fired_turns": sum(g["endgame_fired"] for g in all_games),
            "per_evader": per_evader}


def main() -> None:
    games = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_GAMES
    config = Config.load("config")
    report = {"description": "blind cop capture strength per arm over the whole "
                             "evader pool, same seeds, shipped Perception pipeline",
              "games_per_evader_per_arm": games,
              "arms": {arm: run_arm(config, arm, games) for arm in ARMS}}
    base = report["arms"]["baseline"]["capture_rate"]
    report["capture_delta_vs_baseline"] = {
        arm: round(report["arms"][arm]["capture_rate"] - base, 3)
        for arm in ARMS if arm != "baseline"}
    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
