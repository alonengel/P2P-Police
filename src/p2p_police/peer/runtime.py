"""Geometric peer runtime (PRD 02): negotiate, lockstep turn loop, end check.
Both peers replicate the SAME GameEngine and apply both actions locally, so
the physics never diverges; moves come from the [strategy] seam (PRD 03) and
per-half-turn crash-resume checkpoints live in peer/resume.py (E6)."""

import contextlib
import queue

from p2p_police.domain import protocol
from p2p_police.domain.engine import GameEngine
from p2p_police.domain.errors import GameRuleError
from p2p_police.domain.negotiation import build_agreement, verify_agreement
from p2p_police.domain.primitives import GamePhase, Move, Outcome, Role
from p2p_police.domain.state_machine import GamePhaseMachine
from p2p_police.infra.mcp_client import McpTransport
from p2p_police.infra.mcp_server import PeerInboxes
from p2p_police.peer.deadline import Deadline, DeadlineExpiredError
from p2p_police.peer.perception import Perception
from p2p_police.peer.resume import NullResume, handle_controls
from p2p_police.peer.sealing import SealedExchange
from p2p_police.peer.watchdog import NullWatchdog
from p2p_police.shared.sysinfo import hardware_spec
from p2p_police.strategy.brain_base import BrainBase
from p2p_police.strategy.deception import Deceiver
from p2p_police.strategy.talk_providers import build_talk_chain


