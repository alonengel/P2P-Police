"""OwnState: the hidden wire's engine wrapper — own truth only (rules 8-9)."""

import pytest

from p2p_police.domain.errors import GameRuleError, IllegalBarrierError, IllegalMoveError
from p2p_police.domain.primitives import Role
from p2p_police.domain.rules import RuleSet
from p2p_police.wire.own_state import OwnState, ReceivedScent


def own(role=Role.POLICE, start=(0, 0)):
    return OwnState(role, 7, start, RuleSet(14, 35, 35))


def test_rival_position_is_structurally_absent():
    state = own()
    assert Role.THIEF not in state.positions
    with pytest.raises(KeyError):
        _ = state.positions[Role.THIEF]


def test_the_thief_holds_the_opening_token():
    """Reference cadence: the THIEF seeds turn 1 (demo runtime seeds the
    thief's take_turn before the receive-respond loop)."""
    assert own().next_actor is Role.THIEF
    assert own(Role.THIEF, (3, 3)).next_actor is Role.THIEF


def test_apply_own_move_walks_the_board():
    state = own(Role.THIEF, (3, 3))  # the thief opens
    state.apply_own_action({"type": "move", "move": "S"})
    assert state.cell == (4, 3)
    assert state.next_actor is Role.POLICE


def test_illegal_move_rejected_not_fixed():
    with pytest.raises(IllegalMoveError):
        own(Role.THIEF, (0, 0)).apply_own_action({"type": "move", "move": "N"})


def test_out_of_turn_action_rejected():
    police = own()  # the thief opens every round on this wire
    with pytest.raises(GameRuleError):
        police.apply_own_action({"type": "move", "move": "S"})


def test_barrier_placement_validated_and_returned():
    state = own()
    state.next_actor = Role.POLICE  # after the thief's opener
    placed = state.apply_own_action({"type": "barrier", "cell": [0, 1]})
    assert placed == (0, 1)
    assert state.board.is_barrier((0, 1))


def test_thief_may_never_place_barriers():
    thief = own(Role.THIEF, (3, 3))
    with pytest.raises(GameRuleError):
        thief.apply_own_action({"type": "barrier", "cell": [3, 4]})


def test_far_barrier_rejected():
    state = own()
    state.next_actor = Role.POLICE
    with pytest.raises(IllegalBarrierError):
        state.apply_own_action({"type": "barrier", "cell": [5, 5]})


def test_rival_barrier_absorbed_once_duplicates_tolerated():
    state = own()
    state.note_rival_barrier([2, 2])
    state.note_rival_barrier([2, 2])  # at-least-once transport noise
    assert state.board.is_barrier((2, 2))


def test_off_board_rival_barrier_is_protocol_failure():
    with pytest.raises(GameRuleError):
        own().note_rival_barrier([9, 9])


def test_capture_detection_surrounded_and_barrier_on_cell():
    thief = own(Role.THIEF, (0, 0))
    assert not thief.i_am_captured()
    thief.note_rival_barrier([0, 1])
    thief.note_rival_barrier([1, 0])
    assert thief.i_am_captured()  # corner + two walls = surrounded (rule 47)
    other = own(Role.THIEF, (3, 3))
    other.note_rival_barrier([3, 3])
    assert other.i_am_captured()  # barrier on my cell = automatic capture


def test_close_full_turn_updates_own_field_and_clock():
    state = own(start=(3, 3))
    state.close_full_turn()
    assert state.turns_completed == 1
    assert state.scent[Role.POLICE].value_at((3, 3)) == 0.9


def test_survival_threshold():
    state = own()
    state.turns_completed = 35
    assert state.survival_reached()


def test_digest_is_self_only_and_deterministic():
    first, second = own(Role.THIEF, (3, 3)), own(Role.THIEF, (3, 3))
    assert first.digest() == second.digest()
    second.apply_own_action({"type": "move", "move": "E"})
    assert first.digest() != second.digest()


def test_received_scent_absorbs_and_replaces_snapshots():
    scent = ReceivedScent(7)
    scent.absorb({"3,3": 0.9, "3,4": 0.62, "9,9": 0.5})  # off-board dropped
    assert scent.value_at((3, 3)) == 0.9
    assert scent.value_at((3, 4)) == 0.62
    scent.absorb({"3,4": 0.42})  # replace, never merge (sender's truth wins)
    assert scent.value_at((3, 3)) == 0.0
    assert scent.value_at((3, 4)) == 0.42
