"""HiddenExchange: commit-only live wire, reveals deferred to the audit.

Subclasses the hardened SealedExchange RECEIVER (dedup of at-least-once
deliveries, out-of-order buffering, the flood cap, one deadline per expected
message) — reused, not forked. What changes is the protocol on top: per
half-turn only the COMMIT crosses the wire inside the TurnMessage; payloads
and nonces stay local until the end-of-game audit reveals them together
(rule 18 — and stronger: under this wire even the ACTION is secret live).
"""

from p2p_police.domain import crypto
from p2p_police.domain.errors import GameRuleError
from p2p_police.peer.sealing import SealedExchange
from p2p_police.wire import audit_foreign


class HiddenExchange(SealedExchange):
    """Input: my role/sub_game + send/wait callables. Output: sealed own
    records, live rival commits, and the audit verdict over the reveals."""

    def seal_step(
        self, state_digest: str, step: int, action: dict, hint: str, verdict: bool
    ) -> str:
        """Seal my half-turn (full pinned payload) and return ONLY the commit
        — the caller embeds it in the TurnMessage; nothing else leaves."""
        payload = crypto.build_step_payload(
            step, self.role.value, self.sub_game, state_digest, action, hint, verdict
        )
        nonce = crypto.new_nonce()
        commit = crypto.commit_hash(payload, nonce)
        self.own_records.append({"payload": payload, "nonce": nonce, "commit": commit})
        return commit

    last_sent: dict | None = None  # commit-only TurnMessage (resume re-send)
    expected_turn: int = 0  # live expectation: the rival's next own step

    def send_message(self, message: dict) -> None:
        """Push one TurnMessage through the runtime's transport callable.
        The message is remembered so a rival's resume_offer can be answered
        by re-sending it — it carries only the COMMIT, never a reveal."""
        self.last_sent = message
        self._send(message)

    def receive_turn(self, step: int) -> dict:
        """Wait for the rival's TurnMessage for `step` (ITS OWN per-sender
        number) through the hardened receiver; store its commit for the
        audit; return the raw message. The published expectation lets the
        wait adapter key a caught=True final here even when the sender
        re-used its last step number (demo send_final behavior)."""
        self.expected_turn = step
        message = self._next("turn", step)
        if message.get("sender") == self.role.value:
            raise GameRuleError("opponent claimed our role in a turn message")
        commit = message.get("commit")
        if not isinstance(commit, str) or not commit:
            raise GameRuleError(f"turn message {step} carries no commit")
        # The live PUBLIC declarations ride along with the commit: at audit
        # the reveal must re-prove not only the hash but that what was said
        # openly (rules 15-16, 21-22) is what was sealed (audit.verify_declared).
        self.their_records.append({"commit": commit, "declared": {
            "barrier_placed": message.get("barrier_placed"),
            "capture_claim": message.get("capture_claim"),
            "hint": message.get("hint"),
        }})
        return {k: v for k, v in message.items() if k not in ("kind", "turn")}

    def audit_reveals(self, revealed: list[dict]) -> str:
        """'Verified OK' or 'TAMPERED' (binary, ch. 7): every commit RECEIVED
        LIVE must be re-proven by a commit-clean reveal — the live commit is
        the anchor a post-hoc rewrite cannot move. The check is the SHARED
        contract only (schema-agnostic hash, alignment by commit): a foreign
        rival's reveal set may carry extra sealed records (reference step-0
        spec) and a payload schema that is not ours (2026-07-24 finding)."""
        return audit_foreign.verify_reveals(self.their_records, revealed)