class GeometricRuntime:
    """One peer's game loop. Input: role, config, replicated engine,
    transport + inboxes. Output: an end report (outcome, digests, turns)."""

    def __init__(
        self,
        role: Role,
        config,
        engine: GameEngine,
        transport: McpTransport,
        inboxes: PeerInboxes,
        brain: BrainBase,
        gatekeeper=None,
    ) -> None:
        self.role, self.config, self.engine = role, config, engine
        self.transport, self.inboxes = transport, inboxes
        # Local truth only: belief about the RIVAL, fed by scent + hints.
        self.brain, self.perception = brain, Perception(role, config.grid_size)
        self.deceiver = Deceiver(role, config, brain.rng)  # self-mirror lie policy
        self.talk = build_talk_chain(config, brain.rng, gatekeeper)
        self.fsm = GamePhaseMachine()
        # SDK swaps in the real watchdog (rule 7) / resume recorder (E6)
        self.watchdog, self.resume = NullWatchdog(), NullResume()

        self.exchange = SealedExchange(
            role,
            int(config.private["game"]["sub_game_number"]),
            lambda msg: self.transport.send_turn(
                msg, Deadline(self.config.turn_timeout_seconds)
            ),
            lambda what: self._wait(self.inboxes.turns, what),
        )

    def _wait(self, inbox: queue.Queue, what: str) -> dict:
        deadline = Deadline(self.config.turn_timeout_seconds)
        while True:
            self.watchdog.beat()  # polling IS liveness; deadlines guard rivals
            handle_controls(self)  # e.g. a resume_offer from a restarted rival
            deadline.require(what)
            try:
                return inbox.get(timeout=min(0.25, max(0.01, deadline.remaining())))
            except queue.Empty:
                continue

    def negotiate(self) -> dict:
        mine = build_agreement(self.config.shared, self.config.group_id, hardware_spec(),
                               info_mode=self.config.info_mode(),
                               identity=self.config.identity_block())
        self.transport.send_agreement(mine, Deadline(self.config.turn_timeout_seconds))
        theirs = self._wait(self.inboxes.agreements, "opponent agreement")
        verify_agreement(mine, theirs)
        self.opponent_info = theirs  # identity + hashes: persisted into artifacts
        self.opponent_group_id = self.perception.opponent_id = theirs.get("group_id", "unknown")
        return theirs

    def _my_half_turn(self, turn_index: int) -> None:
        self.fsm.transition(GamePhase.COMPUTING_MOVE)
        # [strategy] info_mode: "belief" (default - the Dec-POMDP posture) or
        # "exact" - legal ONLY under a pair-locked bookletter wire, where every
        # position arrived via the agreed protocol and is shared local
        # knowledge (joint ADR line). The live UI shows belief either way.
        exact = self.config.info_mode() == "exact"
        action = self.brain.decide(self.engine, None if exact else self.perception.belief)
        moved = action["move"] if action["type"] == "move" else "STAY"
        claim, truth = self.deceiver.plan_hint(
            self.engine, self.perception, Move[moved], turn_index)
        self.fsm.transition(GamePhase.COMMITTING)
        self.exchange.send_sealed(self.engine, turn_index, action,
                                  self.talk.render(claim, turn_index), truth)
        self.fsm.transition(GamePhase.AWAITING_REVEAL)
        protocol.apply_action(self.engine, self.role, action)
        self.deceiver.observe_own(self.engine, claim)  # mirror sees what leaked
        self.fsm.transition(GamePhase.VERIFYING)
        self.fsm.transition(GamePhase.WAITING_FOR_OPPONENT)
        self.perception.emit(self.engine, turn_index)

    def _their_half_turn(self, turn_index: int) -> None:
        payload = self.exchange.receive_sealed(turn_index)
        actor = Role(payload["role"])
        if actor is self.role:
            raise GameRuleError("opponent claimed our role in a sealed record")
        protocol.apply_action(self.engine, actor, payload["action"])
        self.perception.observe(self.engine, actor, payload.get("hint"))
        self.perception.emit(self.engine, turn_index)


    def play(self, resume_from: int = 0) -> dict:
        """Full lockstep game; failures route to TECHNICAL_LOSS (rules 4-6).
        resume_from > 0 skips negotiation and continues a re-armed game."""
        try:
            if resume_from == 0:
                self.negotiate()
            turn_index = resume_from
            while self.engine.outcome is Outcome.ONGOING:
                turn_index += 1
                self.watchdog.beat()  # heartbeat per half-turn (rule 7)
                if self.engine.next_actor is self.role:
                    self._my_half_turn(turn_index)
                else:
                    self._their_half_turn(turn_index)
                self.resume.checkpoint(self, turn_index)  # E6 half-turn snapshot
        except (DeadlineExpiredError, GameRuleError):
            if self.fsm.can_transition(GamePhase.TECHNICAL_LOSS):
                self.fsm.transition(GamePhase.TECHNICAL_LOSS)
            self.engine.outcome = Outcome.TECHNICAL_LOSS
            raise
        return self._finish()

    def _finish(self) -> dict:
        digest = protocol.end_state_digest(self.engine)
        # Best-effort: if the opponent tore down right after ITS audit
        # reached us, our send may fail although the exchange succeeded.
        with contextlib.suppress(DeadlineExpiredError):
            self.transport.send_audit(
                {
                    "end_state_digest": digest,
                    "group_id": self.config.group_id,
                    "nonces": self.exchange.own_nonces(),
                    "verdicts": self.exchange.own_verdicts(),
                },
                Deadline(self.config.turn_timeout_seconds),
            )
        audit_verdict, digest_match = "not received", False
        try:
            theirs = self._wait(self.inboxes.audits, "opponent audit (nonces + digest)")
            digest_match = theirs.get("end_state_digest") == digest
            self.exchange.apply_revealed_verdicts(theirs.get("verdicts", []))
            audit_verdict = self.exchange.audit_theirs(theirs.get("nonces", []))
            if audit_verdict == "Verified OK":  # never learn from tampered data
                self.perception.profiler.record_audited_verdicts(self.perception.opponent_id, theirs.get("verdicts", []))
        except DeadlineExpiredError:
            pass
        return {
            "role": self.role.value,
            "outcome": self.engine.outcome.value,
            "turns_completed": self.engine.turns_completed,
            "end_state_digest": digest,
            "digest_match": digest_match,
            "audit": audit_verdict,
            "steps_sealed": len(self.exchange.own_records),
            "opponent_group_id": getattr(self, "opponent_group_id", "unknown"),
            "opponent_info": getattr(self, "opponent_info", {}),
        }
