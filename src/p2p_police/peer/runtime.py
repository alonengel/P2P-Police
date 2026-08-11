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
from p2p_police.peer.sealing import SealedExchange, pending_cap_from
from p2p_police.peer.watchdog import NullWatchdog
from p2p_police.shared.info_modes import BOOKLETTER, brain_view, resolve
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
        self.brain, self.perception = brain, Perception.for_peer(role, config)
        # Resolved once, at construction: an illegal regime must fail at startup
        # rather than silently downgrade mid-game.
        self.mode = resolve(config.info_mode(BOOKLETTER), BOOKLETTER)
        self.deceiver = Deceiver(role, config, brain.rng)  # self-mirror lie policy
        self.talk, self.fsm = build_talk_chain(config, brain.rng, gatekeeper), GamePhaseMachine()
        # SDK swaps in the real watchdog (rule 7) / resume recorder (E6)
        self.watchdog, self.resume = NullWatchdog(), NullResume()

        self.exchange = SealedExchange(
            role,
            int(config.private["game"]["sub_game_number"]),
            lambda msg: self.transport.send_turn(
                msg, Deadline(self.config.turn_timeout_seconds)
            ),
            lambda what, deadline=None: self._wait(self.inboxes.turns, what, deadline),
            turn_timeout=config.turn_timeout_seconds, pending_cap=pending_cap_from(config),
        )

    def _wait(self, inbox: queue.Queue, what: str, deadline=None) -> dict:
        deadline = deadline or Deadline(self.config.turn_timeout_seconds)
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
                               info_mode=self.mode.name,
                               identity=self.config.identity_block())
        self.transport.send_agreement(mine, Deadline(self.config.turn_timeout_seconds))
        theirs = self._wait(self.inboxes.agreements, "opponent agreement")
        verify_agreement(mine, theirs)
        self.opponent_info = theirs  # identity + hashes: persisted into artifacts
        self.opponent_group_id = self.perception.opponent_id = theirs.get("group_id", "unknown")
        return theirs

    def _my_half_turn(self, turn_index: int) -> None:
        self.fsm.transition(GamePhase.COMPUTING_MOVE)
        # The information regime decides what the brain may see; the registry
        # decides which regimes this wire can honour (shared/info_modes.py,
        # ADR-0006). The live UI shows the belief map in every regime.
        action = self.brain.decide(self.engine, brain_view(self.mode, self.perception))
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
        actor, action = Role(payload["role"]), payload["action"]
        if actor is self.role:
            raise GameRuleError("opponent claimed our role in a sealed record")
        protocol.apply_action(self.engine, actor, action)
        wall = tuple(action["cell"]) if action["type"] == "barrier" else None
        self.perception.observe(self.engine, actor, payload.get("hint"), barrier_cell=wall)
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
        disclosure = {"end_state_digest": digest, "group_id": self.config.group_id,
                      "nonces": self.exchange.own_nonces(),
                      "verdicts": self.exchange.own_verdicts()}
        with contextlib.suppress(DeadlineExpiredError):
            self.transport.send_audit(
                disclosure, Deadline(self.config.turn_timeout_seconds))
            self.audit_sent = True  # normal-path disclosure done (rules 35-36)
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
            # Mutual-audit evidence (rule 36): trail readings refused as
            # physically impossible. Zero on every honest game measured.
            "scent_readings_refused": self.perception.refused_readings,
            # Where the rival's OWN transmitted trail placed it each turn
            # (emitter solved from the signed update law). Diffed at audit
            # against the positions it reveals: an honest trail matches.
            "rival_trail_track": self.perception.trail_track,
            "opponent_group_id": getattr(self, "opponent_group_id", "unknown"),
            "opponent_info": getattr(self, "opponent_info", {}),
        }
