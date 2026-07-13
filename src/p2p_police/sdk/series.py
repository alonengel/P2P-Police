"""Series aggregation (Appendix VI: 6 sub-games per counted series).

In inter-team play sub-games 1-3 pair our cop with their thief and 4-6 swap
roles, so a team's series is played by BOTH its repos; this module aggregates
the per-sub-game logs into the single result document the league scores
(total points per group, sub-games won, series winner or tie at tie_score).
"""

import json
from pathlib import Path


def _sub_game_score(summary: dict, score_table) -> dict:
    """Points per GROUP for one sub-game, from the writer's log summary."""
    outcome = summary["outcome"]
    cop_points, thief_points = score_table.points_for_name(outcome)
    me, them = summary["group_id"], summary["opponent_group_id"]
    if me == them:  # self-play series: disambiguate by role
        me, them = f"{me}(police)", f"{them}(thief)"
        roles = {me: "police", them: "thief"}
    else:
        roles = {me: summary["role"],
                 them: "thief" if summary["role"] == "police" else "police"}
    return {
        group: cop_points if role == "police" else thief_points
        for group, role in roles.items()
    }


def aggregate_series(results_dir: str | Path, game_id: str, score_table) -> dict:
    """Fold every log_<game_id>_gNN.json into the series result document."""
    logs = sorted(Path(results_dir).glob(f"log_{game_id}_g*.json"))
    if not logs:
        raise FileNotFoundError(f"no logs for game_id {game_id} under {results_dir}")
    totals: dict[str, int] = {}
    won: dict[str, int] = {}
    sub_games, ties = [], 0
    for path in logs:
        doc = json.loads(path.read_text(encoding="utf-8"))
        summary = doc["summary"]
        scores = _sub_game_score(summary, score_table)
        for group, points in scores.items():
            totals[group] = totals.get(group, 0) + points
            won.setdefault(group, 0)
        winner = max(scores, key=lambda g: scores[g])
        if len(set(scores.values())) > 1:
            won[winner] += 1
        sub_games.append(
            {
                "sub_game_number": doc.get("sub_game_number"),
                "outcome": summary["outcome"],
                "turns_completed": summary["turns_completed"],
                "audit": summary.get("audit", ""),
                "scores": scores,
                "log_file": path.name,
            }
        )
    groups = sorted(totals)
    series_tie = len(groups) == 2 and totals[groups[0]] == totals[groups[1]]
    if series_tie:
        tie_points = score_table.series_tie_points()[0]
        ties = 1
        final_winner = None
        totals = {g: totals[g] + tie_points for g in groups}
    else:
        final_winner = max(totals, key=lambda g: totals[g])
    return {
        "game_id": game_id,
        "num_sub_games": len(sub_games),
        "sub_games": sub_games,
        "final_result": {
            "total_score": totals,
            "sub_games_won": won,
            "ties": ties,
            "winner_group": final_winner,
            "series_tie": series_tie,
        },
    }
