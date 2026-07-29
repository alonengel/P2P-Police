"""--counted refusal gate (rules 32/51 + Table 18): an ARMED counted run
must be able to deliver the league report or it plays nothing; training
runs (no --counted) never reach any of these checks."""

from types import SimpleNamespace

import pytest

from p2p_police.domain.errors import GameRuleError
from p2p_police.domain.negotiation import validate_counted_terms
from p2p_police.shared.interlock import EmailInterlockError, ensure_counted_posture

LEAGUE = "rmisegal+uoh26finalgame@gmail.com"
GOOD_SHARED = {"network_and_league": {"num_games": 6}}


def config(email: dict, shared: dict = GOOD_SHARED) -> SimpleNamespace:
    return SimpleNamespace(private={"email": email}, shared=shared)


def test_training_run_is_untouched() -> None:
    """No --counted: disabled mode + personal recipients stay legal."""
    ensure_counted_posture(config({
        "mode": "disabled", "recipient": "engel.alon@gmail.com, Imree.c@gmail.com"}))


def test_armed_and_deliverable_passes() -> None:
    ensure_counted_posture(config({
        "counted_cli_armed": True, "counted": True, "mode": "send",
        "recipient": f"engel.alon@gmail.com, {LEAGUE}"}))


def test_armed_with_email_disabled_is_refused() -> None:
    with pytest.raises(EmailInterlockError, match="mode"):
        ensure_counted_posture(config({
            "counted_cli_armed": True, "counted": True, "mode": "disabled",
            "recipient": LEAGUE}))


def test_armed_without_league_recipient_is_refused() -> None:
    with pytest.raises(EmailInterlockError, match="league"):
        ensure_counted_posture(config({
            "counted_cli_armed": True, "counted": True, "mode": "send",
            "recipient": "engel.alon@gmail.com, Imree.c@gmail.com"}))


def test_armed_without_config_half_is_refused() -> None:
    with pytest.raises(EmailInterlockError, match="config half"):
        ensure_counted_posture(config({
            "counted_cli_armed": True, "mode": "send", "recipient": LEAGUE}))


def test_counted_num_games_deviation_is_refused() -> None:
    """Table 18: num_games is FIXED at 6 on a counted run only — enforced
    at game start (sdk.run_peer), tested here on the domain validator."""
    with pytest.raises(GameRuleError, match="num_games"):
        validate_counted_terms({"network_and_league": {"num_games": 3}})


def test_counted_num_games_six_passes() -> None:
    validate_counted_terms(GOOD_SHARED)


def test_training_short_series_stays_legal() -> None:
    """The same 3-game terms are FINE without --counted (warm-up posture):
    the standard validator never sees COUNTED_FIXED_TERMS."""
    ensure_counted_posture(config(
        {"mode": "disabled", "recipient": "engel.alon@gmail.com"},
        shared={"network_and_league": {"num_games": 3}}))
