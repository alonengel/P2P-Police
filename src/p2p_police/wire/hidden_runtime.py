"""Hidden-information game loop (wire_shape "reference") — an ADDITIONAL
mode beside GeometricRuntime; the bookletter lockstep runtime stays the
untouched default. One TurnMessage per half-turn, moves sealed until audit,
the rival's position structurally unknown (OwnState has no field for it).

Reuses the hardened machinery rather than forking it: the SealedExchange
receiver (dedup / reorder buffer / flood cap / one-deadline-per-expectation)
via HiddenExchange, the Deadline discipline, the watchdog heartbeat seam,
Perception (belief is the ONLY rival estimate — rules 8-9), the self-mirror
Deceiver and the template hint chain (moves stay pure Python, rule 25).
"""

import queue

from p2p_police.domain.errors import GameRuleError
from p2p_police.domain.negotiation import build_agreement, verify_agreement
from p2p_police.domain.primitives import GamePhase, Outcome, Role
from p2p_police.domain.state_machine import GamePhaseMachine
from p2p_police.peer.deadline import Deadline, DeadlineExpiredError
from p2p_police.peer.perception import Perception
from p2p_police.peer.watchdog import NullWatchdog
from p2p_police.shared.sysinfo import hardware_spec
from p2p_police.strategy.deception import Deceiver
from p2p_police.strategy.talk_providers import build_talk_chain
from p2p_police.wire import hidden_turns, lock
from p2p_police.wire.hidden_exchange import HiddenExchange
from p2p_police.wire.own_state import OwnState


class HiddenRuntime:
    """One peer's hidden-mode game loop. Input: role, config, OwnState,
    transport + inboxes, brain. Output: an end report (outcome, audit,
    reconstructed digest, turns)."""

    def __init__(
        self,
        role: Role,
        config,
        own: OwnState,
        transport,
        inboxes,
        brain,
        gatekeeper=None,
    ) -> None:
        self.role, self.config, self.own = role, config, own
        self.transport, self.inboxes, self.brain = transport, inboxes, brain
        self.perception = Perception(role, config.grid_size)
        self.deceiver = Deceiver(role, config, brain.rng)
        self.talk = build_talk_chain(config, brain.rng, gatekeeper)
        self.fsm = GamePhaseMachine()
        self.watchdog = NullWatchdog()  # SDK swaps in the real one (rule 7)
        self.exchange = HiddenExchange(
            role,
            int(config.private["game"]["sub_game_number"]),
            lambda msg: self.transport.send_turn(
                msg, Deadline(self.config.turn_timeout_seconds)
            ),
            self._wait_turn,
            turn_timeout=config.turn_timeout_seconds,
        )
        self.pending_claim_response: dict | None = None

    def _wait(self, inbox: queue.Queue, what: str, deadline=None) -> dict:
        deadline = deadline or Deadline(self.config.turn_timeout_seconds)
        while True:
            self.watchdog.beat()  # polling IS liveness; deadlines guard rivals
            deadline.require(what)
            try:
                return inbox.get(timeout=min(0.25, max(0.01, deadline.remaining())))
            except queue.Empty:
                continue

    def _wait_turn(self, what: str, deadline=None) -> dict:
        """Adapt raw TurnMessages to the hardened receiver's (kind, turn)
        expectation keys — forced LAST so a hostile message cannot spoof."""
        message = self._wait(self.inboxes.turns, what, deadline)
        try:
            step = int(message.get("step", -1))
        except (TypeError, ValueError):
            step = -1
        return {**message, "kind": "turn", "turn": step}

    def negotiate(self) -> dict:
        mine = build_agreement(
            self.config.shared,
            self.config.group_id,
            hardware_spec(),
            info_mode="belief",  # structural under this wire (registry note)
            identity=self.config.identity_block(),
        )
        lock.extend_agreement(mine, self.config)
        self.transport.send_agreement(mine, Deadline(self.config.turn_timeout_seconds))
        theirs = self._wait(self.inboxes.agreements, "opponent agreement")
        verify_agreement(mine, theirs)
        lock.verify_wire_shape(mine, theirs)
        self.opponent_info = theirs
        self.opponent_group_id = self.perception.opponent_id = theirs.get(
            "group_id", "unknown"
        )
        return theirs

    def play(self) -> dict:
        """Full hidden-mode game; failures route to TECHNICAL_LOSS (rules 4-6)."""
        try:
            self.negotiate()
            step = 0
            while self.own.outcome is Outcome.ONGOING:
                step += 1
                self.watchdog.beat()  # heartbeat per half-turn (rule 7)
                if self.own.next_actor is self.role:
                    hidden_turns.my_half_turn(self, step)
                else:
                    step = hidden_turns.their_half_turn(self, step)
        except (DeadlineExpiredError, GameRuleError):
            if self.fsm.can_transition(GamePhase.TECHNICAL_LOSS):
                self.fsm.transition(GamePhase.TECHNICAL_LOSS)
            self.own.outcome = Outcome.TECHNICAL_LOSS
            raise
        return hidden_turns.finish(self)
