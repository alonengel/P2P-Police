"""AgedBeliefTrapCop: the calibrated hunting ceiling for evasion work —
belief-led pounce plus gain-gated surgical walls, blind by construction."""

import random

from p2p_police.domain import protocol
from p2p_police.domain.belief import BeliefMap
from p2p_police.domain.engine import GameEngine
from p2p_police.domain.primitives import Move, Outcome, Role
from p2p_police.domain.rules import RuleSet
from p2p_police.strategy.arena_aged_cop import AgedBeliefTrapCop
from p2p_police.strategy.brain_base import RandomBrain

RULES = RuleSet(max_barriers=14, max_moves=35, survival_threshold=35)


def sharp_belief(cell) -> BeliefMap:
    """Belief with a dominant peak on `cell` (barrier-origin boost trick)."""
    belief = BeliefMap(7)
    board = GameEngine(7, (0, 0), (6, 6), RULES).board
    for _ in range(3):
        belief.observe_barrier(cell, _FakeWall(board, cell))
    return belief


class _FakeWall:
    """Board view that reports `wall` blocked (belief-shaping helper)."""

    def __init__(self, board, wall) -> None:
        self._board, self._wall, self.grid_size = board, wall, board.grid_size

    def is_barrier(self, cell) -> bool:
        return cell == self._wall or self._board.is_barrier(cell)

    def is_passable(self, cell) -> bool:
        return cell != self._wall and self._board.is_passable(cell)


def test_sharp_adjacent_peak_gets_walled_for_the_capture() -> None:
    """KILL_MASS met and the peak inside placement reach: wall the peak
    itself (rule 46 captures if right). The corner boost concentrates
    ~0.47 mass on (0,1); the cop stands one step away."""
    engine = GameEngine(7, (0, 2), (6, 6), RULES)
    belief = sharp_belief((0, 0))  # mass piles on (0,1) and (1,0)
    assert belief.value_at((0, 1)) >= 0.3  # KILL_MASS premise holds
    cop = AgedBeliefTrapCop(Role.POLICE, random.Random(1))
    action = cop.decide(engine, belief)
    assert action == {"type": "barrier", "cell": [0, 1]}


def test_open_board_gain_gate_refuses_pointless_walls() -> None:
    """A close-but-open peak is chased, not walled: one wall on an open
    board shrinks nothing, and the gain gate keeps the quota."""
    engine = GameEngine(7, (3, 3), (6, 6), RULES)
    action = AgedBeliefTrapCop(Role.POLICE, random.Random(4)).decide(
        engine, sharp_belief((3, 4)))
    assert action["type"] == "move"


def test_weak_uniform_belief_never_spends_a_wall() -> None:
    engine = GameEngine(7, (3, 3), (6, 6), RULES)
    cop = AgedBeliefTrapCop(Role.POLICE, random.Random(2))
    action = cop.decide(engine, BeliefMap(7))  # uniform: peak mass ~0.02
    assert action["type"] == "move"


def test_far_peak_never_spends_a_wall() -> None:
    engine = GameEngine(7, (0, 0), (6, 6), RULES)
    cop = AgedBeliefTrapCop(Role.POLICE, random.Random(3))
    action = cop.decide(engine, sharp_belief((6, 6)))  # far beyond TRAP_RANGE
    assert action["type"] == "move"
    landing = Move[action["move"]].applied_to((0, 0))
    assert landing in {(0, 1), (1, 0)}  # pursuing the believed peak


def test_blind_aged_cop_hunts_down_a_random_thief() -> None:
    """The measurement bar: blind (scent-belief only) pursuit + surgical
    walls must convincingly beat a random evader."""
    captures = 0
    for seed in range(15):
        engine = GameEngine(7, (0, 0), (3, 3), RULES)
        cop = AgedBeliefTrapCop(Role.POLICE, random.Random(seed))
        thief = RandomBrain(Role.THIEF, random.Random(seed + 500))
        belief = BeliefMap(7)
        while engine.outcome is Outcome.ONGOING:
            protocol.apply_action(engine, Role.POLICE, cop.decide(engine, belief))
            if engine.outcome is not Outcome.ONGOING:
                break
            protocol.apply_action(engine, Role.THIEF, thief.decide(engine))
            belief.diffuse(engine.board)
            belief.observe_scent(engine.scent[Role.THIEF], engine.board)
        captures += engine.outcome is Outcome.CAPTURE
    assert captures >= 10, f"aged cop captured only {captures}/15 random thieves"
