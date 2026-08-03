"""Failure-path settlement (rules 32/35-36): the emergency audit fires ONLY
when the normal finisher never sent ours, and the artifact funnel records
its own failures on the report instead of eating the report."""

from types import SimpleNamespace

from p2p_police.domain import crypto
from p2p_police.sdk import settlement

CONFIG = SimpleNamespace(turn_timeout_seconds=1, group_id="anrbj666")


def hidden_runtime(sent: list, audit_sent: bool = False, dead: bool = False):
    payload = crypto.build_step_payload(
        1, "police", 1, "d" * 64, {"type": "move", "move": "E"}, "h", True)
    nonce = crypto.new_nonce()
    exchange = SimpleNamespace(own_records=[
        {"payload": payload, "nonce": nonce,
         "commit": crypto.commit_hash(payload, nonce)}])

    def send_audit(message, deadline):
        if dead:
            raise ConnectionError("rival gone")
        sent.append(message)

    runtime = SimpleNamespace(
        own=SimpleNamespace(), exchange=exchange,
        role=SimpleNamespace(value="police"),
        transport=SimpleNamespace(send_audit=send_audit))
    if audit_sent:
        runtime.audit_sent = True
    return runtime


def test_normal_completion_never_resends() -> None:
    """The user's constraint: a game that actually worked must not trigger
    the emergency path — the finisher already sent and set the flag."""
    sent: list = []
    assert settlement.emergency_audit(hidden_runtime(sent, audit_sent=True),
                                      CONFIG) is None
    assert sent == []


def test_failure_path_sends_our_records() -> None:
    sent: list = []
    verdict = settlement.emergency_audit(hidden_runtime(sent), CONFIG)
    assert verdict == "sent"
    assert len(sent) == 1
    message = sent[0]
    assert set(message) == {"sender", "records", "result_claim"}
    assert message["result_claim"] == "technical_loss"


def test_unreachable_rival_is_recorded_not_raised() -> None:
    verdict = settlement.emergency_audit(hidden_runtime([], dead=True), CONFIG)
    assert verdict.startswith("failed: ConnectionError")


def test_settle_report_records_artifact_failure(monkeypatch) -> None:
    monkeypatch.setattr(settlement.reporting, "emit_artifacts",
                        lambda *a: (_ for _ in ()).throw(OSError("disk full")))
    report: dict = {"outcome": "capture"}
    settlement.settle_report(CONFIG, SimpleNamespace(), report)
    assert report["artifacts"] == []
    assert report["artifacts_error"].startswith("OSError")
    assert report["outcome"] == "capture"  # the report itself survives
