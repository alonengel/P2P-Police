"""Game physics — pure logic, zero I/O, parity-locked with the twin repo.

Any change here MUST be ported to the sibling repository in the same session
and pass scripts/check_physics_parity.py (ADR-0001).
"""

from p2p_police.domain.board import Board
from p2p_police.domain.primitives import Cell, GamePhase, Move, Outcome, Role

__all__ = ["Board", "Cell", "GamePhase", "Move", "Outcome", "Role"]
