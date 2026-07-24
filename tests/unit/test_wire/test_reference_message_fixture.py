"""The rival thief's LITERAL step-1 TurnMessage from the 2026-07-24 live
cross-team run: all ten keys present with EXPLICIT nulls, a dense 25-cell
smell_grid mapping (5x5 radial kernel, "r,c" keys - the reference/demo
emission), a microseconds+offset timestamp. Our hidden receive path must
absorb it untouched - proving that run's police silence was transport loss
(the inbound tool call never reached the inbox; logs/p2p_police.log shows
the session open with no CallToolRequest), never shape rejection."""

import random

import pytest

from p2p_police.domain.errors import GameRuleError
from p2p_police.domain.primitives import Role
from p2p_police.infra.mcp_server import PeerInboxes
from p2p_police.sdk import hidden as hidden_mod
from p2p_police.shared.config import Config
from p2p_police.strategy.brain_base import RandomBrain
from p2p_police.wire import codec, hidden_turns
from p2p_police.wire.own_state import ReceivedScent


def radial_25_cells(center=(3, 3), intensity=0.9) -> dict:
    """The reference's 5x5 radial emission (falloff intensity/3, Chebyshev)."""
    grid = {}
    for dr in range(-2, 3):
        for dc in range(-2, 3):
            ring = max(abs(dr), abs(dc))
            value = round(intensity - (intensity / 3) * ring, 3)
            grid[f"{center[0] + dr},{center[1] + dc}"] = value
    return grid


def literal_rival_message() -> dict:
    return {
        "step": 1,
        "sender": "thief",
        "commit": "6c8921b3" + "0" * 56,
        "hint": "They say the crowds near Grand Central hide anyone.",
        "smell_grid": radial_25_cells(),
        "timestamp": "2026-07-24T10:28:21.107590+00:00",
        "barrier_placed": None,
        "capture_claim": None,
        "claim_response": None,
        "win_claim": None,
    }


def test_parse_accepts_the_literal_reference_emission():
    parsed = codec.parse_turn_message(literal_rival_message())
    assert parsed["step"] == 1 and parsed["sender"] == "thief"
    assert parsed["timestamp"] == "2026-07-24T10:28:21.107590+00:00"
    assert len(parsed["smell_grid"]) == 25
    for optional in ("barrier_placed", "capture_claim", "claim_response", "win_claim"):
        assert parsed[optional] is None  # explicit null == omitted


def test_closed_key_set_still_rejects_a_genuinely_unknown_key():
    poisoned = {**literal_rival_message(), "position": [3, 3]}
    with pytest.raises(GameRuleError, match="unknown keys"):
        codec.parse_turn_message(poisoned)


def test_their_half_turn_absorbs_the_literal_message(config_dir):
    config = Config.load(config_dir)
    config.private["network"]["wire_shape"] = "reference"
    inboxes = PeerInboxes()
    rt = hidden_mod.build_runtime(config, transport=None, inboxes=inboxes,
                                  brain=RandomBrain(Role.POLICE, random.Random(3)))
    inboxes.turns.put(literal_rival_message())
    hidden_turns.their_half_turn(rt)
    assert rt.their_step == 1
    assert rt.own.turns_completed == 1  # the thief's step ticked the round
    assert rt.own.next_actor is Role.POLICE  # token passed - we now answer
    assert rt.exchange.their_records[-1]["commit"].startswith("6c8921b3")
    assert rt.perception.last_hint.startswith("They say the crowds")
    assert rt.own.scent[Role.THIEF].value_at((3, 3)) == 0.9  # dense grid absorbed


def test_sparse_serializer_and_dense_reference_grid_are_one_format():
    """Both directions speak {"r,c": intensity}: our sparse serializer's
    output and the reference's dense 25-cell kernel absorb identically
    (a 0.0-valued cell is legal on the wire and stays zero)."""
    received = ReceivedScent(7)
    received.absorb({**radial_25_cells(), "0,0": 0.0})
    assert received.value_at((3, 3)) == 0.9
    assert received.value_at((1, 1)) == 0.3  # outer ring
    assert received.value_at((0, 0)) == 0.0
    round_trip = ReceivedScent(7)
    round_trip.absorb(codec.serialize_scent(received))
    assert round_trip.values() == received.values()
