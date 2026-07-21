"""Slow re-run of the legal-config-range fuzzer (E5) at a small sample count.
The committed artifact comes from CLI runs of scripts/config_fuzz.py; tests
write theirs to tmp_path (same isolation rule as the chaos drills)."""

import json
import random
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import config_fuzz  # noqa: E402

pytestmark = pytest.mark.slow


def _knobs() -> dict:
    from p2p_police.shared.config import Config

    return Config.load(config_fuzz.ROOT / "config").private["fuzz"]


def test_sampler_stays_inside_the_legal_space() -> None:
    """250 draws: minimums only ever raised, FIXED terms never touched
    (sample_shared asserts that itself), starts valid and distinct."""
    base = json.loads(
        (config_fuzz.ROOT / "config" / "game.json").read_text(encoding="utf-8"))
    knobs, rng = _knobs(), random.Random(0)
    for _ in range(250):
        shared = config_fuzz.sample_shared(rng, base, knobs)
        board, limits = shared["board_and_agents"], shared["movement_and_barriers"]
        grid = board["grid_size"]
        assert 7 <= grid <= int(knobs["grid_size_max"])
        assert 14 <= limits["max_barriers"] <= int(knobs["max_barriers_max"])
        assert 35 <= limits["max_moves"] <= int(knobs["max_moves_max"])
        assert limits["max_moves"] == limits["survival_threshold"]
        cop, thief = board["cop_start"], board["thief_start"]
        assert cop != thief
        for cell in (cop, thief):
            assert 0 <= cell[0] < grid and 0 <= cell[1] < grid


def test_small_fuzz_run_passes_every_invariant(tmp_path: Path) -> None:
    summary = config_fuzz.run_fuzz(samples=2, seed=424242, out_dir=tmp_path,
                                   evidence_path=tmp_path / "config-fuzz.md")
    assert summary["failed"] == 0, summary["failing_configs"]
    assert summary["passed"] == 2
    artifact = json.loads((tmp_path / "config_fuzz.json").read_text(encoding="utf-8"))
    assert artifact["results"] and all(row["ok"] for row in artifact["results"])
    assert "passed" in (tmp_path / "config-fuzz.md").read_text(encoding="utf-8")
