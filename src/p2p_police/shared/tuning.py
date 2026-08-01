"""Strategy-layer tunables: [strategy.endgame] / [strategy.info_gain] /
[strategy.trap] / [deception] defaults.

Both tables live in the PRIVATE config (game.toml) - pure play-strength
knobs, never agreed game terms. The defaults below encode the measured
keep-gate verdict (docs/evidence/cop-strength.md); Config accessors in
shared/config.py merge the TOML block over them, coercing each value to the
default's type so a TOML int never silently changes a float comparison.
Brains built without a Config (unit arenas) run on these same defaults.
"""

ENDGAME_DEFAULTS: dict = {
    "enabled": True,               # keep-gate RE-OPENED 2026-07-26. It failed while
    #                                the scent-floor belief never sharpened to a
    #                                provable support (0 fires / 160 games even at
    #                                K=8). The dwell-plateau pin sharpened it: 230
    #                                fires / 120 games, capture 0.625 -> 0.850 over
    #                                the whole evader pool. The old verdict was
    #                                about the BELIEF, not the solver.
    "max_support_cells": 3,        # run only when the belief support is this sharp
    "support_mass_threshold": 0.05,  # cells at/above this mass form the support
    "max_horizon_turns": 5,        # lookahead in full turns; min(this, turns left)
    "node_cap": 20000,             # search states before deferring to the heuristic
    "time_cap_ms": 150.0,          # wall-clock cap - never risk the turn deadline
}

INFO_GAIN_DEFAULTS: dict = {
    "enabled": True,               # keep-gate RE-OPENED 2026-07-26, but ONLY in
    #                                combination: alone it still measures NEGATIVE
    #                                (0.558 vs 0.625 baseline, 0 solver fires). Its
    #                                value is an interaction - steering toward
    #                                informative cells opens the solver's support
    #                                gate 29% more often (230 -> 296 fires), taking
    #                                the pair to 0.983. Never enable it alone.
    "weight": 1.0,                 # entropy nats traded per BFS step in the blend
    "match_tolerance": 0.08,       # kernel readings this close are indistinguishable
    "mismatch_likelihood": 0.15,   # mass retained by hypotheses the reading refutes
}


TRAP_DEFAULTS: dict = {
    "escape_limit": 3,             # wall only a thief down to this many exits...
    "range": 3,                    # ...and already this close in BFS steps
    #                                Both were 2 while the posterior was too
    #                                blunt to justify a placement; with the
    #                                dwell-plateau pin the quota is worth
    #                                spending a step earlier - swept 2/3/4/5
    #                                over 60-150 games, 3 wins outright
    #                                (docs/evidence/cop-strength.md)
    "prefer_landing_capture": True,  # when the believed cell is a legal STEP,
    #                                take the step instead of walling it. A
    #                                LANDING capture is claim-mediated: the
    #                                rival's truth duty must answer it. A
    #                                barrier capture (rules 46/47) is only ever
    #                                self-declared by the rival, so a peer that
    #                                never runs its own imprisonment check just
    #                                plays on - measured live 2026-08-01, three
    #                                sealed-in games scored as survival.
}


DECEPTION_DEFAULTS: dict = {
    "max_lies": 2,                 # conservative cop budget - lie only while closing
    "cooldown_turns": 6,           # minimum full turns between lies
    "exposure_threshold": 0.4,     # mirror mass near our true cell that arms a lie
    "opponent_distance_threshold": 2,  # believed rival distance: mask the approach
    "exposure_radius": 1,          # Manhattan radius of the exposure mass
    "baseline_truth_probability": 0.5,
}


def _merge(defaults: dict, block: dict) -> dict:
    merged = dict(defaults)
    for key, default in defaults.items():
        if key in block:
            merged[key] = type(default)(block[key])
    return merged


def endgame_table(private: dict) -> dict:
    """[strategy.endgame] from a private-config dict, defaults filled in."""
    return _merge(ENDGAME_DEFAULTS, private.get("strategy", {}).get("endgame", {}))


def info_gain_table(private: dict) -> dict:
    """[strategy.info_gain] from a private-config dict, defaults filled in."""
    return _merge(INFO_GAIN_DEFAULTS, private.get("strategy", {}).get("info_gain", {}))


def trap_table(private: dict) -> dict:
    """[strategy.trap] from a private-config dict, defaults filled in."""
    return _merge(TRAP_DEFAULTS, private.get("strategy", {}).get("trap", {}))


def deception_table(private: dict) -> dict:
    """[deception] self-mirror lie policy (private, never a signed term)."""
    return _merge(DECEPTION_DEFAULTS, private.get("deception", {}))
