"""Judging a FOREIGN-schema rival's revealed half fairly (league SPEC).

The shared interop contract is exactly two things: the canonical JSON and
the commit construction SHA256(canonical(payload) + "|" + nonce). The
PAYLOAD schema and the end-digest construction are PER-TEAM choices, NOT
interop constraints — so the audit must never call an honest rival a cheat
for sealing different keys than ours.

Live finding (2026-07-24, first full cross-team games): a reference-shaped
rival played 35 clean turns and our audit still rendered TAMPERED, because
(1) its reveal set carries a step-0 system-spec record whose commit never
crossed the live turn wire, so a strict zip+length check can never align;
(2) our commit recompute refused payloads missing OUR pinned field set; and
(3) the physics reconstruction assumed our role/action keys. The tiers here
fix all three: the commit check is schema-agnostic, alignment is BY COMMIT,
and a commit-clean but unparseable half is judged only on what is derivable
(per-sender step continuity, revealed-position movement legality) — never
labeled TAMPERED for its schema. Digest comparison across two different
per-team constructions is meaningless: it reports not-comparable (None).
"""

import hashlib

from p2p_police.domain.crypto import REQUIRED_RECORD_FIELDS, canonical
from p2p_police.domain.primitives import Role

VERIFIED, TAMPERED = "Verified OK", "TAMPERED"
NOT_COMPARABLE = None  # digest_match when the two constructions differ


def commit_clean(record: dict) -> bool:
    """The SHARED contract only: does SHA256(canonical(payload)+'|'+nonce)
    recompute to the commit — for ANY payload schema (no field demands)."""
    try:
        material = f"{canonical(record['payload'])}|{record['nonce']}"
        return hashlib.sha256(material.encode("utf-8")).hexdigest() == record["commit"]
    except (KeyError, TypeError, ValueError):
        return False


def verify_reveals(live_records: list, revealed: list) -> str:
    """Tamper criterion (tier a): every revealed record commit-clean AND
    every commit RECEIVED LIVE re-proven by one of them. Alignment is BY
    COMMIT, never by list position: a reference rival's reveal set also
    carries its step-0 spec record, which anchors no live step and so can
    rewrite nothing — tolerated. Matched payloads+nonces merge into the
    live records for the later tiers."""
    if not all(commit_clean(record) for record in revealed):
        return TAMPERED
    by_commit = {record["commit"]: record for record in revealed}
    for live in live_records:
        full = by_commit.get(live.get("commit"))
        if full is None:
            return TAMPERED  # a live step the reveal cannot re-prove
        live.update(payload=full["payload"], nonce=full["nonce"])
    return VERIFIED


def parses_as_ours(records: list) -> bool:
    """True only when every payload-carrying record fits OUR schema — the
    gate before the strict full physics reconstruction may judge a rival."""
    payloads = [record.get("payload") for record in records]
    roles = {role.value for role in Role}
    return bool(payloads) and all(
        isinstance(payload, dict)
        and all(field in payload for field in REQUIRED_RECORD_FIELDS)
        and payload.get("role") in roles
        and isinstance(payload.get("action"), dict)
        for payload in payloads
    )


def _step_of(record: dict):
    step = record.get("payload", {}).get("step") if isinstance(record, dict) else None
    return step if isinstance(step, int) and not isinstance(step, bool) else None


def continuity_ok(records: list) -> bool:
    """Per-sender step continuity: the readable playing steps must count
    1..N with no gap or duplicate (a step-0 declaration record may ride
    along); records exposing no integer step derive nothing — not a crime."""
    steps = [step for step in map(_step_of, records) if step is not None]
    playing = sorted(step for step in steps if step >= 1)
    return playing == list(range(1, len(playing) + 1))


def movement_ok(records: list, grid: int) -> bool:
    """Whatever movement legality IS derivable from the reveals: a payload
    exposing a [row, col] integer position must stay on the agreed board
    and reach the next revealed position by one N/S/E/W/STAY step."""
    track = []
    for record in sorted((r for r in records if _step_of(r) is not None), key=_step_of):
        position = record["payload"].get("position")
        if isinstance(position, list) and len(position) == 2 \
                and all(isinstance(part, int) and not isinstance(part, bool)
                        for part in position):
            if not all(0 <= part < grid for part in position):
                return False
            track.append((_step_of(record), tuple(position)))
    for (step_a, cell_a), (step_b, cell_b) in zip(track, track[1:], strict=False):
        if step_b == step_a + 1 and \
                abs(cell_b[0] - cell_a[0]) + abs(cell_b[1] - cell_a[1]) > 1:
            return False
    return True


def unconceded_capture(their_records: list, barriers: list, grid: int) -> dict | None:
    """Rule 46/47 adjudicated from a FOREIGN rival's own revealed positions.

    A barrier capture is only ever SELF-declared: under hidden information the
    cop cannot see that its wall sealed the thief, so a peer that never runs
    its own imprisonment check simply plays on and claims survival (measured
    live 2026-08-01). The reveal settles it after the fact — their positions
    are in their own records — so the evidence exists even though the live
    game could not use it. Returns the first breach as an evidence dict, or
    None. Reported, never a unilateral rewrite: the logs decide (rule 35).
    """
    walls = {(cell[0], cell[1]) for cell in barriers}
    for record in sorted((r for r in their_records if _step_of(r) is not None),
                         key=_step_of):
        cell = record.get("payload", {}).get("position")
        if not (isinstance(cell, list) and len(cell) == 2):
            continue
        spot = (cell[0], cell[1])
        neighbors = [(spot[0] + dr, spot[1] + dc)
                     for dr, dc in ((-1, 0), (1, 0), (0, 1), (0, -1))]
        sealed = all(not (0 <= r < grid and 0 <= c < grid) or (r, c) in walls
                     for r, c in neighbors)
        if spot in walls or sealed:
            return {"step": _step_of(record), "cell": list(spot),
                    "rule": "46 (barrier on the thief)" if spot in walls
                            else "47 (fully surrounded)",
                    "barriers": sorted(list(w) for w in walls)}
    return None


def judge(their_records: list, grid: int, barriers=None) -> dict:
    """Tier-b verdict over a commit-clean FOREIGN-schema half. 'Verified OK'
    means: commits clean + no derivable-rule violation. The digest tier is
    only defined when both sides share one construction — here it is not,
    so digest_match reports not-comparable (null), never false.
    `disputed_capture` carries rule-46/47 evidence when their own reveal
    proves a capture their peer never conceded (evidence, not a verdict)."""
    ok = continuity_ok(their_records) and movement_ok(their_records, grid)
    return {
        "audit": VERIFIED if ok else TAMPERED,
        "digest_match": NOT_COMPARABLE,
        "disputed_capture": unconceded_capture(their_records, barriers or [], grid),
    }


def foreign_verdict(their_records: list, grid: int, barriers) -> tuple:
    """The tier-b triple the hidden runtime consumes: (audit, digest_match,
    disputed_capture)."""
    tier = judge(their_records, grid, barriers)
    return tier["audit"], tier["digest_match"], tier["disputed_capture"]
