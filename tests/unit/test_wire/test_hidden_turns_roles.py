"""their_half_turn: only the THIEF's truth-duty flow can concede a capture.

Queued live finding: any caught=True used to classify as capture regardless
of the sender's role — but the claim flow is one-directional (the cop
claims, the thief answers about its own cell; rules 21-22). A police-role
caught=True must never hand the receiving thief a fake game end."""

from types import SimpleNamespace

from p2p_police.domain.primitives import Outcome, Role
from p2p_police.domain.rules import RuleSet
from p2p_police.wire import codec, hidden_turns
from p2p_police.wire.own_state import OwnState


def rival_message(sender: str, caught: bool) -> dict:
    return codec.build_turn_message(
        1, sender, "harmless hint", {}, "c" * 64,
        claim_response={"caught": caught, "claim": [3, 3]})


def stub_runtime(role: Role, message: dict) -> SimpleNamespace:
    start = (0, 0) if role is Role.POLICE else (3, 3)
    own = OwnState(role, 7, start, RuleSet(14, 35, 35))
    own.next_actor = role.rival  # mid-round: the rival's half-turn is due
    return SimpleNamespace(
        role=role, own=own, their_step=0, pending_claim_response=None,
        exchange=SimpleNamespace(receive_turn=lambda step: message),
        perception=SimpleNamespace(observe=lambda *_: None, emit=lambda *_: None),
    )


def test_thief_conceding_caught_ends_the_cops_game_as_capture() -> None:
    rt = stub_runtime(Role.POLICE, rival_message("thief", caught=True))
    hidden_turns.their_half_turn(rt)
    assert rt.own.outcome is Outcome.CAPTURE


def test_police_role_caught_true_cannot_fake_our_capture() -> None:
    """A cop has no concession to make: its caught=True is noise, and the
    receiving thief's game continues."""
    rt = stub_runtime(Role.THIEF, rival_message("police", caught=True))
    hidden_turns.their_half_turn(rt)
    assert rt.own.outcome is Outcome.ONGOING


def test_caught_false_answer_never_classifies_either_side() -> None:
    for role, sender in ((Role.POLICE, "thief"), (Role.THIEF, "police")):
        rt = stub_runtime(role, rival_message(sender, caught=False))
        hidden_turns.their_half_turn(rt)
        assert rt.own.outcome is Outcome.ONGOING
