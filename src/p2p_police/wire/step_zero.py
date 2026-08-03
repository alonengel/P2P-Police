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
