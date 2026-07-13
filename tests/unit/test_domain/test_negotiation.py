"""Negotiation tests encode rules 11-12: byte-identity via canonical sha,
fixed values immutable, minimums upward-only, commit order pinned."""

import pytest

from p2p_police.domain.errors import GameRuleError
from p2p_police.domain.negotiation import (
    build_agreement,
    config_sha256,
    validate_shared_terms,
    verify_agreement,
)


def test_sha_is_stable_across_key_order(shared_terms: dict) -> None:
    reordered = dict(reversed(list(shared_terms.items())))
    assert config_sha256(shared_terms) == config_sha256(reordered)


def test_any_value_change_changes_the_sha(shared_terms: dict) -> None:
    original = config_sha256(shared_terms)
    shared_terms["world"]["map_area"] = "London"
    assert config_sha256(shared_terms) != original


def test_valid_terms_pass_validation(shared_terms: dict) -> None:
    validate_shared_terms(shared_terms)


def test_changed_fixed_value_is_rejected(shared_terms: dict) -> None:
    shared_terms["scoring"]["capture_cop"] = 25
    with pytest.raises(GameRuleError, match="FIXED"):
        validate_shared_terms(shared_terms)


def test_changed_fixed_pheromone_is_rejected(shared_terms: dict) -> None:
    shared_terms["pheromones"]["pheromone_decay"] = 0.2
    with pytest.raises(GameRuleError, match="FIXED"):
        validate_shared_terms(shared_terms)


def test_lowered_minimum_is_rejected(shared_terms: dict) -> None:
    shared_terms["board_and_agents"]["grid_size"] = 5
    with pytest.raises(GameRuleError, match="MINIMUM"):
        validate_shared_terms(shared_terms)


def test_raised_minimum_is_accepted(shared_terms: dict) -> None:
    shared_terms["board_and_agents"]["grid_size"] = 10
    validate_shared_terms(shared_terms)


def test_missing_mandatory_key_is_rejected(shared_terms: dict) -> None:
    del shared_terms["scoring"]["tie_score"]
    with pytest.raises(GameRuleError, match="missing"):
        validate_shared_terms(shared_terms)


def test_agreement_carries_sha_order_and_schema(shared_terms: dict) -> None:
    agreement = build_agreement(shared_terms, "anrbj666")
    assert agreement["config_sha256"] == config_sha256(shared_terms)
    assert agreement["commit_order"] == "police_first"
    assert agreement["schema_version"] == "1.3"
    assert agreement["group_id"] == "anrbj666"


def test_matching_agreements_verify(shared_terms: dict) -> None:
    mine = build_agreement(shared_terms, "anrbj666")
    theirs = build_agreement(shared_terms, "rival-team")
    verify_agreement(mine, theirs)


def test_sha_mismatch_fails_verification(shared_terms: dict) -> None:
    mine = build_agreement(shared_terms, "anrbj666")
    shared_terms["world"]["map_area"] = "Paris"
    theirs = build_agreement(shared_terms, "rival-team")
    with pytest.raises(GameRuleError, match="config_sha256"):
        verify_agreement(mine, theirs)


def test_commit_order_mismatch_fails_verification(shared_terms: dict) -> None:
    mine = build_agreement(shared_terms, "anrbj666")
    theirs = dict(mine, commit_order="thief_first")
    with pytest.raises(GameRuleError, match="commit_order"):
        verify_agreement(mine, theirs)
