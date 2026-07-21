"""Slow integration re-run of the chaos drills D1-D4 (real HTTP MCP peers).

Committed JSONL evidence under docs/evidence/drills/ comes from CLI runs of
scripts/chaos_drills.py; tests write their evidence to tmp_path so re-runs
never dirty the repo (same rule as the profiler isolation in conftest)."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import chaos_drills  # noqa: E402
from chaos_lib import EvidenceLog  # noqa: E402

pytestmark = pytest.mark.slow


def test_d1_duplicate_delivery_is_absorbed(tmp_path: Path) -> None:
    path = tmp_path / "d1.jsonl"
    row = chaos_drills.drill_d1(chaos_drills.load_config(), EvidenceLog(path))
    assert row["passed"], row
    assert row["duplicates_dropped"] >= 2  # both resent messages really dropped
    assert row["audit"] == "Verified OK" and row["digest_match"]
    stages = {json.loads(line)["stage"] for line in path.read_text(encoding="utf-8").splitlines()}
    assert {"start", "inject", "observe", "classify", "outcome"} <= stages


def test_d2_silent_opponent_classifies_and_watchdog_persists(tmp_path: Path) -> None:
    row = chaos_drills.drill_d2(chaos_drills.load_config(),
                                EvidenceLog(tmp_path / "d2.jsonl"),
                                tmp_path / "watchdog_dump.json")
    assert row["passed"], row
    assert row["outcome"] == "technical_loss"  # engine-level classification
    assert row["watchdog_fired"]


def test_d3_transport_flap_heals(tmp_path: Path) -> None:
    row = chaos_drills.drill_d3(chaos_drills.load_config(), EvidenceLog(tmp_path / "d3.jsonl"))
    assert row["passed"], row
    assert row["stall_full_turns"] <= 1  # the outage really froze the game
    assert row["outcome"] != "technical_loss" and row["digest_match"]


def test_d4_budget_exhaustion_classifies_cleanly(tmp_path: Path) -> None:
    config = chaos_drills.load_config()
    row = chaos_drills.drill_d4(config, EvidenceLog(tmp_path / "d4.jsonl"))
    assert row["passed"], row
    assert row["outcome"] == "technical_loss"  # engine-level classification
    budget = config.private["chaos"]["turn_timeout_seconds"]
    assert row["seconds_to_classify"] <= budget + 3.0  # bounded, never a hang
