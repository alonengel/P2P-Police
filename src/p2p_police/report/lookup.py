"""Resolve a log artifact's sibling CONFIG artifact and re-simulate physics.

Rule 20 requires the log to enable replay + verification for a third party.
Two helpers make that self-contained: `terms_for_log` finds the game's own
archived config (never assume defaults for negotiated terms), and
`recompute_digest` rebuilds a fresh engine from those terms, re-applies every
sealed action, and returns the recomputed end-state digest - turning
"records not tampered" into "records not tampered AND physics-legal".
"""

import json
from pathlib import Path

from p2p_police.domain import game_ids, protocol
from p2p_police.domain.engine import GameEngine
from p2p_police.domain.primitives import Role
from p2p_police.domain.rules import RuleSet


def terms_for_log(doc: dict, log_path: str | Path) -> dict | None:
    """The agreed terms archived for THIS game (config/games/), or None."""
    game_id = doc.get("game_id", "")
    sub_game = int(doc.get("sub_game_number", 1))
    name = game_ids.config_name(game_id, sub_game)
    log_dir = Path(log_path).resolve().parent
    for base in (log_dir.parent, Path.cwd()):
        candidate = base / "config" / "games" / name
        if candidate.is_file():
            artifact = json.loads(candidate.read_text(encoding="utf-8"))
            return artifact.get("terms")
    return None


def build_engine(terms: dict) -> GameEngine:
    board = terms["board_and_agents"]
    moves = terms["movement_and_barriers"]
    scent = terms["pheromones"]
    return GameEngine(
        int(board["grid_size"]),
        tuple(board["cop_start"]),
        tuple(board["thief_start"]),
        RuleSet(int(moves["max_barriers"]), int(moves["max_moves"]),
                int(moves["survival_threshold"])),
        center_intensity=scent["pheromone_center_intensity"],
        decay=scent["pheromone_decay"],
        kernel_size=scent["pheromone_grid_size"],
    )


def recompute_digest(doc: dict, terms: dict) -> str:
    """Re-apply every sealed action on a fresh engine; raises on any illegal
    move (an illegal logged move IS tampering evidence), returns the digest."""
    engine = build_engine(terms)
    payloads = [r["payload"] for r in doc.get("records", [])]
    payloads += [r["payload"] for r in doc.get("opponent_records", [])]
    payloads.sort(key=lambda p: p["step"])
    for payload in payloads:
        protocol.apply_action(engine, Role(payload["role"]), payload["action"])
    return protocol.end_state_digest(engine)


def geometry(terms: dict | None) -> tuple[int, tuple, tuple]:
    """(grid, cop_start, thief_start) from terms; book defaults otherwise."""
    if terms is None:
        return 7, (0, 0), (3, 3)
    board = terms["board_and_agents"]
    return (int(board["grid_size"]), tuple(board["cop_start"]),
            tuple(board["thief_start"]))
