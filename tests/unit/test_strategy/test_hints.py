"""Hint tests: word cap enforced on every path, lies never claim the actual
direction, intent flag travels with the hint, templates parse back."""

import random

import pytest

from p2p_police.domain.primitives import Move
from p2p_police.strategy.hints import TEMPLATES, build_hint, enforce_word_limit, parse_claim


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
