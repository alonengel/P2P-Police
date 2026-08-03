"""The ONE end-of-series report email (rule 32 + the grader's Moodle item 4;
ADR-0012 addendum) — split from sdk/series.py for the 150-code-line cap.

Fired only after a successful, settled emit. Attachments carry ALL FOUR
template types — declaration, per-window config and log, result — per the
grader's instruction ("the agent sends the lecturer the 4 signed templates
at game end"); the result stays the report and the body (book §9.3.3). A
partial evidence set is NAMED and refused, never sent.
"""

import json
from pathlib import Path

from p2p_police.domain import game_ids


def series_attachments(dirs: list | None, game_id: str, num_games: int,
                       result_path) -> list[Path]:
    """declaration + config g01..gNN + log g01..gNN + result — each instance
    from whichever results dir holds it (configs live in the owning repo's
    config/games beside its results dir)."""
    from p2p_police.sdk.series import SeriesSettlementError

    roots = [Path(d) for d in (dirs or [Path(result_path).parent])]

    def find(name: str, config_side: bool) -> Path | None:
        for root in roots:
            candidate = (root.parent / "config" / "games" / name) if config_side \
                else (root / name)
            if candidate.is_file():
                return candidate
        return None

    wanted = [(game_ids.declaration_name(game_id), False)]
    wanted += [(game_ids.config_name(game_id, n), True)
               for n in range(1, int(num_games) + 1)]
    wanted += [(game_ids.log_name(game_id, n), False)
               for n in range(1, int(num_games) + 1)]
    found = [(name, find(name, config_side)) for name, config_side in wanted]
    missing = [name for name, path in found if path is None]
    if missing:
        raise SeriesSettlementError(
            "refusing to email a partial evidence set - missing: "
            + ", ".join(missing))
    return [path for _, path in found] + [Path(result_path)]


def maybe_email_series(config, doc: dict, result_path, dirs=None,
                       gatekeeper=None) -> str | None:
    """Auto-fired only in send mode; called strictly AFTER aggregate_series
    returned — the settlement guard has already refused any unsettled series
    (rule 35), so nothing invented can ever be mailed. Body carries the full
    result JSON; the recipient comes from config; the send goes through
    shared/gatekeeper like every other external call. Returns the message
    id, or None when the mode gate held."""
    from p2p_police.shared.interlock import ensure_counted_posture

    ensure_counted_posture(config)  # a counted close must deliver to the league
    email_cfg = config.private.get("email", {})
    if email_cfg.get("mode") != "send":
        return None
    from p2p_police.infra.email_sender import send_report
    from p2p_police.shared.gatekeeper import ApiGatekeeper
    from p2p_police.shared.interlock import ensure_email_allowed

    # lecturer-address interlock: an unarmed run cannot address the league
    # (EmailInterlockError propagates; the CLI reports the refusal)
    ensure_email_allowed(config, email_cfg["recipient"])

    final = doc["final_result"]
    verdict = ("series_tie" if final["series_tie"]
               else f"winner={final['winner_group']}")
    score = " ".join(f"{group}:{points}"
                     for group, points in sorted(final["total_score"].items()))
    message_id = send_report(
        gatekeeper or ApiGatekeeper(config.rate_limits),
        email_cfg["recipient"],
        f"P2P league SERIES result - {doc['game_id']} - {verdict} - {score}",
        json.dumps(doc, indent=2),
        series_attachments(dirs, doc["game_id"],
                           int(doc.get("num_sub_games", 0)), result_path))
    return str(message_id)
