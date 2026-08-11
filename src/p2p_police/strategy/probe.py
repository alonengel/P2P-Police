"""Probe cop for FRIENDLY sparring — a decoy that runs experiments.

A friendly is the only place we see their thief react to APPROACHES WE
CHOOSE. This brain closes on the believed thief along a configured bearing,
then STALKS at a held distance for a set number of turns before closing one
ring — each stalk ring is a question: at what gap does the percher wake?
which way does it break when pressed from the north vs the west? The
answers are read afterwards from the tapes (their revealed moves against
our known approach schedule). It doubles as a decoy — the interception cop
stays unseen.

Selection and script are config-only (FRIENDLY overlay):
    [strategy]
    police_class = "p2p_police.strategy.probe:ProbeCopBrain"
    [strategy.probe]
    bearing = [1, 0]      # approach offset: come from the north side
    stalk_gap = 3         # hold this BFS distance...
    stalk_turns = 4       # ...for this many turns, then tighten one ring
Belief-only, truth-blind; walls are never spent (a probe maps the prey, it
does not spring the trap). Sealed records stay honest throughout.
"""

from p2p_police.domain import protocol
from p2p_police.domain.pathfind import bfs_distances
from p2p_police.domain.primitives import Move, Role
from p2p_police.strategy.brain_base import BrainBase

PROBE_DEFAULTS: dict = {"bearing": [1, 0], "stalk_gap": 3, "stalk_turns": 4}


class ProbeCopBrain(BrainBase):
    """Bearing approach + ring stalking; belief-only, wall-free."""

    def __init__(self, role, rng, config=None) -> None:
        super().__init__(role, rng)
        table = {**PROBE_DEFAULTS,
                 **(config.private.get("strategy", {}).get("probe", {})
                    if config is not None else {})}
        self.bearing = tuple(table["bearing"])
        self.gap = int(table["stalk_gap"])
        self.stalk_turns = int(table["stalk_turns"])
        self._held = 0

    def decide(self, engine, belief=None) -> dict:
        me = engine.positions[Role.POLICE]
        prey = belief.argmax_cell() if belief is not None else engine.positions[Role.THIEF]
        # Aim at the offset post: the prey's cell shifted along our bearing,
        # so the approach arrives from the configured side.
        post = (prey[0] + self.bearing[0] * self.gap,
                prey[1] + self.bearing[1] * self.gap)
        if not engine.board.is_passable(post):
            post = prey
        distances = bfs_distances(engine.board, prey)
        here = distances.get(me, 10**6)
        if here <= self.gap:  # on the ring: hold, then tighten one step
            self._held += 1
            if self._held <= self.stalk_turns:
                return protocol.move_action(Move.STAY)
            self._held = 0
            self.gap = max(1, self.gap - 1)
        target = post if here > self.gap else prey
        path = bfs_distances(engine.board, target)
        moves = [m for m in (Move.N, Move.S, Move.E, Move.W)
                 if engine.board.is_passable(m.applied_to(me))]
        if not moves:
            return protocol.move_action(Move.STAY)
        step = min(moves, key=lambda m: path.get(m.applied_to(me), 10**6))
        return protocol.move_action(step)
