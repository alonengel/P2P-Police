"""The four game artifacts (rulebook ch. 9.3.3, Appendix VI Table 20).

declaration (pre-game fixed data, sealed), config (the agreed locked terms),
log (move-by-move commit-reveal records - the replay verifier's input), and
result (the league-scored summary emailed to the lecturer). All four share
one game_uid; filenames derive from game_id so games never mix.
"""

import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from p2p_police.domain import game_ids
from p2p_police.domain.negotiation import config_sha256
from p2p_police.shared.sysinfo import hardware_spec
from p2p_police.shared.version import CODE_VERSION

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


def git_commit_hash() -> str:
    """The exact code identity played this game (rules 24/53); best effort."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=10
        )
        return out.stdout.strip() or "unknown"
    except OSError:
        return "unknown"


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


def build_declaration(config, game_id: str, game_uid: str, games_played: int) -> dict:
    """Step-0 sealed pre-game data: identity, hardware, commit, game count."""
    doc = _base("declaration", game_id, game_uid, config)
    doc.update(
        {
            "declared_at": utc_now(),
            "group": {
                "group_id": config.group_id,
                "members": config.private["game"].get("members", []),
                "code_version": CODE_VERSION,
                "github_commit": git_commit_hash(),
                "counted_games_played": games_played,
                "hardware_spec": hardware_spec(),
                "llm_model": config.private.get("llm", {}).get("model", "template"),
            },
            "token_budget_per_series": config.shared["network_and_league"][
                "token_budget_per_series"
            ],
        }
    )
    return doc


def build_config_artifact(config, game_id: str, game_uid: str, sub_game: int) -> dict:
    doc = _base("config", game_id, game_uid, config)
    doc.update(
        {
            "sub_game_number": sub_game,
            "config_name": game_ids.config_name(game_id, sub_game),
            "config_sha256": config_sha256(config.shared),
            "terms": config.shared,
        }
    )
    return doc


def build_log(config, game_id: str, game_uid: str, sub_game: int, report: dict,
              own_records: list[dict], their_records: list[dict]) -> dict:
    doc = _base("log", game_id, game_uid, config)
    doc.update(
        {
            "sub_game_number": sub_game,
            "summary": dict(report, group_id=config.group_id, ended_at=utc_now()),
            "records": own_records,          # payload + nonce + commit (post-game reveal)
            "opponent_records": their_records,  # payload + commit (their nonces arrive in audit)
        }
    )
    return doc


def build_result(config, game_id: str, game_uid: str, report: dict,
                 score: tuple[int, int], tokens_total: int) -> dict:
    doc = _base("result", game_id, game_uid, config)
    doc.update(
        {
            "reported_at": utc_now(),
            "group_id": config.group_id,
            "github_commit": git_commit_hash(),
            "outcome": report["outcome"],
            "turns_completed": report["turns_completed"],
            "audit": report.get("audit", ""),
            "end_state_digest": report["end_state_digest"],
            "digest_match": report.get("digest_match", False),
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
