"""Shipped pursuit brain (stage 3: full information; belief arrives stage 4).

Policy: close the TRUE (barrier-aware BFS) distance to the thief; when one
step away, land the capture. Spend a barrier only when it immediately tightens
a nearly-trapped thief (few escape routes) — barriers are a quota resource,
not confetti (ch. 3 resource management).
"""


from p2p_police.domain import protocol
from p2p_police.domain.engine import GameEngine
from p2p_police.domain.pathfind import UNREACHABLE, bfs_distances
from p2p_police.domain.primitives import Cell, Move, Role
from p2p_police.strategy.brain_base import BrainBase

TRAP_ESCAPE_LIMIT = 2  # barrier only when the thief has this many escapes or fewer
TRAP_RANGE = 2  # ...and is already this close


class PoliceBrain(BrainBase):
    """Pursuit + surgical barrier placement."""

    def decide(self, engine: GameEngine) -> dict:
        me = engine.positions[Role.POLICE]
        thief = engine.positions[Role.THIEF]
        distances = bfs_distances(engine.board, thief)

        barrier = self._trap_barrier(engine, me, thief, distances.get(me, UNREACHABLE))
        if barrier is not None:
            return protocol.barrier_action(barrier)

        best_move, best_distance = Move.STAY, distances.get(me, UNREACHABLE)
        for move in self.rng.sample(list(Move), k=len(Move)):  # tie-break randomly
            target = move.applied_to(me)
            if move is Move.STAY or not engine.board.is_passable(target):
                continue
            distance = distances.get(target, UNREACHABLE)
            if distance != UNREACHABLE and (best_distance == UNREACHABLE or distance < best_distance):
                best_move, best_distance = move, distance
        return protocol.move_action(best_move)

    def _trap_barrier(
        self, engine: GameEngine, me: Cell, thief: Cell, my_distance: int
    ) -> Cell | None:
        """A barrier is worth its quota only if the thief is close and nearly
        cornered AND the barrier cell is within our reach (own cell or
        orthogonal neighbor) AND it removes one of the thief's last escapes."""
        if len(engine.board.barriers) >= engine.rules.max_barriers:
            return None
        if my_distance == UNREACHABLE or my_distance > TRAP_RANGE:
            return None
        thief_escapes = [
            m.applied_to(thief)
            for m in (Move.N, Move.S, Move.E, Move.W)
            if engine.board.is_passable(m.applied_to(thief))
        ]
        if len(thief_escapes) > TRAP_ESCAPE_LIMIT:
            return None
        my_reach = {me} | {
            m.applied_to(me)
            for m in (Move.N, Move.S, Move.E, Move.W)
            if engine.board.in_bounds(m.applied_to(me))
        }
        # Placing ON the thief captures outright - take it when reachable.
        if thief in my_reach:
            return thief
        candidates = [c for c in thief_escapes if c in my_reach and not engine.board.is_barrier(c)]
        return candidates[0] if candidates else None


class ThiefForArena(BrainBase):
    """Evasion sparring partner for OUR self-play arena only (the real thief
    brain lives in the P2P-Thief repo): maximize BFS distance from the cop."""

    def decide(self, engine: GameEngine) -> dict:
        cop = engine.positions[Role.POLICE]
        me = engine.positions[Role.THIEF]
        distances = bfs_distances(engine.board, cop)
        best_move, best = Move.STAY, distances.get(me, 0)
        for move in self.rng.sample(list(Move), k=len(Move)):
            target = move.applied_to(me)
            if move is Move.STAY or not engine.board.is_passable(target):
                continue
            distance = distances.get(target, 0)
            if distance > best:
                best_move, best = move, distance
        return protocol.move_action(best_move)
