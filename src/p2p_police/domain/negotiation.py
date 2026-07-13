"""Config identity and pre-game agreement (rulebook ch. 3/5, rules 11-12).

Both peers must load byte-equivalent shared terms; the identity is proven by
exchanging a SHA-256 over the CANONICAL serialization (sorted keys, tight
separators) so formatting differences never mask real disagreement. The
Appendix-VI mandatory table is enforced here: FIXED values must match exactly,
MINIMUMS may only be raised. Parity-locked with the twin repo.
"""

import hashlib
import json

from p2p_police.domain.errors import GameRuleError

# Appendix VI: parameters whose values are FIXED - deviation disqualifies.
FIXED_TERMS: dict[str, object] = {
    "board_and_agents.num_agents": 2,
    "pheromones.pheromone_center_intensity": 0.9,
    "pheromones.pheromone_decay": 0.1,
    "pheromones.pheromone_grid_size": 5,
    "scoring.capture_cop": 20,
    "scoring.capture_thief": 5,
    "scoring.survival_cop": 5,
    "scoring.survival_thief": 10,
    "scoring.tie_score": 2,
    "scoring.technical_loss": 0,
    "movement_and_barriers.move_set": ["N", "S", "E", "W", "STAY"],
    "network_and_league.diversity_reward": 10,
    "network_and_league.min_games_to_pass": 2,
    "network_and_league.max_games_per_team": 10,
}

# Appendix VI: MINIMUMS - negotiable upward only (rule 12).
MINIMUM_TERMS: dict[str, int] = {
    "board_and_agents.grid_size": 7,
    "movement_and_barriers.max_barriers": 14,
    "movement_and_barriers.max_moves": 35,
    "movement_and_barriers.survival_threshold": 35,
    "rate_limiter_gatekeeper.requests_per_minute": 30,
    "rate_limiter_gatekeeper.concurrent_requests": 2,
    "rate_limiter_gatekeeper.retry_backoff_sec": 5,
    "rate_limiter_gatekeeper.max_retries": 3,
    "rate_limiter_gatekeeper.queue_depth": 100,
}

# The intra-round order both sides must explicitly agree on (PRD 01/02).
COMMIT_ORDER = "police_first"


def _lookup(shared: dict, dotted: str) -> object:
    node: object = shared
    for key in dotted.split("."):
        if not isinstance(node, dict) or key not in node:
            raise GameRuleError(f"shared terms missing mandatory key '{dotted}'")
        node = node[key]
    return node


def canonical_terms(shared: dict) -> str:
    """Canonical JSON of the shared terms (sorted keys, tight separators)."""
    return json.dumps(shared, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def config_sha256(shared: dict) -> str:
    """The identity both peers exchange and must match byte-for-byte (rule 11)."""
    return hashlib.sha256(canonical_terms(shared).encode("utf-8")).hexdigest()


def validate_shared_terms(shared: dict) -> None:
    """Enforce the Appendix-VI table on loaded shared terms (rule 12).

    Raises GameRuleError on a changed FIXED value or a lowered MINIMUM -
    playing on such terms disqualifies the scoring.
    """
    for dotted, expected in FIXED_TERMS.items():
        actual = _lookup(shared, dotted)
        if actual != expected:
            raise GameRuleError(f"FIXED term '{dotted}' must be {expected}, got {actual}")
    for dotted, floor in MINIMUM_TERMS.items():
        actual = _lookup(shared, dotted)
        if not isinstance(actual, int | float) or actual < floor:
            raise GameRuleError(f"MINIMUM term '{dotted}' may not drop below {floor}, got {actual}")


def build_agreement(shared: dict, group_id: str) -> dict:
    """The negotiate payload sent to the opponent before any move."""
    validate_shared_terms(shared)
    return {
        "group_id": group_id,
        "config_sha256": config_sha256(shared),
        "commit_order": COMMIT_ORDER,
        "schema_version": _lookup(shared, "schema_version"),
    }


def verify_agreement(mine: dict, theirs: dict) -> None:
    """Fail-fast symmetry check before the first move (rule 11).

    Raises GameRuleError on sha mismatch (different physics), commit-order
    mismatch (guaranteed deadlock), or schema mismatch.
    """
    for field in ("config_sha256", "commit_order", "schema_version"):
        if mine.get(field) != theirs.get(field):
            raise GameRuleError(
                f"agreement mismatch on '{field}': "
                f"mine={mine.get(field)!r} theirs={theirs.get(field)!r}"
            )
