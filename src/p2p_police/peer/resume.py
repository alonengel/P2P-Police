"""Crash-resume persistence (E6): per-half-turn snapshots + resume path.

The runtime checkpoints after every applied half-turn: next expected turn,
both sealed-record logs (own nonces included — they never cross the wire
before audit), the applied-action log and the verified opponent agreement.
A restarted peer replays the actions through protocol.apply_action on a
fresh engine, re-arms the SealedExchange (commit-reveal chain intact) and
continues from the next step. Snapshots are pure LOCAL persistence under
results/local/ (gitignored) — nothing here changes the wire protocol, and
honoring a resume_offer is a per-pair courtesy: the opponent's deadline
rules keep running, so a resume only works inside their turn budget.
"""

import json
import os
import queue
from hashlib import sha256
from pathlib import Path

from p2p_police.domain import protocol
from p2p_police.domain.primitives import Role
from p2p_police.peer.deadline import Deadline


class ResumeError(Exception):
    """Snapshot missing, tampered with, or inconsistent with its replay."""


class NullResume:
    """No-op recorder so the runtime checkpoints unconditionally (flat path)."""

    def checkpoint(self, runtime, turn_index: int) -> None:
        return


class ResumeRecorder:
    """Atomic per-half-turn snapshot writer (tmp file + os.replace)."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def checkpoint(self, runtime, turn_index: int) -> None:
        doc = build_snapshot(runtime, turn_index)
        doc["integrity"] = _integrity(doc)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(doc), encoding="utf-8")
        os.replace(tmp, self.path)  # readers always see a complete snapshot


def _integrity(doc: dict) -> str:
    body = {key: value for key, value in doc.items() if key != "integrity"}
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"))
    return sha256(canonical.encode("utf-8")).hexdigest()


def snapshot_path(config) -> Path:
    sub_game = int(config.private["game"]["sub_game_number"])
    root = Path(__file__).resolve().parents[3]  # repo root, cwd-independent (rule 18)
    return root / "results" / "local" / f"resume_{config.group_id}_g{sub_game:02d}.json"


def build_snapshot(runtime, turn_index: int) -> dict:
    own, their, consumed = runtime.exchange.export_state()
    actions = sorted(
        ({"step": r["payload"]["step"], "role": r["payload"]["role"],
          "action": r["payload"]["action"], "hint": r["payload"]["hint"]}
         for r in own + their),
        key=lambda entry: entry["step"])
    return {"turn": turn_index, "group_id": runtime.config.group_id,
            "opponent_agreement": getattr(runtime, "opponent_info", {}),
            "own_records": own, "their_records": their, "consumed": consumed,
            "actions": actions,
            "state_digest": protocol.end_state_digest(runtime.engine),
            "turns_completed": runtime.engine.turns_completed}


def load_snapshot(path: str | Path) -> dict:
    path = Path(path)
    if not path.is_file():
        raise ResumeError(f"no resume snapshot at {path}")
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ResumeError(f"unreadable resume snapshot {path}: {error}") from error
    if doc.get("integrity") != _integrity(doc):
        raise ResumeError(f"resume snapshot {path} failed its integrity check")
    return doc


def rearm(runtime, snapshot: dict) -> int:
    """Replay the recorded actions into the runtime's FRESH engine through
    the single application path, restore the exchange + agreement, and
    return the last completed half-turn index (play resumes at the next)."""
    for entry in snapshot["actions"]:
        actor = Role(entry["role"])
        protocol.apply_action(runtime.engine, actor, entry["action"])
        if actor is not runtime.role:  # rebuild belief from the recorded hints
            runtime.perception.observe(runtime.engine, actor, entry.get("hint"))
    if protocol.end_state_digest(runtime.engine) != snapshot["state_digest"]:
        raise ResumeError("replayed engine diverged from the snapshot digest")
    runtime.exchange.restore_state(
        snapshot["own_records"], snapshot["their_records"], snapshot["consumed"])
    runtime.opponent_info = snapshot["opponent_agreement"]
    runtime.opponent_group_id = snapshot["opponent_agreement"].get("group_id", "unknown")
    runtime.perception.opponent_id = runtime.opponent_group_id
    return int(snapshot["turn"])


def attach(runtime, config, resume: bool = False) -> int:
    """Wire the recorder (ON by default — pure local persistence, no wire
    change) and, when resuming, re-arm from disk and offer the handshake.
    Returns the turn index play() continues from (0 = fresh game)."""
    path = snapshot_path(config)
    if config.resume_enabled():
        runtime.resume = ResumeRecorder(path)
    if not resume:
        return 0
    turn = rearm(runtime, load_snapshot(path))
    offer_resume(runtime, turn)
    return turn


def discard(config) -> None:
    """Drop the snapshot once a game classified cleanly (stale resumes lie)."""
    snapshot_path(config).unlink(missing_ok=True)


def offer_resume(runtime, turn: int) -> None:
    """Control-channel handshake: tell the counterparty we are back at
    `turn` so it may re-send anything our restart lost (a courtesy — its
    deadline clock never stopped)."""
    runtime.transport.send_control(
        {"kind": "resume_offer", "turn": turn, "group_id": runtime.config.group_id},
        Deadline(runtime.config.turn_timeout_seconds))


def handle_controls(runtime) -> None:
    """Drain the control inbox (called from the runtime's wait loop). A
    resume_offer is answered by re-sending our last sealed pair, if any —
    the sealing dedup absorbs it wherever it already arrived."""
    while True:
        try:
            message = runtime.inboxes.controls.get_nowait()
        except queue.Empty:
            return
        if message.get("kind") == "resume_offer":
            _resend_last_sealed(runtime)


def _resend_last_sealed(runtime) -> None:
    records = runtime.exchange.own_records
    if not records:
        return
    record, deadline = records[-1], Deadline(runtime.config.turn_timeout_seconds)
    step = record["payload"]["step"]
    runtime.transport.send_turn(
        {"kind": "commit", "turn": step, "actor": runtime.role.value,
         "commit": record["commit"]}, deadline)
    public = {k: v for k, v in record["payload"].items() if k != "verdict"}
    runtime.transport.send_turn(
        {"kind": "reveal", "turn": step, "actor": runtime.role.value,
         "payload": public}, deadline)
