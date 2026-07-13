"""Profiler: honesty accumulates across games; weights bounded; liar inverted."""

from pathlib import Path

from p2p_police.strategy.profiler import OpponentProfiler


def test_honesty_rate_accumulates_and_persists(tmp_path: Path) -> None:
    path = tmp_path / "profiles.json"
    profiler = OpponentProfiler(path)
    profiler.record_audited_verdicts("rival", [True, True, False, True])
    assert profiler.honesty_rate("rival") == 0.75
    reloaded = OpponentProfiler(path)
    reloaded.record_audited_verdicts("rival", [False] * 4)
    assert reloaded.honesty_rate("rival") == 0.375  # 3 truths / 8 hints


def test_unknown_opponent_is_neutral(tmp_path: Path) -> None:
    profiler = OpponentProfiler(tmp_path / "p.json")
    assert profiler.honesty_rate("stranger") == 0.5
    inside, outside = profiler.advised_weights("stranger")
    assert abs(inside - outside) < 1e-9


def test_chronic_liar_gets_inverted_weights(tmp_path: Path) -> None:
    profiler = OpponentProfiler(tmp_path / "p.json")
    profiler.record_audited_verdicts("liar", [False] * 10)
    inside, outside = profiler.advised_weights("liar")
    assert inside < 1.0 < outside


def test_saint_gets_amplified_weights(tmp_path: Path) -> None:
    profiler = OpponentProfiler(tmp_path / "p.json")
    profiler.record_audited_verdicts("saint", [True] * 10)
    inside, outside = profiler.advised_weights("saint")
    assert inside == 3.0 and outside < 1.0
