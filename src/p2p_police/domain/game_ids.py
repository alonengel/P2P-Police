"""Game identifiers and the Table-20 artifact filenames (parity-locked).

Filenames derive from game_id + sub-game number so files from different
games can never mix (Appendix VI Table 20 remark).
"""

import uuid


def build_game_id(group_a: str, group_b: str) -> str:
    """Stable, order-independent pairing id: sorted groups joined by -vs-."""
    first, second = sorted([group_a, group_b])
    return f"{first}-vs-{second}"


def new_game_uid() -> str:
    """One shared uid stamped into all four artifacts of a game."""
    return uuid.uuid4().hex


def declaration_name(game_id: str) -> str:
    return f"declaration_{game_id}.json"


def config_name(game_id: str, sub_game: int) -> str:
    return f"config_{game_id}_g{sub_game:02d}.json"


def log_name(game_id: str, sub_game: int) -> str:
    return f"log_{game_id}_g{sub_game:02d}.json"


def result_name(game_id: str) -> str:
    return f"result_{game_id}.json"
