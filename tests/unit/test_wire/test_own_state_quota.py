"""Live rival-barrier quota (Table 15): an illegal 15th+ barrier is refused
the moment it is declared — it must never enter our world and beat us
mid-game with only the post-game audit to notice."""

import pytest

from p2p_police.domain.errors import GameRuleError
from p2p_police.domain.primitives import Role
from p2p_police.domain.rules import RuleSet
from p2p_police.wire.own_state import OwnState


def thief_state(max_barriers: int = 2) -> OwnState:
    return OwnState(Role.THIEF, 7, (3, 3), RuleSet(max_barriers, 35, 35))


def test_barriers_within_quota_are_absorbed() -> None:
    own = thief_state()
    own.note_rival_barrier([0, 0])
    own.note_rival_barrier([0, 1])
    assert len(own.board.barriers) == 2


def test_redelivery_of_a_known_barrier_is_noise_not_quota() -> None:
    own = thief_state()
    own.note_rival_barrier([0, 0])
    own.note_rival_barrier([0, 1])
    own.note_rival_barrier([0, 1])  # at-least-once transport duplicate
    assert len(own.board.barriers) == 2


def test_barrier_beyond_quota_is_a_live_rule_breach() -> None:
    own = thief_state()
    own.note_rival_barrier([0, 0])
    own.note_rival_barrier([0, 1])
    with pytest.raises(GameRuleError, match="max_barriers"):
        own.note_rival_barrier([0, 2])
    assert len(own.board.barriers) == 2  # the illegal wall never landed


def test_illegal_barrier_cannot_fake_our_capture() -> None:
    """The nightmare scenario: a 15th barrier ON OUR CELL must not make
    i_am_captured() concede to an illegal wall."""
    own = thief_state(max_barriers=1)
    own.note_rival_barrier([0, 0])
    with pytest.raises(GameRuleError):
        own.note_rival_barrier([3, 3])  # our cell, beyond quota
    assert not own.i_am_captured()
