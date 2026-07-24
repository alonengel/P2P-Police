"""Reference-v3 negotiate verification: the value-equality refusal matrix
(every differing term named with both values), the signature gate, and the
registry both-declare rule over the alongside declarations."""

import json
from pathlib import Path

import pytest

from p2p_police.domain.errors import GameRuleError
from p2p_police.shared.config import Config
from p2p_police.wire import terms as wire_terms

FLAT_KEYS = sorted(json.loads(
    (Path(__file__).parents[2] / "vectors" / "foreign" / "terms_signature.json")
    .read_text(encoding="utf-8"))["vectors"][0]["terms"])


def _tweak(value):
    """A same-type value guaranteed to differ."""
    if isinstance(value, list):
        return [9, 9]
    if isinstance(value, str):
        return value + "-else"
    return value + 1


def _pair(config_dir) -> tuple[dict, dict]:
    config = Config.load(config_dir)
    return (wire_terms.build_negotiate_message(config),
            wire_terms.build_negotiate_message(config))


def test_value_equal_terms_and_valid_signature_verify(config_dir):
    mine, theirs = _pair(config_dir)
    wire_terms.verify_terms_message(mine["terms"], theirs)  # must not raise


@pytest.mark.parametrize("key", FLAT_KEYS)
def test_one_term_off_refuses_naming_the_key_and_both_values(config_dir, key):
    """Their signature stays VALID over their altered terms, so the refusal
    can only come from the key-by-key value-equality gate."""
    mine, theirs = _pair(config_dir)
    altered = dict(theirs["terms"], **{key: _tweak(theirs["terms"][key])})
    theirs.update(terms=altered, signature=wire_terms.sign_terms(altered, theirs["nonce"]))
    with pytest.raises(GameRuleError) as caught:
        wire_terms.verify_terms_message(mine["terms"], theirs)
    text = str(caught.value)
    assert key in text
    assert repr(mine["terms"][key]) in text and repr(altered[key]) in text


def test_missing_and_unexpected_term_keys_are_both_named(config_dir):
    mine, theirs = _pair(config_dir)
    altered = dict(theirs["terms"], bonus_round=True)
    del altered["setting"]
    theirs.update(terms=altered, signature=wire_terms.sign_terms(altered, theirs["nonce"]))
    with pytest.raises(GameRuleError) as caught:
        wire_terms.verify_terms_message(mine["terms"], theirs)
    text = str(caught.value)
    assert "setting" in text and "missing" in text and "bonus_round" in text


def test_signature_mismatch_refuses_showing_both_hashes(config_dir):
    mine, theirs = _pair(config_dir)
    theirs["signature"] = "f" * 64
    with pytest.raises(GameRuleError) as caught:
        wire_terms.verify_terms_message(mine["terms"], theirs)
    text = str(caught.value)
    assert "f" * 64 in text and wire_terms.sign_terms(theirs["terms"], theirs["nonce"]) in text


@pytest.mark.parametrize("breakage", [
    {"terms": None}, {"terms": "not-a-dict"}, {"nonce": None}, {"nonce": ""},
    {"signature": None},
])
def test_garbled_message_fields_refuse(config_dir, breakage):
    mine, theirs = _pair(config_dir)
    theirs.update(breakage)
    with pytest.raises(GameRuleError):
        wire_terms.verify_terms_message(mine["terms"], theirs)


def test_reference_minimal_message_verifies_without_declarations(config_dir):
    """The unmodified reference peer sends ONLY terms+nonce+signature+identity;
    omitted declarations are never a refusal (registry rule)."""
    mine, theirs = _pair(config_dir)
    minimal = {"terms": theirs["terms"], "nonce": theirs["nonce"],
               "signature": theirs["signature"], "identity": {"group_id": "rival-77"}}
    wire_terms.verify_terms_message(mine["terms"], minimal)
    wire_terms.verify_declarations(mine, minimal)  # must not raise


@pytest.mark.parametrize(("field", "ours", "others", "plays"), [
    ("scent_model_sha256", "a" * 64, "a" * 64, True),
    ("scent_model_sha256", "a" * 64, "b" * 64, False),
    ("scent_model_sha256", "a" * 64, None, True),
    ("scent_model_sha256", None, "b" * 64, True),
    ("info_mode", "belief", "belief", True),
    ("info_mode", "belief", "exact", False),
    ("info_mode", "belief", None, True),
    ("info_mode", None, "exact", True),
    ("sub_game_number", 2, 2, True),
    ("sub_game_number", 2, 5, False),
    ("sub_game_number", 2, None, True),   # reference peers never send it
    ("sub_game_number", None, 5, True),
])
def test_both_declare_truth_table_for_alongside_declarations(field, ours, others, plays):
    mine = {field: ours} if ours is not None else {}
    theirs = {field: others} if others is not None else {}
    if plays:
        wire_terms.verify_declarations(mine, theirs)
    else:
        with pytest.raises(GameRuleError) as caught:
            wire_terms.verify_declarations(mine, theirs)
        assert field in str(caught.value)
        assert repr(ours) in str(caught.value) and repr(others) in str(caught.value)


def test_negotiate_message_declares_sub_game_outside_the_signed_terms(config_dir):
    """The sub-game index rides alongside like info_mode: it must appear in
    the message, never inside the signed flat terms, and stay optional."""
    config = Config.load(config_dir)
    message = wire_terms.build_negotiate_message(config, sub_game=3)
    assert message["sub_game_number"] == 3
    assert "sub_game_number" not in message["terms"]
    wire_terms.verify_terms_message(message["terms"], message)  # signature intact
    assert "sub_game_number" not in wire_terms.build_negotiate_message(config)


def test_sub_game_mismatch_names_the_stale_instance_hazard():
    """Identical terms give identical game_uids across instances - the index
    is the only disambiguator, so the refusal must say what to look for."""
    with pytest.raises(GameRuleError) as caught:
        wire_terms.verify_declarations({"sub_game_number": 2}, {"sub_game_number": 5})
    text = str(caught.value)
    assert "sub_game_number" in text and "2" in text and "5" in text
    assert "stale" in text


def test_peer_group_id_reads_top_level_then_identity_then_unknown():
    assert wire_terms.peer_group_id({"group_id": "abc", "identity": {"group_id": "x"}}) == "abc"
    assert wire_terms.peer_group_id({"identity": {"group_id": "ref-team1"}}) == "ref-team1"
    assert wire_terms.peer_group_id({"identity": None}) == "unknown"
    assert wire_terms.peer_group_id({}) == "unknown"
