"""Decoy cop: friendlies show the tail-chaser, counted ships the interceptor."""

import random
from types import SimpleNamespace

from p2p_police.domain.belief import BeliefMap
from p2p_police.domain.engine import GameEngine
from p2p_police.domain.primitives import Role
from p2p_police.domain.rules import RuleSet
from p2p_police.strategy.brain_base import resolve_brain
from p2p_police.strategy.decoy import DecoyPoliceBrain
from p2p_police.strategy.police_brain import PoliceBrain

RULES = RuleSet(max_barriers=14, max_moves=35, survival_threshold=35)


def _pin(belief: BeliefMap, cell) -> BeliefMap:
    belief.observe_claimed_cell(cell)
    return belief


def test_decoy_never_arms_interception() -> None:
    """Feed both brains the same steadily-marching peak (two E steps): the
    real brain leads the runner; the decoy keeps chasing the peak itself.
    Divergence is asserted on the internal velocity state — the decoy must
    never see a steady heading, whatever the geometry."""
    engine = GameEngine(7, (3, 0), (3, 6), RULES)
    real = PoliceBrain(Role.POLICE, random.Random(3))
    decoy = DecoyPoliceBrain(Role.POLICE, random.Random(3))
    for peak in ((0, 2), (0, 3), (0, 4)):
        belief = _pin(BeliefMap(7), peak)
        real.decide(engine, belief)
        decoy.decide(engine, belief)
    assert real._prev_vel == (0, 1)      # armed: two equal consecutive steps
    assert decoy._prev_vel is None       # decoy: permanently disarmed


def test_overlay_seam_selects_the_decoy_and_defaults_to_the_real_brain() -> None:
    decoy_cfg = SimpleNamespace(private={"strategy": {
        "police_class": "p2p_police.strategy.decoy:DecoyPoliceBrain"}})
    picked = resolve_brain(decoy_cfg, Role.POLICE, random.Random(0))
    assert type(picked) is DecoyPoliceBrain
    bare = resolve_brain(SimpleNamespace(private={}), Role.POLICE, random.Random(0))
    assert type(bare) is PoliceBrain
