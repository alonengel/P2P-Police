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

import logging
import queue
import time
from datetime import UTC, datetime

from p2p_police.domain.errors import GameRuleError
from p2p_police.domain.primitives import GamePhase, Outcome, Role
from p2p_police.domain.state_machine import GamePhaseMachine
from p2p_police.peer.deadline import Deadline, DeadlineExpiredError
from p2p_police.peer.perception import Perception
from p2p_police.peer.resume import NullResume
from p2p_police.peer.sealing import pending_cap_from
from p2p_police.peer.watchdog import NullWatchdog
from p2p_police.shared.info_modes import REFERENCE, resolve
from p2p_police.shared.sysinfo import hardware_spec
from p2p_police.strategy.deception import Deceiver
from p2p_police.strategy.talk_providers import build_talk_chain
from p2p_police.wire import hidden_resume, hidden_turns, lock, repush, terms
from p2p_police.wire.hidden_exchange import HiddenExchange
from p2p_police.wire.own_state import OwnState

_LOG = logging.getLogger(__name__)


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
        self.perception = Perception.for_peer(role, config)
        # Structural, not chosen: this wire carries no rival position, so the
        # registry refuses any regime that would need one (ADR-0006/0010).
        self.mode = resolve(config.info_mode(REFERENCE), REFERENCE)
        self.deceiver = Deceiver(role, config, brain.rng)
        self.talk = build_talk_chain(config, brain.rng, gatekeeper)
        self.fsm = GamePhaseMachine()
        # SDK swaps in the real watchdog (rule 7) / resume recorder (E6)
        self.watchdog, self.resume = NullWatchdog(), NullResume()
        self.exchange = HiddenExchange(
            role,
            int(config.private["game"]["sub_game_number"]),
            lambda msg: self.transport.send_turn(
                msg, Deadline(self.config.turn_timeout_seconds)
            ),
            self._wait_turn,
            turn_timeout=config.turn_timeout_seconds,
            pending_cap=pending_cap_from(config),
        )
        self.pending_claim_response: dict | None = None
        self.clock = time.monotonic  # injectable seam for the repush tests
        # Series-report timestamp: this instance's game start (UTC ISO).
        self.started_at = datetime.now(UTC).isoformat(timespec="seconds")
        # PER-SENDER step clocks (demo own_state.apply_move: step_number
        # advances only on OWN moves — each side numbers 1, 2, 3...).
        self.my_step = 0
        self.their_step = 0

    def _wait(self, inbox: queue.Queue, what: str, deadline=None) -> dict:
        deadline = deadline or Deadline(self.config.turn_timeout_seconds)
        while True:
            self.watchdog.beat()  # polling IS liveness; deadlines guard rivals
            hidden_resume.handle_controls(self)  # a restarted rival's offer
            repush.answer_reoffers(self)  # a re-offering rival still lacks ours
            deadline.require(what)
            try:
                return inbox.get(timeout=min(0.25, max(0.01, deadline.remaining())))
            except queue.Empty:
                continue

    def _wait_turn(self, what: str, deadline=None) -> dict:
        """Adapt raw TurnMessages to the hardened receiver's (kind, turn)
        expectation keys — forced LAST so a hostile message cannot spoof.

        Both senders count 1, 2, 3... so a message echoing OUR OWN role can
        collide with the rival's same-numbered step: drop it as transport
        noise (the deadline keeps judging the rival). A caught=True final is
        keyed to the CURRENT expectation — the demo's send_final re-uses the
        thief's LAST step number (no apply_move before it), so keying it by
        its embedded number would dedup-drop the concession we are owed."""
        while True:
            message = self._wait(self.inboxes.turns, what, deadline)
            if message.get("sender") == self.role.value:
                _LOG.info("inbound_tolerated kind=%s turn=%s reason=%s", "turn",
                          message.get("step"), "own-role echo, never protocol content")
                continue  # our own echo
            try:
                step = int(message.get("step", -1))
            except (TypeError, ValueError):
                step = -1
            response = message.get("claim_response")
            if isinstance(response, dict) and response.get("caught"):
                step = self.exchange.expected_turn or step
            return {**message, "kind": "turn", "turn": step}

    def negotiate(self) -> dict:
        """Reference-v3 flat-terms handshake: signed {terms, nonce, signature}
        (kit CORE vector form — never the bookletter config_sha256), our
        declarations riding alongside under the both-declare refusal rule."""
        mine = terms.build_negotiate_message(
            self.config,
            hardware_spec(),
            info_mode=self.mode.name,  # registry-checked for this wire
            # both-declare guard: a leftover rival instance from a previous
            # window must not pair into the wrong sub-game (uid can't tell).
            sub_game=int(self.config.private["game"]["sub_game_number"]),
            role=self.role.value,  # complementary-role guard (equal refuses)
            # Declared when we know who we are playing: the uid never crosses
            # the wire otherwise, so a derivation-input mismatch stays silent
            # until the reports are diffed.
            opponent_group_id=self.config.opponent_group_id(),
        )
        lock.extend_agreement(mine, self.config)

        def verify(theirs: dict) -> None:
            """Ran INSIDE the wait: a PairingRefusalError (bystander: wrong window
            or our role) keeps the wait alive; the rest stays fatal."""
            terms.verify_terms_message(mine["terms"], theirs)
            terms.verify_declarations(mine, theirs)
            lock.verify_wire_shape(mine, theirs)
            lock.verify_info_mode(mine, theirs)

        # re-push until a VERIFIED counterpart arrives: a greeting swallowed
        # by the rival's dying previous-sub-game peer gets fresh chances at
        # the real one, and a bystander's greeting never costs us the game
        theirs = repush.push_agreement(self, mine, self.clock, verify)
        self.opponent_info = theirs
        self.opponent_group_id = self.perception.opponent_id = terms.peer_group_id(theirs)
        return theirs

    def play(self, resume_from: int = 0) -> dict:
        """Full hidden-mode game; failures route to TECHNICAL_LOSS (rules 4-6).
        resume_from > 0 skips negotiation and continues a re-armed game (the
        per-sender clocks my_step/their_step were restored by the rearm)."""
        try:
            if resume_from == 0:
                self.negotiate()
                from p2p_police.wire.step_zero import seal_step_zero

                seal_step_zero(self)  # sealed commit-id declaration (rule 53)
            while self.own.outcome is Outcome.ONGOING:
                self.watchdog.beat()  # heartbeat per half-turn (rule 7)
                if self.own.next_actor is self.role:
                    hidden_turns.my_half_turn(self)
                else:
                    hidden_turns.their_half_turn(self)
                # E6 snapshot, indexed by total half-turns played
                self.resume.checkpoint(self, self.my_step + self.their_step)
        except (DeadlineExpiredError, GameRuleError):
            if self.fsm.can_transition(GamePhase.TECHNICAL_LOSS):
                self.fsm.transition(GamePhase.TECHNICAL_LOSS)
            self.own.outcome = Outcome.TECHNICAL_LOSS
            raise
        return hidden_turns.finish(self)
