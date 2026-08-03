"""The four game artifacts (rulebook ch. 9.3.3, Appendix VI Table 20).

declaration (pre-game fixed data, sealed), config (the agreed locked terms),
log (move-by-move commit-reveal records - the replay verifier's input), and
result (the league-scored summary emailed to the lecturer). All four share
one game_uid; filenames derive from game_id so games never mix.
"""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from p2p_police.domain import game_ids
from p2p_police.domain.negotiation import config_sha256
from p2p_police.report.code_identity import git_commit_hash  # noqa: F401 (re-export)

SCHEMA = "p2p-police-artifacts"
SCHEMA_VERSION = "1.00"


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def consensus_signature(body: dict) -> str:
    """SHA-256 over the report body in the reference's SETTLEMENT form (ADR-0004):
    sorted keys, native UTF-8, DEFAULT (spaced) separators — deliberately NOT the
    compact commit-reveal canonical. Verification: pop the signature key,
    re-serialize spaced, re-hash (sign-then-insert)."""
    spaced = json.dumps(body, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(spaced.encode("utf-8")).hexdigest()


def build_declaration(*args, **kwargs) -> dict:
    """Book-attached shape — lives in report/declaration.py (150-line cap);
    re-exported here so the sdk keeps one artifacts facade."""
    from p2p_police.report.declaration import build_declaration as _build

    return _build(*args, **kwargs)


def symmetric_outcome_signature(game_id: str, sub_games: list,
                                aggregate: dict) -> str:
    """The reference's mutual-agreement preimage, verbatim: hash ONLY the
    symmetric outcome (game_id + aggregate + rows trimmed to number/roles/
    result/winner/score) — never per-peer tokens or wall-clock timestamps,
    so BOTH peers' values are byte-identical by construction (ADR-0012;
    verified against imreeyal's production value, 2026-08-03)."""
    rows = [{"sub_game_number": e["sub_game_number"], "roles": e["roles"],
             "result": e["result"], "winner_group": e["winner_group"],
             "score": e["score"]} for e in sub_games]
    return consensus_signature({"game_id": game_id, "aggregate": aggregate,
                                "sub_games": rows})


def _base(kind: str, game_id: str, game_uid: str, config) -> dict:
    repos = config.private["game"].get("repos", {})
    return {
        "_schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "report_type": kind,
        "game_id": game_id,
        "game_uid": game_uid,
        "links": {"cop": repos.get("cop", ""), "thief": repos.get("thief", "")},
    }


def build_config_artifact(config, game_id: str, game_uid: str, sub_game: int) -> dict:
    """FLAT agreed sections (both course example sets carry the terms at top
    level, never nested; Imree diff 2026-08-03) — the shared file's own
    _schema/_note/schema_version win over the artifact envelope's."""
    doc = _base("config", game_id, game_uid, config)
    doc.update(config.shared)
    doc.update(
        {
            "sub_game_number": sub_game,
            "config_name": game_ids.config_name(game_id, sub_game),
            "config_sha256": config_sha256(config.shared),
        }
    )
    return doc


def build_log(config, game_id: str, game_uid: str, sub_game: int, report: dict,
              own_records: list[dict], their_records: list[dict]) -> dict:
    doc = _base("log", game_id, game_uid, config)
    doc.update(
        {
            "sub_game_number": sub_game,
            # github_commit: the EMITTING repo's code identity — sub-games
            # alternate role repos, so the series report reads each row's
            # own-side commit from its log (book-attached 4-final-result:
            # commits VARY per sub-game; one-hash-on-six-rows was the bug)
            "summary": dict(report, group_id=config.group_id, ended_at=utc_now(),
                            github_commit=git_commit_hash()),
            "records": own_records,          # payload + nonce + commit (post-game reveal)
            "opponent_records": their_records,  # payload + commit (their nonces arrive in audit)
        }
    )
    return doc


def _winner_group(config, report: dict) -> str:
    """Which group won this sub-game (A.7 result field). Capture -> the cop
    side's group; survival -> the thief side's; technical loss -> the side
    that did NOT cause it (score stays 0/0 either way, App ו): ours by
    default, theirs when the breach is proven from the rival's own message
    (breach_by) - a cheater must never be credited as winner_group."""
    opponent = report.get("opponent_group_id", "unknown")
    role, outcome = report.get("role", ""), report.get("outcome", "")
    if outcome == "technical_loss":
        return config.group_id if report.get("breach_by") == "opponent" else opponent
    we_won = (role == "police") == (outcome == "capture")
    return config.group_id if we_won else opponent


def build_result(config, game_id: str, game_uid: str, report: dict,
                 score: tuple[int, int], tokens_total: int) -> dict:
    from p2p_police.domain.scent import scent_model_spec

    doc = _base("result", game_id, game_uid, config)
    doc.update(
        {
            "reported_at": utc_now(),
            "group_id": config.group_id,
            "opponent_group_id": report.get("opponent_group_id", "unknown"),
            "winner_group": _winner_group(config, report),
            "mcp_servers": config.private["game"].get("mcp_servers", {}),
            "github_commit": git_commit_hash(),
            "outcome": report["outcome"],
            "turns_completed": report["turns_completed"],
            "audit": report.get("audit", ""),
            "end_state_digest": report["end_state_digest"],
            "digest_match": report.get("digest_match", False),
            "agreement": {  # the SHA-backed mutual-agreement confirmations
                "config_sha256": config_sha256(config.shared),
                "scent_model_sha256": config_sha256(scent_model_spec()),
            },
            "score": {"cop": score[0], "thief": score[1]},
            "tokens_total": tokens_total,
        }
    )
    doc["consensus_signature"] = consensus_signature(doc)  # sign-then-insert
    return doc


def emit(doc: dict, directory: Path, filename: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / filename
    path.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path
