"""Pins the engine-level full-turn decay boundary to the golden vectors
(spec-audit GAP-1): decay+emission fire exactly once per completed round, for
BOTH fields — the cross-repo contract, not just a local unit test."""

import json
from pathlib import Path

from p2p_police.domain.engine import GameEngine
from p2p_police.domain.primitives import Move, Role
from p2p_police.domain.rules import RuleSet

VECTORS = json.loads(
    (Path(__file__).parents[2] / "vectors" / "physics_vectors.json").read_text()
)["engine"]["full_turn_boundary"]

MOVES = {"E": Move.E, "W": Move.W, "STAY": Move.STAY}


def test_engine_full_turn_boundary_matches_vectors_exactly() -> None:
    engine = GameEngine(
        7, (0, 0), (3, 3), RuleSet(max_barriers=14, max_moves=35, survival_threshold=35)
    )
    for (cop_key, thief_key), expected in zip(
        VECTORS["rounds"], VECTORS["snapshots"], strict=True
    ):
        engine.police_move(MOVES[cop_key])
        engine.thief_move(MOVES[thief_key])
        assert engine.turns_completed == expected["turns_completed"]
        assert engine.scent[Role.POLICE].values() == expected["police_field"]
        assert engine.scent[Role.THIEF].values() == expected["thief_field"]
