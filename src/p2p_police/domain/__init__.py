"""Game physics — pure logic, zero I/O, parity-locked with the twin repo.

Any change here MUST be ported to the sibling repository in the same session
and pass scripts/check_physics_parity.py (ADR-0001).
"""

from p2p_police.domain.board import Board
from p2p_police.domain.engine import GameEngine
from p2p_police.domain.primitives import Cell, GamePhase, Move, Outcome, Role
from p2p_police.domain.rules import RuleSet
from p2p_police.domain.scent import ScentField
from p2p_police.domain.scoring import ScoreTable
from p2p_police.domain.state_machine import GamePhaseMachine

__all__ = [
    "Board",
    "Cell",
    "GameEngine",
    "GamePhase",
    "GamePhaseMachine",
    "Move",
    "Outcome",
    "Role",
    "RuleSet",
    "ScentField",
    "ScoreTable",
]
