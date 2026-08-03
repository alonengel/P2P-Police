"""Structural conformance of the emitted series result.

A live counterparty diffs our result against the official demo's sample-run
result; the key sets below are transcribed from that sample (course
DemoExamples material by the lecturer's team - used here as the learn-only
reference for KEY STRUCTURE; every value is our own). Our document must be
a key SUPERSET at every level, and game_uid must be the logs' real shared
uid - never null (it is the cross-team series identity both reports must
match on).
"""

import json

from p2p_police.domain.scoring import ScoreTable
from p2p_police.report.artifacts import consensus_signature
from p2p_police.sdk.series import aggregate_series

TABLE = ScoreTable(capture_cop=20, capture_thief=5, survival_cop=5,
                   survival_thief=10, tie_score=2)
UID = "11111111-2222-3333-4444-555555555555"


def write_log(directory, n, outcome, role="police"):
    doc = {"game_uid": UID, "sub_game_number": n, "summary": {
        "outcome": outcome, "turns_completed": 10, "audit": "Verified OK",
        "group_id": "alpha", "opponent_group_id": "beta", "role": role,
        "ended_at": f"2026-07-24T14:0{n}:00+00:00",
        "opponent_info": {"terms": {"num_games": 2},
                          "identity": {"group_id": "beta", "members": ["R. Ival"],
                                       "repos": {"cop": "https://example.test/their-cop",
                                                 "thief": "https://example.test/their-thief"},
                                       "mcp_servers": {"cop": "https://example.test/mcp"}}}}}
    (directory / f"log_a-vs-b_g{n:02d}.json").write_text(json.dumps(doc), encoding="utf-8")

REFERENCE_TOP_KEYS = {
    "_schema", "schema_version", "report_type", "game_id", "game_uid",
    "links", "timezone", "groups", "num_sub_games", "sub_games",
    "final_result", "mutual_agreement",
}
REFERENCE_SUB_GAME_KEYS = {
    "sub_game_number", "roles", "started_at", "ended_at", "result",
    "winner_group", "tie", "github_commit", "tokens", "score",
    "log_files", "audit",
}
REFERENCE_FINAL_KEYS = {
    "total_score", "sub_games_won", "ties", "winner_group", "series_tie",
    "tokens_total_series",
}
REFERENCE_AUDIT_KEYS = {"log_verified", "tampered"}
REFERENCE_AGREEMENT_KEYS = {"sha256", "confirmed"}
REFERENCE_LINK_KEYS = {"declaration", "config", "log", "result"}

OUR_IDENTITY = {
    "group_id": "alpha",
    "members": ["Alon Engel", "Renat Karimov"],
    "repos": {"cop": "https://example.test/our-cop",
              "thief": "https://example.test/our-thief"},
    "mcp_servers": {"cop": "http://127.0.0.1:8802/mcp"},
    "github_commit": "abc123",
    "counted_games_played": 2,
}


def build(tmp_path):
    write_log(tmp_path, 1, "survival")
    write_log(tmp_path, 2, "capture", role="thief")
    doc, _ = aggregate_series(tmp_path, "a-vs-b", TABLE, 2, OUR_IDENTITY)
    return doc


def test_top_level_keys_cover_the_reference(tmp_path) -> None:
    doc = build(tmp_path)
    assert set(doc) >= REFERENCE_TOP_KEYS
    assert doc["report_type"] == "final_game_result"
    assert doc["game_uid"] == UID and doc["game_uid"] is not None
    assert doc["num_sub_games"] == 2 and doc["timezone"]


