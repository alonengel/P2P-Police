"""The sealed step-zero declaration record (book-attached example shape).

The book's attached 3-game-log opens each sub-game's records with a signed
step-zero carrying what changes per sub-game — most importantly the exact
github_commit the declaring side runs (p. 40 חובה box, rule 53). Sealed like
a move (nonce + commit) but it never crosses the live wire: the audit reveal
and the log carry it. The rival holds a SECOND copy of the same fact from our
negotiate identity — two channels that must agree, by construction (pairing
convention with imreeyal, 2026-08-03). HIDDEN WIRE ONLY: the bookletter
runtime stays byte-compatible with unmodified reference peers.
"""

from p2p_police.domain import game_ids


def seal_step_zero(rt) -> None:
    """Append our step-zero record to the exchange right after negotiate
    (the declaration_ref needs the pairing's game_id, known only then)."""
    from p2p_police.report.code_identity import git_commit_hash

    game_id = game_ids.build_game_id(rt.config.group_id, rt.opponent_group_id)
    rt.exchange.seal_record({
        "step": 0,
        "type": "step_zero",
        "declaration_ref": game_ids.declaration_name(game_id),
        "group_id": rt.config.group_id,
        "role": rt.role.value,
        "sub_game_number": rt.exchange.sub_game,
        "github_commit": git_commit_hash(),
    })


def read_theirs(revealed: list, negotiate_identity: dict) -> tuple[dict | None, str | None]:
    """The rival's revealed step-zero payload (None when it sent none) plus
    the two-channel verdict: a sealed github_commit that differs from what
    the SAME window's negotiate identity declared is a FINDING recorded on
    the report (rule-36 evidence) — never an outcome rewrite."""
    payload = next((r.get("payload") for r in revealed
                    if isinstance(r.get("payload"), dict)
                    and r["payload"].get("type") == "step_zero"), None)
    if payload is None:
        return None, None
    declared = (negotiate_identity or {}).get("github_commit")
    if declared and payload.get("github_commit") != declared:
        return payload, (f"sealed step-zero commit {payload.get('github_commit')!r}"
                         f" differs from the negotiate-declared {declared!r}")
    return payload, None


def read_for(rt, audit_message: dict) -> None:
    """Extract + cross-check the rival's step-zero from its audit message,
    storing the report evidence on the runtime (hidden_turns' line budget)."""
    zero, finding = read_theirs(
        audit_message.get("records", []),
        (getattr(rt, "opponent_info", {}) or {}).get("identity", {}))
    rt.step_zero_evidence = {"opponent_step_zero": zero,
                             "step_zero_mismatch": finding}


def evidence(rt) -> dict:
    """The two report keys — None-safe when no audit ever arrived."""
    return getattr(rt, "step_zero_evidence",
                   {"opponent_step_zero": None, "step_zero_mismatch": None})
