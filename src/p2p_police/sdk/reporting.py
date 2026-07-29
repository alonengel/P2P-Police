"""SDK reporting glue: artifacts, auto-email, technical-loss synthesis.

Split from sdk.py (150-line cap); rules 32/35: EVERY game end - including a
technical loss - emits the four artifacts and, in send mode, the email.
"""

import hashlib
import random  # noqa: F401  (kept for parity of imports used in bodies)
from pathlib import Path

from p2p_police.domain import game_ids
from p2p_police.domain.crypto import canonical
from p2p_police.report import artifacts
from p2p_police.wire import terms as wire_terms


def technical_loss_report(my_role, runtime, error: Exception) -> dict:
    """Rule-32 classification for BOTH runtimes: the geometric one digests
    its replicated engine; the hidden one has only OwnState to digest (the
    rival's half is sealed commits — there is no shared frame to hash)."""
    own = getattr(runtime, "own", None)
    if own is not None:
        turns, digest = own.turns_completed, own.digest()
    else:
        from p2p_police.domain import protocol

        turns = runtime.engine.turns_completed
        digest = protocol.end_state_digest(runtime.engine)
    from p2p_police.domain.errors import RivalBreachError

    report = {
        "role": my_role.value,
        "started_at": getattr(runtime, "started_at", None),
        "outcome": "technical_loss",
        "turns_completed": turns,
        "end_state_digest": digest,
        "digest_match": False,
        "audit": "unavailable (technical loss)",
        "steps_sealed": len(runtime.exchange.own_records),
        "opponent_group_id": getattr(runtime, "opponent_group_id", "unknown"),
        "failure": f"{type(error).__name__}: {error}",
    }
    if isinstance(error, RivalBreachError):
        # The breach is PROVEN from the rival's own message: still 0/0, but
        # our report must never name the cheater as winner (rules 21-22/48).
        report["breach_by"] = "opponent"
    return report


def watchdog_state(runtime):
    """State provider for the watchdog's post-mortem dump. Both runtimes
    duck-type positions/turns_completed/outcome — and the hidden OwnState's
    positions dict simply HAS no rival key, so rules 8-9 hold even in a
    crash dump (nothing secret can leak into logs/watchdog_dump.json)."""
    def provide() -> dict:
        holder = getattr(runtime, "engine", None) or runtime.own
        return {
            "positions": {r.value: list(c) for r, c in holder.positions.items()},
            "turns": holder.turns_completed,
            "outcome": holder.outcome.value,
        }
    return provide



def _series_uid(config, game_id: str, opponent_group_id: str) -> str:
    """ONE game_uid per series, derived exactly as the reference derives it.

    The input is the flat NEGOTIATED terms, not our whole game.json - the
    reference's handshake feeds `terms_from_config(config)` to
    `derive_game_ids`, and those flat terms are the only description of the
    game both peers provably hold. Hashing the raw config was deterministic
    too, and permanently different from the opponent's value, which under
    rule 35 makes two honest reports look like they describe different games.

    The marker still freezes the uid for a series (so a discarded attempt and
    the real run cannot drift apart), but it now carries the fingerprint of
    the terms it was minted from and is ignored when they no longer match -
    otherwise a marker written under the old input would resurrect the old
    uid forever.
    """
    terms = wire_terms.terms_from_shared(config.shared)
    fingerprint = hashlib.sha256(canonical(terms).encode("utf-8")).hexdigest()[:16]
    marker = Path("results") / f".game_uid_{game_id}"
    if marker.is_file():
        stored, _, cached = marker.read_text(encoding="utf-8").strip().partition(":")
        if stored == fingerprint and cached:
            return cached
    uid = game_ids.derive_game_uid(terms, config.group_id, opponent_group_id)
    marker.parent.mkdir(exist_ok=True)
    marker.write_text(f"{fingerprint}:{uid}", encoding="utf-8")
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
    log_doc = artifacts.build_log(config, game_id, game_uid, sub_game, report,
                                  runtime.exchange.own_records,
                                  runtime.exchange.their_records)
    if getattr(runtime, "own", None) is not None:
        # Hidden-wire log: verify-log must replay it through the audit
        # reconstruction, not the engine (ADR-0008) — the marker routes it.
        log_doc["wire_shape"] = "reference"
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
        artifacts.emit(log_doc, results, game_ids.log_name(game_id, sub_game)),
        artifacts.emit(
            artifacts.build_result(config, game_id, game_uid, report, score,
                                   runtime.talk.meter.total),
            results, game_ids.result_name(game_id)),
    ]
    return written



def maybe_email(config, report: dict, gatekeeper=None) -> None:
    """Automatic end-of-game report (rule 32) when [email].mode == send.

    Routed through the lecturer-address interlock: a run not doubly armed as
    a counted game structurally cannot address the league — the refusal is
    recorded ON THE REPORT (the game outcome must still reach stdout intact,
    rule 32) and nothing is sent."""
    email_cfg = config.private.get("email", {})
    if email_cfg.get("mode") != "send":
        return
    from p2p_police.infra.email_sender import send_report
    from p2p_police.shared.gatekeeper import ApiGatekeeper
    from p2p_police.shared.interlock import EmailInterlockError, ensure_email_allowed

    try:
        ensure_email_allowed(config, email_cfg["recipient"])
    except EmailInterlockError as refusal:
        report["email_refused"] = str(refusal)
        return
    message_id = send_report(
        gatekeeper or ApiGatekeeper(config.rate_limits),
        email_cfg["recipient"],
        f"P2P league report - {config.group_id} - {report['outcome']}",
        "Automated end-of-game report (rule 32). JSON artifacts attached.",
        [Path(p) for p in report["artifacts"]],
    )
    report["email_message_id"] = message_id
