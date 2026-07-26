"""Does a FORGED trail steer us, and does an honest one ever get refused?

On the reference wire `smell_grid` is a plaintext sibling of `commit`, never
sealed, so no end-of-game hash audit can check it: a hostile peer may transmit
any field at all. Physics is the only check left (peer/perception.py), and
this script measures both directions of it:

  honest        - control, and the property that matters most: ZERO refusals
  decoy_corner  - a dweller's plateau stamped in a far corner
  decoy_drift   - a decoy that starts legal and WALKS a step per turn
  flood         - every cell at the clamp

The false-positive rate is the headline number. The refusal latches, so one
false positive blinds the peer for a whole game - an unsound check on this
path is a self-inflicted denial of service, strictly worse than no check.

Run: uv run python scripts/measure_trail_forgery.py [games_per_evader]
Output: results/experiments/trail_forgery.json
"""

import json
import random
import sys
from pathlib import Path

from p2p_police.domain import protocol
from p2p_police.domain.belief import BeliefMap
from p2p_police.domain.engine import GameEngine
from p2p_police.domain.evidence import SATURATING_OFFSETS, TRAIL_CENTER
from p2p_police.domain.primitives import Outcome, Role
from p2p_police.domain.scent import ScentField
from p2p_police.peer.perception import Perception
from p2p_police.shared.config import Config
from p2p_police.strategy.brain_base import RandomBrain
from p2p_police.strategy.police_brain import PoliceBrain, ThiefForArena

RESULT_PATH = Path("results/experiments/trail_forgery.json")
DEFAULT_GAMES = 20
EVADERS = {"heuristic": ThiefForArena, "random": RandomBrain}
ARMS = ("honest", "decoy_corner", "decoy_drift", "flood")


class _Forged:
    """Engine view whose RIVAL scent is whatever the attacker transmitted."""

    def __init__(self, engine: GameEngine, field: ScentField) -> None:
        self.board, self._engine = engine.board, engine
        self.scent = dict(engine.scent)
        self.scent[Role.THIEF] = field


def forged_field(arm: str, grid: int, turn: int) -> ScentField | None:
    """The field a hostile peer transmits, or None to send the honest one."""
    if arm == "honest":
        return None
    field = ScentField(grid)
    if arm == "flood":
        field._grid = [[TRAIL_CENTER] * grid for _ in range(grid)]
        return field
    # decoy_corner is stamped where the rival cannot possibly be. decoy_drift
    # is the honest worst case: it STARTS on the agreed start cell and walks
    # one legal step per turn, so it never contradicts the movement model -
    # exactly the forgery physics cannot rule out, and it is reported rather
    # than hidden.
    middle = grid // 2
    cell = (0, grid - 1) if arm == "decoy_corner" else (
        max(0, middle - (turn + 1) // 2), min(grid - 1, middle + turn // 2))
    for dr, dc in SATURATING_OFFSETS:
        row, col = cell[0] + dr, cell[1] + dc
        if 0 <= row < grid and 0 <= col < grid:
            field._grid[row][col] = TRAIL_CENTER
    return field


def play(seed: int, config: Config, arm: str, evader_name: str) -> dict:
    engine = GameEngine(config.grid_size, config.cop_start, config.thief_start,
                        config.rule_set())
    cop = PoliceBrain(Role.POLICE, random.Random(seed))
    evader = EVADERS[evader_name](Role.THIEF, random.Random(seed + 999))
    perception = Perception.for_peer(Role.POLICE, config)
    evader_belief = BeliefMap(config.grid_size)
    turn = 0
    while engine.outcome is Outcome.ONGOING:
        action = cop.decide(engine, perception.belief)
        wall = tuple(action["cell"]) if action["type"] == "barrier" else None
        protocol.apply_action(engine, Role.POLICE, action)
        if engine.outcome is not Outcome.ONGOING:
            break
        evader_belief.diffuse(engine.board)
        evader_belief.observe_scent(engine.scent[Role.POLICE], engine.board)
        protocol.apply_action(engine, Role.THIEF, evader.decide(engine, evader_belief))
        turn += 1
        field = forged_field(arm, config.grid_size, turn)
        view = engine if field is None else _Forged(engine, field)
        perception.observe(view, Role.THIEF, None, barrier_cell=wall)
    return {"captured": engine.outcome is Outcome.CAPTURE,
            "refused": perception.refused_readings,
            "detected": not perception.scent_trusted,
            "turns": engine.turns_completed}


def main() -> None:
    games = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_GAMES
    config = Config.load("config")
    arms = {}
    for arm in ARMS:
        played = [play(seed, config, arm, name)
                  for name in EVADERS for seed in range(games)]
        arms[arm] = {
            "games": len(played),
            "capture_rate": round(sum(g["captured"] for g in played) / len(played), 4),
            "detected_rate": round(sum(g["detected"] for g in played) / len(played), 4),
            "mean_refusals": round(sum(g["refused"] for g in played) / len(played), 2),
        }
    report = {
        "description": "forged transmitted trail vs the movement-model check; "
                       "the honest arm's detected_rate is the FALSE-POSITIVE rate",
        "games_per_evader_per_arm": games,
        "false_positive_rate": arms["honest"]["detected_rate"],
        "arms": arms,
    }
    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
