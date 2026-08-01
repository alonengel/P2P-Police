"""Capture-claim truth duty (rules 21-22): structural, not behavioral."""

import inspect

from p2p_police.domain.primitives import Role
from p2p_police.domain.rules import RuleSet
from p2p_police.wire import claims
from p2p_police.wire.own_state import OwnState


def thief_at(cell):
    return OwnState(Role.THIEF, 7, cell, RuleSet(14, 35, 35))


def test_answer_is_truthful_when_the_claim_hits():
    answer = claims.answer_capture_claim(thief_at((3, 3)), [3, 3])
    assert answer == {"claim": [3, 3], "caught": True}


def test_answer_is_truthful_when_the_claim_misses():
    answer = claims.answer_capture_claim(thief_at((3, 4)), [3, 3])
    assert answer == {"claim": [3, 3], "caught": False}


def test_no_strategy_input_can_reach_the_answer():
    """Rules 21-22 enforced by SIGNATURE: the ANSWER is a pure function of
    (own state, claimed cell) - no brain, config, policy or RNG parameter
    exists through which strategy code could bend the truth."""
    assert list(inspect.signature(claims.answer_capture_claim).parameters) == [
        "own", "claim_cell"]
    assert list(inspect.signature(claims.concede_declaration).parameters) == ["own"]
    for fn in (claims.answer_capture_claim, claims.concede_declaration):
        names = set(inspect.signature(fn).parameters)
        assert not names & {"brain", "strategy", "config", "rng", "policy", "deceiver"}


def test_the_outbound_claim_may_choose_silence_but_never_a_lie():
    """The line the truth duty actually draws: WHETHER to claim is strategy
    (a claim broadcasts our true cell, so claiming every turn is a leak);
    WHAT a claim says is not. capture_claim_for may consult belief/config to
    stay quiet, and every value it DOES return is our real cell."""
    own = thief_at((2, 5))  # any OwnState: the claim reads its own cell
    move = {"type": "move", "move": "E"}
    from types import SimpleNamespace

    sharp = SimpleNamespace(belief=SimpleNamespace(value_at=lambda _c: 1.0))
    mute = SimpleNamespace(belief=SimpleNamespace(value_at=lambda _c: 0.0))
    config = SimpleNamespace(private={})
    assert claims.capture_claim_for(move, own, sharp, config) == [2, 5]
    assert claims.capture_claim_for(move, own, mute, config) is None
    assert claims.capture_claim_for(move, own) == [2, 5]  # unfiltered


def test_concede_names_my_true_cell():
    assert claims.concede_declaration(thief_at((2, 5))) == {
        "claim": [2, 5], "caught": True}


def test_cop_claims_its_landing_cell_only_after_a_move():
    cop = OwnState(Role.POLICE, 7, (0, 0), RuleSet(14, 35, 35))
    cop.next_actor = Role.POLICE  # after the thief's opener (reference cadence)
    cop.apply_own_action({"type": "move", "move": "E"})
    assert claims.capture_claim_for({"type": "move", "move": "E"}, cop) == [0, 1]
    assert claims.capture_claim_for({"type": "barrier", "cell": [0, 0]}, cop) is None
