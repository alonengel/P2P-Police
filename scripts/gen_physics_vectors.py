"""Regenerate tests/vectors/physics_vectors.json from the current physics.

WARNING: the vectors are the twin repos' behavioral contract (ADR-0001) AND
part of the scent model locked with opponents (rule 23). Regenerate ONLY on a
deliberate, documented physics change, and copy the output byte-identically
to the sibling repo in the same session.

Usage: uv run python scripts/gen_physics_vectors.py
"""

import json
from pathlib import Path

from p2p_police.domain.board import Board
from p2p_police.domain.engine import GameEngine
from p2p_police.domain.evidence import SATURATING_OFFSETS, decoded_reach, plateau_origin
from p2p_police.domain.primitives import Move, Role
from p2p_police.domain.rules import RuleSet
from p2p_police.domain.scent import EMISSION_KERNEL, ScentField

GRID = 7


def single_deposit_decay() -> list[float]:
    """Value at (3,3): one emission there, then decay-only turns (emitter far)."""
    field = ScentField(GRID)
    field.update((3, 3))
    series = [field.value_at((3, 3))]
    for _ in range(7):
        field.update((0, 0))  # kernel (radius 2) never reaches (3,3) from (0,0)
        series.append(field.value_at((3, 3)))
    return series


def corner_emission() -> list[list[float]]:
    field = ScentField(GRID)
    field.update((0, 0))
    return field.values()


def two_turn_evolution() -> list[list[list[float]]]:
    field = ScentField(GRID)
    snapshots = []
    for emitter in [(3, 3), (3, 4)]:
        field.update(emitter)
        snapshots.append(field.values())
    return snapshots


def engine_full_turn_boundary() -> dict:
    """Pin the ONCE-per-FULL-turn decay boundary at ENGINE level (dossier D.2).

    Scripted rounds: (cop E, thief STAY) then (cop E, thief W). Snapshots of
    BOTH scent fields after each round prove decay+emission fire exactly once
    per completed round — a twin wiring decay per half-move would diverge.
    """
    engine = GameEngine(
        GRID, (0, 0), (3, 3), RuleSet(max_barriers=14, max_moves=35, survival_threshold=35)
    )
    snapshots = []
    for cop_move, thief_move in [(Move.E, Move.STAY), (Move.E, Move.W)]:
        engine.police_move(cop_move)
        engine.thief_move(thief_move)
        snapshots.append(
            {
                "turns_completed": engine.turns_completed,
                "police_field": engine.scent[Role.POLICE].values(),
                "thief_field": engine.scent[Role.THIEF].values(),
            }
        )
    return {"rounds": [["E", "STAY"], ["E", "W"]], "snapshots": snapshots}


def evidence_decode() -> dict:
    """Pin the INFERENCE the twins run over a reading, not just the physics.

    Parity hashing catches drift BETWEEN the twins; these vectors catch a
    change made identically in both — the decode is what every brain scores
    on, so a silent shift in it is a silent shift in play. Cases: the reach
    ladder, a corner dweller's saturated plateau and its fitted origin, and
    the three shapes the fit must REFUSE to pin (silence, a lone spike, an
    open march).
    """
    board = Board(GRID)
    camp = ScentField(GRID)
    for _ in range(12):
        camp.update((6, 6))
    march = ScentField(GRID)
    for col in range(GRID):
        march.update((3, col))
    spike = ScentField(GRID)
    spike.update((3, 3))
    return {
        "saturating_offsets": [list(offset) for offset in SATURATING_OFFSETS],
        "reach_ladder": {str(value): decoded_reach(value)
                         for value in (0.9, 0.81, 0.729, 0.62, 0.2, 0.04, 0.0)},
        "corner_dweller_field": camp.values(),
        "corner_dweller_origin": list(plateau_origin(camp, board, GRID)),
        "refusals": {
            "silence": plateau_origin(ScentField(GRID), board, GRID),
            "lone_spike": plateau_origin(spike, board, GRID),
            "open_march": plateau_origin(march, board, GRID),
        },
    }


def main() -> None:
    payload = {
        "_comment": "Twin-repo physics contract. Byte-identical in both repos.",
        "schema": 3,
        "scent": {
            "kernel": [list(row) for row in EMISSION_KERNEL],
            "grid_size": GRID,
            "single_deposit_decay_at_3_3": single_deposit_decay(),
            "corner_emission_at_0_0": corner_emission(),
            "two_turn_evolution_3_3_then_3_4": two_turn_evolution(),
        },
        "engine": {
            "full_turn_boundary": engine_full_turn_boundary(),
        },
        "evidence": evidence_decode(),
    }
    out = Path("tests/vectors/physics_vectors.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
