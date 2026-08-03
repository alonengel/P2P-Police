"""series-result --email: the ONE series email auto-fires only after a
SUCCESSFUL conformant emit (settlement guard passed) and only in send mode.
A refused (unsettled) series must never email; neither must mode=disabled."""

import json
from pathlib import Path

from p2p_police.cli import build_parser, main
from p2p_police.shared.gatekeeper import ApiGatekeeper

GAME_ID = "anrbj666-vs-beta"


def settled_log(directory: Path, n: int = 1) -> None:
    doc = {"game_uid": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", "sub_game_number": n,
           "summary": {"outcome": "survival", "turns_completed": 35,
                       "audit": "Verified OK", "group_id": "anrbj666",
                       "opponent_group_id": "beta", "role": "police",
                       "ended_at": "2026-07-24T14:00:00+00:00",
                       "opponent_info": {"terms": {"num_games": 1},
                                         "identity": {"group_id": "beta"}}}}
    (directory / f"log_{GAME_ID}_g{n:02d}.json").write_text(json.dumps(doc), encoding="utf-8")


def evidence_files(results: Path) -> None:
    """The rest of the four-template set the email must carry (Moodle item 4):
    declaration beside the logs, config in the owning repo's config/games."""
    (results / f"declaration_{GAME_ID}.json").write_text("{}", encoding="utf-8")
    games = results.parent / "config" / "games"
    games.mkdir(parents=True, exist_ok=True)
    (games / f"config_{GAME_ID}_g01.json").write_text("{}", encoding="utf-8")


def arm(config_dir: Path, mode: str, monkeypatch) -> dict:
    toml = config_dir / "game.toml"
    toml.write_text(toml.read_text(encoding="utf-8").replace('mode = "disabled"',
                                                             f'mode = "{mode}"'),
                    encoding="utf-8")
    calls: dict = {}

    def fake_send(gatekeeper, recipient, subject, body, attachments):
        calls.update(gatekeeper=gatekeeper, recipient=recipient, subject=subject,
                     body=body, attachments=attachments)
        return "series-msg-1"

    monkeypatch.setattr("p2p_police.infra.email_sender.send_report", fake_send)
    return calls


def run_cli(results: Path, config_dir: Path, email: bool = True) -> int:
    argv = ["series-result", "--game-id", GAME_ID,
            "--results-dir", str(results), "--config-dir", str(config_dir)]
    return main(argv + (["--email"] if email else []))


def test_email_flag_defaults_off() -> None:
    assert build_parser().parse_args(["series-result", "--game-id", "x"]).email is False


def test_send_mode_emits_then_emails_the_one_report(tmp_path, config_dir, capsys, monkeypatch):
    calls = arm(config_dir, "send", monkeypatch)
    results = tmp_path / "results"
    results.mkdir()
    settled_log(results)
    evidence_files(results)
    assert run_cli(results, config_dir) == 0
    assert calls["recipient"] == "nobody@example.com"  # from config, never hardcoded
    assert isinstance(calls["gatekeeper"], ApiGatekeeper)  # through shared/gatekeeper
    assert GAME_ID in calls["subject"]  # subject: game_id + final score + winner
    assert "winner=beta" in calls["subject"]
    assert "anrbj666:5" in calls["subject"] and "beta:10" in calls["subject"]
    body = json.loads(calls["body"])  # body IS the result JSON
    assert body["report_type"] == "final_game_result"
    # ALL FOUR template types ride the one email (grader's Moodle item 4)
    assert calls["attachments"] == [
        results / f"declaration_{GAME_ID}.json",
        results.parent / "config" / "games" / f"config_{GAME_ID}_g01.json",
        results / f"log_{GAME_ID}_g01.json",
        results / f"result_{GAME_ID}.json"]
    assert "emailed: series-msg-1" in capsys.readouterr().out


def test_partial_evidence_set_refuses_the_email(tmp_path, config_dir, capsys, monkeypatch):
    """No declaration on disk -> the email names it and refuses; the emit
    itself still happened (the result exists for a re-send after the fix)."""
    calls = arm(config_dir, "send", monkeypatch)
    results = tmp_path / "results"
    results.mkdir()
    settled_log(results)  # no evidence_files: declaration + config missing
    assert run_cli(results, config_dir) == 1
    assert calls == {}
    out = capsys.readouterr().out
    assert "EMAIL REFUSED" in out and f"declaration_{GAME_ID}.json" in out
    assert (results / f"result_{GAME_ID}.json").is_file()


def test_refused_unsettled_series_never_emails(tmp_path, config_dir, capsys, monkeypatch):
    calls = arm(config_dir, "send", monkeypatch)
    results = tmp_path / "results"
    results.mkdir()  # no settled logs -> the settlement guard refuses
    assert run_cli(results, config_dir) == 1
    assert calls == {}
    assert "REFUSED" in capsys.readouterr().out


def test_disabled_mode_emits_but_never_emails(tmp_path, config_dir, capsys, monkeypatch):
    calls = arm(config_dir, "disabled", monkeypatch)
    results = tmp_path / "results"
    results.mkdir()
    settled_log(results)
    assert run_cli(results, config_dir) == 0
    assert calls == {}
    assert (results / f"result_{GAME_ID}.json").is_file()
    assert "emailed:" not in capsys.readouterr().out


def test_without_the_flag_send_mode_stays_manual(tmp_path, config_dir, monkeypatch):
    calls = arm(config_dir, "send", monkeypatch)
    results = tmp_path / "results"
    results.mkdir()
    settled_log(results)
    assert run_cli(results, config_dir, email=False) == 0
    assert calls == {}


def _league_recipient(config_dir: Path, counted_line: str = "") -> None:
    toml = config_dir / "game.toml"
    text = toml.read_text(encoding="utf-8").replace(
        'recipient = "nobody@example.com"',
        f'recipient = "rmisegal+uoh26finalgame@gmail.com"\n{counted_line}')
    toml.write_text(text, encoding="utf-8")


def test_series_email_to_the_league_without_arming_is_refused(
        tmp_path, config_dir, capsys, monkeypatch):
    """The series email path routes through the lecturer-address interlock:
    an unarmed run aggregates fine but the email is refused, loudly."""
    calls = arm(config_dir, "send", monkeypatch)
    _league_recipient(config_dir)
    results = tmp_path / "results"
    results.mkdir()
    settled_log(results)
    assert run_cli(results, config_dir) == 1
    assert calls == {}  # nothing sent
    out = capsys.readouterr().out
    assert "EMAIL REFUSED" in out and "counted" in out
    assert (results / f"result_{GAME_ID}.json").is_file()  # emit still happened


def test_series_email_to_the_league_with_both_armings_sends(
        tmp_path, config_dir, capsys, monkeypatch):
    calls = arm(config_dir, "send", monkeypatch)
    _league_recipient(config_dir, counted_line="counted = true")
    results = tmp_path / "results"
    results.mkdir()
    settled_log(results)
    evidence_files(results)
    argv = ["series-result", "--game-id", GAME_ID, "--results-dir", str(results),
            "--config-dir", str(config_dir), "--email", "--counted"]
    assert main(argv) == 0
    assert calls["recipient"] == "rmisegal+uoh26finalgame@gmail.com"
    assert len(calls["attachments"]) == 4  # declaration, config, log, result
    assert "emailed: series-msg-1" in capsys.readouterr().out
