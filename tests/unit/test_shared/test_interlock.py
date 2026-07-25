"""Lecturer-address interlock: structural, not comment-based — email can
address the league ONLY when a counted game is doubly armed ([email]
counted = true AND the --counted CLI flag); friendlies are unaffected."""

import pytest

from p2p_police.shared.config import Config
from p2p_police.shared.interlock import (
    EmailInterlockError,
    counted_armed,
    ensure_email_allowed,
    league_hits,
)

LEAGUE = "rmisegal@gmail.com"
LEAGUE_ALIAS = "rmisegal+uoh26finalgame@gmail.com"
FRIEND = "teammate@example.com"


def config_with_email(config_dir, **email) -> Config:
    config = Config.load(config_dir)
    config.private["email"] = {"recipient": FRIEND, "mode": "send", **email}
    return config


def test_league_recipient_without_arming_refuses(config_dir):
    config = config_with_email(config_dir)
    with pytest.raises(EmailInterlockError, match="counted"):
        ensure_email_allowed(config, LEAGUE)


@pytest.mark.parametrize("half", [
    {"counted": True},                              # config half only
    {"counted_cli_armed": True},                    # CLI half only
])
def test_one_armed_half_is_never_enough(config_dir, half):
    config = config_with_email(config_dir, **half)
    with pytest.raises(EmailInterlockError):
        ensure_email_allowed(config, LEAGUE_ALIAS)


def test_both_armings_allow_the_league_recipient(config_dir):
    config = config_with_email(config_dir, counted=True, counted_cli_armed=True)
    ensure_email_allowed(config, f"{LEAGUE}, {FRIEND}")  # must not raise
    assert counted_armed(config) is True


def test_friendly_recipients_are_unaffected(config_dir):
    config = config_with_email(config_dir)
    ensure_email_allowed(config, f"{FRIEND}, second.friend@example.com")
    assert league_hits(config, FRIEND) == []


def test_plus_alias_and_case_collapse_onto_the_league_base(config_dir):
    """rmisegal+anything@gmail.com IS the lecturer inbox — the tag and the
    letter case must never sneak a rehearsal email past the interlock."""
    config = config_with_email(config_dir)
    assert league_hits(config, LEAGUE_ALIAS) == [LEAGUE_ALIAS]
    assert league_hits(config, "RMisegal@Gmail.com") == ["RMisegal@Gmail.com"]
    with pytest.raises(EmailInterlockError):
        ensure_email_allowed(config, f"{FRIEND}, {LEAGUE_ALIAS}")


def test_config_league_addresses_extend_the_known_floor(config_dir):
    """[email] league_addresses adds addresses; omitting it never disarms."""
    config = config_with_email(config_dir,
                               league_addresses=["league-desk@example.org"])
    with pytest.raises(EmailInterlockError):
        ensure_email_allowed(config, "league-desk@example.org")
    with pytest.raises(EmailInterlockError):
        ensure_email_allowed(config, LEAGUE)  # the floor still holds
