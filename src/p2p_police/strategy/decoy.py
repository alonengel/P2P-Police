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
