"""Outbound duplicate-delivery drill: the SENDER half of chaos drill D1.

With [chaos] duplicate_outbound_sends on (game.toml knob or the peer
--duplicate-outbound CLI flag) every outbound turn push goes out TWICE —
commit/reveal messages on the bookletter wire, TurnMessages on the hidden
reference-v3 wire; both ride send_turn, so ONE wrapper covers both wire
shapes. Purpose: demonstrate against a live foreign peer (over a tunnel)
that at-least-once delivery from OUR side is absorbed by their receiver
dedup, mirroring what our own receiver already tolerates. Every duplicated
send is recorded as a really-observed JSONL evidence event (chaos_lib
EvidenceLog line shape); a failure of the duplicate itself is drill noise —
recorded, never allowed to kill a game the original ack already secured.
"""

import json
import threading
from datetime import UTC, datetime
from pathlib import Path

DRILL = "outbound_duplicate"


class JsonlEvidence:
    """Append-only JSONL evidence: one observed event per line (thread-safe;
    the chaos_lib.EvidenceLog line shape, importable from src)."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def event(self, drill: str, stage: str, **fields) -> dict:
        record = {"ts": datetime.now(UTC).isoformat(timespec="milliseconds"),
                  "drill": drill, "stage": stage, **fields}
        with self._lock, self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, default=str) + "\n")
        return record


class DuplicatingTransport:
    """Wraps any peer transport; every send_turn goes out twice.

    Input: the inner transport + an evidence sink exposing .event(). Output:
    the ORIGINAL send's ack (the duplicate is injected noise). Setup: no
    state beyond the duplicate counter.
    """

    def __init__(self, inner, evidence) -> None:
        self._inner, self._evidence = inner, evidence
        self.duplicated = 0

    @property
    def beat(self):
        """Watchdog liveness forwards to the INNER transport — its retry
        loops do the beating, so wiring the wrapper must reach them."""
        return self._inner.beat

    @beat.setter
    def beat(self, callback) -> None:
        self._inner.beat = callback

    def send_agreement(self, payload: dict, deadline) -> dict:
        return self._inner.send_agreement(payload, deadline)

    def send_turn(self, payload: dict, deadline) -> dict:
        ack = self._inner.send_turn(payload, deadline)
        ok, error = True, None
        try:
            self._inner.send_turn(payload, deadline)  # the duplicate delivery
        except Exception as failure:  # noqa: BLE001 - drill noise, recorded
            ok, error = False, f"{type(failure).__name__}: {failure}"
        self.duplicated += 1
        self._evidence.event(
            DRILL, "duplicate",
            message_kind=payload.get("kind", "turn_message"),
            turn=payload.get("turn", payload.get("step")),
            target=getattr(self._inner, "opponent_url", "in-process"),
            duplicate_ack_ok=ok, error=error)
        return ack

    def send_audit(self, payload: dict, deadline) -> dict:
        return self._inner.send_audit(payload, deadline)

    def send_control(self, payload: dict, deadline) -> dict:
        return self._inner.send_control(payload, deadline)

    def close(self) -> None:
        self._inner.close()


def maybe_duplicate_outbound(transport, config):
    """SDK seam: wrap the live transport when the [chaos] knob is armed."""
    chaos = config.private.get("chaos", {})
    if not chaos.get("duplicate_outbound_sends", False):
        return transport
    directory = Path(chaos.get("duplicate_outbound_evidence_dir", "docs/evidence/drills"))
    date = datetime.now(UTC).date().isoformat()
    return DuplicatingTransport(transport, JsonlEvidence(directory / f"{DRILL}_{date}.jsonl"))
