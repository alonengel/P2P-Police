"""Series-close automation + email preflight (scripts/league_close.py):
a send posture proves deliverability BEFORE window 1 (OAuth token endpoint
only, no mail moves) and the series aggregates ONLY when every sub-game log
is visible across both results dirs - gaps are named, nothing is invented."""

import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import league_close  # noqa: E402
from conftest import VALID_PRIVATE_TOML, VALID_SHARED  # noqa: E402

GAME_ID = "anrbj666-vs-beta"


def recording_runner(journal: list):
    def run(command, cwd):
        journal.append(command)
        return SimpleNamespace(returncode=0)
    return run


def _series_root(tmp_path: Path, num_games: int) -> tuple[Path, Path]:
    """A fake repo root (config/ + results/) and a sibling results dir."""
    root = tmp_path / "repo"
    (root / "config").mkdir(parents=True)
    shared = json.loads(json.dumps(VALID_SHARED))
    shared["network_and_league"]["num_games"] = num_games
    (root / "config" / "game.json").write_text(json.dumps(shared), encoding="utf-8")
    (root / "config" / "game.toml").write_text(VALID_PRIVATE_TOML, encoding="utf-8")
    (root / "results").mkdir()
    sibling = tmp_path / "sibling-results"
    sibling.mkdir()
    return root, sibling


def _log(directory: Path, n: int, game_id: str = GAME_ID, age: int = 0) -> None:
    path = directory / f"log_{game_id}_g{n:02d}.json"
    path.write_text("{}", encoding="utf-8")
    if age:
        stamp = path.stat().st_mtime - age
        os.utime(path, (stamp, stamp))


def test_close_aggregates_when_every_log_is_visible(tmp_path, capsys):
    root, sibling = _series_root(tmp_path, num_games=2)
    _log(root / "results", 1)
    _log(sibling, 2)  # the sibling repo's window, seen via file access only
    journal: list = []
    code = league_close.close_series(root, sibling, "p2p-police",
                                     recording_runner(journal), counted=True)
    assert code == 0
    command = journal[0]
    assert command[:5] == ["uv", "run", "p2p-police", "series-result", "--game-id"]
    assert command[command.index("--game-id") + 1] == GAME_ID
    assert command.count("--results-dir") == 2  # ours + the sibling's
    assert "--email" in command and "--counted" in command
    assert "all 2 sub-game logs visible" in capsys.readouterr().out


def test_close_names_the_missing_windows_and_aggregates_nothing(tmp_path, capsys):
    root, sibling = _series_root(tmp_path, num_games=6)
    for n in (1, 3, 5):
        _log(root / "results", n)  # our windows settled; the sibling's absent
    journal: list = []
    code = league_close.close_series(root, sibling, "p2p-police",
                                     recording_runner(journal))
    assert code == 1
    assert journal == []  # nothing aggregated, nothing emailed
    out = capsys.readouterr().out
    assert "s2" in out and "s4" in out and "s6" in out and "NOT aggregating" in out


def test_close_with_no_logs_refuses(tmp_path, capsys):
    root, sibling = _series_root(tmp_path, num_games=1)
    code = league_close.close_series(root, sibling, "p2p-police",
                                     recording_runner([]))
    assert code == 1
    assert "nothing to aggregate" in capsys.readouterr().out


def test_find_series_game_id_prefers_the_newest_log(tmp_path):
    results = tmp_path / "results"
    results.mkdir()
    _log(results, 1, game_id="anrbj666-vs-older", age=3600)
    _log(results, 1, game_id=GAME_ID)
    assert league_close.find_series_game_id(results) == GAME_ID
    assert league_close.find_series_game_id(tmp_path / "empty") is None


def test_email_preflight_skips_postures_that_owe_nothing(tmp_path):
    root, _sibling = _series_root(tmp_path, num_games=1)  # mode = "disabled"
    assert league_close.email_preflight(root / "config") is None


def _send_posture(root: Path, recipient: str) -> Path:
    toml = root / "config" / "game.toml"
    text = toml.read_text(encoding="utf-8").replace('mode = "disabled"', 'mode = "send"')
    text = text.replace('recipient = "nobody@example.com"',
                        f'recipient = "{recipient}"')
    toml.write_text(text, encoding="utf-8")
    return root / "config"


def test_email_preflight_send_mode_proves_the_token_first(tmp_path, monkeypatch):
    root, _sibling = _series_root(tmp_path, num_games=1)
    config_dir = _send_posture(root, "teammate@example.com")
    calls: list = []
    monkeypatch.setattr("p2p_police.infra.email_sender._load_token",
                        lambda: calls.append("load") or {"refresh_token": "r"})
    monkeypatch.setattr("p2p_police.infra.email_sender._access_token",
                        lambda token: calls.append("refresh") or "access-ok")
    assert league_close.email_preflight(config_dir) is None
    assert calls == ["load", "refresh"]  # OAuth token endpoint only, no send


def test_email_preflight_refuses_an_empty_recipient(tmp_path):
    root, _sibling = _series_root(tmp_path, num_games=1)
    config_dir = _send_posture(root, "")
    assert "recipient is empty" in league_close.email_preflight(config_dir)


def test_email_preflight_refuses_a_dead_token(tmp_path, monkeypatch):
    root, _sibling = _series_root(tmp_path, num_games=1)
    config_dir = _send_posture(root, "teammate@example.com")

    def boom():
        raise RuntimeError("token.json missing")

    monkeypatch.setattr("p2p_police.infra.email_sender._load_token", boom)
    refusal = league_close.email_preflight(config_dir)
    assert "token refresh against the OAuth endpoint failed" in refusal
    assert "token.json missing" in refusal
