"""SealedExchange: the four-phase commit-reveal flow of one peer (ch. 5).

Per half-turn: COMMIT (hash only) -> opponent's ack locks it -> REVEAL
(payload, nonce still secret) -> apply. At game end the nonces are revealed
and every stored record is recomputed (mutual audit, rules 17-21).
"""

import logging

from p2p_police.domain import crypto, protocol
from p2p_police.domain.engine import GameEngine
from p2p_police.domain.errors import GameRuleError
from p2p_police.domain.primitives import Role
from p2p_police.peer.deadline import Deadline

_LOG = logging.getLogger(__name__)


class SealedExchange:
    """Input: my role/sub_game + send/wait callables from the runtime.
    Output: applied opponent actions + audit verdicts. Setup: empty logs."""

    def __init__(self, role: Role, sub_game: int, send_turn, wait_turn,
                 turn_timeout: float | None = None) -> None:
        self.role = role
        self.sub_game = sub_game
        self._send = send_turn
        self._wait = wait_turn
        self.turn_timeout = turn_timeout  # one deadline per EXPECTED message
        self.own_records: list[dict] = []   # {payload, nonce, commit}
        self.their_records: list[dict] = [] # {payload, commit}
        self._consumed: set[tuple[str, int]] = set()  # dedup: at-least-once transport
        self._pending: dict[tuple[str, int], dict] = {}  # out-of-order buffer

    _PENDING_CAP = 8  # ~2 pairs of lookahead is legitimate; more is flooding

    def _next(self, kind: str, turn_index: int) -> dict:
        """Wait for (kind, turn), SKIPPING duplicates the retrying transport
        may deliver twice (a lost HTTP ack must never become a technical
        loss) and BUFFERING not-yet-expected messages (a crash+resume can
        split or reorder a pair; the deadline still bounds the wait). A
        flooded buffer is the one remaining true desync."""
        expected = (kind, turn_index)
        # ONE deadline for the whole expectation: junk/duplicate deliveries
        # must never reset the clock (a stalling rival could hold a lost
        # game open forever by streaming stale copies every <timeout).
        deadline = Deadline(self.turn_timeout) if self.turn_timeout else None
        label = f"opponent {kind} {turn_index}"
        while True:
            message = self._pending.pop(expected, None) or (
                self._wait(label, deadline) if deadline else self._wait(label))
            key = (str(message.get("kind")), int(message.get("turn", -1)))
            if key in self._consumed:
                _LOG.debug("duplicate delivery dropped: %s (at-least-once transport)", key)
                continue
            if key == expected:
                self._consumed.add(key)
                return message
            if len(self._pending) >= self._PENDING_CAP:
                raise GameRuleError(
                    f"protocol desync: flooded while expecting {kind} {turn_index}"
                )
            self._pending[key] = message

    def send_sealed(
        self, engine: GameEngine, turn_index: int, action: dict, hint: str, verdict: bool
    ) -> None:
        """COMMIT then REVEAL my half-turn; caller applies the action after."""
        payload = crypto.build_step_payload(
            turn_index,
            self.role.value,
            self.sub_game,
            protocol.end_state_digest(engine),  # pre-action anchor (ch. 5 State)
            action,
            hint,
            verdict,
        )
        nonce = crypto.new_nonce()
        sealed = crypto.commit_hash(payload, nonce)
        # phase 1+2: the transport ack of the commit message IS the lock
        self._send({"kind": "commit", "turn": turn_index, "actor": self.role.value,
                    "commit": sealed})
        # phase 3: reveal - the NONCE and the INTENT flag stay secret until
        # audit (revealing intent live would hand the rival our lie bit and
        # kill the deception game; ch. 5 separates commitment from disclosure)
        public = {k: v for k, v in payload.items() if k != "verdict"}
        self._send({"kind": "reveal", "turn": turn_index, "actor": self.role.value,
                    "payload": public})
        self.own_records.append({"payload": payload, "nonce": nonce, "commit": sealed})

    def receive_sealed(self, turn_index: int) -> dict:
        """Wait for the opponent's commit then reveal; store; return payload."""
        commit_msg = self._next("commit", turn_index)
        if commit_msg.get("actor") == self.role.value:
            raise GameRuleError("opponent echoed our own role in a commit")
        reveal_msg = self._next("reveal", turn_index)
        payload = reveal_msg.get("payload") or {}
        missing = [f for f in crypto.REQUIRED_RECORD_FIELDS
                   if f != "verdict" and f not in payload]
        if missing:
            raise GameRuleError(f"opponent reveal missing sealed fields: {missing}")
        self.their_records.append({"payload": payload, "commit": commit_msg["commit"]})
        return payload

    def export_state(self) -> tuple[list[dict], list[dict], list[list]]:
        """Crash-resume view (peer/resume.py): records + consumed keys, all
        JSON-shaped so the snapshot round-trips through disk byte-stably."""
        return (list(self.own_records), list(self.their_records),
                sorted([kind, turn] for kind, turn in self._consumed))

    def restore_state(self, own: list[dict], their: list[dict], consumed: list) -> None:
        """Re-arm a resumed exchange with its persisted records — nonces and
        commits intact, so the commit-reveal chain and the end-of-game audit
        continue as if the crash never happened."""
        self.own_records, self.their_records = list(own), list(their)
        self._consumed = {(str(kind), int(turn)) for kind, turn in consumed}

    def own_nonces(self) -> list[str]:
        return [record["nonce"] for record in self.own_records]

    def own_verdicts(self) -> list[bool]:
        """Intent flags, disclosed only at audit alongside the nonces."""
        return [record["payload"]["verdict"] for record in self.own_records]

    def audit_theirs(self, revealed_nonces: list[str]) -> str:
        """'Verified OK' or 'TAMPERED' (binary; one forged step voids all).

        Persists the revealed nonces into their_records so the SUBMITTED log
        lets any third party re-verify the opponent's half too (rules 20/36).
        """
        if len(revealed_nonces) == len(self.their_records):
            for record, nonce in zip(self.their_records, revealed_nonces, strict=True):
                record["nonce"] = nonce
        return crypto.audit_records(self.their_records, revealed_nonces)

    def apply_revealed_verdicts(self, verdicts: list[bool]) -> None:
        """Insert the rival's audited intent flags so their records hash
        complete - and so the profiler learns their true honesty rate."""
        if len(verdicts) == len(self.their_records):
            for record, verdict in zip(self.their_records, verdicts, strict=True):
                record["payload"]["verdict"] = verdict
