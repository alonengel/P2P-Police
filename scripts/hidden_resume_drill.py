"""Kill-and-resume drill on the HIDDEN wire (E6 x reference-v3): crash our
peer mid-game, resume from the own-state snapshot, finish with audits
Verified OK — while reveals still never ride the live wire (the resume
handshake re-sends the last COMMIT-bearing TurnMessage only, rule 18).

Over real HTTP MCP (roundtrip pattern): our HiddenRuntime plays an
in-process RandomBrain stub in the rival role. After the configured number
of half-turns the runtime is DISCARDED (transport closed, undelivered inbox
mail dropped). A fresh runtime re-arms from results/local/resume_hidden_*.json,
offers the control handshake and plays to completion. Every JSONL line is a
really-observed event (chaos evidence style). Knobs: config/game.toml
[resume]. Run: uv run python scripts/hidden_resume_drill.py [--evidence-dir=...]
"""

import random
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import chaos_lib  # evidence format + play helpers, reused read-only
import chaos_net

from p2p_police.domain.primitives import Outcome, Role
from p2p_police.infra.mcp_client import McpTransport
from p2p_police.peer import resume as base
from p2p_police.sdk.reporting import technical_loss_report
from p2p_police.shared.config import Config
from p2p_police.strategy.brain_base import RandomBrain, resolve_brain
from p2p_police.wire import hidden_resume, hidden_turns
from p2p_police.wire.hidden_runtime import HiddenRuntime
from p2p_police.wire.own_state import OwnState

ROOT = Path(__file__).resolve().parents[1]
MY_ROLE = Role.POLICE  # this repo drills the police resume path (twin: thief)
DRILL = "hidden_resume_recovery"


def load_config() -> Config:
    """Real shipped config; the hidden wire armed, drill-scale turn budget."""
    config = Config.load(ROOT / "config")
    config.private["network"]["wire_shape"] = "reference"
    config.private["network"]["turn_timeout_seconds"] = \
        config.private["resume"]["drill_turn_timeout_seconds"]
    return config


def _runtime(role: Role, config: Config, transport, inboxes, brain) -> HiddenRuntime:
    pheromones = config.pheromones
    start = config.cop_start if role is Role.POLICE else config.thief_start
    own = OwnState(role, config.grid_size, start, config.rule_set(),
                   center_intensity=pheromones["pheromone_center_intensity"],
                   decay=pheromones["pheromone_decay"],
                   kernel_size=pheromones["pheromone_grid_size"])
    return HiddenRuntime(role, config, own, transport, inboxes, brain)


def _run_resumed(runtime: HiddenRuntime, start_step: int) -> dict:
    started = time.perf_counter()
    try:
        report, error = runtime.play(resume_from=start_step), None
    except Exception as failure:  # noqa: BLE001 - mirrors sdk.run_peer's net
        report = technical_loss_report(runtime.role, runtime, failure)
        error = f"{type(failure).__name__}: {failure}"
    return {"report": report, "elapsed": round(time.perf_counter() - started, 3),
            "phase": runtime.fsm.state.value, "error": error}


