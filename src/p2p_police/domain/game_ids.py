"""Game identifiers and the Table-20 artifact filenames (parity-locked).

Filenames derive from game_id + sub-game number so files from different
games can never mix (Appendix VI Table 20 remark). The game_uid follows the
official reference construction (ADR-0004): a pure function of the agreed
terms + the two group ids, so BOTH peers compute the identical uid with no
extra round-trip and all eight artifacts (four per team) share it.
"""

import hashlib
import uuid

from p2p_police.domain.crypto import canonical


def build_game_id(group_a: str, group_b: str) -> str:
    """Stable, order-independent pairing id: sorted groups joined by -vs-."""
    first, second = sorted([group_a, group_b])
    return f"{first}-vs-{second}"


def derive_game_uid(terms: dict, group_a: str, group_b: str) -> str:
    """Shared uid both peers derive independently (reference form):
    UUID over SHA256(canonical(terms) | sorted group ids), first 16 bytes."""
    seed = f"{canonical(terms)}|{'|'.join(sorted([group_a, group_b]))}"
    return str(uuid.UUID(bytes=hashlib.sha256(seed.encode("utf-8")).digest()[:16]))


def declaration_name(game_id: str) -> str:
    return f"declaration_{game_id}.json"


def config_name(game_id: str, sub_game: int) -> str:
    return f"config_{game_id}_g{sub_game:02d}.json"


def log_name(game_id: str, sub_game: int) -> str:
    return f"log_{game_id}_g{sub_game:02d}.json"


def result_name(game_id: str) -> str:
    return f"result_{game_id}.json"
