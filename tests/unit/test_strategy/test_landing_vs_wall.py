"""Landing-vs-wall hybrid ([strategy.trap]).

A barrier capture is SELF-declared by the rival (measured live 2026-08-01:
three sealed-in games played on and scored survival); a landing capture is
claim-mediated and enforceable. So step in when the believed cell is a legal
step — except at the buzzer, where a landing that misses cannot be recovered
while a wall still shrinks the board.
"""

import random

from p2p_police.domain.engine import GameEngine
from p2p_police.domain.primitives import Role
from p2p_police.domain.rules import RuleSet
from p2p_police.strategy.police_brain import PoliceBrain


def board_with_cop_beside_thief(turns_done: int) -> GameEngine:
    """Cop at (0,1) adjacent to a corner thief at (0,0): only two escapes, so
    the trap gate is open and the wall-vs-step choice is the live one."""
    engine = GameEngine(7, (0, 1), (0, 0), RuleSet(14, 35, 35))
    engine.turns_completed = turns_done
    return engine


def brain(private: dict | None = None) -> PoliceBrain:
    from types import SimpleNamespace

    config = SimpleNamespace(private=private or {})
    return PoliceBrain(Role.POLICE, random.Random(7), config=config)


def test_mid_game_steps_in_rather_than_walling() -> None:
    action = brain().decide(board_with_cop_beside_thief(5))
    assert action["type"] == "move"  # claim-mediated capture, enforceable


def test_at_the_buzzer_takes_the_wall() -> None:
    """Two turns left: a missed landing is unrecoverable, the wall is not."""
    action = brain().decide(board_with_cop_beside_thief(34))
    assert action["type"] == "barrier"
    assert action["cell"] == [0, 0]  # ON the believed cell (rule 46)


def test_the_deadline_is_configurable() -> None:
    private = {"strategy": {"trap": {"landing_deadline_turns": 10}}}
    action = brain(private).decide(board_with_cop_beside_thief(28))
    assert action["type"] == "barrier"  # inside a widened deadline


def test_the_preference_can_be_disarmed() -> None:
    private = {"strategy": {"trap": {"prefer_landing_capture": False}}}
    action = brain(private).decide(board_with_cop_beside_thief(5))
    assert action["type"] == "barrier"  # old behaviour, on demand
