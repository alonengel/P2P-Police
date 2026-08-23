"""League-day series runner - drives THIS repo's (police) sub-game windows.

The book's role alternation gives the police repo the ODD sub-games of a
counted series and the thief repo the EVEN ones; on league day each repo
starts its own runner at the agreed time (T-protocol) and the two runners
interleave into one continuous 6-sub-game series. Every window launches
the real committed CLI in a subprocess (`uv run p2p-police peer
--sub-game N [--seed base+N]`) and waits for it - strictly sequential.
A lockfile carrying our pid under results/local/ makes a second concurrent
runner instance refuse to start: the orchestration-layer half of the
double-instance guard (the wire layer's game_uid/sub_game_number checks
are the other half). HONESTY: a failed window is logged to stdout and the
runner moves on - nothing is retried blindly and nothing is fabricated;
the series-result settlement guard (rule 35) downstream refuses the whole
series if any window never settled.

Bookends (scripts/league_close.py): a send posture proves email
deliverability BEFORE window 1 (else the run refuses with zero games
played), and after this runner's last window settles the series
auto-closes IF every sub-game log is visible across both repos' results
dirs - otherwise the missing windows are named and nothing aggregates.

Usage: uv run python scripts/league_series.py --sub-games "1,3,5" [--seed 900]
"""

import argparse
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import league_close

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from p2p_police.report.archive import archive_for_pairing  # noqa: E402
from p2p_police.shared.config import Config  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
ROLE, CLI, PARITY = "police", "p2p-police", 0 if os.environ.get("LEAGUE_PARITY_FLIP") else 1  # police: ODD windows (FLIP: this pairing gives our police the evens)
LOCK_PATH = ROOT / "results" / "local" / "league_series.lock"
# The twin repo's results dir: read-only FILE access for the series close -
# never an import (workspace iron rule); its runner owns the other windows.
SIBLING_RESULTS = ROOT.parent / "P2P-Thief" / "results"


def parse_sub_games(spec: str) -> list[int]:
    """This repo's windows only: the book's alternation is not negotiable."""
    windows = [int(part) for part in spec.replace(" ", "").split(",") if part]
    wrong = [n for n in windows if n < 1 or n % 2 != PARITY]
    if not windows or wrong:
        raise ValueError(f"the {ROLE} repo plays only the "
                         f"{'even' if PARITY == 0 else 'odd'} sub-games of a "
                         f"series (role alternation); got {spec!r}")
    return windows


def acquire_lock(path: Path) -> bool:
    """Single-instance guard: O_EXCL lockfile carrying our pid."""
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(path, "x", encoding="ascii") as handle:  # x = O_CREAT|O_EXCL
            handle.write(str(os.getpid()))
    except FileExistsError:
        return False
    return True


def _stamp() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def run_window(window: int, seed_base: int | None, runner,
               counted: bool = False) -> dict:
    """One sub-game via the real CLI; the exit code is reported verbatim."""
    # a FRESH window must never inherit a dead game's context: wipe this
    # sub-game's stale local resume state (resume is an explicit --resume
    # operator action, never an accident of leftover disk state)
    for stale in (ROOT / "results" / "local").glob(f"resume_*_g{window:02d}.json"): stale.unlink(missing_ok=True)  # noqa: E701
    command = ["uv", "run", CLI, "peer", "--sub-game", str(window)]
    # LEAGUE_GUI=1 -> watch our local truth live (own view only, rules 8-9)
    command += ["--gui"] if os.environ.get("LEAGUE_GUI") else []
    command += ["--seed", str(seed_base + window)] if seed_base is not None else []
    # --counted arms the CLI half of the lecturer-address interlock
    command += ["--counted"] if counted else []
    print(f"[{_stamp()}] window s{window}: launching {' '.join(command)}", flush=True)
    started = time.perf_counter()
    code = int(runner(command, cwd=ROOT).returncode)
    elapsed = round(time.perf_counter() - started, 1)
    verdict = ("settled (exit 0)" if code == 0
               else f"FAILED (exit {code}) - logged, nothing fabricated; the "
                    "settlement guard will refuse the series unless it settles")
    print(f"[{_stamp()}] window s{window}: {verdict} after {elapsed}s", flush=True)
    return {"window": window, "exit": code}




