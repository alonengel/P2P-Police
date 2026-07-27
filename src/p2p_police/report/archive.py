"""Clear a pairing's artifacts out of the aggregation path before a series.

Nothing in the protocol distinguishes a rehearsal from a counted series: the
same pair, the same signed terms and the same num_games derive the SAME
game_uid, by construction. So `sdk/series.collect_logs` cannot tell last
week's practice run from today's counted one - it votes on a consensus uid and
refuses on a tie, which means a previous run's logs left in `results/` either
deadlock the settlement or, far worse, get counted. A reported score assembled
partly from a game that never counted is the failure this module exists to
make impossible.

Archived, never deleted: the destination is `results/local/`, which is
gitignored (so repeated rehearsals create no churn) and which the aggregator's
NON-recursive glob cannot see. Evidence worth keeping is promoted to
`docs/evidence/` by hand, as a decision rather than a side effect.
"""

import shutil
import time
from pathlib import Path

from p2p_police.domain.game_ids import build_game_id

ARCHIVE_ROOT = Path("results") / "local" / "archived-series"


def archive_prior_series(game_id: str, results: Path, games: Path,
                         archive_root: Path | None = None) -> list:
    """Move every artifact of `game_id` aside. Returns the new paths.

    Input: the pairing's game_id plus the two directories the aggregator and
    the config archive read. Output: the archived paths (empty when the path
    was already clean, which is the common case). Setup: none - the
    destination is derived, timestamped, and created on demand.
    """
    targets = [
        *sorted(results.glob(f"log_{game_id}_g*.json")),
        *sorted(games.glob(f"config_{game_id}_g*.json")),
        *[p for p in (results / f"declaration_{game_id}.json",
                      results / f"result_{game_id}.json") if p.is_file()],
    ]
    if not targets:
        return []
    root = archive_root or (results.parent / ARCHIVE_ROOT)
    destination = root / f"{game_id}-{time.strftime('%Y%m%d-%H%M%S')}"
    destination.mkdir(parents=True, exist_ok=True)
    return [Path(shutil.move(str(path), str(destination / path.name)))
            for path in targets]


def archive_for_pairing(root: Path, config) -> str:
    """Clear this session's pairing from the path; return a status line.

    Always says what it did, because "nothing was archived" and "the archive
    never ran" look identical in a log otherwise, and a series that quietly
    skipped this step is the one that mis-settles.

    Refuses to GUESS the pairing: with no expected opponent the derived id
    would be `<us>-vs-unknown`, a REAL pairing this repo holds artifacts
    under, so an unconfigured run would archive evidence for a pairing the
    series is not even playing.
    """
    opponent = config.opponent_group_id()
    if not opponent:
        return ("aggregation path: NOT cleared - no expected opponent configured "
                "(set [game] opponent_group_id or pass --opponent-group)")
    game_id = build_game_id(config.group_id, opponent)
    moved = archive_prior_series(game_id, root / "results", root / "config" / "games")
    if not moved:
        return f"aggregation path clean for {game_id} (nothing to archive)"
    return (f"aggregation path: archived {len(moved)} prior artifact(s) for "
            f"{game_id} -> {moved[0].parent}")
