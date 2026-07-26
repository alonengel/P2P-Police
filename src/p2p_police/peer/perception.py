"""Perception: one peer's LOCAL truth (rules 8-9) - belief, hints, snapshots.

Everything the live GUI may show flows through here: my cell, my belief map,
public barriers, the received hint. The rival's true position never does.
"""

from p2p_police.domain.belief import BeliefMap
from p2p_police.domain.engine import GameEngine
from p2p_police.domain.primitives import Outcome, Role
from p2p_police.strategy.hints import landmark_region, parse_claim
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

    def observe(
        self, engine: GameEngine, rival: Role, hint_text: str | None,
        barrier_cell=None,
    ) -> None:
        """Diffuse, weigh rival scent, then the (lie-checked) hint (ch. 4).

        A freshly declared barrier placement (passed by the runtime the turn
        it lands) first pins the placer's origin cells — law of barriers."""
        self.last_hint = hint_text or ""
        self.belief.diffuse(engine.board)
        if barrier_cell is not None:
            self.belief.observe_barrier(
                (barrier_cell[0], barrier_cell[1]), engine.board)
        rival_scent = engine.scent[rival]
        self.belief.observe_scent(rival_scent, engine.board)
        # Hint tiers: directional claim first; place-name talk falls through
        # to the gazetteer and lands as a region observation. Both carry the
        # profiler's reputation weights; both stay scent-lie-checked.
        claim = parse_claim(hint_text) if hint_text else None
        weights = self.profiler.advised_weights(self.opponent_id)
        if claim:
            self.belief.observe_hint(claim, rival_scent, weights)
        else:
            region = landmark_region(hint_text, self.belief.grid_size) if hint_text else None
            if region:
                self.belief.observe_region(region, rival_scent, weights)
        # Last, and deliberately: a fitted dwell plateau is physics the rival
        # emitted about itself, so it outranks anything it CHOSE to say.
        self.belief.observe_plateau(rival_scent, engine.board)

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
