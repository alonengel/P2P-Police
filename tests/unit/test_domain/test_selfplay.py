"""PRD-01 definition of done: a full random-legal self-play game runs
crash-free to CAPTURE or SURVIVAL, within the move cap, across many seeds."""

import random

import pytest

from p2p_police.domain.engine import GameEngine
from p2p_police.domain.primitives import Move, Outcome, Role
from p2p_police.domain.rules import RuleSet

RULES = RuleSet(max_barriers=14, max_moves=35, survival_threshold=35)


def play_random_game(seed: int) -> GameEngine:
    """Random-legal agents: the cop occasionally spends a barrier, both sides
    otherwise take uniformly random legal moves."""
    rng = random.Random(seed)
    engine = GameEngine(7, (0, 0), (3, 3), RULES)
    while engine.outcome is Outcome.ONGOING:
        cop_cell = engine.positions[Role.POLICE]
        placeable = [
            c
            for c in [cop_cell] + [m.applied_to(cop_cell) for m in (Move.N, Move.S, Move.E, Move.W)]
            if engine.board.in_bounds(c) and not engine.board.is_barrier(c)
        ]
        if rng.random() < 0.2 and len(engine.board.barriers) < RULES.max_barriers and placeable:
            engine.police_place_barrier(rng.choice(placeable))
        else:
            engine.police_move(rng.choice(engine.board.legal_moves(cop_cell)))
        if engine.outcome is Outcome.ONGOING:
            thief_cell = engine.positions[Role.THIEF]
            engine.thief_move(rng.choice(engine.board.legal_moves(thief_cell)))
    return engine


@pytest.mark.parametrize("seed", range(20))
def test_random_selfplay_completes_legally(seed: int) -> None:
    engine = play_random_game(seed)
    assert engine.outcome in (Outcome.CAPTURE, Outcome.SURVIVAL)
    assert engine.turns_completed <= RULES.max_moves
    assert len(engine.board.barriers) <= RULES.max_barriers


def test_selfplay_reaches_both_outcomes_across_seeds() -> None:
    """Sanity that the random arena is not degenerate: both endings occur."""
    outcomes = {play_random_game(seed).outcome for seed in range(30)}
    assert Outcome.CAPTURE in outcomes
    assert Outcome.SURVIVAL in outcomes
