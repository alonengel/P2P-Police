"""Role strategy: brains behind the [strategy] seam. Moves are pure Python."""

from p2p_police.strategy.brain_base import BrainBase, RandomBrain, resolve_brain

__all__ = ["BrainBase", "RandomBrain", "resolve_brain"]
