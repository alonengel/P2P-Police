"""Reference-v3 flat-terms negotiate handshake (league kit CORE vector).

The registered reference-v3 wire shape uses the REFERENCE's literal
negotiate form: a flat 14-key `terms` dict + `nonce` + `signature =
SHA256(canonical(terms) + "|" + nonce)` — pinned byte-for-byte by the kit's
terms_signature vector. The bookletter agreement's config_sha256
substitution is a bookletter-v3 property and must NOT appear here. Terms
are DERIVED from the signed game.json (never duplicated); the locked-model
declarations (scent_model_sha256, wire_shape_sha256 via wire/lock.py,
info_mode) ride alongside OUTSIDE the signature under the registry's
refusal rule: refuse only when BOTH peers declare a family and the values
differ — omission is never refusal (the unmodified reference peer declares
nothing at all).
"""

import hashlib

from p2p_police.domain.crypto import canonical, new_nonce
from p2p_police.domain.errors import GameRuleError
from p2p_police.domain.negotiation import config_sha256, validate_shared_terms
from p2p_police.domain.scent import scent_model_spec

# Families verified here by both-declare (wire_shape stays in wire/lock.py).
BOTH_DECLARE_FIELDS = ("scent_model_sha256", "info_mode")


def terms_from_shared(shared: dict) -> dict:
    """Derive the reference's flat 14-key terms from the signed game.json.

    Mirrors the reference's terms_from_config extraction key-for-key —
    notably max_steps maps from survival_threshold (the reference overlays
    movement_and_barriers.survival_threshold onto its rules.max_steps).
    The flat form has ONE step field, so a config where max_moves diverges
    from survival_threshold cannot be represented faithfully: refuse.
    """
    validate_shared_terms(shared)
    board, world = shared["board_and_agents"], shared["world"]
    moves, scent = shared["movement_and_barriers"], shared["pheromones"]
    if moves["max_moves"] != moves["survival_threshold"]:
        raise GameRuleError(
            "flat terms carry a single max_steps: max_moves "
            f"{moves['max_moves']} != survival_threshold {moves['survival_threshold']}")
    return {
        "board_size": board["grid_size"],
        "smell_grid_size": scent["pheromone_grid_size"],
        "decay_per_step": scent["pheromone_decay"],
        "emit_intensity": scent["pheromone_center_intensity"],
        "min_center_intensity": scent["min_center_intensity"],
        "max_steps": moves["survival_threshold"],
        "barriers_max": moves["max_barriers"],
        "setting": world["map_area"],
        "hint_max_words": world["hint_max_words"],
        "axis_origin_corner": board["axis_origin_corner"],
        "axis_start_index": board["axis_start_index"],
        "thief_start": list(board["thief_start"]),
        "cop_start": list(board["cop_start"]),
        "num_games": shared["network_and_league"]["num_games"],
    }


def sign_terms(terms: dict, nonce: str) -> str:
    """signature = SHA256(canonical(terms) + "|" + nonce) — the kit vector's
    exact construction (same preimage form as a step commit)."""
    return hashlib.sha256(f"{canonical(terms)}|{nonce}".encode()).hexdigest()


def build_negotiate_message(config, hardware: dict | None = None,
                            info_mode: str = "belief") -> dict:
    """The reference-shaped negotiate payload with our declarations alongside.

    A reference peer verifies exactly {terms, nonce, signature} and reads
    identity; every other key is an extra it ignores. The identity block,
    the sealed hardware hash and the locked-model declarations keep rules
    24/37-38/49 riding on this wire shape too.
    """
    terms = terms_from_shared(config.shared)
    nonce = new_nonce()
    message = {
        "terms": terms,
        "nonce": nonce,
        "signature": sign_terms(terms, nonce),
        "group_id": config.group_id,
        "identity": {**config.identity_block(), "group_id": config.group_id},
        "scent_model_sha256": config_sha256(scent_model_spec()),
        "info_mode": info_mode,
    }
    if hardware is not None:
        message["hardware_spec_sha256"] = config_sha256(hardware)
    return message


def _diff_lines(mine: dict, theirs: dict) -> list[str]:
    """Every differing key, each named with BOTH values (interop debugging:
    a rival must see exactly which term diverges, not just 'mismatch')."""
    lines = []
    for key in sorted(set(mine) | set(theirs)):
        if key not in theirs:
            lines.append(f"{key}: mine={mine[key]!r} theirs=<missing>")
        elif key not in mine:
            lines.append(f"{key}: mine=<missing> theirs={theirs[key]!r}")
        elif mine[key] != theirs[key]:
            lines.append(f"{key}: mine={mine[key]!r} theirs={theirs[key]!r}")
    return lines


def verify_terms_message(mine_terms: dict, message: dict) -> None:
    """The pre-game gate: their terms must VALUE-EQUAL ours key-by-key and
    their signature must recompute over the terms+nonce they sent."""
    theirs = message.get("terms")
    if not isinstance(theirs, dict):
        raise GameRuleError(f"negotiate message carries no terms dict: {theirs!r}")
    diffs = _diff_lines(mine_terms, theirs)
    if diffs:
        raise GameRuleError("agreement terms mismatch: " + "; ".join(diffs))
    nonce, signature = message.get("nonce"), message.get("signature")
    if not isinstance(nonce, str) or not nonce or not isinstance(signature, str):
        raise GameRuleError(
            f"negotiate message missing nonce/signature: "
            f"nonce={nonce!r} signature={signature!r}")
    expected = sign_terms(theirs, nonce)
    if signature != expected:
        raise GameRuleError(
            f"terms signature mismatch: theirs={signature!r} != "
            f"SHA256(canonical(terms)|nonce)={expected!r}")


def verify_declarations(mine: dict, theirs: dict) -> None:
    """Registry refusal rule over the alongside declarations: refuse ONLY
    when both peers declare a family and the values differ (kit section 7)."""
    for field in BOTH_DECLARE_FIELDS:
        ours, others = mine.get(field), theirs.get(field)
        if ours is not None and others is not None and ours != others:
            raise GameRuleError(
                f"negotiate declaration mismatch on '{field}': "
                f"mine={ours!r} theirs={others!r}")


def peer_group_id(message: dict) -> str:
    """The rival's id: ours rides top-level; the reference's sits in identity."""
    identity = message.get("identity") or {}
    return message.get("group_id") or identity.get("group_id") or "unknown"
