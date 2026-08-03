"""Rule-52 structural guard: at most ONE counted series per rival pairing
(split from sdk/series.py for the 150-code-line cap).

The ledger under results/local/ remembers every series whose report email
actually reached the league — results/local/ is gitignored and outside the
pre-series archive globs, so it survives both rehearsal churn and the
archive sweep. Rehearsal series (no league email) never enter it, which is
exactly the boundary the team wants: only games reported to the lecturer
count against the one-counted-game-per-rival rule.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

from p2p_police.sdk.series import SeriesSettlementError


def _counted_ledger(results_dir) -> Path:
    return Path(results_dir) / "local" / "counted_series.json"


def refuse_repeat_counted(results_dir, game_id: str, uid: str) -> None:
    """Refuse a NEW game_uid for a pairing already league-reported; the SAME
    uid is this series re-closing (e.g. an email retry) — allowed."""
    path = _counted_ledger(results_dir)
    if not path.is_file():
        return
    prior = json.loads(path.read_text(encoding="utf-8")).get(game_id)
    if prior and prior.get("game_uid") != uid:
        raise SeriesSettlementError(
            f"rule 52: a counted series against pairing {game_id} was already "
            f"reported to the league on {prior.get('reported_at')} (game_uid "
            f"{prior.get('game_uid')}); one counted game per rival - refusing")


def first_meeting(results_dir, game_id: str, uid: str) -> bool:
    """League-standings input (book-attached 4-final-result): is this the
    first counted meeting of the pairing? True unless a DIFFERENT series
    against this pairing was already league-reported — the SAME uid is this
    series re-closing (an email retry) and still the first meeting."""
    path = _counted_ledger(results_dir)
    if not path.is_file():
        return True
    prior = json.loads(path.read_text(encoding="utf-8")).get(game_id)
    return not prior or prior.get("game_uid") == uid


def record_counted(results_dir, game_id: str, uid: str, message_id) -> None:
    """Append this counted series to the ledger AFTER the league email sent."""
    path = _counted_ledger(results_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    ledger = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    ledger[game_id] = {
        "game_uid": uid,
        "message_id": str(message_id),
        "reported_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    path.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")
