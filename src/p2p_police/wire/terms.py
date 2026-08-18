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
from p2p_police.domain.game_ids import derive_game_uid
from p2p_police.domain.negotiation import config_sha256, validate_shared_terms
from p2p_police.domain.scent import scent_model_spec

# Families verified here by both-declare (wire_shape stays in wire/lock.py).
# sub_game_number rides here too: identical terms give identical game_uids
# across instances, so the index is the ONLY thing that stops a leftover
# rival instance from another window pairing into the wrong sub-game.
# game_uid rides here under the same rule (joint proposal with the pairing
# team): the uid never crosses the wire in the reference shape, so two peers
# deriving it from DIFFERENT inputs stay silently divergent for a whole series
# and nothing notices until the reports are diffed. Declaring it turns that
# into a refusal at handshake time.
BOTH_DECLARE_FIELDS = ("scent_model_sha256", "info_mode", "sub_game_number", "game_uid")


class PairingRefusalError(GameRuleError):
    """Wrong counterpart, not a violation: the agreement names another
    sub-game window or carries our own role. Refuse the AGREEMENT (a
    bystander) and keep waiting for the real counterpart — never a
    first-offense technical loss (wire/repush.py absorbs these)."""


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
                            info_mode: str = "belief",
                            sub_game: int | None = None,
                            role: str | None = None,
                            opponent_group_id: str | None = None) -> dict:
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
        "info_mode": info_mode,
    }
    # The registry refusal rule fires only when BOTH sides declare a family;
    # `[game] declare_scent_model = false` omits ours — the pairwise
    # arrangement for a rival locked to the OTHER registered model who cannot
    # suppress its own declaration (its lone value then plays; ours would
    # refuse it). Default: declare, and refuse on mismatch as always.
    if bool(config.private.get("game", {}).get("declare_scent_model", True)):
        message["scent_model_sha256"] = config_sha256(scent_model_spec())
    if hardware is not None:
        message["hardware_spec_sha256"] = config_sha256(hardware)
    if sub_game is not None:  # rides OUTSIDE the signed terms, like info_mode
        message["sub_game_number"] = int(sub_game)
    if role is not None:  # agreed mutual shape: unsigned TOP-LEVEL key too
        message["role"] = str(role)
    if opponent_group_id:
        # Derived HERE, from the flat terms just signed above - the caller
        # passes a group id, never a uid, so no call site can feed the
        # derivation the wrong object (which is precisely the divergence this
        # declaration exists to catch). Needs both group ids, so a peer with
        # no expected opponent configured simply declares nothing.
        message["game_uid"] = derive_game_uid(terms, config.group_id, str(opponent_group_id))
    return message


def _diff_lines(mine: dict, theirs: dict) -> list[str]:
    """Every differing key, each named with BOTH values (interop debugging:
    a rival must see exactly which term diverges, not just 'mismatch')."""
    missing = "<missing>"
    return [
        f"{key}: mine={mine.get(key, missing)!r} theirs={theirs.get(key, missing)!r}"
        for key in sorted(set(mine) | set(theirs))
        if key not in mine or key not in theirs or mine[key] != theirs[key]
    ]


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
    when both peers declare a family and the values differ (kit section 7).
    `role` inverts the comparison: peers must be COMPLEMENTARY, so refusal
    fires when both declare and the values are EQUAL; omission still plays.
    Wrong-window / same-role refusals classify as PairingRefusalError (a
    bystander, tolerable); locked-model mismatches stay plain-fatal."""
    for field in BOTH_DECLARE_FIELDS:
        ours, others = mine.get(field), theirs.get(field)
        if ours is not None and others is not None and ours != others:
            hint = (" - is a stale rival instance from a previous sub-game "
                    "window still running?" if field == "sub_game_number" else "")
            error = PairingRefusalError if field == "sub_game_number" else GameRuleError
            raise error(
                f"negotiate declaration mismatch on '{field}': "
                f"mine={ours!r} theirs={others!r}{hint}")
    my_role, their_role = mine.get("role"), theirs.get("role")
    if my_role is not None and their_role is not None and my_role == their_role:
        raise PairingRefusalError(
            f"negotiate role collision: both peers declare role={my_role!r} "
            "- peers must be complementary (police vs thief); is a same-role "
            "instance (or our own echo) pointed at us?")


def peer_group_id(message: dict) -> str:
    """The rival's id: ours rides top-level; the reference's sits in identity."""
    identity = message.get("identity") or {}
    return message.get("group_id") or identity.get("group_id") or "unknown"
