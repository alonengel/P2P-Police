"""A new series must start from a clean aggregation path.

Nothing in the protocol distinguishes a rehearsal from a counted series: same
pair, same terms, same num_games, therefore the SAME game_uid. So the
aggregator cannot tell them apart, and a previous run's logs left in results/
either deadlock settlement (a uid tie is refused) or, worse, get counted -
a reported score built partly from a game that never counted.

Archiving is therefore a precondition of starting, not tidying afterwards.
"""

import json
from pathlib import Path

from p2p_police.report.archive import archive_prior_series


def _write(path: Path, uid: str, sub: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"game_uid": uid, "sub_game_number": sub}), encoding="utf-8")


def test_prior_artifacts_leave_the_aggregation_path(tmp_path: Path) -> None:
    results, games = tmp_path / "results", tmp_path / "config" / "games"
    for sub in (1, 3, 5):
        _write(results / f"log_anrbj666-vs-rival88_g{sub:02d}.json", "old-uid", sub)
        _write(games / f"config_anrbj666-vs-rival88_g{sub:02d}.json", "old-uid", sub)
    _write(results / "declaration_anrbj666-vs-rival88.json", "old-uid", 1)
    _write(results / "result_anrbj666-vs-rival88.json", "old-uid", 1)
    _write(results / "log_anrbj666-vs-OTHER_g01.json", "keep", 1)  # another pairing

    moved = archive_prior_series("anrbj666-vs-rival88", results, games)

    assert len(moved) == 8
    assert not list(results.glob("log_anrbj666-vs-rival88_g*.json"))
    assert not list(games.glob("config_anrbj666-vs-rival88_g*.json"))
    assert (results / "log_anrbj666-vs-OTHER_g01.json").is_file()  # untouched


def test_archives_land_outside_git_and_outside_the_glob(tmp_path: Path) -> None:
    """results/local/ is gitignored, and the aggregator's glob is NOT
    recursive - so an archived series is both off git and invisible to
    collect_logs, without anything being deleted."""
    results = tmp_path / "results"
    _write(results / "log_anrbj666-vs-rival88_g01.json", "old-uid", 1)

    moved = archive_prior_series("anrbj666-vs-rival88", results, tmp_path / "config/games")

    assert moved and all("local" in str(p.parent) for p in moved)
    assert all(p.is_file() for p in moved)  # preserved, never deleted
    assert not list(results.glob("log_*.json"))


def test_a_clean_path_is_a_no_op(tmp_path: Path) -> None:
    results = tmp_path / "results"
    results.mkdir()
    assert archive_prior_series("anrbj666-vs-rival88", results, tmp_path / "config/games") == []


def test_it_refuses_to_guess_the_pairing(tmp_path: Path) -> None:
    """`<us>-vs-unknown` is a REAL pairing this repo holds artifacts under, so
    an unconfigured run must not archive evidence for a series it is not
    playing. It says so rather than staying silent: 'nothing was archived' and
    'the archive never ran' look identical in a log otherwise."""
    from types import SimpleNamespace

    from p2p_police.report.archive import archive_for_pairing

    _write(tmp_path / "results" / "log_anrbj666-vs-unknown_g01.json", "uid", 1)
    unconfigured = SimpleNamespace(group_id="anrbj666", opponent_group_id=lambda: None)
    note = archive_for_pairing(tmp_path, unconfigured)
    assert "NOT cleared" in note
    assert (tmp_path / "results" / "log_anrbj666-vs-unknown_g01.json").is_file()

    configured = SimpleNamespace(group_id="anrbj666", opponent_group_id=lambda: "rival88")
    assert "clean for anrbj666-vs-rival88" in archive_for_pairing(tmp_path, configured)