def resume_plan(resume: bool, now: float) -> tuple[bool, float]:
    """(sweep?, tempo-gate `since`). A --resume replays windows of the
    LIVE series: never sweep it aside, and existing predecessor logs
    satisfy the gate (2026-08-23 w5: a partial re-run archive-swept its
    own series, then gated on the logs it had just moved — the peer
    never launched and the rival's replay found a dead door)."""
    return (not resume), (0.0 if resume else now)


def wait_for_previous(window: int, since: float, timeout_sec: float = 1800.0) -> bool:
    """Series tempo: window N launches only after sub-game N-1's log exists
    (either repo's results dir, fresher than this run) - the series is ONE
    sequence across both roles, and a window that starts its budget before
    the rival's driver reaches it burns the budget against nobody."""
    if window <= 1:
        return True
    name = f"log_*_g{window - 1:02d}.json"
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        for base in (ROOT / "results", SIBLING_RESULTS):
            if any(hit.stat().st_mtime >= since for hit in base.glob(name)):
                return True
        time.sleep(3)
    return False

def main(argv: list[str] | None = None, runner=subprocess.run) -> int:
    parser = argparse.ArgumentParser(
        description=f"drive this repo's ({ROLE}) sub-game windows of a counted series")
    parser.add_argument("--sub-games", required=True,
                        help='comma list of THIS repo\'s windows, e.g. "1,3,5"')
    parser.add_argument("--seed", type=int, default=None,
                        help="base seed; window N runs the peer with seed base+N")
    parser.add_argument("--counted", action="store_true",
                        help="counted league series: --counted flows to every peer "
                             "window and the close (lecturer-address interlock)")
    parser.add_argument("--resume", action="store_true",
                        help="replay LIVE-series windows: no sweep; old logs pass the gate")
    args = parser.parse_args(argv)
    try:
        windows = parse_sub_games(args.sub_games)
    except ValueError as error:
        print(f"REFUSED: {error}")
        return 2
    refusal = league_close.email_preflight(ROOT / "config", counted=args.counted)
    if refusal is not None:  # a send posture that cannot deliver plays NOTHING
        print(f"REFUSED (email preflight, zero games played): {refusal}")
        return 2
    if not acquire_lock(LOCK_PATH):
        holder = LOCK_PATH.read_text(encoding="ascii", errors="replace").strip() or "?"
        print(f"REFUSED: another league_series runner holds {LOCK_PATH} (pid "
              f"{holder}); if that run is truly dead, delete the lockfile and retry")
        return 2
    try:
        sweep, run_start = resume_plan(args.resume, time.time())
        if sweep and runner is subprocess.run:  # injected runners = tests: touch nothing
            # A rehearsal derives the SAME uid as a counted run, so leftovers
            # either deadlock the settlement or get counted: start clean.
            print(archive_for_pairing(ROOT, Config.load(ROOT / "config")))
        rows = []
        for window in windows:
            live = runner is subprocess.run  # injected runners = tests: no tempo wait
            if live and not wait_for_previous(window, run_start):
                print(f"window s{window}: previous sub-game never settled in "
                      "either results dir - not launching into a dead window")
                rows.append({"window": window, "exit": 1})
                continue
            rows.append(run_window(window, args.seed, runner, args.counted))
    finally:
        LOCK_PATH.unlink(missing_ok=True)  # ours: we acquired it above
    failed = [f"s{row['window']}" for row in rows if row["exit"] != 0]
    if failed:
        print(f"series windows done; FAILED: {', '.join(failed)} - re-run those "
              "windows before aggregating (series-result will refuse otherwise)")
        return 1
    print(f"series windows done; all {len(rows)} settled")
    return league_close.close_series(ROOT, SIBLING_RESULTS, CLI, runner,
                                     counted=args.counted)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
