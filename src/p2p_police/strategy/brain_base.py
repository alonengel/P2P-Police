"""The strategy seam (rulebook ch. 6, Appendix VI Table 22).

`[strategy]` in game.toml may point at any "package.module:Class" brain; an
empty section runs the shipped heuristic. Moves are ALWAYS decided here in
pure Python — the LLM never navigates (rule 25 default).
"""

import random
from importlib import import_module

from p2p_police.domain import protocol
from p2p_police.domain.engine import GameEngine
from p2p_police.domain.primitives import Role


class BrainBase:
    """Contract every brain fulfills.

    Input: the replicated engine (full information at stage 3; belief-driven
    from stage 4). Output: one protocol action dict. Setup: role + RNG.
    """

    def __init__(self, role: Role, rng: random.Random) -> None:
        self.role = role
        self.rng = rng

    def decide(self, engine: GameEngine, belief=None) -> dict:
        """belief=None -> full information (arena); a BeliefMap when blind."""
        raise NotImplementedError


class RandomBrain(BrainBase):
    """Uniform random legal move — the arena baseline every real brain must beat."""

    def decide(self, engine: GameEngine, belief=None) -> dict:
        cell = engine.positions[self.role]
        return protocol.move_action(self.rng.choice(engine.board.legal_moves(cell)))


def resolve_brain(config, role: Role, rng: random.Random) -> BrainBase:
    """Build the configured brain, or the shipped heuristic when unset.

    Reads `[strategy] police_class/thief_class` = "pkg.module:Class" from the
    private config (Table 22); import errors surface loudly — a silently
    wrong brain would be a league-day disaster.
    """
    key = f"{role.value}_class"
    spec = config.private.get("strategy", {}).get(key)
    if spec:
        module_name, _, class_name = spec.partition(":")
        brain_class = getattr(import_module(module_name), class_name)
        return brain_class(role, rng)
    return _shipped_brain(role, rng)


def _shipped_brain(role: Role, rng: random.Random) -> BrainBase:
    if role is Role.POLICE:
        from p2p_police.strategy.police_brain import PoliceBrain

        return PoliceBrain(role, rng)
    return RandomBrain(role, rng)  # twin repo ships ThiefBrain here
