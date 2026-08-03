"""The series RESULT document, key-structured like the official demo's
sample-run result (course DemoExamples, learn-only reference; key layout
reproduced with attribution - the values are all ours). It carries what the
book mandates for the final result (ch. 9, rules 49/54): all four GitHub
repo links, both sides' FastMCP addresses, the mutual-agreement
confirmations, timestamps and total tokens. Team IDENTITY (members, hardware,
llm_model) is NOT here: the book's attached example homes it in the
declaration file, and this document carries the flat id pair only.
"""

from p2p_police.domain import game_ids
from p2p_police.report.artifacts import symmetric_outcome_signature

_SCHEMA = ("Summary and final result for the WHOLE series between two teams: "
           "per-sub-game scores + aggregate; identity lives in the declaration.")
# The sample's fixed label, not a tunable: our timestamps stay UTC ISO-8601
# with explicit offsets, so this tags the league's wall-clock zone only.
TIMEZONE = "Asia/Jerusalem"
SCHEMA_VERSION = "1.1"


def _names(summary: dict) -> tuple[str, str, str, str]:
    """(me, them, my_role, their_role); self-play series disambiguate the
    twin repos by role suffix (both carry the same group_id)."""
    me = summary.get("group_id", "us")
    them = summary.get("opponent_group_id", "them")
    role = summary.get("role", "police")
    other = "thief" if role == "police" else "police"
    if me == them:
        me, them = f"{me}({role})", f"{them}({other})"
    return me, them, role, other


def _entry(parsed: dict, score_table, our_identity: dict) -> dict:
    """One reference-keyed sub_games[] entry from one settled log."""
    summary = parsed["summary"]
    me, them, role, other = _names(summary)
    cop_points, thief_points = score_table.points_for_name(summary["outcome"])
    score = {me: cop_points if role == "police" else thief_points,
             them: cop_points if other == "police" else thief_points}
    winner = None if score[me] == score[them] else max(score, key=score.get)
    identity = (summary.get("opponent_info") or {}).get("identity") or {}
    return {
        "sub_game_number": parsed["sub"],
        "roles": {me: role, them: other},
        "started_at": summary.get("started_at"),
        "ended_at": summary.get("ended_at"),
        "result": summary["outcome"],
        "winner_group": winner,
        "tie": winner is None,
        # role-aware (book-attached example: commits VARY per sub-game): our
        # column is the hash the EMITTING repo stamped into its own log
        # summary; theirs prefers the SEALED copy (their revealed step-zero)
        # over that window's negotiate-declared identity
        "github_commit": {me: summary.get("github_commit")
                          or our_identity.get("github_commit", "unknown"),
                          them: (summary.get("opponent_step_zero") or {})
                          .get("github_commit")
                          or identity.get("github_commit", "unknown")},
        "tokens": {me: int(summary.get("tokens_total") or 0),
                   them: int(identity.get("tokens_total") or 0)},
        "score": score,
        "log_files": {me: parsed["file"], them: parsed["file"]},
        "audit": {"log_verified": summary.get("audit") == "Verified OK",
                  "tampered": summary.get("audit") == "TAMPERED"},
    }


def _groups(by_slot: dict) -> tuple[list[str], str]:
    """The RESULT file's groups field: the flat id pair, sample-verbatim.

    The book's attached example (docs/sample-run/result_*.json) homes team
    identity in the DECLARATION — `groups` here is a list of two ids and
    nothing else. Our earlier enrichment was additive rather than wrong, but
    it made two honest reports diff on shape, and the schema already has a
    file for identity (2026-08-01 report-diff with imreeyal)."""
    me, them, _, _ = _names(by_slot[min(by_slot)]["summary"])
    return [me, them], them


def _repo_map(by_slot: dict, our_identity: dict) -> dict:
    """Both teams' repo URLs: ours from config, theirs from the identity they
    declared at the handshake (rule 49 — all four links in the emailed file)."""
    me, them, _, _ = _names(by_slot[min(by_slot)]["summary"])
    theirs = ((by_slot[min(by_slot)]["summary"].get("opponent_info") or {})
              .get("identity") or {})
    return {me: dict(our_identity.get("repos", {})),
            them: dict(theirs.get("repos", {}))}


