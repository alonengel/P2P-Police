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

    def send_message(self, message: dict) -> None:
        """Push one TurnMessage through the runtime's transport callable.
        The message is remembered so a rival's resume_offer can be answered
        by re-sending it — it carries only the COMMIT, never a reveal."""
        self.last_sent = message
        self._send(message)

    def receive_turn(self, step: int) -> dict:
        """Wait for the rival's TurnMessage for `step` through the hardened
        receiver; store its commit for the audit; return the raw message."""
        message = self._next("turn", step)
        if message.get("sender") == self.role.value:
            raise GameRuleError("opponent claimed our role in a turn message")
        commit = message.get("commit")
        if not isinstance(commit, str) or not commit:
            raise GameRuleError(f"turn message {step} carries no commit")
        self.their_records.append({"commit": commit})
        return {k: v for k, v in message.items() if k not in ("kind", "turn")}

    def audit_reveals(self, revealed: list[dict]) -> str:
        """'Verified OK' or 'TAMPERED' (binary, ch. 7): every revealed record
        must re-hash to the commit RECEIVED LIVE for that step — the live
        commit is the anchor a post-hoc rewrite cannot move."""
        if len(revealed) != len(self.their_records):
            return "TAMPERED"
        for live, full in zip(self.their_records, revealed, strict=True):
            try:
                if full["commit"] != live["commit"]:
                    return "TAMPERED"
                if not crypto.verify_commit(full["payload"], full["nonce"], full["commit"]):
                    return "TAMPERED"
            except (KeyError, TypeError, ValueError):
                return "TAMPERED"  # malformed audit material IS a failed audit
            live.update(payload=full["payload"], nonce=full["nonce"])
        return "Verified OK"
