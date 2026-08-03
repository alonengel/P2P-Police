"""Failure-path settlement (rules 32/35-36) — split from sdk/reporting.py
for the 150-code-line cap.

Two duties the happy path never exercises: when play() raised before the
normal finisher could run, the rival may still be alive and is owed our
audit disclosure (rules 35-36); and the artifact funnel must never let its
own exception eat a settled game's report (rule 32) — a failure lands ON
the report, which still reaches stdout. No email here: the one mandatory
report email is the SERIES result (book §9.3.3), sent at aggregation.
"""

from p2p_police.peer.deadline import Deadline
from p2p_police.sdk import reporting


def ensure_counted_ready(config) -> None:
    """--counted start gate: the email posture must deliver to the league
    (interlock) and the Table-18 FIXED terms must hold — else the run plays
    ZERO games. Training runs (no --counted) pass straight through."""
    from p2p_police.shared.interlock import ensure_counted_posture

    ensure_counted_posture(config)
    if config.private.get("email", {}).get("counted_cli_armed"):
        from p2p_police.domain.negotiation import validate_counted_terms

        validate_counted_terms(config.shared)  # Table 18, league only


def emergency_audit(runtime, config) -> str | None:
    """Best-effort audit disclosure on the FAILURE path only.

    The normal finishers set runtime.audit_sent after their own send, so a
    game that completed (even with the rival's audit missing) never
    double-sends. Returns None (nothing owed), 'sent', or 'failed: ...' —
    recorded on the report either way; the rival being unreachable is
    expected here and must never mask the original failure."""
    if getattr(runtime, "audit_sent", False):
        return None
    try:
        if getattr(runtime, "own", None) is not None:
            from p2p_police.wire import audit

            payload = audit.build_audit_payload(
                runtime.exchange, runtime.role.value, "technical_loss")
        else:
            from p2p_police.domain import protocol

            payload = {
                "end_state_digest": protocol.end_state_digest(runtime.engine),
                "group_id": config.group_id,
                "nonces": runtime.exchange.own_nonces(),
                "verdicts": runtime.exchange.own_verdicts(),
            }
        runtime.transport.send_audit(
            payload, Deadline(config.turn_timeout_seconds))
        return "sent"
    except Exception as error:  # noqa: BLE001 - best effort by design
        return f"failed: {type(error).__name__}: {error}"


def settle_report(config, runtime, report: dict) -> None:
    """Rule-32 hardening: the artifact write is best-effort — an exception
    is recorded on the report instead of raising, so the settled outcome
    always reaches stdout. Sub-game ends never email (book §9.3.3: only
    the series result is the mandated report email)."""
    try:
        report["artifacts"] = [
            str(p) for p in reporting.emit_artifacts(config, runtime, report)]
    except Exception as error:  # noqa: BLE001 - recorded, never fatal
        report["artifacts"] = []
        report["artifacts_error"] = f"{type(error).__name__}: {error}"
