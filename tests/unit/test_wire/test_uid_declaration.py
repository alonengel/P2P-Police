"""The derived game_uid, declared at the handshake (joint proposal).

The uid never crosses the wire in the reference shape, so two peers deriving
it from DIFFERENT inputs stay silently divergent for a whole series - nothing
notices until the two reports are diffed the next morning. Declaring it under
the both-declare rule turns that into a refusal at T+seconds.

Both-declare semantics, unchanged from the other families: refuse only when
BOTH peers declare and the values differ; omission never refuses, so an
unmodified reference peer stays playable.
"""

import pytest

from p2p_police.domain import game_ids
from p2p_police.domain.errors import GameRuleError
from p2p_police.shared.config import Config
from p2p_police.wire import terms


def _message(config, opponent=None):
    return terms.build_negotiate_message(config, opponent_group_id=opponent)


def test_declared_uid_is_derived_from_the_flat_terms(config_dir) -> None:
    """Derived INSIDE the builder from the terms it just signed - a caller
    cannot feed it the wrong object, which is exactly the bug this catches."""
    config = Config.load(config_dir)
    message = _message(config, "imreeyal")
    expected = game_ids.derive_game_uid(
        message["terms"], config.group_id, "imreeyal")
    assert message["game_uid"] == expected


def test_no_opponent_configured_declares_nothing(config_dir) -> None:
    """The uid needs BOTH group ids, and a symmetric handshake does not know
    the peer's until its message arrives. Absent an expected opponent we
    simply do not declare - which the both-declare rule tolerates."""
    assert "game_uid" not in _message(Config.load(config_dir))


def test_matching_uids_pass_and_a_mismatch_refuses(config_dir) -> None:
    config = Config.load(config_dir)
    mine = _message(config, "imreeyal")
    terms.verify_declarations(mine, dict(mine))  # same derivation both sides

    divergent = dict(mine, game_uid="deadbeef-0000-0000-0000-000000000000")
    with pytest.raises(GameRuleError, match="game_uid"):
        terms.verify_declarations(mine, divergent)


def test_omission_on_either_side_never_refuses(config_dir) -> None:
    """Interop: an unmodified reference peer declares nothing at all, and a
    peer that could not derive it (no expected opponent) declares nothing
    either. Neither may cost anyone a game."""
    config = Config.load(config_dir)
    declared = _message(config, "imreeyal")
    silent = _message(config)
    terms.verify_declarations(declared, silent)
    terms.verify_declarations(silent, declared)