def test_sub_game_entries_cover_the_reference_keys(tmp_path) -> None:
    doc = build(tmp_path)
    for entry in doc["sub_games"]:
        assert set(entry) >= REFERENCE_SUB_GAME_KEYS
        assert set(entry["audit"]) >= REFERENCE_AUDIT_KEYS
        assert set(entry["roles"].values()) == {"police", "thief"}
        assert set(entry["score"]) == {"alpha", "beta"}
    first = doc["sub_games"][0]  # survival with us as cop -> thief side won
    assert first["result"] == "survival" and first["winner_group"] == "beta"
    assert first["tie"] is False and first["ended_at"]
    second = doc["sub_games"][1]  # capture with us as thief -> cop side won
    assert second["winner_group"] == "beta"
    assert second["github_commit"]["alpha"] == "abc123"


def test_final_result_and_links_cover_the_reference(tmp_path) -> None:
    doc = build(tmp_path)
    assert set(doc["final_result"]) >= REFERENCE_FINAL_KEYS
    assert set(doc["links"]) >= REFERENCE_LINK_KEYS
    assert doc["links"]["result"] == "result_a-vs-b.json"
    github = doc["links"]["github"]  # the book's four repo links, both teams
    urls = [url for repos in github.values() for url in repos.values()]
    assert len(urls) == 4 and all(url.startswith("https://") for url in urls)


def test_groups_is_the_flat_id_pair_sample_verbatim(tmp_path) -> None:
    """The book's attached example homes identity in the DECLARATION; the
    result's `groups` is two ids and nothing else, so two honest reports
    cannot diff on shape (2026-08-01 report-diff with imreeyal)."""
    doc = build(tmp_path)
    assert doc["groups"] == ["alpha", "beta"]
    assert doc["timezone"] == "Asia/Jerusalem"  # the sample's label


def test_all_four_repo_links_survive_the_flattening(tmp_path) -> None:
    """Rule 49 still needs both teams' cop+thief links in the emailed file —
    they live under links.github, sourced from config + their handshake."""
    github = build(tmp_path)["links"]["github"]
    assert set(github) == {"alpha", "beta"}
    assert github["alpha"] == OUR_IDENTITY["repos"]
    assert github["beta"]["cop"] == "https://example.test/their-cop"


def test_mutual_agreement_signed_then_inserted_and_confirmed(tmp_path) -> None:
    """EXACTLY the book-attached shape {sha256, confirmed}: enrichment
    belongs in the LOG's agreement block, never here (Imree diff 2026-08-03)."""
    doc = build(tmp_path)
    agreement = doc["mutual_agreement"]
    assert set(agreement) == REFERENCE_AGREEMENT_KEYS
    assert agreement["confirmed"] is True
    body = {k: v for k, v in doc.items() if k != "mutual_agreement"}
    assert agreement["sha256"] == consensus_signature(body)


def test_league_fields_friendly_fabricates_no_counted_record(tmp_path) -> None:
    """UNCOUNTED default: declared counts pass through UNBUMPED and no
    diversity reward — a rehearsal must not assert counted-game facts
    (imreeyal pair diff 2026-08-03, same bug class both teams)."""
    final = build(tmp_path)["final_result"]
    assert final["games_played_including_this"]["alpha"] \
        == OUR_IDENTITY["counted_games_played"]
    assert final["games_played_including_this"]["beta"] == 0
    assert final["first_meeting_between_groups"] is True  # factually true
    assert all(applied is False for applied
               in final["diversity_reward_applied"].values())


def test_league_fields_counted_series_bumps_and_rewards(tmp_path) -> None:
    """COUNTED arming: counts include this game; the diversity reward rides
    the winner of a first counted meeting only (book-attached shape)."""
    write_log(tmp_path, 1, "survival")
    write_log(tmp_path, 2, "capture", role="thief")
    doc, _ = aggregate_series(tmp_path, "a-vs-b", TABLE, 2, OUR_IDENTITY,
                              counted=True)
    final = doc["final_result"]
    assert final["games_played_including_this"]["alpha"] \
        == OUR_IDENTITY["counted_games_played"] + 1
    assert final["games_played_including_this"]["beta"] == 1
    winner = final["winner_group"]
    assert all(applied == (group == winner) for group, applied
               in final["diversity_reward_applied"].items())
