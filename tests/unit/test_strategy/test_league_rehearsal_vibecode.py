"""League rehearsal: the vibecode friendly's exact thief, replayed blind.

2026-08-08 post-mortem (g01/g03, audits Verified OK): our cop REACHED the
rival thief's cell at step 11 and never claimed. Two causes, both pinned
here: their move-echo hints ("moving s") predated the single-letter
vocabulary so the belief heard nothing, and scent alone left the landing
cell under the claim gate. The rival thief is argmax-deterministic and
open-loop — the sealed records give its exact path, so the rematch is
replayable: same moves, same hint template, and the claim must be ARMED
the moment the chase connects.
"""

import random

from p2p_police.domain import protocol
from p2p_police.domain.belief import BeliefMap
from p2p_police.domain.engine import GameEngine
from p2p_police.domain.primitives import Move, Outcome, Role
from p2p_police.domain.rules import RuleSet
from p2p_police.strategy.hints import parse_claim, parse_move_echo
from p2p_police.strategy.police_brain import PoliceBrain

RULES = RuleSet(max_barriers=14, max_moves=35, survival_threshold=35)

# The rival's sealed g01 move sequence (byte-identical in g03): three south,
# three east, then a two-cell corner oscillation to the buzzer.
VIBECODE_PATH = (["S"] * 3 + ["E"] * 3 + ["W", "E"] * 15)[:35]
OVERLAY_GATE = 0.02   # config/game.local.toml [strategy.claim] vs this rival
LEAGUE_GATE = 0.10    # committed default the g01 belief never crossed


def replay(seed: int, hint_mode: str):
    """Blind replay vs the scripted rival: (outcome, capture_step, armed).

    hint_mode mirrors perception's tiers — "echo" (motion translate, the
    fix), "region" (the pre-fix misread that pushed belief to the wrong
    board half), "none" (deaf). Engine convention is cop-first, so the
    cop's senses run one thief move BEHIND the real thief-first wire —
    a strictly harder rehearsal.
    """
    engine = GameEngine(7, (0, 0), (3, 3), RULES)
    cop, belief = PoliceBrain(Role.POLICE, random.Random(seed)), BeliefMap(7)
    step = 0
    while engine.outcome is Outcome.ONGOING and step < len(VIBECODE_PATH):
        step += 1
        action = cop.decide(engine, belief)
        mass = None
        if action["type"] == "move":
            landing = Move[action["move"]].applied_to(engine.positions[Role.POLICE])
            mass = belief.value_at(landing)
        protocol.apply_action(engine, Role.POLICE, action)
        if engine.outcome is Outcome.CAPTURE:
            return engine.outcome, step, mass
        if engine.outcome is not Outcome.ONGOING:
            break
        their_move = VIBECODE_PATH[step - 1]
        if Move[their_move] in engine.board.legal_moves(engine.positions[Role.THIEF]):
            protocol.apply_action(engine, Role.THIEF,
                                  protocol.move_action(Move[their_move]))
        hint = f"moving {their_move.lower()}"
        echo = parse_move_echo(hint) if hint_mode == "echo" else None
        if echo:
            belief.observe_motion(echo, engine.board)
        else:
            belief.diffuse(engine.board)
        belief.observe_scent(engine.scent[Role.THIEF], engine.board)
        if hint_mode == "region":
            claim = parse_claim(hint)
            if claim:
                belief.observe_hint(claim, engine.scent[Role.THIEF])
    return engine.outcome, None, None


def test_echo_hints_convert_the_corner_dance_into_an_armed_capture() -> None:
    """The rematch, rehearsed: capture must come EARLY with the claim armed
    past the LEAGUE gate — the overlay's 0.02 is then belt-and-braces."""
    for seed in range(5):
        outcome, step, mass = replay(seed, hint_mode="echo")
        assert outcome is Outcome.CAPTURE, f"seed {seed}: no capture ({outcome})"
        assert step <= 20, f"seed {seed}: capture too late (step {step})"
        assert mass is not None and mass >= LEAGUE_GATE, (
            f"seed {seed}: claim below league gate at capture (mass {mass})")
        assert mass >= OVERLAY_GATE


def test_region_misread_of_echoes_is_pinned_as_harmful() -> None:
    """Regression pin for the pre-fix behavior: reading "moving w" as a
    west-HALF region claim pushes belief off the corner camper — echo
    reading must never regress to it. Harm shows as a lost or later or
    weaker game, never as an improvement."""
    for seed in range(5):
        echo = replay(seed, hint_mode="echo")
        region = replay(seed, hint_mode="region")
        assert echo[0] is Outcome.CAPTURE
        if region[0] is Outcome.CAPTURE:
            assert echo[1] <= region[1], f"seed {seed}: region beat echo"
