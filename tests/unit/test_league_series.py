"""League-day series runner: role-window parity, the single-instance lock,
sequential subprocess launches, and honest continue-on-failure behavior."""

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import league_series  # noqa: E402


@pytest.fixture(autouse=True)
def isolated_lock(tmp_path, monkeypatch):
    monkeypatch.setattr(league_series, "LOCK_PATH", tmp_path / "league_series.lock")


def fake_runner(journal: list, fail_windows: set[int] | None = None):
    def run(command, cwd):
        window = int(command[command.index("--sub-game") + 1])
        journal.append(command)
        return SimpleNamespace(returncode=1 if window in (fail_windows or set()) else 0)
    return run


def test_this_repo_plays_only_its_parity_windows(capsys):
    assert league_series.main(["--sub-games", "2,4,6"], runner=fake_runner([])) == 2
    out = capsys.readouterr().out
    assert "REFUSED" in out and "odd" in out  # police repo = odd windows


def test_windows_run_sequentially_with_derived_seeds(capsys):
    journal: list = []
    code = league_series.main(["--sub-games", "1,3,5", "--seed", "900"],
                              runner=fake_runner(journal))
    assert code == 0
    assert [c[c.index("--sub-game") + 1] for c in journal] == ["1", "3", "5"]
    assert [c[c.index("--seed") + 1] for c in journal] == ["901", "903", "905"]
    assert all(c[:4] == ["uv", "run", "p2p-police", "peer"] for c in journal)
    assert "all 3 settled" in capsys.readouterr().out


def test_failed_window_is_logged_never_fabricated_and_run_continues(capsys):
    journal: list = []
    code = league_series.main(["--sub-games", "1,3,5"],
                              runner=fake_runner(journal, fail_windows={3}))
    assert code == 1  # honest non-zero exit; nothing synthesized
    assert len(journal) == 3  # s5 still ran after s3 failed
    out = capsys.readouterr().out
    assert "s3" in out and "FAILED" in out and "fabricat" in out


def test_second_instance_refuses_and_leaves_the_lock_alone(capsys):
    league_series.LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    league_series.LOCK_PATH.write_text("4242", encoding="ascii")
    journal: list = []
    assert league_series.main(["--sub-games", "1"], runner=fake_runner(journal)) == 2
    assert journal == []  # no window ever launched
    assert league_series.LOCK_PATH.read_text(encoding="ascii") == "4242"  # not ours to release
    assert "4242" in capsys.readouterr().out


def test_lock_is_released_after_the_run():
    assert league_series.main(["--sub-games", "1"], runner=fake_runner([])) == 0
    assert not league_series.LOCK_PATH.exists()