def run_drill(config: Config, evidence: chaos_lib.EvidenceLog, snap_path: Path) -> dict:
    knobs = config.private["resume"]
    backoff = float(knobs["drill_retry_backoff_sec"])
    my_in, my_port = chaos_net.start_inbox_server("hidden_resume_mine")
    stub_in, stub_port = chaos_net.start_inbox_server("hidden_resume_stub")
    stub_url, my_url = f"http://127.0.0.1:{stub_port}/mcp", f"http://127.0.0.1:{my_port}/mcp"
    stub_config = load_config()
    stub_config.private["network"]["turn_timeout_seconds"] = (
        config.turn_timeout_seconds * float(knobs["drill_stub_patience_factor"]))
    stub = _runtime(MY_ROLE.rival, stub_config, McpTransport(my_url, backoff), stub_in,
                    RandomBrain(MY_ROLE.rival, random.Random(int(knobs["drill_stub_seed"]))))
    mine_t = McpTransport(stub_url, backoff)
    mine = _runtime(MY_ROLE, config, mine_t, my_in,
                    resolve_brain(config, MY_ROLE, random.Random(int(knobs["drill_my_seed"]))))
    snap_path.unlink(missing_ok=True)
    mine.resume = base.ResumeRecorder(snap_path, builder=hidden_resume.build_snapshot)
    crash_after = int(knobs["drill_crash_after_half_turns"])
    evidence.event(DRILL, "start", crash_after_half_turns=crash_after,
                   turn_timeout_sec=config.turn_timeout_seconds, snapshot=str(snap_path))
    stub_thread, stub_box = chaos_lib.play_in_thread(stub, DRILL)

    # -- the pre-crash life: drive the real hidden loop up to the kill point --
    mine.negotiate()
    step = 0
    while mine.own.outcome is Outcome.ONGOING and step < crash_after:
        step += 1  # total half-turns; the wire clocks are per-sender on `mine`
        if mine.own.next_actor is mine.role:
            hidden_turns.my_half_turn(mine)
        else:
            hidden_turns.their_half_turn(mine)
        mine.resume.checkpoint(mine, mine.my_step + mine.their_step)

    # -- the crash: transport gone, undelivered inbox mail lost, object dropped --
    crash_at = time.perf_counter()
    mine_t.close()
    dropped = 0
    for q in (my_in.agreements, my_in.turns, my_in.audits, my_in.controls):
        while not q.empty():
            q.get_nowait()
            dropped += 1
    del mine
    evidence.event(DRILL, "crash", killed_after_half_turns=step,
                   undelivered_messages_lost=dropped)

    # -- the resume: fresh runtime, restored own-state, control handshake --
    snapshot = base.load_snapshot(snap_path)
    mine2 = _runtime(MY_ROLE, config, McpTransport(stub_url, backoff), my_in,
                     resolve_brain(config, MY_ROLE, random.Random(int(knobs["drill_my_seed"]))))
    start_step = hidden_resume.rearm(mine2, snapshot)
    mine2.resume = base.ResumeRecorder(snap_path, builder=hidden_resume.build_snapshot)
    base.offer_resume(mine2, start_step)
    seconds_to_resume = round(time.perf_counter() - crash_at, 3)
    evidence.event(DRILL, "resume", seconds_to_resume=seconds_to_resume,
                   half_turns_recovered=start_step, own_digest=snapshot["own_digest"])

    result = _run_resumed(mine2, start_step)
    stub_thread.join(timeout=config.turn_timeout_seconds * 3)
    row = chaos_lib.finish_row(evidence, DRILL, result, stub_box,
                               {"seconds_to_resume": seconds_to_resume,
                                "turns_recovered": start_step})
    row["passed"] = (row["outcome"] in ("capture", "survival") and row["digest_match"]
                     and row["audit"] == "Verified OK"
                     and stub_box.get("report", {}).get("audit") == "Verified OK"
                     and row["outcome"] == stub_box.get("report", {}).get("outcome")
                     and seconds_to_resume < config.turn_timeout_seconds)
    snap_path.unlink(missing_ok=True)  # drill hygiene: no stale resume state
    return row


def main(argv: list[str]) -> int:
    from p2p_police.strategy import profiler
    profiler.PROFILE_PATH = ROOT / "logs" / "resume_profiles.json"  # never league memory
    evidence_dir = ROOT / "docs" / "evidence" / "drills"
    for arg in argv:
        if arg.startswith("--evidence-dir="):
            evidence_dir = Path(arg.split("=", 1)[1])
    date = datetime.now(UTC).date().isoformat()
    evidence = chaos_lib.EvidenceLog(evidence_dir / f"{DRILL}_{date}.jsonl")
    snap_path = ROOT / "results" / "local" / f"hidden_resume_drill_{MY_ROLE.value}.json"
    row = run_drill(load_config(), evidence, snap_path)
    print(f"{DRILL:<26} {'PASS' if row['passed'] else 'FAIL'}  "
          f"outcome={row.get('outcome')} turns={row.get('turns_completed')} "
          f"recovered={row.get('turns_recovered')} half-turns "
          f"resume={row.get('seconds_to_resume')}s", flush=True)
    return 0 if row["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
