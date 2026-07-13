"""Wire protocol for the geometric stage (PRD 02) — parity-locked.

Both peers must build, parse and APPLY turn messages identically, and must
derive the same end-state digest, or lockstep silently breaks. Serial
coordinates are the book's deliberate stage-2 shape; free language replaces
hints in stage 4 (rule 27 governs real games).
"""

import hashlib
import json

from p2p_police.domain.engine import GameEngine
from p2p_police.domain.errors import GameRuleError
from p2p_police.domain.primitives import Cell, Move, Role


def move_action(move: Move) -> dict:
    return {"type": "move", "move": move.name}


def barrier_action(cell: Cell) -> dict:
    return {"type": "barrier", "cell": [cell[0], cell[1]]}


def turn_message(
    turn_index: int, actor: Role, action: dict, hint: str | None = None
) -> dict:
    message = {"turn": turn_index, "actor": actor.value, "action": action}
    if hint is not None:
        message["hint"] = hint
    return message


def parse_turn_message(payload: dict) -> tuple[int, Role, dict]:
    """Validate and unpack an incoming turn message.

    Raises GameRuleError on malformed payloads — a garbled message from the
    opponent is a protocol failure, never something to guess around.
    """
    try:
        turn_index = int(payload["turn"])
        actor = Role(payload["actor"])
        action = payload["action"]
        kind = action["type"]
    except (KeyError, TypeError, ValueError) as error:
        raise GameRuleError(f"malformed turn message {payload!r}: {error}") from error
    if kind == "move":
        if action.get("move") not in Move.__members__:
            raise GameRuleError(f"unknown move in turn message: {action!r}")
    elif kind == "barrier":
        cell = action.get("cell")
        if not (isinstance(cell, list) and len(cell) == 2):
            raise GameRuleError(f"malformed barrier cell in turn message: {action!r}")
    else:
        raise GameRuleError(f"unknown action type in turn message: {kind!r}")
    hint = payload.get("hint")
    if hint is not None and not isinstance(hint, str):
        raise GameRuleError(f"malformed hint in turn message: {hint!r}")
    return turn_index, actor, action


def apply_action(engine: GameEngine, actor: Role, action: dict) -> None:
    """Apply a parsed action to the local engine — the single application
    path BOTH peers use, so replicated engines stay in lockstep."""
    if action["type"] == "barrier":
        if actor is not Role.POLICE:
            raise GameRuleError("only the police may place barriers")
        engine.police_place_barrier((action["cell"][0], action["cell"][1]))
    elif actor is Role.POLICE:
        engine.police_move(Move[action["move"]])
    else:
        engine.thief_move(Move[action["move"]])


def end_state_digest(engine: GameEngine) -> str:
    """Canonical SHA-256 of the final game state (positions, barriers, turns,
    outcome). Matching digests prove the two replicated engines agreed."""
    state = {
        "positions": {role.value: list(cell) for role, cell in engine.positions.items()},
        "barriers": sorted([list(c) for c in engine.board.barriers]),
        "turns_completed": engine.turns_completed,
        "outcome": engine.outcome.value,
    }
    canonical = json.dumps(state, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
