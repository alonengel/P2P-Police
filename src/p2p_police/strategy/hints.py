"""Verbal hints: free-language sentences over a structured claim (ch. 6.5).

The MOVE is always pure Python; hints only talk. The template provider is the
book's default (0 tokens). Every provider path — template today, LLM modes
later — passes through enforce_word_limit (hint_max_words applies to ALL).
"""

import random

from p2p_police.domain.primitives import Move

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
    actual_move: Move, tell_truth: bool, hint_max_words: int, rng: random.Random
) -> tuple[str, str, bool]:
    """Compose (text, claimed_direction, intent_is_truth).

    A lie claims a direction different from the actual move; the intent flag
    is sealed inside the commit (ch. 5) so 'lying truthfully' is impossible.
    """
    actual = actual_move.name
    claim = actual if tell_truth else rng.choice([d for d in TEMPLATES if d != actual])
    text = enforce_word_limit(rng.choice(TEMPLATES[claim]), hint_max_words)
    return text, claim, tell_truth


def parse_claim(text: str) -> str | None:
    """Recover the direction claim from OUR template text (opponents' free
    text gets belief-weighted only when a claim is recognizable)."""
    for claim, sentences in TEMPLATES.items():
        for sentence in sentences:
            if text in sentence or sentence.startswith(text):
                return claim
    return None
