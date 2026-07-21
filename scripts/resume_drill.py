"""Kill-and-resume drill (E6): crash our peer mid-game, resume from the
per-half-turn snapshot, finish the game with audits Verified OK.

Over real HTTP MCP (roundtrip pattern): our runtime plays an in-process
RandomBrain stub in the rival role. After the configured number of
half-turns the runtime is DISCARDED (transport closed, undelivered inbox
mail dropped — a restart loses both). A fresh runtime re-arms from
results/local/resume_*.json, sends the resume_offer control handshake and
plays to completion. Every JSONL line is a really-observed event (chaos
evidence style). Knobs: config/game.toml [resume]. Run:
uv run python scripts/resume_drill.py [--evidence-dir=...]
"""

import random
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import chaos_lib  # evidence format + play helpers, reused read-only
import chaos_net

from p2p_police.domain.engine import GameEngine
from p2p_police.domain.primitives import Outcome, Role
from p2p_police.infra.mcp_client import McpTransport
from p2p_police.peer import resume as resume_mod
from p2p_police.peer.runtime import GeometricRuntime
from p2p_police.sdk.reporting import technical_loss_report
from p2p_police.shared.config import Config
from p2p_police.strategy.brain_base import RandomBrain, resolve_brain

ROOT = Path(__file__).resolve().parents[1]
MY_ROLE = Role.POLICE  # this repo drills the police resume path (twin: thief)
DRILL = "resume_recovery"


def load_config() -> Config:
    """Real shipped config; only the turn budget shrinks to the drill scale."""
    config = Config.load(ROOT / "config")
    config.private["network"]["turn_timeout_seconds"] = \
        config.private["resume"]["drill_turn_timeout_seconds"]
    return config


def _runtime(role: Role, config: Config, transport, inboxes, brain) -> GeometricRuntime:
    ph = config.pheromones
    engine = GameEngine(config.grid_size, config.cop_start, config.thief_start,
                       config.rule_set(), center_intensity=ph["pheromone_center_intensity"],
                       decay=ph["pheromone_decay"], kernel_size=ph["pheromone_grid_size"])
    return GeometricRuntime(role, config, engine, transport, inboxes, brain)


def _run_resumed(runtime: GeometricRuntime, start_turn: int) -> dict:
    """run_classified's shape, but continuing from the re-armed turn (the
    chaos helper always starts fresh; chaos files stay untouched)."""
    started = time.perf_counter()
    try:
        report, error = runtime.play(resume_from=start_turn), None
    except Exception as failure:  # noqa: BLE001 - mirrors sdk.run_peer's net
        report = technical_loss_report(runtime.role, runtime, failure)
        error = f"{type(failure).__name__}: {failure}"
    return {"report": report, "elapsed": round(time.perf_counter() - started, 3),
            "phase": runtime.fsm.state.value, "error": error}


def run_drill(config: Config, evidence: chaos_lib.EvidenceLog,
              snap_path: Path) -> dict:
    knobs = config.private["resume"]
    backoff = float(knobs["drill_retry_backoff_sec"])
    my_in, my_port = chaos_net.start_inbox_server("resume_mine")
    stub_in, stub_port = chaos_net.start_inbox_server("resume_stub")
    stub_url, my_url = f"http://127.0.0.1:{stub_port}/mcp", f"http://127.0.0.1:{my_port}/mcp"
    # The stub's deadline starts BEFORE our crash; its patience must cover the
    # crash window plus scheduler load, or the drill races itself. Our own
    # resume time is still asserted against the REAL one-turn budget below.
    stub_config = load_config()
    stub_config.private["network"]["turn_timeout_seconds"] = (
        config.turn_timeout_seconds * float(knobs["drill_stub_patience_factor"]))
    stub = _runtime(MY_ROLE.rival, stub_config, McpTransport(my_url, backoff), stub_in,
                    RandomBrain(MY_ROLE.rival, random.Random(int(knobs["drill_stub_seed"]))))
    mine_t = McpTransport(stub_url, backoff)
    mine = _runtime(MY_ROLE, config, mine_t, my_in,
                    resolve_brain(config, MY_ROLE, random.Random(int(knobs["drill_my_seed"]))))
    snap_path.unlink(missing_ok=True)
    mine.resume = resume_mod.ResumeRecorder(snap_path)
    crash_after = int(knobs["drill_crash_after_half_turns"])
    evidence.event(DRILL, "start", crash_after_half_turns=crash_after,
                   turn_timeout_sec=config.turn_timeout_seconds, snapshot=str(snap_path))
    stub_thread, stub_box = chaos_lib.play_in_thread(stub, DRILL)

    # -- the pre-crash life: drive the real loop shape up to the kill point --
    mine.negotiate()
    turn = 0
    while mine.engine.outcome is Outcome.ONGOING and turn < crash_after:
        turn += 1
        if mine.engine.next_actor is mine.role:
            mine._my_half_turn(turn)
        else:
            mine._their_half_turn(turn)
        mine.resume.checkpoint(mine, turn)

    # -- the crash: transport gone, undelivered inbox mail lost, object dropped --
    crash_at = time.perf_counter()
    mine_t.close()
    dropped = 0
    for q in (my_in.agreements, my_in.turns, my_in.audits, my_in.controls):
        while not q.empty():
            q.get_nowait()
            dropped += 1
    del mine
    evidence.event(DRILL, "crash", killed_after_half_turns=turn,
                   undelivered_messages_lost=dropped)

    # -- the resume: fresh runtime, replayed engine, control handshake --
    snapshot = resume_mod.load_snapshot(snap_path)
    mine2 = _runtime(MY_ROLE, config, McpTransport(stub_url, backoff), my_in,
                     resolve_brain(config, MY_ROLE, random.Random(int(knobs["drill_my_seed"]))))
    start_turn = resume_mod.rearm(mine2, snapshot)
    mine2.resume = resume_mod.ResumeRecorder(snap_path)
    resume_mod.offer_resume(mine2, start_turn)
    seconds_to_resume = round(time.perf_counter() - crash_at, 3)
    evidence.event(DRILL, "resume", seconds_to_resume=seconds_to_resume,
                   turns_recovered=start_turn, state_digest=snapshot["state_digest"])

    result = _run_resumed(mine2, start_turn)
    stub_thread.join(timeout=config.turn_timeout_seconds * 3)
    row = chaos_lib.finish_row(evidence, DRILL, result, stub_box,
                               {"seconds_to_resume": seconds_to_resume,
                                "turns_recovered": start_turn})
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
    snap_path = ROOT / "results" / "local" / f"resume_drill_{MY_ROLE.value}.json"
    row = run_drill(load_config(), evidence, snap_path)
    print(f"{DRILL:<26} {'PASS' if row['passed'] else 'FAIL'}  "
          f"outcome={row.get('outcome')} turns={row.get('turns_completed')} "
          f"recovered={row.get('turns_recovered')} half-turns "
          f"resume={row.get('seconds_to_resume')}s", flush=True)
    return 0 if row["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