def _links(game_id: str, github: dict) -> dict:
    """The reference's logical-role filenames + all four GitHub repo URLs
    (both teams' cop and thief repos, book ch. 9)."""
    return {
        "declaration": game_ids.declaration_name(game_id),
        "config": f"config_{game_id}_g<NN>.json",
        "log": f"log_{game_id}_g<NN>.json",
        "result": game_ids.result_name(game_id),
        "github": github,
    }


def build_series_result(game_id: str, game_uid: str, by_slot: dict,
                        score_table, expected_games: int,
                        our_identity: dict, first_meeting: bool = True,
                        counted: bool = False) -> dict:
    """Assemble the full reference-conformant result document. The
    mutual_agreement sha256 is sign-then-insert over the rest of the doc
    (ADR-0004 settlement form); confirmed = every sub-game audit clean."""
    groups, them = _groups(by_slot)
    sub_games = [_entry(by_slot[n], score_table, our_identity)
                 for n in sorted(by_slot)]
    totals: dict[str, int] = {}
    won: dict[str, int] = {}
    tokens: dict[str, int] = {}
    ties = 0
    for entry in sub_games:
        for group, points in entry["score"].items():
            totals[group] = totals.get(group, 0) + points
            won.setdefault(group, 0)
            tokens[group] = tokens.get(group, 0) + entry["tokens"][group]
        if entry["winner_group"] is None:
            ties += 1
        else:
            won[entry["winner_group"]] += 1
    names = sorted(totals)
    series_tie = len(names) == 2 and totals[names[0]] == totals[names[1]]
    if series_tie:
        tie_points = score_table.series_tie_points()[0]
        totals = {group: totals[group] + tie_points for group in names}
        winner = None
    else:
        winner = max(totals, key=lambda group: totals[group])
    me = next(g for g in groups if g != them)

    # Rules 37-38 declarations, INCLUDING this game: ours from our config's
    # declared count, theirs the largest count any window's handshake declared
    def _declared(n: int) -> int:
        info = by_slot[n]["summary"].get("opponent_info") or {}
        return int((info.get("identity") or {}).get("counted_games_played", 0))

    theirs_declared = max((_declared(n) for n in by_slot), default=0)
    bump = 1 if counted else 0
    aggregate = {"total_score": totals, "sub_games_won": won, "ties": ties,
                 "winner_group": winner, "series_tie": series_tie}
    doc = {
        "_schema": _SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "report_type": "final_game_result",
        "game_id": game_id,
        "game_uid": game_uid,
        "links": _links(game_id, _repo_map(by_slot, our_identity)),
        "timezone": TIMEZONE,
        "groups": groups,
        "num_sub_games": expected_games,
        "sub_games": sub_games,
        "final_result": {
            **aggregate,
            "tokens_total_series": tokens,
            # league standings inputs (book-attached 4-final-result), keyed
            # on the COUNTED arming: a friendly must not fabricate a counted
            # record — no count bump, no reward (imreeyal pair diff
            # 2026-08-03: both teams converged on this bug class)
            "games_played_including_this": {
                me: int(our_identity.get("counted_games_played", 0)) + bump,
                them: theirs_declared + bump},
            "first_meeting_between_groups": first_meeting,
            "diversity_reward_applied": {
                g: bool(counted and first_meeting and winner == g) for g in names},
        },
    }
    doc["mutual_agreement"] = {  # the REFERENCE symmetric-outcome scope:
        # byte-identical on BOTH peers by construction — the only form a
        # grader can machine-check as agreement (rule 35; ADR-0012 third
        # addendum, adopted jointly with imreeyal)
        "sha256": symmetric_outcome_signature(game_id, sub_games, aggregate),
        "confirmed": all(e["audit"]["log_verified"] for e in sub_games),
    }
    return doc
