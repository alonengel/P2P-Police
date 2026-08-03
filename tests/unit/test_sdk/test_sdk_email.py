"""Report-email cadence (book §9.3.3): sub-game ends NEVER email — the one
mandated report email is the series result (tests/unit/test_sdk/
test_series_email.py); verify_log paths."""

import json
from pathlib import Path

from p2p_police.sdk import reporting, settlement
from p2p_police.sdk.sdk import SimulationSdk


def make_sdk(config_dir: Path, mode: str) -> SimulationSdk:
    toml = config_dir / "game.toml"
    toml.write_text(toml.read_text(encoding="utf-8").replace('mode = "disabled"',
                                                             f'mode = "{mode}"'),
                    encoding="utf-8")
    return SimulationSdk(str(config_dir))


def test_game_end_never_emails_even_in_send_mode(config_dir: Path, monkeypatch) -> None:
    """Book §9.3.3 (p. 79): the result file is THE mandated emailed report —
    one per series, from the aggregation step. A sub-game settlement must not
    email even when [email].mode == 'send'."""
    sdk = make_sdk(config_dir, "send")
    monkeypatch.setattr(
        "p2p_police.infra.email_sender.send_report",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("game end emailed")))
    monkeypatch.setattr(settlement.reporting, "emit_artifacts", lambda *a: [])
    report: dict = {"outcome": "capture"}
    settlement.settle_report(sdk.config, object(), report)
    assert "email_message_id" not in report
    assert "email_error" not in report


def test_reporting_module_has_no_email_path() -> None:
    """The per-sub-game email path stays deleted (book §9.3.3)."""
    assert not hasattr(reporting, "maybe_email")


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
