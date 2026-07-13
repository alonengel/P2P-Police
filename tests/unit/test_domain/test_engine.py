"""Engine tests encode the round structure (cop first, thief closes the turn),
the barrier-forgoes-move law, mid-round captures, and the decay boundary."""

import pytest

from p2p_police.domain.engine import GameEngine
from p2p_police.domain.errors import GameRuleError
from p2p_police.domain.primitives import Move, Outcome, Role
from p2p_police.domain.rules import RuleSet

RULES = RuleSet(max_barriers=14, max_moves=35, survival_threshold=35)


def make_engine(cop=(0, 0), thief=(3, 3)) -> GameEngine:
    return GameEngine(7, cop, thief, RULES)


def test_start_positions_must_be_passable() -> None:
    with pytest.raises(ValueError):
        GameEngine(7, (0, 0), (9, 9), RULES)


def test_thief_cannot_act_before_cop() -> None:
    engine = make_engine()
    with pytest.raises(GameRuleError):
        engine.thief_move(Move.N)


def test_cop_cannot_act_twice_in_a_round() -> None:
    engine = make_engine()
    engine.police_move(Move.E)
    with pytest.raises(GameRuleError):
        engine.police_move(Move.E)


def test_barrier_placement_forgoes_the_move() -> None:
    engine = make_engine()
    engine.police_place_barrier((0, 1))
    assert engine.positions[Role.POLICE] == (0, 0)
    engine.thief_move(Move.STAY)
    assert engine.turns_completed == 1


def test_full_turn_updates_both_scent_fields_once() -> None:
    engine = make_engine()
    engine.police_move(Move.E)
    engine.thief_move(Move.STAY)
    assert engine.scent[Role.POLICE].value_at((0, 1)) == 0.9
    assert engine.scent[Role.THIEF].value_at((3, 3)) == 0.9
    assert engine.turns_completed == 1


def test_no_scent_before_first_full_turn() -> None:
    engine = make_engine()
    engine.police_move(Move.E)
    assert engine.scent[Role.POLICE].value_at((0, 1)) == 0.0


def test_barrier_on_thief_cell_captures_immediately() -> None:
    engine = make_engine(cop=(3, 2), thief=(3, 3))
    engine.police_place_barrier((3, 3))
    assert engine.outcome is Outcome.CAPTURE


def test_landing_capture_by_cop_move() -> None:
    engine = make_engine(cop=(3, 2), thief=(3, 3))
    engine.police_move(Move.E)
    assert engine.outcome is Outcome.CAPTURE


def test_thief_walking_into_cop_is_captured() -> None:
    engine = make_engine(cop=(3, 2), thief=(3, 3))
    engine.police_move(Move.STAY)
    engine.thief_move(Move.W)
    assert engine.outcome is Outcome.CAPTURE


def test_surrounding_the_thief_captures() -> None:
    engine = make_engine(cop=(1, 1), thief=(0, 0))
    engine.board.add_barrier((1, 0))  # pre-set one wall for test brevity
    engine.police_place_barrier((0, 1))
    assert engine.outcome is Outcome.CAPTURE


def test_survival_at_threshold() -> None:
    rules = RuleSet(max_barriers=14, max_moves=3, survival_threshold=3)
    engine = GameEngine(7, (0, 0), (6, 6), rules)
    for _ in range(3):
        engine.police_move(Move.STAY)
        engine.thief_move(Move.STAY)
    assert engine.outcome is Outcome.SURVIVAL
    assert engine.turns_completed == 3


def test_no_actions_after_game_over() -> None:
    engine = make_engine(cop=(3, 2), thief=(3, 3))
    engine.police_move(Move.E)
    with pytest.raises(GameRuleError):
        engine.thief_move(Move.N)
