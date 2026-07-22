"""Hidden-wire crash-resume (E6 pattern under reference-v3 secrecy rules).

The geometric snapshot replays BOTH sides' actions into a fresh engine; the
hidden wire cannot — the rival's moves are sealed commits until audit. So
the snapshot persists exactly what this peer truly holds: the OwnState facts
(my cell, the public barrier record, the boundary-cell history that replays
my scent field deterministically, the clock and turn token, the rival's last
transmitted scent snapshot) plus the HiddenExchange records (own nonces
never crossed the wire pre-audit, so they may live in a LOCAL file) and the
verified opponent agreement. The resume_offer control handshake re-sends
only the last sealed TurnMessage — it carries the COMMIT alone, so a
crash+resume can never become a pre-audit reveal (rule 18 survives E6).
"""

import queue
from pathlib import Path

from p2p_police.peer import resume as base
from p2p_police.wire import codec


def snapshot_path(config) -> Path:
    """Distinct from the geometric snapshot: the shapes are not exchangeable."""
    sub_game = int(config.private["game"]["sub_game_number"])
    root = Path(__file__).resolve().parents[3]  # repo root, cwd-independent
    return root / "results" / "local" / (
        f"resume_hidden_{config.group_id}_g{sub_game:02d}.json")


def build_snapshot(rt, step: int) -> dict:
    """Everything a fresh HiddenRuntime needs to continue this peer's game."""
    own_records, their_records, consumed = rt.exchange.export_state()
    own = rt.own
    return {
        "turn": step,
        "group_id": rt.config.group_id,
        "opponent_agreement": getattr(rt, "opponent_info", {}),
        "own_records": own_records,
        "their_records": their_records,
        "consumed": consumed,
        "own": {
            "cell": list(own.cell),
            "barriers": sorted([list(cell) for cell in own.board.barriers]),
            "boundary_cells": [list(cell) for cell in own.boundary_cells],
            "turns_completed": own.turns_completed,
            "my_token": own.next_actor is own.role,
            "rival_scent": codec.serialize_scent(own.scent[own.role.rival]),
        },
        "pending_claim_response": rt.pending_claim_response,
        "last_sent": rt.exchange.last_sent,
        "own_digest": own.digest(),
    }


def rearm(rt, snapshot: dict) -> int:
    """Restore OwnState through its own public surface (barrier law, scent
    replay via the recorded boundary cells), re-arm the exchange (commit
    chain + dedup keys intact) and return the last completed half-turn."""
    own, block = rt.own, snapshot["own"]
    own.positions[own.role] = (block["cell"][0], block["cell"][1])
    for cell in block["barriers"]:
        own.board.add_barrier((cell[0], cell[1]))
    for cell in block["boundary_cells"]:
        own.scent[own.role].update((cell[0], cell[1]))
        own.boundary_cells.append((cell[0], cell[1]))
    own.turns_completed = int(block["turns_completed"])
    own.next_actor = own.role if block["my_token"] else own.role.rival
    own.scent[own.role.rival].absorb(block["rival_scent"])
    if own.digest() != snapshot["own_digest"]:
        raise base.ResumeError("restored own-state diverged from the snapshot digest")
    rt.exchange.restore_state(
        snapshot["own_records"], snapshot["their_records"], snapshot["consumed"])
    rt.exchange.last_sent = snapshot.get("last_sent")
    rt.pending_claim_response = snapshot.get("pending_claim_response")
    rt.opponent_info = snapshot["opponent_agreement"]
    rt.opponent_group_id = rt.perception.opponent_id = snapshot[
        "opponent_agreement"].get("group_id", "unknown")
    return int(snapshot["turn"])


def attach(rt, config, resume: bool = False) -> int:
    """Wire the recorder (same atomic writer, hidden snapshot builder) and,
    when resuming, re-arm from disk + offer the control handshake. Returns
    the half-turn index play() continues from (0 = fresh game)."""
    path = snapshot_path(config)
    if config.resume_enabled():
        rt.resume = base.ResumeRecorder(path, builder=build_snapshot)
    if not resume:
        return 0
    step = rearm(rt, base.load_snapshot(path))
    base.offer_resume(rt, step)  # the courtesy handshake is wire-shape-free
    return step


def discard(config) -> None:
    """Drop the snapshot once a game classified cleanly (stale resumes lie)."""
    snapshot_path(config).unlink(missing_ok=True)


def handle_controls(rt) -> None:
    """Drain the control inbox from the hidden wait loop. A resume_offer is
    answered by re-sending our last sealed TurnMessage: the COMMIT rides
    again, the reveal never does (rule 18), and the rival's hardened
    receiver dedups it if it already arrived."""
    while True:
        try:
            message = rt.inboxes.controls.get_nowait()
        except queue.Empty:
            return
        if message.get("kind") == "resume_offer" and rt.exchange.last_sent:
            rt.exchange.send_message(rt.exchange.last_sent)
