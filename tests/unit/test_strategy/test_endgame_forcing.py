"""Endgame soundness against the physics itself: the returned first action
really converts against EVERY legal reply (engine-adjudicated rollout), the
whole blind decision path never touches the rival's true cell, and a full
game with both boosters on completes legally."""

import random
from types import SimpleNamespace

from p2p_police.domain import protocol
from p2p_police.domain.belief import BeliefMap
from p2p_police.domain.engine import GameEngine
from p2p_police.domain.primitives import Outcome, Role
from p2p_police.domain.rules import RuleSet
from p2p_police.shared.tuning import ENDGAME_DEFAULTS
from p2p_police.strategy.brain_base import RandomBrain
from p2p_police.strategy.endgame import EndgameSolver
from p2p_police.strategy.police_brain import PoliceBrain

RULES = RuleSet(max_barriers=14, max_moves=35, survival_threshold=35)


class FakeBelief:
    """Support-only belief stub (twin of the one in test_endgame.py)."""

    def __init__(self, grid_size: int, cells: list) -> None:
        self.grid_size, self._cells = grid_size, list(cells)

    def values(self) -> list[list[float]]:
        grid = [[0.0] * self.grid_size for _ in range(self.grid_size)]
        for row, col in self._cells:
            grid[row][col] = 1.0 / len(self._cells)
        return grid

    def argmax_cell(self):
        return self._cells[0]


def pocket_engine() -> GameEngine:
    """Thief at (0,0) with (1,0) walled and the cop at (0,3): no one-turn
    kill, but a proven two-turn coffin (true and believed positions coincide
    here - this file adjudicates real rollouts against the physics)."""
    engine = GameEngine(7, (0, 3), (0, 0), RULES)
    engine.board.add_barrier((1, 0))
    return engine


def explore_all_replies(make_engine, horizon: int, replies: tuple = ()) -> None:
    """Depth-first over every thief reply line; the solver must convert each
    within `horizon` full turns (the test, not the solver, may read truth)."""
    engine = make_engine()
    fresh = EndgameSolver({**ENDGAME_DEFAULTS, "enabled": True,
                           "max_horizon_turns": horizon})
    step = 0
    while engine.outcome is Outcome.ONGOING:
        oracle = FakeBelief(7, [engine.positions[Role.THIEF]])  # test-side truth
        action = fresh.solve(engine, oracle)
        assert action is not None, f"forcing line lost at step {step}: {replies}"
        protocol.apply_action(engine, Role.POLICE, action)
        if engine.outcome is not Outcome.ONGOING:
            break
        legal = engine.board.legal_moves(engine.positions[Role.THIEF])
        if step < len(replies):
            protocol.apply_action(engine, Role.THIEF, protocol.move_action(replies[step]))
        else:
            for move in legal:
                explore_all_replies(make_engine, horizon, (*replies, move))
            return
        step += 1
    assert engine.outcome is Outcome.CAPTURE
    assert engine.turns_completed <= horizon


def test_pocket_forcing_line_converts_against_every_reply() -> None:
    explore_all_replies(pocket_engine, horizon=2)


class GuardedPositions(dict):
    """positions proxy that trips the moment anyone asks for the rival."""

    def __getitem__(self, role):
        assert role is not Role.THIEF, "live path read the rival's TRUE cell"
        return super().__getitem__(role)


BOOSTED = SimpleNamespace(private={"strategy": {"endgame": {"enabled": True},
                                                "info_gain": {"enabled": True}}})


def test_blind_decide_path_never_reads_rival_truth() -> None:
    """Both boosters forced ON so the guard covers their whole code path."""
    engine = pocket_engine()
    engine.positions = GuardedPositions(engine.positions)
    brain = PoliceBrain(Role.POLICE, random.Random(0), BOOSTED)
    for support in ([(0, 0)], [(0, 0), (4, 4), (2, 5), (5, 1)]):  # forced + spread
        action = brain.decide(engine, FakeBelief(7, support))
        assert action["type"] in ("move", "barrier")


def test_full_blind_game_with_boosters_completes_legally() -> None:
    for seed in range(3):
        engine = GameEngine(7, (0, 0), (3, 3), RULES)
        cop = PoliceBrain(Role.POLICE, random.Random(seed), BOOSTED)
        thief = RandomBrain(Role.THIEF, random.Random(seed + 500))
        belief = BeliefMap(7)
        while engine.outcome is Outcome.ONGOING:
            protocol.apply_action(engine, Role.POLICE, cop.decide(engine, belief))
            if engine.outcome is not Outcome.ONGOING:
                break
            protocol.apply_action(engine, Role.THIEF, thief.decide(engine))
            belief.diffuse(engine.board)
            belief.observe_scent(engine.scent[Role.THIEF], engine.board)
        assert engine.outcome in (Outcome.CAPTURE, Outcome.SURVIVAL)
        assert cop.endgame.settings["enabled"] and cop.info_gain["enabled"]


def test_shipped_defaults_leave_both_boosters_off() -> None:
    """Keep-gate verdict is the DEFAULT: a config-less brain plays baseline."""
    cop = PoliceBrain(Role.POLICE, random.Random(0))
    assert not cop.endgame.settings["enabled"] and not cop.info_gain["enabled"]
