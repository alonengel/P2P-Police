"""Every log artifact COMMITTED to the repo must replay-verify clean.

A stale sealed log (e.g. one generated before a byte-form migration and
never regenerated) reads TAMPERED to any grader or rival running the
replay verifier - this guard makes that class of drift impossible to miss.
Swept homes: results/ top level (the counted series once played - it
starts EMPTY so counted artifacts arrive as pure adds), the per-window
friendly snapshots, and the dev-history archive; the latter two are laid
out as mini repo roots so each log's config artifact resolves beside it."""

from pathlib import Path

import pytest

from p2p_police.sdk.sdk import SimulationSdk

ROOT = Path(__file__).resolve().parents[3]
LOGS = sorted(
    [*(ROOT / "results").glob("log_*.json"),
     *(ROOT / "results" / "friendlies").glob("*/results/log_*.json"),
     *(ROOT / "results" / "dev-history" / "results").glob("log_*.json")])


@pytest.mark.parametrize("log_path", LOGS, ids=lambda p: p.name)
def test_committed_log_verifies_ok(log_path: Path) -> None:
    assert SimulationSdk.verify_log(str(log_path)) == "Verified OK"


def test_the_guard_actually_saw_the_logs() -> None:
    assert LOGS, "no committed log artifacts found - the guard is vacuous"
