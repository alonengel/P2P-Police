"""Geometric peer runtime (PRD 02): negotiate, lockstep turn loop, end check.

Both peers replicate the SAME GameEngine; each applies its own action locally
and mirrors the opponent's received action, so the physics never diverges.
Moves come from the configured brain via the [strategy] seam (PRD 03).
"""

import contextlib
import queue

from p2p_police.domain import protocol
from p2p_police.domain.engine import GameEngine
from p2p_police.domain.errors import GameRuleError
from p2p_police.domain.negotiation import build_agreement, verify_agreement
from p2p_police.domain.primitives import Outcome, Role
from p2p_police.infra.mcp_client import McpTransport
from p2p_police.infra.mcp_server import PeerInboxes
from p2p_police.peer.deadline import Deadline, DeadlineExpiredError
from p2p_police.strategy.brain_base import BrainBase


class GeometricRuntime:
    """One peer's game loop for the stage-2 milestone.

    Input: role, loaded config, replicated engine, transport + inboxes.
    Output: an end report (outcome, digests, turn count).
    """

    def __init__(
        self,
        role: Role,
        config,
        engine: GameEngine,
        transport: McpTransport,
        inboxes: PeerInboxes,
        brain: BrainBase,
    ) -> None:
        self.role = role
        self.config = config
        self.engine = engine
        self.transport = transport
        self.inboxes = inboxes
        self.brain = brain

    def _wait(self, inbox: queue.Queue, what: str) -> dict:
        deadline = Deadline(self.config.turn_timeout_seconds)
        while True:
            deadline.require(what)
            try:
                return inbox.get(timeout=min(0.25, max(0.01, deadline.remaining())))
            except queue.Empty:
                continue

    def negotiate(self) -> dict:
        """Exchange and verify agreements before any move (rules 11-12)."""
        mine = build_agreement(self.config.shared, self.config.group_id)
        self.transport.send_agreement(mine, Deadline(self.config.turn_timeout_seconds))
        theirs = self._wait(self.inboxes.agreements, "opponent agreement")
        verify_agreement(mine, theirs)
        return theirs

    def _my_half_turn(self, turn_index: int) -> None:
        action = self.brain.decide(self.engine)
        protocol.apply_action(self.engine, self.role, action)
        message = protocol.turn_message(turn_index, self.role, action)
        self.transport.send_turn(message, Deadline(self.config.turn_timeout_seconds))

    def _their_half_turn(self, turn_index: int) -> None:
        payload = self._wait(self.inboxes.turns, f"opponent turn {turn_index}")
        seen_index, actor, action = protocol.parse_turn_message(payload)
        if actor is self.role or seen_index != turn_index:
            raise GameRuleError(
                f"turn desync: expected opponent turn {turn_index}, got {payload!r}"
            )
        protocol.apply_action(self.engine, actor, action)

    def play(self) -> dict:
        """Run negotiation and the full lockstep game; return the end report."""
        self.negotiate()
        turn_index = 0
        while self.engine.outcome is Outcome.ONGOING:
            turn_index += 1
            if self.engine.next_actor is self.role:
                self._my_half_turn(turn_index)
            else:
                self._their_half_turn(turn_index)
        return self._finish()

    def _finish(self) -> dict:
        digest = protocol.end_state_digest(self.engine)
        # Best-effort: if the opponent tore down right after ITS audit
        # reached us, our send may fail although the exchange succeeded.
        with contextlib.suppress(DeadlineExpiredError):
            self.transport.send_audit(
                {"end_state_digest": digest, "group_id": self.config.group_id},
                Deadline(self.config.turn_timeout_seconds),
            )
        try:
            theirs = self._wait(self.inboxes.audits, "opponent end-state digest")
            digest_match = theirs.get("end_state_digest") == digest
        except DeadlineExpiredError:
            digest_match = False
        return {
            "role": self.role.value,
            "outcome": self.engine.outcome.value,
            "turns_completed": self.engine.turns_completed,
            "end_state_digest": digest,
            "digest_match": digest_match,
        }
