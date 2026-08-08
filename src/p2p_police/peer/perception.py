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
from p2p_police.domain.primitives import Outcome, Role
from p2p_police.domain.trail_forensics import (
    credible_cells,
    incredible_saturation,
    transition_emitters,
)
from p2p_police.strategy.hints import landmark_region, parse_claim, parse_move_echo
from p2p_police.strategy.profiler import OpponentProfiler


class Perception:
    """Input: opponent turns. Output: belief + GUI snapshots (local only).

    Setup: role, grid size, and optionally the AGREED rival start cell - the
    one rival position both sides signed, which seeds the movement model that
    keeps a forged trail from being believed.
    """

    def __init__(self, role: Role, grid_size: int, rival_start=None,
                 hint_cap: int = 15) -> None:
        self.role = role
        self.belief = BeliefMap(grid_size)
        self.last_hint = ""
        # Inbound VIEW cap (the signed hint_max_words): belief/GUI/profiler
        # never consume more words than the rival signed for; the MESSAGE
        # stays untouched — the audit's live-vs-sealed hint check must
        # compare originals (imreeyal parity hardening, 2026-08-03).
        self._hint_cap = int(hint_cap)
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
        self._previous_field: list | None = None  # last accepted frame
        self._law_breaks = 0  # consecutive frames no single emitter explains

    @classmethod
    def for_peer(cls, role: Role, config) -> "Perception":
        """Build from the signed config, seeding the movement model with the
        rival's AGREED start cell. That cell is not local truth leaking - it
        is a public term both sides committed to, and it is what makes the
        very first forged reading checkable instead of merely plausible."""
        rival_start = config.thief_start if role is Role.POLICE else config.cop_start
        return cls(role, config.grid_size, rival_start=rival_start,
                   hint_cap=int(config.shared["world"].get("hint_max_words", 15)))

    def observe(
        self, engine: GameEngine, rival: Role, hint_text: str | None,
        barrier_cell=None,
    ) -> None:
        """Diffuse, weigh rival scent, then the (lie-checked) hint (ch. 4).

        A freshly declared barrier placement (passed by the runtime the turn
        it lands) first pins the placer's origin cells — law of barriers."""
        if hint_text:  # inbound view capped at the signed word limit
            hint_text = " ".join(hint_text.split()[: self._hint_cap])
        self.last_hint = hint_text or ""
        # A literal move-echo IS the movement model for this turn (league
        # rival 2026-08-08); anything else keeps the one-step diffusion.
        echo = parse_move_echo(hint_text) if hint_text else None
        if echo:
            self.belief.observe_motion(echo, engine.board)
        else:
            self.belief.diffuse(engine.board)
        if barrier_cell is not None:
            self.belief.observe_barrier(
                (barrier_cell[0], barrier_cell[1]), engine.board)
        rival_scent = engine.scent[rival]
        self._anchor_age += 1
        allowed = credible_cells(engine.board, self._anchor,
                                 self._anchor_age, self.grid_size)
        broken = self._breaks_the_law(rival_scent, engine.board)
        if self.scent_trusted and incredible_saturation(
            rival_scent, engine.board, self.grid_size, allowed
        ):
            # The envelope check is a GROSS violation: saturation somewhere no
            # emitter could have reached is not transport noise, so it latches
            # outright. Re-checking it per turn is defeatable anyway - a refused
            # turn cannot refresh the anchor, and the allowed set then relaxes
            # to the whole board within a few turns.
            self.scent_trusted = False
        # The baseline advances to whatever ARRIVED, accepted or refused.
        # Holding it at the last ACCEPTED frame never recovers: every later
        # frame then sits two-or-more advances away and breaks forever, so a
        # single glitch blinds the peer for the rest of the game. Advancing
        # costs exactly two poisoned comparisons - the bad frame, and the
        # honest one paired against it - and then honest traffic re-accepts.
        self._previous_field = rival_scent.values()
        if broken or not self.scent_trusted:
            self.refused_readings += 1
            return  # belief runs on diffusion, hints and barrier origins only
        self.belief.observe_scent(rival_scent, engine.board)
        # Hint tiers: directional claim first; place-name talk falls through
        # to the gazetteer and lands as a region observation. Both carry the
        # profiler's reputation weights; both stay scent-lie-checked.
        # An echo already consumed the hint as motion — no region double-count.
        claim = None if echo else (parse_claim(hint_text) if hint_text else None)
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

    def _breaks_the_law(self, rival_scent, board) -> bool:
        """Do two consecutive frames admit NO single emitter (ADR-0010)?


        This is the check that closes the gap the reachability envelope leaves:
        a forgery can walk its decoy one legal step per turn, but the update law
        binds the whole board, so it would also have to move its own HISTORY -
        and a cell may never fall below (1-rho) times its previous value.

        EVERY break refuses the frame - a reading the law cannot explain never
        reaches belief, which is the same rule we ask of anyone else. The
        LATCH is separate and needs three in a row, because a single transient
        frame necessarily poisons two comparisons (itself, and the honest one
        paired against it); latching at two would make every glitch permanent.
        """
        if self._previous_field is None:
            return False  # nothing to compare the first frame against
        if not any(any(row) for row in rival_scent.values()):
            # An EMPTY field is absence of data, not impossible data. A peer
            # honouring a lock that says the trail is not transmitted sends
            # nothing to check, and refusing that would latch us against a peer
            # doing exactly what the declared lock asks. (Under book-v1 an
            # empty field explains no emitter at all, so without this the
            # checker refuses every frame of such a game.)
            return False
        if transition_emitters(self._previous_field, rival_scent.values(),
                               board, self.grid_size):
            self._law_breaks = 0
            return False
        self._law_breaks += 1
        if self._law_breaks >= 3:
            self.scent_trusted = False
        return True

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
