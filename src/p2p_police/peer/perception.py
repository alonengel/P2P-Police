"""Perception: one peer's LOCAL truth (rules 8-9) - belief, hints, snapshots.

Everything the live GUI may show flows through here: my cell, my belief map,
public barriers, the received hint. The rival's true position never does.

Trust boundary. Under the replicated-engine wire the rival's trail is a
CONSEQUENCE of applied moves, so it is unforgeable in the book's sense. Under
the reference wire it is TRANSMITTED - `smell_grid` rides beside `commit`,
never inside it, so no end-of-game hash audit can ever check it. This module
is where an asserted trail becomes belief, so this is where it is held to the
movement model: a reading claiming a clamp-level deposit somewhere no emitter
moving a step per turn could have reached is refused WHOLE for that turn
(the diffused prior stands) rather than partly believed.
"""

from p2p_police.domain.belief import BeliefMap
from p2p_police.domain.engine import GameEngine
from p2p_police.domain.evidence import credible_cells, incredible_saturation
from p2p_police.domain.primitives import Outcome, Role
from p2p_police.strategy.hints import landmark_region, parse_claim
from p2p_police.strategy.profiler import OpponentProfiler


class Perception:
    """Input: opponent turns. Output: belief + GUI snapshots (local only).

    Setup: role, grid size, and optionally the AGREED rival start cell - the
    one rival position both sides signed, which seeds the movement model that
    keeps a forged trail from being believed.
    """

    def __init__(self, role: Role, grid_size: int, rival_start=None) -> None:
        self.role = role
        self.belief = BeliefMap(grid_size)
        self.last_hint = ""
        self.on_snapshot = None  # optional live-GUI feed
        self.profiler = OpponentProfiler()
        self.opponent_id = "unknown"
        self.grid_size = grid_size
        # Movement-model anchor: the AGREED start cell and the number of rival
        # turns since. It is deliberately never re-anchored to a later estimate.
        # Doing so measured catastrophic (pool capture 0.983 -> 0.358): a
        # walker's saturated trail legitimately extends BEHIND it, into cells
        # unreachable from where it stands now, so a tight rolling anchor
        # refuses honest readings - and with the latch below, one false
        # positive blinds us for the whole game. Anchoring on the start is
        # SOUND by construction (every position it ever held is within
        # `elapsed` steps of the start, so every legal deposit is allowed),
        # which is worth far more than being tight late: an unsound check on
        # this path is a self-inflicted denial of service.
        self._anchor = tuple(rival_start) if rival_start is not None else None
        self._anchor_age = 0
        self.refused_readings = 0  # evidence counter, surfaced in the summary
        self.scent_trusted = True  # latches false on a physically impossible reading

    @classmethod
    def for_peer(cls, role: Role, config) -> "Perception":
        """Build from the signed config, seeding the movement model with the
        rival's AGREED start cell. That cell is not local truth leaking - it
        is a public term both sides committed to, and it is what makes the
        very first forged reading checkable instead of merely plausible."""
        rival_start = config.thief_start if role is Role.POLICE else config.cop_start
        return cls(role, config.grid_size, rival_start=rival_start)

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
        self._anchor_age += 1
        allowed = credible_cells(engine.board, self._anchor,
                                 self._anchor_age, self.grid_size)
        if self.scent_trusted and incredible_saturation(
            rival_scent, engine.board, self.grid_size, allowed
        ):
            # A reading that breaks the movement model is not partly true, and
            # half-believing it is exactly how a forgery steers us. One such
            # reading is already proof the channel is broken or hostile, so the
            # refusal LATCHES: re-checking each turn independently is what let
            # the first version be defeated, because a refused turn cannot
            # refresh the anchor and the reachable set grows to the whole board
            # within a few turns. There is no recovering information from a
            # channel that lies - the achievable goal is to stop being STEERED
            # by it, and to leave the refusal in the record for the audit.
            self.scent_trusted = False
        if not self.scent_trusted:
            self.refused_readings += 1
            return  # belief runs on diffusion, hints and barrier origins only
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
