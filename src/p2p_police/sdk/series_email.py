"""The ONE end-of-series report email (rule 32; split from sdk/series.py for
the 150-code-line cap).

Attachment policy — RESULT ONLY (ADR-0012, second addendum): the result file
is "הדוח המחייב הנשלח בדוא"ל" (book §9.3.3) and it REFERENCES the per-window
logs and configs (log_files, links) rather than embedding them; the course
chatbot confirms the reference implementation emails only the result. The
other three template types reach the lecturer via GitHub (§9.4, App ו §2
rules 4-5) — commit and push them per game. Moodle item 4 is read as the
delivery of all four templates across BOTH channels, per the bot's answer.
"""

import json
from pathlib import Path


def maybe_email_series(config, doc: dict, result_path,
                       gatekeeper=None) -> str | None:
    """Auto-fired only in send mode; called strictly AFTER aggregate_series
    returned — the settlement guard has already refused any unsettled series
    (rule 35), so nothing invented can ever be mailed. Body carries the full
    result JSON, the emitted result file rides as THE attachment, recipient
    from config, send through shared/gatekeeper. Returns the message id, or
    None when the mode gate held."""
    from p2p_police.shared.interlock import ensure_counted_posture

    ensure_counted_posture(config)  # a counted close must deliver to the league
    email_cfg = config.private.get("email", {})
    if email_cfg.get("mode") != "send":
        return None
    from p2p_police.infra.email_sender import send_report
    from p2p_police.shared.gatekeeper import ApiGatekeeper
    from p2p_police.shared.interlock import ensure_email_allowed

    # lecturer-address interlock: an unarmed run cannot address the league
    # (EmailInterlockError propagates; the CLI reports the refusal)
    ensure_email_allowed(config, email_cfg["recipient"])

    final = doc["final_result"]
    verdict = ("series_tie" if final["series_tie"]
               else f"winner={final['winner_group']}")
    score = " ".join(f"{group}:{points}"
                     for group, points in sorted(final["total_score"].items()))
    message_id = send_report(
        gatekeeper or ApiGatekeeper(config.rate_limits),
        email_cfg["recipient"],
        f"P2P league SERIES result - {doc['game_id']} - {verdict} - {score}",
        json.dumps(doc, indent=2),
        [Path(result_path)])
    return str(message_id)
