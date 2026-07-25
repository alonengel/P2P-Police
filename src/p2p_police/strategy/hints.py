"""Verbal hints: free-language sentences over a structured claim (ch. 6.5).

The MOVE is always pure Python; hints only talk. The template provider is the
book's default (0 tokens). Every provider path — template today, LLM modes
later — passes through enforce_word_limit (hint_max_words applies to ALL).
"""

import json
import random
from pathlib import Path

from p2p_police.domain.primitives import Cell, Move

GAZETTEER_PATH = Path(__file__).resolve().parents[3] / "config" / "gazetteer.json"
_gazetteer_cache: dict | None = None

# Deterministic templates per claimed direction: free language, parseable by
# US because we authored them (rivals only ever see the text).
TEMPLATES: dict[str, list[str]] = {
    "N": ["Heading uptown, try to keep up.", "North wind suits me fine today."],
    "S": ["Slipping south past the docks.", "Downtown crowds hide me well."],
    "E": ["East side alleys are friendly tonight.", "Chasing sunrise eastward."],
    "W": ["West end, catch me if you can.", "Fading west into the park shadows."],
    "STAY": ["Comfortable right where I am.", "Not moving an inch, promise."],
}


def enforce_word_limit(text: str, hint_max_words: int) -> str:
    """Hard cap from the signed config — applies to every provider (rule)."""
    words = text.split()
    return " ".join(words[:hint_max_words])


def build_hint(
    actual_move: Move, tell_truth: bool, hint_max_words: int, rng: random.Random,
    decoy: str | None = None,
) -> tuple[str, str, bool]:
    """Compose (text, claimed_direction, intent_is_truth).

    A lie claims a direction different from the actual move — random by
    default, or the caller's chosen `decoy` (the deception policy aims it
    away from the true heading). The intent flag is sealed inside the commit
    (ch. 5) so 'lying truthfully' is impossible; an invalid or truth-equal
    decoy falls back to the random pick rather than leak the real heading.
    """
    actual = actual_move.name
    if tell_truth:
        claim = actual
    elif decoy and decoy != actual and decoy in TEMPLATES:
        claim = decoy
    else:
        claim = rng.choice([d for d in TEMPLATES if d != actual])
    text = enforce_word_limit(rng.choice(TEMPLATES[claim]), hint_max_words)
    return text, claim, tell_truth


# Free-text direction vocabulary: real rivals speak prose, not our templates.
DIRECTION_WORDS: dict[str, tuple[str, ...]] = {
    "N": ("north", "uptown", "upward", "up ", "top"),
    "S": ("south", "downtown", "downward", "down ", "bottom", "docks"),
    "E": ("east", "sunrise", "right side", "rightward"),
    "W": ("west", "sunset", "left side", "leftward"),
    "STAY": ("stay", "not moving", "right where", "standing still", "same spot",
             "not an inch", "holding"),
}


def parse_claim(text: str) -> str | None:
    """Recover a directional claim from ANY hint text.

    Fast path: our own templates. Fallback: keyword vocabulary over free
    prose (league rivals speak their own language). Ambiguous or opaque
    text yields None - belief then rests on scent alone, never on a guess.
    """
    for claim, sentences in TEMPLATES.items():
        if text in sentences:  # exact template match only - substrings lie
            return claim
    lowered = f" {text.lower()} "
    matches = {
        claim
        for claim, words in DIRECTION_WORDS.items()
        if any(word in lowered for word in words)
    }
    return matches.pop() if len(matches) == 1 else None


def _gazetteer_entries() -> dict:
    """config/gazetteer.json landmark table (private, per-peer). Cached;
    a missing file simply disables the tier (parse falls through to None)."""
    global _gazetteer_cache
    if _gazetteer_cache is None:
        _gazetteer_cache = (
            json.loads(GAZETTEER_PATH.read_text(encoding="utf-8"))
            if GAZETTEER_PATH.is_file() else {"landmarks": {}}
        )
    return _gazetteer_cache["landmarks"]


def landmark_region(text: str, grid_size: int, entries: dict | None = None) -> set[Cell] | None:
    """Third parsing tier (after templates and direction words): place-name
    talk -> the board region the private gazetteer maps it to.

    A UNIQUE landmark mention wins; ambiguous or unknown talk yields None —
    belief then rests on scent alone, never on a guess. Regions are
    fractional row/col bands scaled by cell-center membership, so no grid
    size is hardcoded. INBOUND parsing only: our own hints stay free
    language (rule 27 stays untouched on the wire)."""
    lowered = f" {text.lower()} "
    matched = [entry for entry in (entries if entries is not None else _gazetteer_entries())
               .values() if any(alias in lowered for alias in entry["aliases"])]
    if len(matched) != 1:
        return None
    (row_lo, row_hi), (col_lo, col_hi) = matched[0]["rows"], matched[0]["cols"]
    region = {
        (row, col)
        for row in range(grid_size)
        for col in range(grid_size)
        if row_lo <= (row + 0.5) / grid_size < row_hi
        and col_lo <= (col + 0.5) / grid_size < col_hi
    }
    return region or None
