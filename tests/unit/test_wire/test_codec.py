"""Reference-v3 codec: the demo TurnMessage shape, closed key set."""

import pytest

from p2p_police.domain.errors import GameRuleError
from p2p_police.domain.scent import ScentField
from p2p_police.wire import codec
from p2p_police.wire.own_state import ReceivedScent


def message(**overrides):
    base = codec.build_turn_message(1, "police", "hello there", {"0,0": 0.9}, "c" * 64)
    base.update(overrides)
    return base


def test_registry_example_keys_are_all_present():
    msg = message()
    for key in ("step", "commit", "hint", "smell_grid", "barrier_placed"):
        assert key in msg  # the lock doc's example turn_message_keys


def test_shape_is_closed_and_has_no_position_field():
    msg = message()
    assert set(msg) == set(codec.REQUIRED_KEYS) | set(codec.OPTIONAL_KEYS)
    assert "position" not in msg
    assert "positions" not in msg


def test_round_trip():
    parsed = codec.parse_turn_message(message(barrier_placed=[2, 2]))
    assert parsed["step"] == 1
    assert parsed["sender"] == "police"
    assert parsed["barrier_placed"] == [2, 2]
    assert parsed["capture_claim"] is None


def test_unknown_key_rejected():
    """Closed shape: a position (or anything else) can never ride along."""
    with pytest.raises(GameRuleError):
        codec.parse_turn_message(message(position=[3, 3]))


def test_missing_required_key_rejected():
    bad = message()
    del bad["commit"]
    with pytest.raises(GameRuleError):
        codec.parse_turn_message(bad)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("capture_claim", [1]),
        ("barrier_placed", "x"),
        ("claim_response", {"claim": [1, 2]}),  # missing 'caught'
        ("claim_response", {"caught": True}),   # missing 'claim'
        ("win_claim", {"kind": 3}),
        ("smell_grid", [1, 2]),
        ("sender", "judge"),
        ("hint", 7),
    ],
)
def test_malformed_fields_rejected(field, value):
    with pytest.raises(GameRuleError):
        codec.parse_turn_message(message(**{field: value}))


def test_valid_claim_flow_fields_parse():
    parsed = codec.parse_turn_message(
        message(sender="thief", claim_response={"claim": [3, 3], "caught": True},
                win_claim={"type": "survival"}))
    assert parsed["claim_response"]["caught"] is True
    assert parsed["win_claim"] == {"type": "survival"}


def test_scent_serialization_round_trips_through_the_wire():
    field = ScentField(7)
    field.update((3, 3))
    field.update((3, 4))
    received = ReceivedScent(7)
    received.absorb(codec.serialize_scent(field))
    assert received.values() == field.values()


def test_zero_cells_stay_off_the_wire():
    field = ScentField(7)
    field.update((0, 0))
    wire = codec.serialize_scent(field)
    assert wire  # something crossed
    assert all(value > 0 for value in wire.values())
    assert "6,6" not in wire
