"""Technical-loss blame attribution: the score stays 0/0 (App ו) whichever
side caused it, but our report must never credit a proven cheater as
winner_group — a rival-caused breach names US the non-offending side."""

from types import SimpleNamespace

import pytest

from p2p_police.domain.errors import GameRuleError, RivalBreachError
from p2p_police.domain.primitives import Role
from p2p_police.report.artifacts import _winner_group
from p2p_police.sdk.reporting import technical_loss_report

CONFIG = SimpleNamespace(group_id="anrbj666")


def runtime_stub() -> SimpleNamespace:
    own = SimpleNamespace(turns_completed=3, digest=lambda: "ab" * 32)
    return SimpleNamespace(own=own, exchange=SimpleNamespace(own_records=[]),
                           opponent_group_id="rival888")


def test_rival_breach_is_attributed_to_the_opponent() -> None:
    report = technical_loss_report(
        Role.THIEF, runtime_stub(), RivalBreachError("15th barrier"))
    assert report["outcome"] == "technical_loss"
    assert report["breach_by"] == "opponent"


def test_local_failure_carries_no_breach_attribution() -> None:
    report = technical_loss_report(
        Role.THIEF, runtime_stub(), GameRuleError("our own state broke"))
    assert "breach_by" not in report


def test_winner_group_never_credits_the_cheater() -> None:
    report = {"outcome": "technical_loss", "opponent_group_id": "rival888",
              "role": "thief", "breach_by": "opponent"}
    assert _winner_group(CONFIG, report) == "anrbj666"


def test_winner_group_default_technical_loss_stays_ours_to_lose() -> None:
    report = {"outcome": "technical_loss", "opponent_group_id": "rival888",
              "role": "thief"}
    assert _winner_group(CONFIG, report) == "rival888"


def test_quota_breach_raises_the_attributed_type() -> None:
    from p2p_police.domain.rules import RuleSet
    from p2p_police.wire.own_state import OwnState

    own = OwnState(Role.THIEF, 7, (3, 3), RuleSet(1, 35, 35))
    own.note_rival_barrier([0, 0])
    with pytest.raises(RivalBreachError):
        own.note_rival_barrier([0, 1])
