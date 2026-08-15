"""Tolerant identity reader: nested `opponent_info.identity` wins, a FLAT
opponent_info is the fallback.

League 2026-08-15 (best2934): a peer sent its identity fields flat on
opponent_info — no nested `identity` block — declaring
counted_games_played: 1 and its commit on every handshake, and our reader
looked one level too deep, recording 0 and "unknown" while the truth sat
in our own wire record. Split from test_series_doc.py for the 150-line cap.
"""

import json

from p2p_police.domain.scoring import ScoreTable
from p2p_police.sdk.series import aggregate_series

TABLE = ScoreTable(capture_cop=20, capture_thief=5, survival_cop=5,
                   survival_thief=10, tie_score=2)
UID = "11111111-2222-3333-4444-555555555555"
OUR_IDENTITY = {
    "group_id": "alpha",
    "repos": {"cop": "https://example.test/our-cop",
              "thief": "https://example.test/our-thief"},
    "github_commit": "abc123",
    "counted_games_played": 2,
}


def write_flat_log(directory, n, outcome, role):
    doc = {"game_uid": UID, "sub_game_number": n, "summary": {
        "outcome": outcome, "turns_completed": 10, "audit": "Verified OK",
        "group_id": "alpha", "opponent_group_id": "beta", "role": role,
        "ended_at": f"2026-07-24T14:0{n}:00+00:00",
        "opponent_info": {"code_version": "1.00",
                          "counted_games_played": 1,
                          "github_commit": "f1a7" * 10,
                          "repos": {"cop": "https://example.test/fc",
                                    "thief": "https://example.test/ft"}}}}
    (directory / f"log_a-vs-b_g{n:02d}.json").write_text(
        json.dumps(doc), encoding="utf-8")


def test_flat_identity_opponent_info_is_read(tmp_path) -> None:
    write_flat_log(tmp_path, 1, "survival", "police")
    write_flat_log(tmp_path, 2, "capture", "thief")
    doc, _ = aggregate_series(tmp_path, "a-vs-b", TABLE, 2, OUR_IDENTITY)
    assert doc["final_result"]["games_played_including_this"]["beta"] == 1
    assert doc["sub_games"][0]["github_commit"]["beta"] == "f1a7" * 10
    assert doc["links"]["github"]["beta"] == {
        "cop": "https://example.test/fc", "thief": "https://example.test/ft"}


def test_nested_identity_still_wins_over_flat_siblings(tmp_path) -> None:
    """When BOTH shapes appear, the nested block is authoritative."""
    doc = {"game_uid": UID, "sub_game_number": 1, "summary": {
        "outcome": "survival", "turns_completed": 10, "audit": "Verified OK",
        "group_id": "alpha", "opponent_group_id": "beta", "role": "police",
        "ended_at": "2026-07-24T14:01:00+00:00",
        "opponent_info": {"counted_games_played": 9,
                          "identity": {"group_id": "beta",
                                       "counted_games_played": 1}}}}
    (tmp_path / "log_a-vs-b_g01.json").write_text(
        json.dumps(doc), encoding="utf-8")
    result, _ = aggregate_series(tmp_path, "a-vs-b", TABLE, 1, OUR_IDENTITY)
    assert result["final_result"]["games_played_including_this"]["beta"] == 1
