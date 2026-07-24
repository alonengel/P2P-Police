"""The series RESULT document, key-structured like the official demo's
sample-run result (course DemoExamples, learn-only reference; key layout
reproduced with attribution - the values are all ours). It carries what the
book mandates for the final result (ch. 9, rules 49/54): both teams'
identities, all four GitHub repo links, both sides' FastMCP addresses, the
mutual-agreement confirmations, timestamps and total tokens. Timestamps in
our artifacts are UTC ISO-8601, hence the fixed "UTC" timezone tag.
"""

from p2p_police.domain import game_ids
from p2p_police.report.artifacts import consensus_signature

_SCHEMA = ("Summary and final result for the WHOLE series between two "
           "teams: per-group score for every sub-game plus the aggregate "
           "outcome. Static team metadata is carried in groups[] and in "
           "the linked declaration.")
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
        "github_commit": {me: our_identity.get("github_commit", "unknown"),
                          them: identity.get("github_commit", "unknown")},
        "tokens": {me: int(summary.get("tokens_total") or 0),
                   them: int(identity.get("tokens_total") or 0)},
        "score": score,
        "log_files": {me: parsed["file"], them: parsed["file"]},
        "audit": {"log_verified": summary.get("audit") == "Verified OK",
                  "tampered": summary.get("audit") == "TAMPERED"},
    }


def _groups(by_slot: dict, our_identity: dict) -> tuple[list[dict], str]:
    """BOTH teams' identity blocks: ours from config, the opponent's from
    the identity it declared at the negotiate handshake (stored per log)."""
    first = by_slot[min(by_slot)]["summary"]
    me, them, _, _ = _names(first)
    identity = (first.get("opponent_info") or {}).get("identity") or {}
    return [
        {"group_id": me,
         "members": list(our_identity.get("members", [])),
         "repos": dict(our_identity.get("repos", {})),
         "mcp_servers": dict(our_identity.get("mcp_servers", {}))},
        {"group_id": them,
         "members": list(identity.get("members", [])),
         "repos": dict(identity.get("repos", {})),
         "mcp_servers": dict(identity.get("mcp_servers", {}))},
    ], them


def _links(game_id: str, groups: list[dict]) -> dict:
    """The reference's logical-role filenames + all four GitHub repo URLs
    (both teams' cop and thief repos, book ch. 9)."""
    return {
        "declaration": game_ids.declaration_name(game_id),
        "config": f"config_{game_id}_g<NN>.json",
        "log": f"log_{game_id}_g<NN>.json",
        "result": game_ids.result_name(game_id),
        "github": {g["group_id"]: dict(g["repos"]) for g in groups},
    }


def build_series_result(game_id: str, game_uid: str, by_slot: dict,
                        score_table, expected_games: int,
                        our_identity: dict) -> dict:
    """Assemble the full reference-conformant result document. The
    mutual_agreement sha256 is sign-then-insert over the rest of the doc
    (ADR-0004 settlement form); confirmed = every sub-game audit clean."""
    groups, them = _groups(by_slot, our_identity)
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
    doc = {
        "_schema": _SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "report_type": "final_game_result",
        "game_id": game_id,
        "game_uid": game_uid,
        "links": _links(game_id, groups),
        "timezone": "UTC",
        "groups": groups,
        "num_sub_games": expected_games,
        "sub_games": sub_games,
        "final_result": {
            "total_score": totals,
            "sub_games_won": won,
            "ties": ties,
            "winner_group": winner,
            "series_tie": series_tie,
            "tokens_total_series": tokens,
        },
    }
    doc["mutual_agreement"] = {  # sign-then-insert, like the game result
        "sha256": consensus_signature(doc),
        "confirmed": all(e["audit"]["log_verified"] for e in sub_games),
        "opponent_group_id": them,
        "per_sub_game_audit": {f"s{e['sub_game_number']}": e["audit"]
                               for e in sub_games},
    }
    return doc
