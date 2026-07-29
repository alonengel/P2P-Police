"""League-day series runner: role-window parity, the single-instance lock,
sequential subprocess launches, honest continue-on-failure behavior, the
email preflight (refuse with ZERO games played) and the auto-close hook."""

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import league_close  # noqa: E402
import league_series  # noqa: E402


@pytest.fixture(autouse=True)
def isolated_lock(tmp_path, monkeypatch):
    monkeypatch.setattr(league_series, "LOCK_PATH", tmp_path / "league_series.lock")


@pytest.fixture
def quiet_bookends(monkeypatch):
    """Runner-flow tests: preflight passes, close is a spy returning 0."""
    closes: list = []
    monkeypatch.setattr(league_close, "email_preflight", lambda config_dir, counted=False: None)
    monkeypatch.setattr(
        league_close, "close_series",
        lambda root, sibling, cli, runner, counted=False: closes.append(
            {"cli": cli, "counted": counted}) or 0)
    return closes


def fake_runner(journal: list, fail_windows: set[int] | None = None):
    def run(command, cwd):
        journal.append(command)
        if "series-result" in command:
            return SimpleNamespace(returncode=0)
        window = int(command[command.index("--sub-game") + 1])
        return SimpleNamespace(returncode=1 if window in (fail_windows or set()) else 0)
    return run


def test_this_repo_plays_only_its_parity_windows(capsys, quiet_bookends):
    assert league_series.main(["--sub-games", "2,4,6"], runner=fake_runner([])) == 2
    out = capsys.readouterr().out
    assert "REFUSED" in out and "odd" in out  # police repo = odd windows


def test_windows_run_sequentially_with_derived_seeds(capsys, quiet_bookends):
    journal: list = []
    code = league_series.main(["--sub-games", "1,3,5", "--seed", "900"],
                              runner=fake_runner(journal))
    assert code == 0
    assert [c[c.index("--sub-game") + 1] for c in journal] == ["1", "3", "5"]
    assert [c[c.index("--seed") + 1] for c in journal] == ["901", "903", "905"]
    assert all(c[:4] == ["uv", "run", "p2p-police", "peer"] for c in journal)
    assert all("--counted" not in c for c in journal)  # not a counted run
    assert "all 3 settled" in capsys.readouterr().out
    assert quiet_bookends == [{"cli": "p2p-police", "counted": False}]


def test_failed_window_is_logged_never_fabricated_and_run_continues(capsys, quiet_bookends):
    journal: list = []
    code = league_series.main(["--sub-games", "1,3,5"],
                              runner=fake_runner(journal, fail_windows={3}))
    assert code == 1  # honest non-zero exit; nothing synthesized
    assert len(journal) == 3  # s5 still ran after s3 failed
    assert quiet_bookends == []  # an unsettled series never auto-closes
    out = capsys.readouterr().out
    assert "s3" in out and "FAILED" in out and "fabricat" in out


def test_second_instance_refuses_and_leaves_the_lock_alone(capsys, quiet_bookends):
    league_series.LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    league_series.LOCK_PATH.write_text("4242", encoding="ascii")
    journal: list = []
    assert league_series.main(["--sub-games", "1"], runner=fake_runner(journal)) == 2
    assert journal == []  # no window ever launched
    assert league_series.LOCK_PATH.read_text(encoding="ascii") == "4242"  # not ours to release
    assert "4242" in capsys.readouterr().out


def test_lock_is_released_after_the_run(quiet_bookends):
    assert league_series.main(["--sub-games", "1"], runner=fake_runner([])) == 0
    assert not league_series.LOCK_PATH.exists()


def test_preflight_refusal_plays_zero_games(capsys, monkeypatch):
    """A send posture that cannot deliver refuses the WHOLE run: exit 2 and
    not a single window launched."""
    monkeypatch.setattr(league_close, "email_preflight",
                        lambda config_dir, counted=False: "token refresh failed (stub)")
    journal: list = []
    assert league_series.main(["--sub-games", "1,3,5"], runner=fake_runner(journal)) == 2
    assert journal == []  # zero games played
    out = capsys.readouterr().out
    assert "zero games played" in out and "token refresh failed" in out
    assert not league_series.LOCK_PATH.exists()


def test_counted_flag_flows_to_every_window_and_the_close(quiet_bookends):
    journal: list = []
    assert league_series.main(["--sub-games", "1", "--counted"],
                              runner=fake_runner(journal)) == 0
    assert all("--counted" in c for c in journal)
    assert quiet_bookends == [{"cli": "p2p-police", "counted": True}]
