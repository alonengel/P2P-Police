"""Live public declarations vs the sealed reveals (rules 15-16, 21-22) —
split from wire/audit.py for the 150-code-line cap.

What a peer DECLARED live beside its commit (barrier cell, hint, capture
claim) must match what its reveal proves it sealed; a mismatch is tampering
evidence. Records carrying no declared block (commit-only halves, geometric
records, pre-upgrade logs) derive nothing and are never refused.
"""

from p2p_police.domain.errors import GameRuleError


def sealed_barrier(payload: dict) -> list | None:
    action = payload.get("action")
    if not (isinstance(action, dict) and action.get("type") == "barrier"):
        return None
    return [action["cell"][0], action["cell"][1]]


def verify_declared(record: dict) -> dict:
    """Returns the declared block ({} when the record carries none)."""
    payload, declared = record.get("payload"), record.get("declared")
    if not isinstance(payload, dict) or not isinstance(declared, dict):
        return {}
    placed = declared.get("barrier_placed")
    if (list(placed) if placed is not None else None) != sealed_barrier(payload):
        raise GameRuleError(
            f"step {payload.get('step')}: live barrier declaration {placed} "
            "does not match the sealed action - tampering evidence")
    hint = declared.get("hint")
    if hint is not None and hint != payload.get("hint"):
        raise GameRuleError(
            f"step {payload.get('step')}: live hint differs from the sealed "
            "hint - tampering evidence")
    return declared
