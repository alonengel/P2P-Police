"""Opaque hint mode: free language that leaks nothing (rule 27 + ch.4).

Our shipped templates narrate the heading — which hands a fleeing thief the
one thing it needs to stay away from us. The thief twin learned this the hard
way in the 2026-08-11 series; the cop side has the same leak and its own
(deliberately different) taunt voice. Free language is required by rule 27;
informative language is not.
"""

import random
from pathlib import Path

from p2p_police.strategy.hints import TAUNTS, TEMPLATES
from p2p_police.strategy.talk_providers import TalkChain

DIRECTION_WORDS = ("north", "south", "east", "west", "uptown", "downtown",
                   "sunrise", "docks", "left", "right", "up", "down",
                   "staying", "moving", "not moving", "right where")


def _chain(opaque: bool) -> TalkChain:
    return TalkChain(None, 1, "New York", 15, random.Random(0), opaque=opaque)


def test_taunts_never_name_a_direction() -> None:
    for line in TAUNTS:
        lowered = line.lower()
        for word in DIRECTION_WORDS:
            assert word not in lowered, f"{line!r} leaks {word!r}"


def test_taunts_stay_inside_the_signed_word_cap() -> None:
    for line in TAUNTS:
        assert len(line.split()) <= 15, f"{line!r} is over the cap"


def test_opaque_mode_renders_the_same_text_for_every_claim() -> None:
    """The text must be independent of our real heading — otherwise a rival
    could invert it. Same seed, every claim, identical output."""
    rendered = {claim: _chain(True).render(claim, step=1) for claim in TEMPLATES}
    assert len(set(rendered.values())) == 1, rendered
    assert next(iter(rendered.values())) in TAUNTS


def test_candid_mode_is_untouched_and_still_the_default() -> None:
    """Friendlies keep the informative voice; only the counted overlay flips."""
    text = _chain(False).render("S", step=1)
    assert text in TEMPLATES["S"]
    from p2p_police.shared.config import Config
    chain = TalkChain(None, 1, "NY", 15, random.Random(0))
    assert chain.opaque is False
    assert "hint_mode" not in str(Config.load("config").shared)  # never signed


def test_cop_voice_is_not_the_thief_twins_voice() -> None:
    """Role policies must differ between the repos (ADR-0001 iron rule):
    duplicated STATIC physics is deliberate, duplicated PERSONALITY is not."""
    thief_bank = (Path(__file__).resolve().parents[4] / "P2P-Thief" / "src"
                  / "p2p_thief" / "strategy" / "hints.py")
    if not thief_bank.is_file():   # sibling absent (CI checkout of one repo)
        return
    text = thief_bank.read_text(encoding="utf-8")
    for line in TAUNTS:
        assert line not in text, f"cop taunt {line!r} is copied from the thief"
