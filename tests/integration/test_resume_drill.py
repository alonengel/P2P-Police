"""Slow re-run of the kill-and-resume drill (E6) over real HTTP MCP.
Committed JSONL evidence comes from CLI runs of scripts/resume_drill.py;
tests write theirs to tmp_path (chaos-drill isolation rule)."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import resume_drill  # noqa: E402
from chaos_lib import EvidenceLog  # noqa: E402

pytestmark = pytest.mark.slow


def test_kill_and_resume_drill_recovers_and_finishes(tmp_path: Path) -> None:
    evidence = tmp_path / "resume.jsonl"
    row = resume_drill.run_drill(resume_drill.load_config(), EvidenceLog(evidence),
                                 tmp_path / "snap.json")
    assert row["passed"], row
    assert row["turns_recovered"] >= 1
    assert row["audit"] == "Verified OK" and row["digest_match"]
    assert row["seconds_to_resume"] < resume_drill.load_config().turn_timeout_seconds
    stages = [json.loads(line)["stage"]
              for line in evidence.read_text(encoding="utf-8").splitlines()]
    assert stages[:3] == ["start", "crash", "resume"] and "outcome" in stages
