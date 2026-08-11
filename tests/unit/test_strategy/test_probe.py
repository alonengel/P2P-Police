"""Probe cop: bearing approach, ring stalk, no walls ever."""

import random
from types import SimpleNamespace

from p2p_police.domain.belief import BeliefMap
from p2p_police.domain.engine import GameEngine
from p2p_police.domain.primitives import Role
from p2p_police.domain.rules import RuleSet
from p2p_police.strategy.brain_base import resolve_brain
from p2p_police.strategy.probe import ProbeCopBrain

RULES = RuleSet(max_barriers=14, max_moves=35, survival_threshold=35)


def _cfg(bearing=(1, 0), gap=2, turns=2):
    return SimpleNamespace(private={"strategy": {
        "police_class": "p2p_police.strategy.probe:ProbeCopBrain",
        "probe": {"bearing": list(bearing), "stalk_gap": gap,
                  "stalk_turns": turns}}})


def _belief_on(cell) -> BeliefMap:
    belief = BeliefMap(7)
    belief.observe_claimed_cell(cell)
    return belief


def test_probe_never_places_walls_and_always_moves_legally() -> None:
    from p2p_police.domain.primitives import Move
    engine = GameEngine(7, (0, 0), (6, 6), RULES)
    brain = ProbeCopBrain(Role.POLICE, random.Random(0), config=_cfg())
    for _ in range(20):
        action = brain.decide(engine, _belief_on((6, 6)))
        assert action["type"] == "move"              # a probe maps, never traps
        engine.police_move(Move[action["move"]])
        if engine.outcome.value != "ongoing":
            break                                    # stalked all the way in
        engine.thief_move(Move.STAY)
    assert len(engine.board.barriers) == 0


def test_probe_stalks_on_the_ring_before_tightening() -> None:
    engine = GameEngine(7, (4, 6), (6, 6), RULES)    # already at BFS gap 2
    brain = ProbeCopBrain(Role.POLICE, random.Random(0), config=_cfg(gap=2, turns=3))
    stays = sum(brain.decide(engine, _belief_on((6, 6)))["move"] == "STAY"
                for _ in range(3))
    assert stays == 3                                # held the ring, then tightens


def test_probe_is_seam_selectable() -> None:
    picked = resolve_brain(_cfg(bearing=(0, 1)), Role.POLICE, random.Random(0))
    assert type(picked) is ProbeCopBrain
    assert picked.bearing == (0, 1)
