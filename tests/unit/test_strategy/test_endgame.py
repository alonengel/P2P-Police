"""Exact endgame solver: forced positions convert, escapable/oversized ones
defer, compute caps defer, and the rival's TRUE cell is never read - the
belief support is the solver's only source of thief candidates."""

from pathlib import Path

from p2p_police.domain import protocol
from p2p_police.domain.engine import GameEngine
from p2p_police.domain.primitives import Move
from p2p_police.domain.rules import RuleSet
from p2p_police.shared.tuning import ENDGAME_DEFAULTS
from p2p_police.strategy.endgame import EndgameSolver, support_cells

RULES = RuleSet(max_barriers=14, max_moves=35, survival_threshold=35)


class FakeBelief:
    """Support-only belief stub: mass split evenly over chosen cells."""

    def __init__(self, grid_size: int, cells: list) -> None:
        self.grid_size, self._cells = grid_size, list(cells)

    def values(self) -> list[list[float]]:
        grid = [[0.0] * self.grid_size for _ in range(self.grid_size)]
        for row, col in self._cells:
            grid[row][col] = 1.0 / len(self._cells)
        return grid

    def argmax_cell(self):
        return self._cells[0]


def solver(**overrides) -> EndgameSolver:
    """Solver under test: forced ON (the shipped default is the keep-gate's
    honest OFF; docs/evidence/cop-strength.md)."""
    return EndgameSolver({**ENDGAME_DEFAULTS, "enabled": True, **overrides})


def test_shipped_default_is_off_and_gates_solve() -> None:
    assert ENDGAME_DEFAULTS["enabled"] is False  # measured keep-gate verdict
    disabled = EndgameSolver(dict(ENDGAME_DEFAULTS))
    assert disabled.solve(pocket_engine(), FakeBelief(7, [(0, 0)])) is None


def pocket_engine() -> GameEngine:
    """Thief believed at (0,0) with (1,0) walled: a two-turn coffin. The TRUE
    thief sits far away at (6,6) - the solver must never look at it."""
    engine = GameEngine(7, (0, 2), (6, 6), RULES)
    engine.board.add_barrier((1, 0))
    return engine


def test_support_cells_reads_threshold() -> None:
    belief = FakeBelief(7, [(0, 0), (3, 3)])
    assert support_cells(belief, 0.4) == [(0, 0), (3, 3)]
    assert support_cells(belief, 0.6) == []


def test_capture_in_one_lands_on_the_believed_cell() -> None:
    engine = GameEngine(7, (0, 1), (6, 6), RULES)  # true thief FAR from support
    action = solver(max_horizon_turns=1).solve(engine, FakeBelief(7, [(0, 0)]))
    assert action == protocol.move_action(Move.W)  # forcing moves outrank barriers


def test_forced_capture_in_two_is_found() -> None:
    """One step farther out there is no one-turn kill, but stepping to (0,2)
    forces it: STAY -> wall (0,1) surrounds; E -> walks into the cop."""
    engine = GameEngine(7, (0, 3), (6, 6), RULES)
    engine.board.add_barrier((1, 0))
    two = solver(max_horizon_turns=2)
    assert two.solve(engine, FakeBelief(7, [(0, 0)])) == protocol.move_action(Move.W)
    assert solver(max_horizon_turns=1).solve(engine, FakeBelief(7, [(0, 0)])) is None


def test_pocket_horizon_one_seals_with_the_surrounding_barrier() -> None:
    """With no room to walk a line, the only one-turn force is rule 47: wall
    (0,1) and the believed cell has zero orthogonal escapes."""
    action = solver(max_horizon_turns=1).solve(pocket_engine(), FakeBelief(7, [(0, 0)]))
    assert action == protocol.barrier_action((0, 1))


def test_open_board_is_never_claimed_forced() -> None:
    engine = GameEngine(7, (0, 0), (6, 6), RULES)
    assert solver(max_horizon_turns=3).solve(engine, FakeBelief(7, [(3, 3)])) is None


def test_wide_or_empty_support_defers() -> None:
    engine = pocket_engine()
    wide = FakeBelief(7, [(0, 0), (0, 1), (1, 1), (2, 2)])  # 4 > max_support_cells
    assert solver().solve(engine, wide) is None
    assert solver(support_mass_threshold=0.9).solve(engine, wide) is None  # empty


def test_forced_line_must_cover_every_support_cell() -> None:
    """A pocket plus a far free cell: no single action forces both -> defer."""
    action = solver(max_horizon_turns=2).solve(
        pocket_engine(), FakeBelief(7, [(0, 0), (5, 5)]))
    assert action is None


def test_node_cap_defers_to_heuristic() -> None:
    capped = solver(max_horizon_turns=2, node_cap=3)
    assert capped.solve(pocket_engine(), FakeBelief(7, [(0, 0)])) is None
    assert capped.fired == 0


def test_time_cap_defers_on_a_large_search() -> None:
    starved = solver(max_horizon_turns=5, time_cap_ms=0.0)
    assert starved.solve(pocket_engine(), FakeBelief(7, [(3, 3)])) is None


def test_no_turns_left_defers() -> None:
    engine = pocket_engine()
    engine.turns_completed = RULES.survival_threshold
    assert solver().solve(engine, FakeBelief(7, [(0, 0)])) is None


def test_endgame_source_never_names_the_rival_position() -> None:
    """Live-path guard: the solver may know Role.POLICE (self) only."""
    source = Path("src/p2p_police/strategy/endgame.py").read_text(encoding="utf-8")
    assert "Role.THIEF" not in source
