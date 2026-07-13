"""Perception: one peer's LOCAL truth (rules 8-9) - belief, hints, snapshots.

Everything the live GUI may show flows through here: my cell, my belief map,
public barriers, the received hint. The rival's true position never does.
"""

from p2p_police.domain.belief import BeliefMap
from p2p_police.domain.engine import GameEngine
from p2p_police.domain.primitives import Outcome, Role
from p2p_police.strategy.hints import parse_claim
from p2p_police.strategy.profiler import OpponentProfiler


class Perception:
    """Input: opponent turns. Output: belief + GUI snapshots (local only)."""

    def __init__(self, role: Role, grid_size: int) -> None:
        self.role = role
        self.belief = BeliefMap(grid_size)
        self.last_hint = ""
        self.on_snapshot = None  # optional live-GUI feed
        self.profiler = OpponentProfiler()
        self.opponent_id = "unknown"

    def observe(self, engine: GameEngine, rival: Role, hint_text: str | None) -> None:
        """Diffuse, weigh rival scent, then the (lie-checked) hint (ch. 4)."""
        self.last_hint = hint_text or ""
        self.belief.diffuse(engine.board)
        rival_scent = engine.scent[rival]
        self.belief.observe_scent(rival_scent, engine.board)
        claim = parse_claim(hint_text) if hint_text else None
        if claim:
            self.belief.observe_hint(
                claim, rival_scent, self.profiler.advised_weights(self.opponent_id)
            )

    def emit(self, engine: GameEngine, turn_index: int) -> None:
        if self.on_snapshot is None:
            return
        self.on_snapshot(
            {
                "turn": turn_index,
                "my_cell": engine.positions[self.role],
                "my_role": self.role.value,
                "belief": self.belief.values(),
                "barriers": sorted(engine.board.barriers),
                "my_turn": engine.next_actor is self.role,
                "hint": self.last_hint,
                "outcome": engine.outcome.value,
                "game_over": engine.outcome is not Outcome.ONGOING,
            }
        )
