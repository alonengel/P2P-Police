"""Arena measurement cop: aged-belief tracking + low-threshold pounce +
gain-gated surgical walls (self-contained sparring instrument).

The hunting pattern our evasion work must survive: a cop that TRUSTS the
reach-decoded belief early — pouncing on weak peaks instead of waiting for
certainty, so a camper's beacon is punished before it can relocate — and
spends its wall quota only on placements that provably shrink the believed
room. Blind by construction: decide() consumes a BeliefMap; the true thief
cell is read only in the belief-less full-information fallback.
"""

import random

from p2p_police.domain import protocol
from p2p_police.domain.engine import GameEngine
from p2p_police.domain.errors import IllegalBarrierError
from p2p_police.domain.pathfind import bfs_distances
from p2p_police.domain.primitives import Cell, Move, Role
from p2p_police.domain.rules import validate_barrier_placement

FAR = 10 ** 6
POUNCE_MASS = 0.08  # trust threshold: pounce even on a weak peak
TRAP_RANGE = 3  # consider spending a wall inside this believed distance
GAIN_MIN = 3  # a wall must shrink the believed room by at least this
KILL_MASS = 0.30  # wall the believed cell itself only when belief is sharp


class _Walled:
    """Board view with one hypothetical wall."""

    def __init__(self, board, extra: Cell) -> None:
        self._board, self._extra, self.grid_size = board, extra, board.grid_size

    def is_passable(self, cell) -> bool:
        return cell != self._extra and self._board.is_passable(cell)


class AgedBeliefTrapCop:
    """Belief-led pursuit: chase the peak, wall the pocket when it pays."""

    def __init__(self, role: Role, rng: random.Random) -> None:
        self.role, self.rng = role, rng

    def _legal_walls(self, engine: GameEngine) -> list[Cell]:
        me = engine.positions[Role.POLICE]
        walls = []
        for cell in [me] + [m.applied_to(me) for m in (Move.N, Move.S, Move.E, Move.W)]:
            try:
                validate_barrier_placement(engine.board, engine.rules, me, cell)
                walls.append(cell)
            except IllegalBarrierError:
                continue
        return walls

    def _surgical_wall(self, engine, prey: Cell, mass: float, my_distance: int):
        """A placement is worth quota only when the believed thief is close
        AND the wall provably shrinks its room; a sharp peak inside reach is
        walled directly (a wall on the thief's cell captures, rule 46)."""
        walls = self._legal_walls(engine)
        if not walls or mass < POUNCE_MASS or my_distance > TRAP_RANGE:
            return None
        if prey in walls and mass >= KILL_MASS:
            return prey
        surgical = [wall for wall in walls if wall != prey]
        if not surgical:
            return None
        room = len(bfs_distances(engine.board, prey))
        best = min(surgical,
                   key=lambda w: len(bfs_distances(_Walled(engine.board, w), prey)))
        if room - len(bfs_distances(_Walled(engine.board, best), prey)) >= GAIN_MIN:
            return best
        return None

    def decide(self, engine: GameEngine, belief=None) -> dict:
        me = engine.positions[Role.POLICE]
        if belief is None:  # full-information harness fallback
            prey, mass = engine.positions[Role.THIEF], 1.0
        else:
            prey = belief.argmax_cell()
            mass = belief.value_at(prey)
        distances = bfs_distances(engine.board, prey)
        wall = self._surgical_wall(engine, prey, mass, distances.get(me, FAR))
        if wall is not None:
            return protocol.barrier_action(wall)
        moves = self.rng.sample(engine.board.legal_moves(me),
                                k=len(engine.board.legal_moves(me)))
        return protocol.move_action(
            min(moves, key=lambda m: distances.get(m.applied_to(me), FAR)))
