"""Chaos drills: fault-inject REAL games over HTTP MCP and record evidence.

D1 duplicate-delivery (sealing dedup absorbs an at-least-once resend),
D2 silent-opponent (deadline -> clean technical loss + watchdog persist),
D3 transport-flap-heal (endpoint dies briefly, retrying transport heals),
D4 budget-exhaustion (endpoint dead past the budget -> classified, no hang),
D5 outbound-duplicate (WE resend every turn push; the receiver dedup absorbs).
All knobs live in config/game.toml [chaos]; every JSONL line is an event that
actually happened. Run: uv run python scripts/chaos_drills.py [d1 d2 d3 d4 d5 tunnel]
"""

import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import chaos_lib
from chaos_lib import EvidenceLog
from chaos_outage import drill_d3, drill_d4  # noqa: F401 - re-exported for tests
from chaos_outbound import drill_d5  # noqa: F401 - re-exported for tests

from p2p_police.peer.watchdog import Watchdog
from p2p_police.shared.config import Config

ROOT = Path(__file__).resolve().parents[1]


def load_config() -> Config:
    """Real shipped config; only the turn budget shrinks to the drill scale."""
    config = Config.load(ROOT / "config")
    config.private["network"]["turn_timeout_seconds"] = \
        config.private["chaos"]["turn_timeout_seconds"]
    return config


def drill_d1(config, evidence: EvidenceLog) -> dict:
    name, chaos = "d1_duplicate_delivery", config.private["chaos"]

    def hook(kind, payload):
        evidence.event(name, "inject", fault=kind, stub_turn=payload.get("turn"),
                       message_kind=payload.get("kind"))
    dedup = chaos_lib.DedupObserver()
    net = chaos_lib.wire_pair(config, chaos, stub_wrap=lambda t: chaos_lib.FaultyStubTransport(
        t, duplicate_turn=chaos["duplicate_stub_turn"], on_inject=hook))
    evidence.event(name, "start", duplicate_stub_turn=chaos["duplicate_stub_turn"],
                   turn_timeout_sec=chaos["turn_timeout_seconds"])
    thread, stub_box = chaos_lib.play_in_thread(net["stub"], name)
    mine = chaos_lib.run_classified(net["mine"])
    thread.join(timeout=chaos["turn_timeout_seconds"] * 3)
    dedup.detach()
    evidence.event(name, "observe", duplicates_dropped=dedup.dropped)
    row = chaos_lib.finish_row(evidence, name, mine, stub_box,
                               {"duplicates_dropped": dedup.dropped})
    row["passed"] = (row["outcome"] != "technical_loss" and row["digest_match"]
                     and row["audit"] == "Verified OK" and dedup.dropped >= 2)
    return row


def drill_d2(config, evidence: EvidenceLog, dump_path: Path) -> dict:
    name, chaos = "d2_silent_opponent", config.private["chaos"]
    inject_at: dict = {}

    def hook(kind, payload):
        inject_at.setdefault("t", time.perf_counter())
        evidence.event(name, "inject", fault=kind, stub_turn=payload.get("turn"))
    net = chaos_lib.wire_pair(config, chaos, stub_wrap=lambda t: chaos_lib.FaultyStubTransport(
        t, silent_from_turn=chaos["silent_stub_turn"], on_inject=hook))
    dump_path.unlink(missing_ok=True)
    runtime = net["mine"]
    watchdog = Watchdog(
        chaos["watchdog_timeout_sec"],
        lambda: {"positions": {r.value: list(c) for r, c in runtime.engine.positions.items()},
                 "turns": runtime.engine.turns_completed,
                 "outcome": runtime.engine.outcome.value},
        net["mine_t"].close, dump_path=dump_path, poll_interval=0.2)
    runtime.watchdog = watchdog
    watchdog.start()
    evidence.event(name, "start", silent_stub_turn=chaos["silent_stub_turn"],
                   turn_timeout_sec=chaos["turn_timeout_seconds"],
                   watchdog_timeout_sec=chaos["watchdog_timeout_sec"])
    thread, stub_box = chaos_lib.play_in_thread(net["stub"], name)
    mine = chaos_lib.run_classified(runtime)
    seconds_to_classify = round(time.perf_counter() - inject_at.get("t", time.perf_counter()), 3)
    # beats stop with the loop; the watchdog must notice ON ITS OWN and persist
    give_up = time.perf_counter() + chaos["watchdog_timeout_sec"] + 3
    while not watchdog.fired and time.perf_counter() < give_up:
        time.sleep(0.05)
    watchdog.stop()
    thread.join(timeout=chaos["turn_timeout_seconds"] * 3)
    dump = json.loads(dump_path.read_text(encoding="utf-8")) if dump_path.is_file() else None
    evidence.event(name, "observe", seconds_to_classify=seconds_to_classify,
                   watchdog_fired=watchdog.fired, watchdog_dump=dump,
                   stub_thread_exited=not thread.is_alive())
    row = chaos_lib.finish_row(evidence, name, mine, stub_box,
                               {"seconds_to_classify": seconds_to_classify,
                                "watchdog_fired": watchdog.fired})
    # the FSM may legally sit in a phase with no TECHNICAL_LOSS edge (book
    # table); the classification lives in the engine outcome + error type
    row["passed"] = (row["outcome"] == "technical_loss"
                     and "DeadlineExpiredError" in (mine["error"] or "")
                     and seconds_to_classify <= chaos["turn_timeout_seconds"] * 2  # load-tolerant
                     and watchdog.fired and dump is not None and not thread.is_alive())
    return row


DRILLS = {"d1": ("d1_duplicate_delivery", drill_d1),
          "d2": ("d2_silent_opponent",
                 lambda c, e: drill_d2(c, e, ROOT / "logs" / "chaos_watchdog_dump.json")),
          "d3": ("d3_transport_flap_heal", drill_d3),
          "d4": ("d4_budget_exhaustion", drill_d4),
          "d5": ("d5_outbound_duplicate", drill_d5)}


def main(argv: list[str]) -> int:
    from p2p_police.strategy import profiler
    profiler.PROFILE_PATH = ROOT / "logs" / "chaos_profiles.json"  # never league memory
    names = [a for a in argv if not a.startswith("--")] or ["d1", "d2", "d3", "d4", "d5"]
    evidence_dir = ROOT / "docs" / "evidence" / "drills"
    for arg in argv:
        if arg.startswith("--evidence-dir="):
            evidence_dir = Path(arg.split("=", 1)[1])
    date, rows = datetime.now(UTC).date().isoformat(), []
    for name in names:
        if name == "tunnel":
            from chaos_tunnel import drill_tunnel
            rows.append(drill_tunnel(load_config(),
                                     EvidenceLog(evidence_dir / f"tunnel_kill_heal_{date}.jsonl")))
            continue
        file_name, runner = DRILLS[name]
        rows.append(runner(load_config(), EvidenceLog(evidence_dir / f"{file_name}_{date}.jsonl")))
    for row in rows:
        print(f"{row['drill']:<26} {'PASS' if row['passed'] else 'FAIL'}  "
              f"outcome={row.get('outcome')} turns={row.get('turns_completed')} "
              f"elapsed={row.get('elapsed_sec')}s", flush=True)
    return 0 if all(row["passed"] for row in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
