"""SDK glue: auto-email fires only in send mode (rule 32); verify_log paths."""

import json
from pathlib import Path

from p2p_police.sdk import reporting
from p2p_police.sdk.sdk import SimulationSdk


def make_sdk(config_dir: Path, mode: str) -> SimulationSdk:
    toml = config_dir / "game.toml"
    toml.write_text(toml.read_text(encoding="utf-8").replace('mode = "disabled"',
                                                             f'mode = "{mode}"'),
                    encoding="utf-8")
    return SimulationSdk(str(config_dir))


def test_disabled_mode_sends_nothing(config_dir: Path) -> None:
    sdk = make_sdk(config_dir, "disabled")
    report = {"outcome": "capture", "artifacts": []}
    reporting.maybe_email(sdk.config, report)
    assert "email_message_id" not in report


def test_send_mode_calls_the_sender(config_dir: Path, monkeypatch, tmp_path: Path) -> None:
    sdk = make_sdk(config_dir, "send")
    attachment = tmp_path / "result_x.json"
    attachment.write_text("{}", encoding="utf-8")
    calls = {}

    def fake_send(gate, recipient, subject, body, attachments):
        calls.update(recipient=recipient, n=len(attachments))
        return "msg-123"

    monkeypatch.setattr("p2p_police.infra.email_sender.send_report", fake_send)
    report = {"outcome": "survival", "artifacts": [str(attachment)]}
    reporting.maybe_email(sdk.config, report)
    assert report["email_message_id"] == "msg-123"
    assert calls == {"recipient": "nobody@example.com", "n": 1}


def test_league_recipient_without_arming_is_refused_on_the_report(
        config_dir: Path, monkeypatch) -> None:
    """Lecturer-address interlock through maybe_email: nothing sends, the
    refusal lands ON the report (the game outcome must still surface)."""
    sdk = make_sdk(config_dir, "send")
    sdk.config.private["email"]["recipient"] = "rmisegal+uoh26finalgame@gmail.com"
    calls: list = []
    monkeypatch.setattr("p2p_police.infra.email_sender.send_report",
                        lambda *a, **k: calls.append(a) or "never")
    report = {"outcome": "survival", "artifacts": []}
    reporting.maybe_email(sdk.config, report)
    assert calls == []  # structurally cannot fire
    assert "email_message_id" not in report
    assert "counted" in report["email_refused"]


def test_league_recipient_with_both_armings_sends(config_dir: Path, monkeypatch) -> None:
    sdk = make_sdk(config_dir, "send")
    sdk.config.private["email"].update(recipient="rmisegal@gmail.com",
                                       counted=True, counted_cli_armed=True)
    monkeypatch.setattr("p2p_police.infra.email_sender.send_report",
                        lambda *a, **k: "msg-armed")
    report = {"outcome": "survival", "artifacts": []}
    reporting.maybe_email(sdk.config, report)
    assert report["email_message_id"] == "msg-armed"
    assert "email_refused" not in report


def test_verify_log_both_verdicts(tmp_path: Path) -> None:
    from p2p_police.domain import crypto

    payload = crypto.build_step_payload(1, "police", 1, "d", {"type": "move", "move": "N"}, "h", True)
    nonce = crypto.new_nonce()
    good = {"records": [{"payload": payload, "nonce": nonce,
                         "commit": crypto.commit_hash(payload, nonce)}]}
    path = tmp_path / "log.json"
    path.write_text(json.dumps(good), encoding="utf-8")
    assert SimulationSdk.verify_log(str(path)).startswith("Verified OK")
    good["records"][0]["payload"]["hint"] = "changed"
    path.write_text(json.dumps(good), encoding="utf-8")
    assert SimulationSdk.verify_log(str(path)) == "TAMPERED"
