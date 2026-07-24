"""Series aggregation: totals/tie math plus the settlement guard (rule 35),
the stale-log contamination guards, and multi-dir (both role repos) input."""

import json
from pathlib import Path

import pytest

from p2p_police.domain.scoring import ScoreTable
from p2p_police.sdk.series import SeriesSettlementError, aggregate_series

TABLE = ScoreTable(capture_cop=20, capture_thief=5, survival_cop=5, survival_thief=10, tie_score=2)
UID = "11111111-2222-3333-4444-555555555555"
STALE_UID = "99999999-8888-7777-6666-555555555555"


def write_log(directory: Path, n: int, outcome: str, me="alpha", them="beta", role="police",
              uid=UID, num_games=2, audit="Verified OK", game_id="a-vs-b") -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    doc = {"game_uid": uid, "sub_game_number": n, "summary": {
        "outcome": outcome, "turns_completed": 10, "audit": audit,
        "group_id": me, "opponent_group_id": them, "role": role,
        "ended_at": f"2026-07-24T14:0{n}:00+00:00",
        "opponent_info": {"terms": {"num_games": num_games},
                          "identity": {"group_id": them, "members": ["R. Ival"],
                                       "repos": {"cop": "https://example.test/their-cop",
                                                 "thief": "https://example.test/their-thief"},
                                       "mcp_servers": {"cop": "https://example.test/mcp"}}}}}
    path = directory / f"log_{game_id}_g{n:02d}.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def test_two_game_sweep_totals_winner_and_real_uid(tmp_path: Path) -> None:
    write_log(tmp_path, 1, "survival")
    write_log(tmp_path, 2, "survival")
    doc, excluded = aggregate_series(tmp_path, "a-vs-b", TABLE, 2)
    assert excluded == []
    assert doc["game_uid"] == UID  # the logs' shared uid, never null
    final = doc["final_result"]
    assert final["total_score"] == {"alpha": 10, "beta": 20}
    assert final["winner_group"] == "beta" and not final["series_tie"]
    assert final["sub_games_won"] == {"alpha": 0, "beta": 2}
    assert final["tokens_total_series"] == {"alpha": 0, "beta": 0}


def test_series_tie_pays_tie_score(tmp_path: Path) -> None:
    write_log(tmp_path, 1, "capture")                # alpha(cop) 20 / beta 5
    write_log(tmp_path, 2, "capture", role="thief")  # alpha(thief) 5 / beta 20
    doc, _ = aggregate_series(tmp_path, "a-vs-b", TABLE, 2)
    final = doc["final_result"]
    assert final["series_tie"] and final["winner_group"] is None
    assert final["total_score"] == {"alpha": 27, "beta": 27}  # 25 + tie 2


def test_selfplay_groups_disambiguated_by_role(tmp_path: Path) -> None:
    write_log(tmp_path, 1, "survival", me="anrbj666", them="anrbj666")
    write_log(tmp_path, 2, "survival", me="anrbj666", them="anrbj666", role="thief")
    doc, _ = aggregate_series(tmp_path, "a-vs-b", TABLE, 2)
    assert set(doc["final_result"]["total_score"]) == {"anrbj666(police)", "anrbj666(thief)"}


def test_settlement_guard_refuses_5_of_6_naming_s6(tmp_path: Path) -> None:
    """Rule 35: a report that quietly completes a missing game endangers the
    counterparty - 5 settled logs of a declared 6 must refuse, naming s6."""
    for n in range(1, 6):
        write_log(tmp_path, n, "survival", num_games=6)
    with pytest.raises(SeriesSettlementError) as caught:
        aggregate_series(tmp_path, "a-vs-b", TABLE, 6)
    assert "s6" in str(caught.value) and "no settled log" in str(caught.value)


def test_settlement_guard_refuses_unclean_audit_naming_the_slot(tmp_path: Path) -> None:
    write_log(tmp_path, 1, "survival")
    write_log(tmp_path, 2, "survival", audit="TAMPERED")
    with pytest.raises(SeriesSettlementError) as caught:
        aggregate_series(tmp_path, "a-vs-b", TABLE, 2)
    assert "s2" in str(caught.value) and "TAMPERED" in str(caught.value)


def test_multi_dir_aggregation_pools_both_role_repos(tmp_path: Path) -> None:
    write_log(tmp_path / "police", 1, "survival")
    write_log(tmp_path / "thief", 2, "survival", role="thief")
    doc, excluded = aggregate_series(
        [tmp_path / "police", tmp_path / "thief"], "a-vs-b", TABLE, 2)
    assert excluded == []
    assert [e["sub_game_number"] for e in doc["sub_games"]] == [1, 2]


def test_stale_uid_log_excluded_by_name_not_silently(tmp_path: Path) -> None:
    write_log(tmp_path / "fresh", 1, "survival")
    write_log(tmp_path / "fresh", 2, "survival", role="thief")
    stale = write_log(tmp_path / "old", 1, "capture", uid=STALE_UID)
    doc, excluded = aggregate_series(
        [tmp_path / "fresh", tmp_path / "old"], "a-vs-b", TABLE, 2)
    assert doc["game_uid"] == UID
    assert doc["sub_games"][0]["result"] == "survival"  # the stale capture never entered
    assert any(stale.name in note and STALE_UID in note for note in excluded)


def test_wrong_declared_num_games_excluded_by_name(tmp_path: Path) -> None:
    write_log(tmp_path / "fresh", 1, "survival")
    write_log(tmp_path / "fresh", 2, "survival", role="thief")
    stale = write_log(tmp_path / "old", 2, "capture", num_games=6)
    doc, excluded = aggregate_series(
        [tmp_path / "fresh", tmp_path / "old"], "a-vs-b", TABLE, 2)
    assert doc["sub_games"][1]["result"] == "survival"
    assert any(stale.name in note and "num_games=6" in note for note in excluded)


def test_uid_disagreement_without_majority_refuses(tmp_path: Path) -> None:
    write_log(tmp_path, 1, "survival")
    write_log(tmp_path, 2, "survival", uid=STALE_UID)
    with pytest.raises(SeriesSettlementError) as caught:
        aggregate_series(tmp_path, "a-vs-b", TABLE, 2)
    assert "disagree" in str(caught.value)
    assert UID in str(caught.value) and STALE_UID in str(caught.value)


def test_no_logs_refuse(tmp_path: Path) -> None:
    with pytest.raises(SeriesSettlementError):
        aggregate_series(tmp_path, "nope", TABLE, 2)
