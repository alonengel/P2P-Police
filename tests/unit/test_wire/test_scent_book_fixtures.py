"""Interop-kit fixtures for multiplicative_book_v1, byte-exact (zero tolerance).

The hidden wire transmits our OWN field under the locked book model, so the
serialized bytes must equal what the registry pins for that model. The CORE
canonical-json / commit-reveal / game_uid fixtures are already covered by
tests/unit/test_reference_conformance.py; this file adds the pheromone math
under the book model plus the serialization the wire actually ships.
"""

import json
from pathlib import Path

from p2p_police.domain.scent import EMISSION_KERNEL, ScentField
from p2p_police.wire.codec import serialize_scent

FIXTURE = json.loads(
    (Path(__file__).parents[2] / "wire_vectors" / "scent_book_v3.json").read_text(
        encoding="utf-8"))


def test_kernel_matches_the_registered_lookup_verbatim():
    expected = FIXTURE["kernel"]
    ours = [list(row) for row in EMISSION_KERNEL]
    assert ours == expected


def test_emit_cases_byte_exact():
    for case in FIXTURE["emit"]:
        field = ScentField(7)
        field.update(tuple(case["center"]))
        assert serialize_scent(field) == case["field"], case["note"]


def test_field_walk_three_turns_byte_exact():
    walk = FIXTURE["field_walk"]
    field = ScentField(walk["board_size"])
    for turn in walk["turns"]:
        field.update(tuple(turn["center"]))
        assert serialize_scent(field) == turn["field"], f"turn {turn['turn']}"


def test_scalar_pure_decay_and_clamp_traces():
    traces = FIXTURE["scalar_traces"]
    decay = traces["pure_decay"]
    assert (1 - 0.1) * decay["tau"] + decay["delta"] == decay["after"]
    clamp = traces["clamp"]
    assert (1 - 0.1) * clamp["tau"] + clamp["delta"] == clamp["raw"]
    field = ScentField(7)
    field.update((3, 3))  # empty + centre deposit = saturated 0.9
    field.update((3, 4))  # decayed 0.81 + orthogonal 0.62 -> clamped
    assert field.value_at((3, 3)) == clamp["after"]


def test_scalar_chain_through_the_field():
    steps = FIXTURE["scalar_traces"]["chain"]["steps"]
    field = ScentField(7)
    field.update((3, 4))  # orthogonal deposit at (3,3): delta 0.62
    assert field.value_at((3, 3)) == steps[0]["tau"]
    field.update((3, 5))  # kernel distance 2: delta 0.2
    assert field.value_at((3, 3)) == steps[1]["tau"]
    field.update((3, 5))
    assert field.value_at((3, 3)) == steps[2]["tau"]


def test_ordering_probe_pins_our_evaluation_order():
    """(1 - rho) * tau + delta, exactly as the field computes it — the
    algebraically-equal alternative diverges in the last IEEE-754 bit."""
    for case in FIXTURE["ordering_probe"]["cases"]:
        pinned = (1 - 0.1) * case["tau"] + case["delta"]
        assert pinned == case["pinned_order"]
        assert pinned != case["alternative_order"]
