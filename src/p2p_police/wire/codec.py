"""Reference-v3 wire codec: ONE TurnMessage per half-turn (demo shape).

Keys follow the official demo protocol — step / sender / hint / smell_grid /
commit / timestamp plus the optional public declarations (barrier_placed,
capture_claim, claim_response, win_claim). The move is SEALED inside
`commit` and revealed only at the end-of-game audit (nonce AND payload stay
secret until then, rule 18); the sender's position has NO field in this
shape, which is the structural hidden-information guarantee. The key set is
CLOSED: an unknown key is rejected, so a position can never ride along.
"""

from datetime import UTC, datetime

from p2p_police.domain.errors import GameRuleError
from p2p_police.domain.primitives import Role

REQUIRED_KEYS = ("step", "sender", "hint", "smell_grid", "commit", "timestamp")
OPTIONAL_KEYS = ("barrier_placed", "capture_claim", "claim_response", "win_claim")
FINAL_CAUGHT_HINT = "You got me — fair catch."  # demo protocol's mandatory closure


def now_iso() -> str:
    """Real-time ISO-8601 stamp (book: mandatory per move)."""
    return datetime.now(UTC).isoformat()


def serialize_scent(field) -> dict:
    """ScentField -> sparse {"r,c": intensity}; zero cells stay off the wire."""
    grid = field.values()
    return {
        f"{row},{col}": grid[row][col]
        for row in range(len(grid))
        for col in range(len(grid))
        if grid[row][col] > 0.0
    }


def build_turn_message(
    step: int,
    sender: str,
    hint: str,
    smell_grid: dict,
    commit: str,
    *,
    barrier_placed: list | None = None,
    capture_claim: list | None = None,
    claim_response: dict | None = None,
    win_claim: dict | None = None,
) -> dict:
    """Everything one peer tells the other about its turn — and nothing more."""
    return {
        "step": step,
        "sender": sender,
        "hint": hint,
        "smell_grid": smell_grid,
        "commit": commit,
        "timestamp": now_iso(),
        "barrier_placed": barrier_placed,
        "capture_claim": capture_claim,
        "claim_response": claim_response,
        "win_claim": win_claim,
    }


def _require_cell(value, name: str) -> None:
    if not (isinstance(value, list) and len(value) == 2
            and all(isinstance(part, int) for part in value)):
        raise GameRuleError(f"malformed {name} in turn message: {value!r}")


def parse_turn_message(payload: dict) -> dict:
    """Validate an incoming TurnMessage; a garbled message from the rival is
    a protocol failure, never something to guess around (rules 4-6)."""
    unknown = set(payload) - set(REQUIRED_KEYS) - set(OPTIONAL_KEYS)
    if unknown:
        raise GameRuleError(f"unknown keys in turn message: {sorted(unknown)}")
    missing = [key for key in REQUIRED_KEYS if key not in payload]
    if missing:
        raise GameRuleError(f"turn message missing fields: {missing}")
    try:
        step = int(payload["step"])
        Role(payload["sender"])
    except (TypeError, ValueError) as error:
        raise GameRuleError(f"malformed turn message {payload!r}: {error}") from error
    if step < 1:  # per-sender numbering: each side's own steps start at 1
        raise GameRuleError(f"turn message step must be >= 1, got {step}")
    if not isinstance(payload["hint"], str) or not isinstance(payload["commit"], str):
        raise GameRuleError("turn message hint/commit must be strings")
    if not isinstance(payload["smell_grid"], dict):
        raise GameRuleError("turn message smell_grid must be a mapping")
    for name in ("barrier_placed", "capture_claim"):
        if payload.get(name) is not None:
            _require_cell(payload[name], name)
    response = payload.get("claim_response")
    if response is not None:
        if not isinstance(response, dict) or "caught" not in response:
            raise GameRuleError(f"malformed claim_response: {response!r}")
        _require_cell(response.get("claim"), "claim_response.claim")
    win = payload.get("win_claim")
    if win is not None and not (isinstance(win, dict) and isinstance(win.get("type"), str)):
        raise GameRuleError(f"malformed win_claim: {win!r}")
    return {**{key: payload.get(key) for key in OPTIONAL_KEYS}, **{
        "step": step,
        "sender": payload["sender"],
        "hint": payload["hint"],
        "smell_grid": payload["smell_grid"],
        "commit": payload["commit"],
        "timestamp": payload["timestamp"],
    }}
