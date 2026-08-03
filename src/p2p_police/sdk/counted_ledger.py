"""Rule-52 structural guard: at most ONE counted series per rival pairing
(split from sdk/series.py for the 150-code-line cap).

The ledger is COMMITTED evidence (`results/counted_series.json`): a false
game-count declaration is project-level disqualification (rule 38), so the
guard must survive a fresh clone, a different machine, and the SIBLING repo
having closed the series — reads consult every supplied results dir (both
role repos) plus the legacy gitignored `results/local/` copy; the write
lands in the committed path and the runbook commits it beside the game
artifacts. Rehearsal series (no league email) never enter it, which is
exactly the boundary the team wants: only games reported to the lecturer
count against the one-counted-game-per-rival rule. (Durability finding:
imreeyal repo review 2026-08-03, #4.)
"""

import json
from datetime import UTC, datetime
from pathlib import Path

from p2p_police.sdk.series import SeriesSettlementError

LEDGER = "counted_series.json"


def _read_paths(results_dirs) -> list[Path]:
    dirs = ([results_dirs] if isinstance(results_dirs, (str, Path))
            else list(results_dirs))
    paths: list[Path] = []
    for d in dirs:  # committed path first; gitignored legacy copy second
        paths += [Path(d) / LEDGER, Path(d) / "local" / LEDGER]
    return paths


def _prior(results_dirs, game_id: str) -> dict | None:
    for path in _read_paths(results_dirs):
        if path.is_file():
            entry = json.loads(path.read_text(encoding="utf-8")).get(game_id)
            if entry:
                return entry
    return None


def refuse_repeat_counted(results_dirs, game_id: str, uid: str) -> None:
    """Refuse a NEW game_uid for a pairing already league-reported; the SAME
    uid is this series re-closing (e.g. an email retry) — allowed."""
    prior = _prior(results_dirs, game_id)
    if prior and prior.get("game_uid") != uid:
        raise SeriesSettlementError(
            f"rule 52: a counted series against pairing {game_id} was already "
            f"reported to the league on {prior.get('reported_at')} (game_uid "
            f"{prior.get('game_uid')}); one counted game per rival - refusing")


def first_meeting(results_dirs, game_id: str, uid: str) -> bool:
    """League-standings input (book-attached 4-final-result): is this the
    first counted meeting of the pairing? True unless a DIFFERENT counted
    series against this pairing was already league-reported — the SAME uid
    is this series re-closing and still the first meeting."""
    prior = _prior(results_dirs, game_id)
    return not prior or prior.get("game_uid") == uid


def record_counted(results_dir, game_id: str, uid: str, message_id) -> None:
    """Append this counted series AFTER the league email sent — into the
    COMMITTED path; commit it with the game artifacts (runbook step 5)."""
    path = Path(results_dir) / LEDGER
    path.parent.mkdir(parents=True, exist_ok=True)
    ledger = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    ledger[game_id] = {
        "game_uid": uid,
        "message_id": str(message_id),
        "reported_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    path.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")
