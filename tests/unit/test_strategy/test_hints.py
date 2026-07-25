"""Hint tests: word cap enforced on every path, lies never claim the actual
direction, intent flag travels with the hint, templates parse back, and
place-name talk resolves through the private gazetteer tier."""

import random

import pytest

from p2p_police.domain.primitives import Move
from p2p_police.strategy.hints import (
    TEMPLATES,
    build_hint,
    enforce_word_limit,
    landmark_region,
    parse_claim,
)


def test_word_limit_truncates_hard() -> None:
    assert enforce_word_limit("one two three four five", 3) == "one two three"


@pytest.mark.parametrize("seed", range(10))
def test_hint_never_exceeds_limit(seed: int) -> None:
    text, _, _ = build_hint(Move.N, tell_truth=bool(seed % 2), hint_max_words=15,
                            rng=random.Random(seed))
    assert len(text.split()) <= 15


def test_truthful_hint_claims_the_actual_move() -> None:
    _, claim, truth = build_hint(Move.E, True, 15, random.Random(1))
    assert claim == "E" and truth


@pytest.mark.parametrize("seed", range(10))
def test_lying_hint_never_claims_the_actual_move(seed: int) -> None:
    _, claim, truth = build_hint(Move.S, False, 15, random.Random(seed))
    assert claim != "S" and not truth


def test_all_templates_parse_back_to_their_claim() -> None:
    for claim, sentences in TEMPLATES.items():
        for sentence in sentences:
            assert parse_claim(sentence) == claim


def test_unknown_free_text_yields_no_claim() -> None:
    assert parse_claim("You will never find me, copper!") is None


def test_free_text_directions_parse() -> None:
    assert parse_claim("You'll never catch me heading north, copper!") == "N"
    assert parse_claim("Vanishing into the sunset...") == "W"
    assert parse_claim("I am not moving an inch today") == "STAY"


def test_ambiguous_or_opaque_free_text_yields_none() -> None:
    assert parse_claim("Going north then doubling back south!") is None
    assert parse_claim("The pigeons know where I am.") is None


def test_landmark_talk_resolves_to_a_board_region() -> None:
    """Place-name prose that the direction tier cannot read (parse_claim is
    None) resolves through config/gazetteer.json into a cell region."""
    text = "Salt air by the harbor suits me fine."
    assert parse_claim(text) is None  # direction-blind without the gazetteer
    region = landmark_region(text, 7)
    assert region and all(0 <= r < 7 and 0 <= c < 7 for r, c in region)
    assert region == {(r, c) for r in (4, 5, 6) for c in range(7)}  # south band


def test_landmark_regions_scale_with_grid_size() -> None:
    """Fractional bands, cell-center membership: no grid size is hardcoded."""
    for grid in (5, 7, 9, 11):
        region = landmark_region("Meet me at the old market stalls.", grid)
        assert region
        assert all(0 <= r < grid and 0 <= c < grid for r, c in region)
        assert len(region) < grid * grid  # a landmark is never the whole board


def test_unknown_or_ambiguous_landmarks_yield_none() -> None:
    """Never guess: unknown places and multi-landmark talk stay None (the
    belief then rests on scent alone, exactly like opaque direction talk)."""
    assert landmark_region("You will never find my hideout.", 7) is None
    assert landmark_region("Between the harbor and the old market.", 7) is None


def test_landmark_tier_uses_injected_gazetteer_entries() -> None:
    entries = {"lair": {"aliases": ["lair"], "rows": [0.0, 0.5], "cols": [0.5, 1.0]}}
    region = landmark_region("back to my lair", 4, entries)
    assert region == {(0, 2), (0, 3), (1, 2), (1, 3)}
    assert landmark_region("back to my lair", 4, {}) is None
