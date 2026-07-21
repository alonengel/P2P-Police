"""Legal-config-range fuzzer (E5): sample the space a rival may LEGALLY
propose (Appendix VI: minimums negotiable upward; FIXED terms untouchable)
and prove a full game survives every sample.

Per sample: board 7..grid_size_max, barriers 14..max_barriers_max,
max_moves=survival 35..max_moves_max, valid distinct start cells. FIXED
values (scent 0.9/0.10/5x5, scoring 20/5/5/10/tie 2, move set 4+STAY) are
asserted untouched. Each sampled config drives a full in-process self-play
game — our runtime vs a scripted RandomBrain stub over real HTTP MCP (the
integration-roundtrip machinery) — and the invariants are checked: legal
outcome, matching digests, clean audits, turn/barrier bounds respected.
Artifacts: results/experiments/config_fuzz.json + docs/evidence/config-fuzz.md.
Run: uv run python scripts/config_fuzz.py [--samples N] [--seed S]
Helpers (sampling, wiring, invariants, evidence): scripts/config_fuzz_lib.py.
"""

import argparse
import json
import random
import sys
import threading
import time
from datetime import UTC, datetime
from pathlib import Path

import config_fuzz_lib as lib

from p2p_police.domain.primitives import Role
from p2p_police.peer.runtime import GeometricRuntime
from p2p_police.shared.config import Config
from p2p_police.strategy.brain_base import RandomBrain, resolve_brain

ROOT = lib.ROOT
sample_shared = lib.sample_shared  # re-export: tests exercise the sampler here
MY_ROLE = Role.POLICE  # this repo fuzzes the police runtime (twin: thief)


def run_sample(index: int, shared: dict, net: dict, knobs: dict) -> dict:
    config = lib.load_config(shared, float(knobs["turn_timeout_seconds"]))
    for inbox in (net["my_in"], net["stub_in"]):  # no stale mail between games
        for q in (inbox.agreements, inbox.turns, inbox.audits, inbox.controls):
            while not q.empty():
                q.get_nowait()
    mine = lib.build_runtime(MY_ROLE, config, net["mine_t"], net["my_in"],
                             resolve_brain(config, MY_ROLE, random.Random(1000 + index)))
    stub = lib.build_runtime(MY_ROLE.rival, config, net["stub_t"], net["stub_in"],
                             RandomBrain(MY_ROLE.rival, random.Random(2000 + index)))
    boxes: dict[str, dict] = {"mine": {}, "stub": {}}

    def play(runtime: GeometricRuntime, name: str) -> None:
        try:
            boxes[name]["report"] = runtime.play()
        except Exception as error:  # noqa: BLE001 - a fuzz crash IS the finding
            boxes[name]["error"] = f"{type(error).__name__}: {error}"
    threads = [threading.Thread(target=play, args=(r, n), daemon=True)
               for n, r in (("mine", mine), ("stub", stub))]
    started = time.perf_counter()
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=float(knobs["turn_timeout_seconds"]) * 4)
    failures = lib.check_invariants(shared, boxes, mine)
    limits = shared["movement_and_barriers"]
    return {"sample": index, "grid_size": shared["board_and_agents"]["grid_size"],
            "max_barriers": limits["max_barriers"], "max_moves": limits["max_moves"],
            "cop_start": shared["board_and_agents"]["cop_start"],
            "thief_start": shared["board_and_agents"]["thief_start"],
            "outcome": boxes["mine"].get("report", {}).get("outcome"),
            "turns": boxes["mine"].get("report", {}).get("turns_completed"),
            "barriers_placed": len(mine.engine.board.barriers),
            "elapsed_sec": round(time.perf_counter() - started, 3),
            "ok": not failures, "failures": failures}


def run_fuzz(samples: int, seed: int, out_dir: Path, evidence_path: Path) -> dict:
    knobs = Config.load(ROOT / "config").private["fuzz"]
    base = json.loads((ROOT / "config" / "game.json").read_text(encoding="utf-8"))
    rng, rows, failing = random.Random(seed), [], []
    net = lib.wire_pair(float(knobs["retry_backoff_sec"]))
    for index in range(samples):
        shared = lib.sample_shared(rng, base, knobs)
        row = run_sample(index, shared, net, knobs)
        rows.append(row)
        if not row["ok"]:
            failing.append({"row": row, "shared_config": shared})  # verbatim repro
        print(f"sample {index:02d} grid={row['grid_size']} barriers={row['max_barriers']} "
              f"moves={row['max_moves']} -> {'PASS' if row['ok'] else 'FAIL'} "
              f"({row['outcome']}, {row['turns']} turns)", flush=True)
    summary = {"generated_utc": datetime.now(UTC).isoformat(timespec="seconds"),
               "role": MY_ROLE.value, "seed": seed, "samples": samples,
               "passed": sum(r["ok"] for r in rows), "failed": sum(not r["ok"] for r in rows),
               "bounds": {"grid_size": [7, int(knobs["grid_size_max"])],
                          "max_barriers": [14, int(knobs["max_barriers_max"])],
                          "max_moves_and_survival": [35, int(knobs["max_moves_max"])]},
               "results": rows, "failing_configs": failing}
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "config_fuzz.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    lib.write_evidence(summary, evidence_path)
    return summary


def main(argv: list[str]) -> int:
    from p2p_police.strategy import profiler
    profiler.PROFILE_PATH = ROOT / "logs" / "fuzz_profiles.json"  # never league memory
    knobs = Config.load(ROOT / "config").private["fuzz"]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=int, default=int(knobs["samples"]))
    parser.add_argument("--seed", type=int, default=int(knobs["seed"]))
    args = parser.parse_args(argv)
    summary = run_fuzz(args.samples, args.seed, ROOT / "results" / "experiments",
                       ROOT / "docs" / "evidence" / "config-fuzz.md")
    print(f"config_fuzz: {summary['passed']}/{summary['samples']} passed", flush=True)
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
