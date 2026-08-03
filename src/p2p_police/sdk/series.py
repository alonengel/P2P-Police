"""Series aggregation guards (Appendix VI: num_games sub-games per series).

Sub-games alternate roles, so a team's full series record spans BOTH its
role repos - aggregation accepts several results directories. Three guards
protect the counterparty (rule 35: a report must never quietly invent or
complete a missing game): every sub-game 1..num_games needs a settled,
audit-clean log; logs from another series window (wrong game_uid or wrong
declared num_games - identical terms give identical game_uids across
instances, so BOTH must match) are excluded BY NAME, never silently; and
logs that cannot agree on one series game_uid are refused outright.
"""

import json
from pathlib import Path

from p2p_police.report.series_doc import build_series_result


class SeriesSettlementError(Exception):
    """The series is not settled enough to emit an honest result."""


def _parse(path: Path) -> dict:
    doc = json.loads(path.read_text(encoding="utf-8"))
    summary = doc.get("summary") or {}
    terms = (summary.get("opponent_info") or {}).get("terms") or {}
    return {
        "path": path,
        "file": path.name,
        "uid": doc.get("game_uid"),
        "sub": int(doc.get("sub_game_number") or 0),
        "declared_games": terms.get("num_games"),
        "summary": summary,
    }


def _consensus_uid(parsed: list[dict], excluded: list[str]) -> str:
    """The uid shared by the most logs; a tie IS disagreement -> refuse."""
    counts: dict[str, int] = {}
    for entry in parsed:
        if entry["uid"]:
            counts[entry["uid"]] = counts.get(entry["uid"], 0) + 1
    if not counts:
        raise SeriesSettlementError(
            "no usable sub-game logs found" + _notes(excluded))
    best = max(counts.values())
    leaders = sorted(uid for uid, count in counts.items() if count == best)
    if len(leaders) > 1:
        raise SeriesSettlementError(
            "logs disagree on the series game_uid (no majority): "
            + ", ".join(leaders) + _notes(excluded))
    return leaders[0]


def _notes(excluded: list[str]) -> str:
    return ("; excluded logs: " + "; ".join(excluded)) if excluded else ""


def collect_logs(results_dirs: list, game_id: str,
                 expected_games: int) -> tuple[dict, list[str], str]:
    """Gather log_<game_id>_gNN.json across all dirs -> (by_slot, excluded,
    series game_uid). Only logs whose game_uid AND declared num_games match
    the series are kept; every rejected file is named with its reason."""
    paths = [p for d in results_dirs
             for p in sorted(Path(d).glob(f"log_{game_id}_g*.json"))]
    parsed, excluded = [], []
    for path in paths:
        try:
            entry = _parse(path)
        except (OSError, ValueError) as error:
            excluded.append(f"{path}: unreadable ({error})")
            continue
        declared = entry["declared_games"]
        if declared is not None and int(declared) != int(expected_games):
            excluded.append(f"{path}: declares num_games={declared}, "
                            f"this series plays {expected_games}")
            continue
        parsed.append(entry)
    uid = _consensus_uid(parsed, excluded)
    by_slot: dict[int, dict] = {}
    for entry in parsed:
        if entry["uid"] != uid:
            excluded.append(f"{entry['path']}: game_uid {entry['uid']} "
                            f"!= series game_uid {uid}")
        elif entry["sub"] in by_slot:
            excluded.append(f"{entry['path']}: duplicate log for sub-game "
                            f"s{entry['sub']}")
        else:
            by_slot[entry["sub"]] = entry
    return by_slot, excluded, uid


def require_settled(by_slot: dict, game_id: str, expected_games: int,
                    excluded: list[str]) -> None:
    """The settlement guard: EVERY sub-game 1..num_games must be covered by
    a settled log whose audit is clean - else refuse, naming each gap."""
    problems = []
    for n in range(1, int(expected_games) + 1):
        entry = by_slot.get(n)
        if entry is None:
            problems.append(f"s{n}: no settled log")
        elif entry["summary"].get("audit") != "Verified OK":
            problems.append(
                f"s{n}: audit not clean ({entry['summary'].get('audit')!r})")
    if problems:
        raise SeriesSettlementError(
            f"refusing to emit a series result for {game_id} (rule 35 - a "
            "report must never invent a missing game): "
            + "; ".join(problems) + _notes(excluded))


def aggregate_series(results_dirs, game_id: str, score_table,
                     expected_games: int, our_identity: dict | None = None,
                     counted: bool = False) -> tuple[dict, list[str]]:
    """Fold the settled logs of sub-games 1..num_games (possibly spread over
    both role repos' results dirs) into the reference-conformant series
    result. Returns (doc, excluded); excluded names every ignored log.
    `counted` keys the league-standings fields: a friendly passes False and
    fabricates no counted record."""
    dirs = ([results_dirs] if isinstance(results_dirs, (str, Path))
            else list(results_dirs))
    by_slot, excluded, uid = collect_logs(dirs, game_id, expected_games)
    require_settled(by_slot, game_id, expected_games, excluded)
    from p2p_police.sdk.counted_ledger import first_meeting  # circular-safe here

    doc = build_series_result(game_id, uid, by_slot, score_table,
                              int(expected_games), our_identity or {},
                              first_meeting=first_meeting(dirs[0], game_id, uid),
                              counted=counted)
    return doc, excluded


from p2p_police.sdk.series_email import maybe_email_series  # noqa: E402,F401 (re-export)
