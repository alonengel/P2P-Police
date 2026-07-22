"""Wire-shape lock + negotiation seam (both-declare, like info_mode).

The signed terms are a frozen key set, so the wire-shape choice is declared
as the SHA-256 of a published lock doc (config/wire_shape_lock.json — the
interop registry's `reference-v3` entry, one shared {family, name, params,
example} envelope) under `wire_shape_sha256` in the negotiate extras — the
same pattern as scent_model_sha256. Refusal fires ONLY when both peers
declare and the hashes differ; omission is never refusal. The bookletter
runtime stays the untouched default: an undeclared game is byte-identical
to before this module existed.
"""

import json
from pathlib import Path

from p2p_police.domain.errors import GameRuleError
from p2p_police.domain.negotiation import config_sha256

BOOKLETTER = "bookletter"
REFERENCE = "reference"

_LOCK_DOC_PATH = Path(__file__).resolve().parents[3] / "config" / "wire_shape_lock.json"
_lock_doc_cache: dict | None = None


def wire_shape_lock_doc() -> dict:
    """The published reference-v3 lock document both peers hash."""
    global _lock_doc_cache
    if _lock_doc_cache is None:
        _lock_doc_cache = json.loads(_LOCK_DOC_PATH.read_text(encoding="utf-8"))
    return _lock_doc_cache


def wire_shape_sha256() -> str:
    """sha256(canonical_json(doc)) — the registry-comparable declaration."""
    return config_sha256(wire_shape_lock_doc())


def wire_shape(config) -> str:
    """[network] wire_shape: 'bookletter' (default) | 'reference'."""
    value = config.private.get("network", {}).get("wire_shape", BOOKLETTER)
    if value not in (BOOKLETTER, REFERENCE):
        raise GameRuleError(f"unknown wire_shape {value!r} in game.toml [network]")
    return value


def extend_agreement(agreement: dict, config) -> dict:
    """Declare the wire-shape hash ONLY when the reference path is armed —
    the default (bookletter) agreement stays byte-identical to before."""
    if wire_shape(config) == REFERENCE:
        agreement["wire_shape_sha256"] = wire_shape_sha256()
    return agreement


def verify_wire_shape(mine: dict, theirs: dict) -> None:
    """The registry refusal rule: refuse only when BOTH peers declare a wire
    shape and the hashes differ; silence on either side means play."""
    ours, others = mine.get("wire_shape_sha256"), theirs.get("wire_shape_sha256")
    if ours is not None and others is not None and ours != others:
        raise GameRuleError(
            f"wire-shape mismatch: mine={ours!r} theirs={others!r} "
            "— both declared, hashes differ (locked-model refusal rule)"
        )
