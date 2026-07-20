"""SDK reporting glue: artifacts, auto-email, technical-loss synthesis.

Split from sdk.py (150-line cap); rules 32/35: EVERY game end - including a
technical loss - emits the four artifacts and, in send mode, the email.
"""

import random  # noqa: F401  (kept for parity of imports used in bodies)
from pathlib import Path

from p2p_police.domain import game_ids
from p2p_police.report import artifacts


def technical_loss_report(my_role, runtime, error: Exception) -> dict:
    from p2p_police.domain import protocol

    return {
        "role": my_role.value,
        "outcome": "technical_loss",
        "turns_completed": runtime.engine.turns_completed,
        "end_state_digest": protocol.end_state_digest(runtime.engine),
        "digest_match": False,
        "audit": "unavailable (technical loss)",
        "steps_sealed": len(runtime.exchange.own_records),
        "opponent_group_id": getattr(runtime, "opponent_group_id", "unknown"),
        "failure": f"{type(error).__name__}: {error}",
    }



def _series_uid(config, game_id: str, opponent_group_id: str) -> str:
    """ONE game_uid per series, DERIVED from the agreed terms + group ids
    (reference form, ADR-0004) so the opponent computes the identical uid.
    The marker file freezes the series' uid against mid-series term changes."""
    marker = Path("results") / f".game_uid_{game_id}"
    if marker.is_file():
        return marker.read_text(encoding="utf-8").strip()
    uid = game_ids.derive_game_uid(config.shared, config.group_id, opponent_group_id)
    marker.parent.mkdir(exist_ok=True)
    marker.write_text(uid, encoding="utf-8")
    return uid


def emit_artifacts(config, runtime, report: dict) -> list:
    """Write the four Table-20 artifacts (results/ + archived config)."""
    opponent_group_id = report.get("opponent_group_id", "unknown")
    game_id = game_ids.build_game_id(config.group_id, opponent_group_id)
    game_uid = _series_uid(config, game_id, opponent_group_id)
    sub_game = int(config.private["game"]["sub_game_number"])
    from p2p_police.domain.primitives import Outcome

    score = config.score_table().points_for(Outcome(report["outcome"]))
    results = Path("results")
    written = [
        artifacts.emit(
            artifacts.build_declaration(
                config, game_id, game_uid,
                int(config.private["game"].get("counted_games_played", 0)),
                opponent=report.get("opponent_info", {})),
            results, game_ids.declaration_name(game_id)),
        artifacts.emit(
            artifacts.build_config_artifact(config, game_id, game_uid, sub_game),
            Path("config/games"), game_ids.config_name(game_id, sub_game)),
        artifacts.emit(
            artifacts.build_log(config, game_id, game_uid, sub_game, report,
                                runtime.exchange.own_records,
                                runtime.exchange.their_records),
            results, game_ids.log_name(game_id, sub_game)),
        artifacts.emit(
            artifacts.build_result(config, game_id, game_uid, report, score,
                                   runtime.talk.meter.total),
            results, game_ids.result_name(game_id)),
    ]
    return written



def maybe_email(config, report: dict, gatekeeper=None) -> None:
    """Automatic end-of-game report (rule 32) when [email].mode == send."""
    email_cfg = config.private.get("email", {})
    if email_cfg.get("mode") != "send":
        return
    from p2p_police.infra.email_sender import send_report
    from p2p_police.shared.gatekeeper import ApiGatekeeper

    message_id = send_report(
        gatekeeper or ApiGatekeeper(config.rate_limits),
        email_cfg["recipient"],
        f"P2P league report - {config.group_id} - {report['outcome']}",
        "Automated end-of-game report (rule 32). JSON artifacts attached.",
        [Path(p) for p in report["artifacts"]],
    )
    report["email_message_id"] = message_id
