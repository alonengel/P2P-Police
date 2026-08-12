"""Decoy cop for FRIENDLY sparring only — yesterday's follower, on purpose.

League rivals tune against whatever we show them in friendlies (we tune
against their tapes the same way; nis-yar1 rebuilt their whole cop between
two of ours). The interception cop is our counted-day weapon and it has
already been live-validated (g05, 2026-08-11, capture at 23) — every extra
friendly it plays is free tape for their next counter. This decoy is the
PRE-interception brain, bit for bit: same walls, same endgame, same belief;
it simply never leads the target, so rivals keep tuning against the
tail-chaser they already beat.

Selection is config-only (never code): the FRIENDLY overlay sets
    [strategy]
    police_class = "p2p_police.strategy.decoy:DecoyPoliceBrain"
and the counted overlay leaves [strategy] unset, which ships the real brain.
Friendlies are uncounted practice — no rule governs how strong a practice
opponent must be, and every sealed record stays honest either way.
"""

from p2p_police.strategy.police_brain import PoliceBrain


class DecoyPoliceBrain(PoliceBrain):
    """PoliceBrain with the interception permanently disarmed."""

    def decide(self, engine, belief=None) -> dict:
        # A never-steady heading gates interception off (police_brain fires
        # only on two equal consecutive peak steps); everything else — trap
        # walls, endgame solver, info-gain pursuit — is the shipped brain.
        self._prev_peak = None
        self._prev_vel = None
        return super().decide(engine, belief)


class StallDecoyPoliceBrain(DecoyPoliceBrain):
    """Metronome impersonation for FRIENDLY sparring: approach to gap 2 on
    the believed cell and HOLD — never close to 1, never place a wall.

    The bait: rivals who study the tape see the gap-2 hold they themselves
    play and read it as us adopting their cop. The natural counter-tune is
    a thief CONFIDENT at gap 2 — lingering, slipping past the holder — and
    that confidence is exactly what the counted-day brain's contact-dwell
    quota release converts. Selected only by the friendly overlay:
        [strategy]
        police_class = "p2p_police.strategy.decoy:StallDecoyPoliceBrain"
    """

    def decide(self, engine, belief=None) -> dict:
        from p2p_police.domain import protocol
        from p2p_police.domain.pathfind import bfs_distances
        from p2p_police.domain.primitives import Move, Role
        me = engine.positions[Role.POLICE]
        prey = belief.argmax_cell() if belief is not None else engine.positions[Role.THIEF]
        distances = bfs_distances(engine.board, prey)
        if distances.get(me, 99) <= 2:
            return protocol.move_action(Move.STAY)   # the hold, faithfully
        moves = [m for m in (Move.N, Move.S, Move.E, Move.W)
                 if engine.board.is_passable(m.applied_to(me))]
        if not moves:
            return protocol.move_action(Move.STAY)
        step = min(moves, key=lambda m: distances.get(m.applied_to(me), 99))
        return protocol.move_action(step)
