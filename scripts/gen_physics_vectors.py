"""Regenerate tests/vectors/physics_vectors.json from the current physics.

WARNING: the vectors are the twin repos' behavioral contract (ADR-0001) AND
part of the scent model locked with opponents (rule 23). Regenerate ONLY on a
deliberate, documented physics change, and copy the output byte-identically
to the sibling repo in the same session.

Usage: uv run python scripts/gen_physics_vectors.py
"""

import json
from pathlib import Path

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


def main() -> None:
    payload = {
        "_comment": "Twin-repo physics contract. Byte-identical in both repos.",
        "schema": 1,
        "scent": {
            "kernel": [list(row) for row in EMISSION_KERNEL],
            "grid_size": GRID,
            "single_deposit_decay_at_3_3": single_deposit_decay(),
            "corner_emission_at_0_0": corner_emission(),
            "two_turn_evolution_3_3_then_3_4": two_turn_evolution(),
        },
    }
    out = Path("tests/vectors/physics_vectors.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
