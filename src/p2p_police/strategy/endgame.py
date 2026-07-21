"""Exact endgame solver: memoized adversarial search over the belief support.

BELIEF-CORRECT SEMANTICS (the cop never knows the true thief cell): a capture
is FORCED only when ONE first action forces it against EVERY thief cell
carrying non-negligible belief mass AND every legal reply thereafter. The
rival's true position is never read (guard-tested); candidate cells come from
the BeliefMap alone, and all lookahead runs on lightweight board views over
domain's public API - domain state stays read-only.

Search: win/loss minimax with memoization; the exists/forall early exits ARE
alpha-beta pruning specialized to boolean payoffs. Compute is hard-capped
(nodes + wall clock, [strategy.endgame]); any cap hit defers to the heuristic
brain - optimality is never worth the turn deadline.
"""

import time

from p2p_police.domain import protocol
from p2p_police.domain.board import Board
from p2p_police.domain.primitives import Cell, Move, Role

ORTHOGONAL = (Move.N, Move.S, Move.E, Move.W)
_MOVE_RANK = {move.name: rank for rank, move in enumerate((*ORTHOGONAL, Move.STAY))}


class _BudgetError(Exception):
    """Node or time cap exhausted - the caller defers to the heuristic."""


class _View:
    """Read-only board plus hypothetical barriers (domain is never mutated)."""

    def __init__(self, board: Board, extra: frozenset) -> None:
        self._board, self._extra = board, extra

    def is_passable(self, cell: Cell) -> bool:
        return cell not in self._extra and self._board.is_passable(cell)

    def is_surrounded(self, cell: Cell) -> bool:
        return all(not self.is_passable(m.applied_to(cell)) for m in ORTHOGONAL)


def support_cells(belief, threshold: float) -> list[Cell]:
    """Cells carrying non-negligible mass, read off a values() snapshot."""
    values = belief.values()
    return [(row, col) for row, masses in enumerate(values)
            for col, mass in enumerate(masses) if mass >= threshold]


def _action_order(action: tuple) -> tuple:
    """Deterministic pick: forcing moves before barriers (quota is precious)."""
    kind, arg = action
    return (0, _MOVE_RANK[arg], (0, 0)) if kind == "move" else (1, 0, arg)


class EndgameSolver:
    """PoliceBrain pre-check: the forcing line's first action, or None.

    Input: engine (read-only) + the cop's BeliefMap of the thief.
    Output: a protocol action dict, or None (defer to the heuristic).
    Setup: a [strategy.endgame] table (shared/tuning.py defaults).
    """

    def __init__(self, settings: dict) -> None:
        self.settings = settings
        self.fired = 0  # measurement: turns this solver decided

    def solve(self, engine, belief) -> dict | None:
        if not self.settings["enabled"] or belief is None:
            return None
        support = support_cells(belief, self.settings["support_mass_threshold"])
        if not 1 <= len(support) <= self.settings["max_support_cells"]:
            return None
        remaining = engine.rules.survival_threshold - engine.turns_completed
        horizon = min(int(self.settings["max_horizon_turns"]), remaining)
        me = engine.positions[Role.POLICE]
        if horizon < 1 or me in support:  # under our feet = boundary handles it
            return None
        quota = engine.rules.max_barriers - len(engine.board.barriers)
        self._memo: dict = {}
        self._nodes = 0
        self._deadline = time.monotonic() + self.settings["time_cap_ms"] / 1000.0
        actions = self._cop_actions(me, frozenset(), quota, engine.board)
        try:
            # Iterative deepening: the SHALLOWEST forcing depth first. Playing a
            # depth-h line leaves every reply forced in h-1, so re-solving each
            # turn strictly closes on the capture - no forcing-forever dance.
            for depth in range(1, horizon + 1):
                forcing: set | None = None
                for cell in support:
                    wins = {
                        action for action in actions
                        if self._forces(action, me, cell, frozenset(), quota, depth, engine.board)
                    }
                    forcing = wins if forcing is None else forcing & wins
                    if not forcing:
                        break
                if forcing:
                    kind, arg = min(forcing, key=_action_order)
                    self.fired += 1
                    return (protocol.move_action(Move[arg]) if kind == "move"
                            else protocol.barrier_action(arg))
        except _BudgetError:
            return None
        return None

    def _tick(self) -> None:
        self._nodes += 1
        if self._nodes > self.settings["node_cap"] or (
            self._nodes % 64 == 0 and time.monotonic() > self._deadline
        ):
            raise _BudgetError

    def _cop_actions(self, cop: Cell, extra: frozenset, quota: int, board: Board) -> list:
        view = _View(board, extra)
        actions = [("move", m.name) for m in (*ORTHOGONAL, Move.STAY)
                   if m is Move.STAY or view.is_passable(m.applied_to(cop))]
        if quota > 0:  # law of barriers: own cell or an orthogonal neighbor
            actions += [("barrier", target)
                        for target in (cop, *(m.applied_to(cop) for m in ORTHOGONAL))
                        if board.in_bounds(target) and view.is_passable(target)]
        return actions

    def _forces(self, action: tuple, cop: Cell, thief: Cell, extra: frozenset,
                quota: int, horizon: int, board: Board) -> bool:
        """Does `action` force capture of `thief` within `horizon` full turns?"""
        self._tick()
        kind, arg = action
        if kind == "barrier":
            if arg == thief:
                return True  # rule 46: barrier on the thief captures outright
            extra, quota, landed = extra | {arg}, quota - 1, cop
        else:
            landed = Move[arg].applied_to(cop)
            if landed == thief:
                return True
        view = _View(board, extra)
        if view.is_surrounded(thief):
            return True
        for reply in (Move.STAY, *ORTHOGONAL):
            target = reply.applied_to(thief)
            if reply is not Move.STAY and not view.is_passable(target):
                continue
            if target == landed or view.is_surrounded(target):
                continue  # this reply is captured at the boundary
            if horizon == 1 or not self._wins(landed, target, extra, quota, horizon - 1, board):
                return False
        return True

    def _wins(self, cop: Cell, thief: Cell, extra: frozenset,
              quota: int, horizon: int, board: Board) -> bool:
        key = (cop, thief, extra, horizon)
        cached = self._memo.get(key)
        if cached is None:
            cached = any(
                self._forces(action, cop, thief, extra, quota, horizon, board)
                for action in self._cop_actions(cop, extra, quota, board)
            )
            self._memo[key] = cached
        return cached
