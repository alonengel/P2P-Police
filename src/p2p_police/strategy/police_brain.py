"""Shipped pursuit brain (stage 3: full information; belief arrives stage 4).

Policy: close the TRUE (barrier-aware BFS) distance to the thief; when one
step away, land the capture. Spend a barrier only when it immediately tightens
a nearly-trapped thief (few escape routes) — barriers are a quota resource,
not confetti (ch. 3 resource management), but an UNSPENT quota buys nothing
either, so the trap gate is config-driven and swept ([strategy.trap]).
Two belief-mode boosters, each config-gated and keep-gate-measured
(docs/evidence/cop-strength.md): an exact endgame pre-check
(strategy/endgame.py) and an information-gain move term (strategy/info_gain.py)
blended into the pursuit score.
"""

import random

from p2p_police.domain import protocol
from p2p_police.domain.engine import GameEngine
from p2p_police.domain.pathfind import UNREACHABLE, bfs_distances
from p2p_police.domain.primitives import Cell, Move, Role
from p2p_police.shared.tuning import endgame_table, info_gain_table, trap_table
from p2p_police.strategy.brain_base import BrainBase
from p2p_police.strategy.endgame import EndgameSolver
from p2p_police.strategy.info_gain import expected_gain


class PoliceBrain(BrainBase):
    """Pursuit + surgical barriers + exact endgame + info-gain steering."""

    def __init__(self, role: Role, rng: random.Random, config=None) -> None:
        super().__init__(role, rng)
        private = config.private if config is not None else {}
        self.endgame = EndgameSolver(endgame_table(private))
        self.info_gain = info_gain_table(private)
        self.trap = trap_table(private)

    def decide(self, engine: GameEngine, belief=None) -> dict:
        if belief is not None:  # exact pre-check: play a PROVEN forcing line
            forced = self.endgame.solve(engine, belief)
            if forced is not None:
                return forced
        me = engine.positions[Role.POLICE]
        # Blind mode (real games): hunt the belief peak, never the true cell.
        thief = belief.argmax_cell() if belief is not None else engine.positions[Role.THIEF]
        distances = bfs_distances(engine.board, thief)

        barrier = self._trap_barrier(engine, me, thief, distances.get(me, UNREACHABLE))
        if barrier is not None:
            return protocol.barrier_action(barrier)

        blend = belief is not None and self.info_gain["enabled"]
        best_move, best_score = Move.STAY, self._score(me, distances, belief, blend)
        for move in self.rng.sample(list(Move), k=len(Move)):  # tie-break randomly
            target = move.applied_to(me)
            if move is Move.STAY or not engine.board.is_passable(target):
                continue
            score = self._score(target, distances, belief, blend)
            if score is not None and (best_score is None or score > best_score):
                best_move, best_score = move, score
        return protocol.move_action(best_move)

    def _score(self, cell: Cell, distances: dict, belief, blend: bool) -> float | None:
        """Pursuit score: closer is better; when blind, landings whose scent
        reading would sharpen the belief earn their information's worth."""
        distance = distances.get(cell, UNREACHABLE)
        if distance == UNREACHABLE:
            return None
        score = -float(distance)
        if blend:
            score += self.info_gain["weight"] * expected_gain(belief, cell, self.info_gain)
        return score

    def _trap_barrier(
        self, engine: GameEngine, me: Cell, thief: Cell, my_distance: int
    ) -> Cell | None:
        """A barrier is worth its quota only if the thief is close and nearly
        cornered AND the barrier cell is within our reach (own cell or
        orthogonal neighbor) AND it removes one of the thief's last escapes."""
        if len(engine.board.barriers) >= engine.rules.max_barriers:
            return None
        if my_distance == UNREACHABLE or my_distance > self.trap["range"]:
            return None
        thief_escapes = [
            m.applied_to(thief)
            for m in (Move.N, Move.S, Move.E, Move.W)
            if engine.board.is_passable(m.applied_to(thief))
        ]
        if len(thief_escapes) > self.trap["escape_limit"]:
            return None
        my_reach = {me} | {
            m.applied_to(me)
            for m in (Move.N, Move.S, Move.E, Move.W)
            if engine.board.in_bounds(m.applied_to(me))
        }
        # Placing ON the believed cell captures outright (rule 46) - but that
        # capture is SELF-DECLARED by the rival, while a landing capture is
        # claim-mediated and its truth duty is enforceable. When the cell is a
        # legal step, step: walk the capture in rather than wall it.
        if thief in my_reach:
            step_in = (self.trap["prefer_landing_capture"]
                       and thief != me and engine.board.is_passable(thief))
            return None if step_in else thief
        candidates = [c for c in thief_escapes if c in my_reach and not engine.board.is_barrier(c)]
        return candidates[0] if candidates else None


class ThiefForArena(BrainBase):
    """Evasion sparring partner for OUR self-play arena only (the real thief
    brain lives in the P2P-Thief repo): maximize BFS distance from the cop."""

    def decide(self, engine: GameEngine, belief=None) -> dict:
        cop = belief.argmax_cell() if belief is not None else engine.positions[Role.POLICE]
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
