"""Reference-v3 flat-terms negotiate: derivation from the signed config and
byte-exact reproduction of the league kit's CORE terms_signature vector."""

import json
from pathlib import Path

import pytest

from p2p_police.domain.crypto import canonical
from p2p_police.domain.errors import GameRuleError
from p2p_police.shared.config import Config
from p2p_police.wire import terms as wire_terms

VECTOR = json.loads(
    (Path(__file__).parents[2] / "vectors" / "foreign" / "terms_signature.json")
    .read_text(encoding="utf-8"))["vectors"][0]


def test_flat_terms_derive_from_the_signed_config(config_dir, shared_terms):
    flat = wire_terms.terms_from_shared(Config.load(config_dir).shared)
    board = shared_terms["board_and_agents"]
    scent = shared_terms["pheromones"]
    assert set(flat) == set(VECTOR["terms"])  # the reference's exact 14-key set
    assert flat["board_size"] == board["grid_size"]
    assert flat["smell_grid_size"] == scent["pheromone_grid_size"]
    assert flat["decay_per_step"] == scent["pheromone_decay"]
    assert flat["emit_intensity"] == scent["pheromone_center_intensity"]
    assert flat["min_center_intensity"] == scent["min_center_intensity"]
    assert flat["max_steps"] == shared_terms["movement_and_barriers"]["survival_threshold"]
    assert flat["barriers_max"] == shared_terms["movement_and_barriers"]["max_barriers"]
    assert flat["setting"] == shared_terms["world"]["map_area"]
    assert flat["hint_max_words"] == shared_terms["world"]["hint_max_words"]
    assert flat["axis_origin_corner"] == board["axis_origin_corner"]
    assert flat["axis_start_index"] == board["axis_start_index"]
    assert flat["thief_start"] == board["thief_start"]
    assert flat["cop_start"] == board["cop_start"]
    assert flat["num_games"] == shared_terms["network_and_league"]["num_games"]


def test_flat_terms_track_config_edits_not_hardcoded_values(shared_terms):
    shared_terms["board_and_agents"]["grid_size"] = 9
    shared_terms["world"]["map_area"] = "Tel Aviv"
    shared_terms["network_and_league"]["num_games"] = 3
    flat = wire_terms.terms_from_shared(shared_terms)
    assert flat["board_size"] == 9
    assert flat["setting"] == "Tel Aviv"
    assert flat["num_games"] == 3


def test_kit_vector_reproduced_byte_exactly_from_a_matching_config(shared_terms):
    """A config holding the vector's values must reproduce its terms dict,
    canonical serialization AND signature byte-for-byte (CORE gate)."""
    shared_terms["world"]["map_area"] = "Haifa"  # the vector's synthetic setting
    flat = wire_terms.terms_from_shared(shared_terms)
    assert flat == VECTOR["terms"]
    assert canonical(flat) == canonical(VECTOR["terms"])
    assert wire_terms.sign_terms(flat, VECTOR["nonce"]) == VECTOR["signature"]


def test_signature_construction_matches_the_kit_vector():
    assert wire_terms.sign_terms(VECTOR["terms"], VECTOR["nonce"]) == VECTOR["signature"]


def test_divergent_step_caps_cannot_be_flattened(shared_terms):
    """The flat form carries ONE max_steps; a config where max_moves and
    survival_threshold diverge cannot be represented faithfully."""
    shared_terms["movement_and_barriers"]["max_moves"] = 40  # minimums may rise
    with pytest.raises(GameRuleError, match="max_steps"):
        wire_terms.terms_from_shared(shared_terms)


def test_message_shape_signature_and_declarations(config_dir):
    config = Config.load(config_dir)
    message = wire_terms.build_negotiate_message(config, {"ram_gb": 32})
    assert message["terms"] == wire_terms.terms_from_shared(config.shared)
    assert message["signature"] == wire_terms.sign_terms(message["terms"], message["nonce"])
    assert message["group_id"] == "anrbj666"
    assert message["identity"]["group_id"] == "anrbj666"
    assert message["info_mode"] == "belief"
    assert len(message["scent_model_sha256"]) == 64
    assert len(message["hardware_spec_sha256"]) == 64
    # config_sha256 substitution is a bookletter-v3 property - never here.
    assert "config_sha256" not in message
    assert set(message) == {"terms", "nonce", "signature", "group_id", "identity",
                            "scent_model_sha256", "info_mode", "hardware_spec_sha256"}


def test_agreed_mutual_shape_rides_both_unsigned_top_level_keys(config_dir):
    """The cross-team agreed wire shape: `sub_game_number` AND `role` ride
    as TOP-LEVEL unsigned keys beside identity/nonce/terms/signature —
    exact spelling, never inside the signed flat terms."""
    config = Config.load(config_dir)
    message = wire_terms.build_negotiate_message(config, sub_game=4, role="police")
    assert message["sub_game_number"] == 4
    assert message["role"] == "police"
    assert "sub_game_number" not in message["terms"] and "role" not in message["terms"]
    wire_terms.verify_terms_message(message["terms"], message)  # signature intact
    assert set(message) == {"terms", "nonce", "signature", "group_id", "identity",
                            "scent_model_sha256", "info_mode",
                            "sub_game_number", "role"}


def test_hardware_seal_only_rides_when_a_spec_is_given(config_dir):
    message = wire_terms.build_negotiate_message(Config.load(config_dir))
    assert "hardware_spec_sha256" not in message


def test_each_message_gets_a_fresh_nonce(config_dir):
    config = Config.load(config_dir)
    first = wire_terms.build_negotiate_message(config)
    second = wire_terms.build_negotiate_message(config)
    assert first["nonce"] != second["nonce"]
    assert first["signature"] != second["signature"]


def test_scent_declaration_suppressed_by_pairing_knob(config_dir):
    """`[game] declare_scent_model = false` — the pairwise arrangement for a
    rival locked to the OTHER registered scent model who cannot suppress its
    own declaration (najamjad, 2026-08-18): the registry's refusal rule fires
    only when BOTH sides declare, so omitting ours lets its lone declaration
    play while the default stays declare-and-refuse-on-mismatch."""
    config = Config.load(config_dir)
    config.private.setdefault("game", {})["declare_scent_model"] = False
    message = wire_terms.build_negotiate_message(config)
    assert "scent_model_sha256" not in message
    theirs = {"scent_model_sha256": "81" * 32}
    wire_terms.verify_declarations(message, theirs)  # lone declaration: plays
    declared = wire_terms.build_negotiate_message(Config.load(config_dir))
    assert len(declared["scent_model_sha256"]) == 64  # default unchanged
    with pytest.raises(GameRuleError, match="scent_model_sha256"):
        wire_terms.verify_declarations(declared, theirs)  # both declare: refuse
