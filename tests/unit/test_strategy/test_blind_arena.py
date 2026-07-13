"""PRD-04 MILESTONE: the belief map, not luck, drives the moves - a cop that
only ever sees the thief's scent field and (half-lying) hints still hunts."""

import random

from p2p_police.domain import protocol
from p2p_police.domain.belief import BeliefMap
from p2p_police.domain.engine import GameEngine
from p2p_police.domain.primitives import Move, Outcome, Role
from p2p_police.domain.rules import RuleSet
from p2p_police.strategy.brain_base import RandomBrain
from p2p_police.strategy.hints import build_hint, parse_claim
from p2p_police.strategy.police_brain import PoliceBrain

RULES = RuleSet(max_barriers=14, max_moves=35, survival_threshold=35)


def play_blind(seed: int) -> Outcome:
    rng = random.Random(seed)
    engine = GameEngine(7, (0, 0), (3, 3), RULES)
    cop = PoliceBrain(Role.POLICE, rng)
    thief = RandomBrain(Role.THIEF, random.Random(seed + 500))
    belief = BeliefMap(7)
    while engine.outcome is Outcome.ONGOING:
        protocol.apply_action(engine, Role.POLICE, cop.decide(engine, belief))
        if engine.outcome is not Outcome.ONGOING:
            break
        action = thief.decide(engine)
        protocol.apply_action(engine, Role.THIEF, action)
        # the cop's senses: thief scent + a half-honest hint - never the truth
        text, _, _ = build_hint(Move[action["move"]], rng.random() < 0.5, 15, rng)
        belief.diffuse(engine.board)
        belief.observe_scent(engine.scent[Role.THIEF], engine.board)
        claim = parse_claim(text)
        if claim:
            belief.observe_hint(claim, engine.scent[Role.THIEF])
    return engine.outcome


def test_belief_driven_cop_still_captures_random_thief() -> None:
    captures = sum(play_blind(seed) is Outcome.CAPTURE for seed in range(25))
    assert captures >= 15, f"blind cop captured only {captures}/25"
