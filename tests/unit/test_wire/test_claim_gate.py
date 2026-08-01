"""The capture-claim gate: claim our TRUE cell, but not every turn.

The claim names our real position, so an unconditional claim broadcasts the
cop's exact cell on every move — and a claim-reading thief collapses its
estimate onto it (2026-08-01: the rival's thief does exactly that, and their
own published sweep prices a quiet cop at ~24% of cop points). Gating changes
what we SAY, never whether what we say is true.
"""

from types import SimpleNamespace

from p2p_police.domain.primitives import Role
from p2p_police.domain.rules import RuleSet
from p2p_police.wire import claims
from p2p_police.wire.own_state import OwnState

MOVE = {"type": "move", "move": "E"}


def cop_at(cell) -> OwnState:
    own = OwnState(Role.POLICE, 7, cell, RuleSet(14, 35, 35))
    return own


def perception_with(mass: float, cell) -> SimpleNamespace:
    belief = SimpleNamespace(value_at=lambda c, m=mass: m if c == cell else 0.0)
    return SimpleNamespace(belief=belief)


def config_with(threshold: float | None = None) -> SimpleNamespace:
    strategy = {"claim": {"threshold": threshold}} if threshold is not None else {}
    return SimpleNamespace(private={"strategy": strategy})


def test_sharp_belief_claims() -> None:
    own = cop_at((3, 3))
    claim = claims.capture_claim_for(MOVE, own, perception_with(0.8, (3, 3)),
                                     config_with())
    assert claim == [3, 3]  # our TRUE cell, as always


def test_diffuse_belief_stays_quiet() -> None:
    own = cop_at((3, 3))
    assert claims.capture_claim_for(
        MOVE, own, perception_with(0.01, (3, 3)), config_with()) is None


def test_the_threshold_is_configurable() -> None:
    own = cop_at((3, 3))
    loud = config_with(0.0)  # claim always: the historical behaviour
    assert claims.capture_claim_for(
        MOVE, own, perception_with(0.01, (3, 3)), loud) == [3, 3]
    quiet = config_with(0.99)
    assert claims.capture_claim_for(
        MOVE, own, perception_with(0.5, (3, 3)), quiet) is None


def test_a_barrier_never_claims() -> None:
    own = cop_at((3, 3))
    barrier = {"type": "barrier", "cell": [3, 4]}
    assert claims.capture_claim_for(
        barrier, own, perception_with(1.0, (3, 3)), config_with()) is None


def test_unfiltered_call_keeps_the_old_shape() -> None:
    """Replay and tests may call without a belief: claim unconditionally."""
    assert claims.capture_claim_for(MOVE, cop_at((3, 3))) == [3, 3]
