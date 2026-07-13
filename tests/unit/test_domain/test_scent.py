"""Scent tests pin the parity-locked pheromone model against the golden
vectors (ADR-0001) and encode ch. 4: kernel emission, once-per-turn decay,
clamping, and the silent-cell-is-zero principle."""

import json
from pathlib import Path

import pytest

from p2p_police.domain.scent import EMISSION_KERNEL, ScentField

VECTORS = json.loads(
    (Path(__file__).parents[2] / "vectors" / "physics_vectors.json").read_text()
)["scent"]


def test_kernel_matches_golden_vector_exactly() -> None:
    assert [list(row) for row in EMISSION_KERNEL] == VECTORS["kernel"]


def test_kernel_center_is_0_9_and_symmetric() -> None:
    assert EMISSION_KERNEL[2][2] == 0.9
    for r in range(5):
        for c in range(5):
            assert EMISSION_KERNEL[r][c] == EMISSION_KERNEL[4 - r][4 - c]
            assert EMISSION_KERNEL[r][c] == EMISSION_KERNEL[c][r]


def test_single_deposit_decay_series_matches_vectors_exactly() -> None:
    """0.9, then (1-rho) per turn: the 0.81 expectation used for lie detection."""
    field = ScentField(VECTORS["grid_size"])
    field.update((3, 3))
    series = [field.value_at((3, 3))]
    for _ in range(7):
        field.update((0, 0))
        series.append(field.value_at((3, 3)))
    assert series == VECTORS["single_deposit_decay_at_3_3"]


def test_corner_emission_matches_vectors_exactly() -> None:
    field = ScentField(VECTORS["grid_size"])
    field.update((0, 0))
    assert field.values() == VECTORS["corner_emission_at_0_0"]


def test_two_turn_evolution_matches_vectors_exactly() -> None:
    field = ScentField(VECTORS["grid_size"])
    snapshots = []
    for emitter in [(3, 3), (3, 4)]:
        field.update(emitter)
        snapshots.append(field.values())
    assert snapshots == VECTORS["two_turn_evolution_3_3_then_3_4"]


def test_untouched_cell_is_silent_zero() -> None:
    field = ScentField(7)
    field.update((0, 0))
    assert field.value_at((6, 6)) == 0.0


def test_re_emission_is_clamped_at_center_intensity() -> None:
    """Dwelling on a cell keeps it high but never above 0.9 (tau range)."""
    field = ScentField(7)
    for _ in range(5):
        field.update((3, 3))
    assert field.value_at((3, 3)) == 0.9


def test_values_returns_a_defensive_copy() -> None:
    field = ScentField(7)
    field.values()[0][0] = 123.0
    assert field.value_at((0, 0)) == 0.0


def test_config_mismatch_with_fixed_kernel_is_rejected() -> None:
    with pytest.raises(ValueError):
        ScentField(7, center_intensity=0.8)
    with pytest.raises(ValueError):
        ScentField(7, kernel_size=3)
    with pytest.raises(ValueError):
        ScentField(7, decay=0.0)
