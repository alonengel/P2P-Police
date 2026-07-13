"""Series aggregation: per-group totals, sub-games won, tie at tie_score."""

import json
from pathlib import Path

import pytest

from p2p_police.domain.scoring import ScoreTable
from p2p_police.sdk.series import aggregate_series

TABLE = ScoreTable(capture_cop=20, capture_thief=5, survival_cop=5, survival_thief=10, tie_score=2)


def write_log(directory: Path, n: int, outcome: str, me="alpha", them="beta", role="police"):
    doc = {"sub_game_number": n, "summary": {
        "outcome": outcome, "turns_completed": 10, "audit": "Verified OK",
        "group_id": me, "opponent_group_id": them, "role": role}}
    (directory / f"log_a-vs-b_g{n:02d}.json").write_text(json.dumps(doc), encoding="utf-8")


def test_two_game_sweep(tmp_path: Path) -> None:
    write_log(tmp_path, 1, "survival")
    write_log(tmp_path, 2, "survival")
    doc = aggregate_series(tmp_path, "a-vs-b", TABLE)
    final = doc["final_result"]
    assert final["total_score"] == {"alpha": 10, "beta": 20}
    assert final["winner_group"] == "beta" and not final["series_tie"]
    assert final["sub_games_won"] == {"alpha": 0, "beta": 2}


def test_series_tie_pays_tie_score(tmp_path: Path) -> None:
    write_log(tmp_path, 1, "capture")            # alpha(cop) 20 / beta 5
    write_log(tmp_path, 2, "capture", role="thief")  # alpha(thief) 5 / beta 20
    doc = aggregate_series(tmp_path, "a-vs-b", TABLE)
    final = doc["final_result"]
    assert final["series_tie"] and final["winner_group"] is None
    assert final["total_score"] == {"alpha": 27, "beta": 27}  # 25 + tie 2


def test_selfplay_groups_disambiguated_by_role(tmp_path: Path) -> None:
    write_log(tmp_path, 1, "survival", me="anrbj666", them="anrbj666")
    doc = aggregate_series(tmp_path, "a-vs-b", TABLE)
    assert set(doc["final_result"]["total_score"]) == {"anrbj666(police)", "anrbj666(thief)"}


def test_missing_logs_raise(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        aggregate_series(tmp_path, "nope", TABLE)
