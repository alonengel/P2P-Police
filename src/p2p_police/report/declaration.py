"""The pre-game declaration artifact — book-attached example shape (split
from report/artifacts.py for the 150-code-line cap; ADR-0012 records the
example-set precedence).

Symmetric groups (group_1/group_2 ORDERED BY group_id, so both teams'
declarations agree on which column is which), game start/end times and the
token cap at top level, per-group identity incl. hardware. Our column is
config truth; the rival's is what its handshake identity declared — nobody
can source the opponent locally. Signature format stays per-team (documented
divergence): ours is sha256 over the canonical group block.
"""

from p2p_police.domain import game_ids
from p2p_police.domain.negotiation import config_sha256
from p2p_police.report.code_identity import git_commit_hash
from p2p_police.shared.sysinfo import hardware_spec
from p2p_police.shared.version import CODE_VERSION

TIMEZONE = "Asia/Jerusalem"


def _links(game_id: str) -> dict:
    return {
        "declaration": game_ids.declaration_name(game_id),
        "config": f"config_{game_id}_g<NN>.json",
        "log": f"log_{game_id}_g<NN>.json",
        "result": game_ids.result_name(game_id),
    }


def _our_group(config, games_played: int) -> dict:
    game = config.private["game"]
    spec = hardware_spec()
    block = {
        "group_id": config.group_id,
        "group_name": game.get("group_name", config.group_id),
        "members": game.get("members", []),
        "repos": game.get("repos", {}),
        "mcp_servers": game.get("mcp_servers", {}),
        "llm_model": (config.private.get("llm", {}).get("model")
                      or config.private.get("trash_talk", {})
                      .get("provider", "template")),
        "hardware_spec": spec,
        "hardware_spec_sha256": config_sha256(spec),
        "code_version": CODE_VERSION,
        "github_commit": git_commit_hash(),
        "counted_games_played": games_played,
    }
    block["signature"] = "sha256:" + config_sha256(block)  # sign-then-insert
    return block


def _their_group(opponent: dict | None) -> dict:
    identity = (opponent or {}).get("identity") or {}
    group_id = ((opponent or {}).get("group_id")
                or identity.get("group_id", "unknown"))
    return {
        "group_id": group_id,
        "group_name": identity.get("group_name", group_id),
        "members": identity.get("members", []),
        "repos": identity.get("repos", {}),
        "mcp_servers": identity.get("mcp_servers", {}),
        "llm_model": identity.get("llm_model", "undeclared"),
        # foreign identity blocks have shipped the spec under either key
        "hardware_spec": identity.get("hardware_spec") or identity.get("spec", {}),
        "hardware_spec_sha256": (opponent or {}).get("hardware_spec_sha256", ""),
        "github_commit": identity.get("github_commit", "unknown"),
        "counted_games_played": int(identity.get("counted_games_played", 0)),
        "signature": identity.get("signature", "undeclared"),
    }


def build_declaration(config, game_id: str, game_uid: str, games_played: int,
                      opponent: dict | None = None,
                      started_at: str | None = None) -> dict:
    """The book-attached 1-pre-game-declaration key set, plus our additive
    evidence fields (github_commit, counted_games_played, consensus seal)."""
    from p2p_police.report.artifacts import (  # local: artifacts re-exports us
        SCHEMA,
        SCHEMA_VERSION,
        consensus_signature,
        utc_now,
    )

    ours, theirs = _our_group(config, games_played), _their_group(opponent)
    pair = sorted((ours, theirs), key=lambda g: str(g.get("group_id")))
    budget = config.shared["network_and_league"]["token_budget_per_series"]
    doc = {
        "_schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "report_type": "declaration",
        "declaration_type": "pre_game_declaration",
        "game_id": game_id,
        "game_uid": game_uid,
        "links": _links(game_id),
        "timezone": TIMEZONE,
        "game_started_at": started_at,
        "game_ended_at": utc_now(),
        "declared_at": utc_now(),
        "num_sub_games": int(config.shared["network_and_league"]["num_games"]),
        "max_tokens_per_game": budget,
        "token_budget_per_series": budget,
        "groups": {"group_1": pair[0], "group_2": pair[1]},
    }
    doc["consensus_signature"] = consensus_signature(doc)  # sign-then-insert
    return doc
