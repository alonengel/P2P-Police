"""Every log artifact COMMITTED to results/ must replay-verify clean.

A stale sealed log (e.g. one generated before a byte-form migration and
never regenerated) reads TAMPERED to any grader or rival running the
replay verifier - this guard makes that class of drift impossible to miss."""

from pathlib import Path

import pytest

from p2p_police.sdk.sdk import SimulationSdk

RESULTS = Path(__file__).resolve().parents[3] / "results"
LOGS = sorted(RESULTS.glob("log_*.json"))


@pytest.mark.parametrize("log_path", LOGS, ids=lambda p: p.name)
def test_committed_log_verifies_ok(log_path: Path) -> None:
    assert SimulationSdk.verify_log(str(log_path)) == "Verified OK"


def test_the_guard_actually_saw_the_logs() -> None:
    assert LOGS, "results/ holds no log artifacts - the guard is vacuous"
