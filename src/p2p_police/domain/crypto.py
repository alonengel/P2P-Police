"""Commit-reveal cryptography (rulebook ch. 5) — parity-locked.

The sealed record is RICHER than the book's four core fields: it carries
step, role, sub_game, the action, the hint text and the intent verdict
(PRD-01/06 pinned field set). Canonical JSON (sorted keys, tight separators,
native UTF-8) and the pipe-appended nonce preimage follow the official
reference implementation byte-for-byte (ADR-0004) so foreign peers audit us
without adapters. Nonces come from `secrets` and stay private until the
end-of-game audit (rule 18).
"""

import hashlib
import json
import secrets

REQUIRED_RECORD_FIELDS = ("step", "role", "sub_game", "state_digest", "action", "hint", "verdict")


def canonical(payload: dict) -> str:
    """The single serialization both repos and the replay viewer must share."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def new_nonce() -> str:
    """Fresh cryptographic nonce — blocks dictionary attacks over the tiny
    move space (ch. 5 box); never reuse, never reveal before audit."""
    return secrets.token_hex(16)


def build_step_payload(
    step: int, role: str, sub_game: int, state_digest: str, action: dict, hint: str, verdict: bool
) -> dict:
    """The full sealed record for one half-turn (the pinned field set)."""
    return {
        "step": step,
        "role": role,
        "sub_game": sub_game,
        "state_digest": state_digest,
        "action": action,
        "hint": hint,
        "verdict": verdict,
    }


def commit_hash(payload: dict, nonce: str) -> str:
    """H_commit = SHA-256 over canonical(payload) + "|" + nonce (reference form).

    The pinned field set binds MOVE payloads only: a `type`-keyed payload is
    a system record (the book-attached log's sealed step-zero declaration)
    whose schema is its own — same hash construction, no field demands."""
    if "type" not in payload:
        missing = [f for f in REQUIRED_RECORD_FIELDS if f not in payload]
        if missing:
            raise ValueError(f"sealed payload missing fields: {missing}")
    material = f"{canonical(payload)}|{nonce}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def verify_commit(payload: dict, nonce: str, expected_hash: str) -> bool:
    """Constant-time comparison; ANY mismatch is proven tampering (rule 19)."""
    return secrets.compare_digest(commit_hash(payload, nonce), expected_hash)


def audit_records(their_records: list[dict], revealed_nonces: list[str]) -> str:
    """End-of-game audit: recompute every commitment with the revealed nonces.

    Input: records [{payload, commit}] in step order + the rival's nonces.
    Output: 'Verified OK' or 'TAMPERED' — binary, no almost-matches (ch. 7).
    """
    if len(their_records) != len(revealed_nonces):
        return "TAMPERED"
    for record, nonce in zip(their_records, revealed_nonces, strict=True):
        try:
            if not verify_commit(record["payload"], nonce, record["commit"]):
                return "TAMPERED"
        except (ValueError, KeyError, TypeError):
            return "TAMPERED"  # malformed audit material IS a failed audit
    return "Verified OK"
