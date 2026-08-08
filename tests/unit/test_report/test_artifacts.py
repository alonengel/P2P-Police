"""Artifact tests: Table-20 naming, shared game_uid, step-0 fields, emission."""

from pathlib import Path

from p2p_police.domain import game_ids
from p2p_police.report import artifacts
from p2p_police.shared.config import Config


def test_filenames_follow_table_20() -> None:
    assert game_ids.declaration_name("a-vs-b") == "declaration_a-vs-b.json"
    assert game_ids.config_name("a-vs-b", 3) == "config_a-vs-b_g03.json"
    assert game_ids.log_name("a-vs-b", 12) == "log_a-vs-b_g12.json"
    assert game_ids.result_name("a-vs-b") == "result_a-vs-b.json"


def test_game_id_is_order_independent() -> None:
    assert game_ids.build_game_id("zeta", "alpha") == game_ids.build_game_id("alpha", "zeta")


def test_declaration_carries_step0_fields(config_dir: Path) -> None:
    """Book-attached 1-pre-game-declaration shape: symmetric group_1/group_2
    ordered by group_id, game times + token cap at top level."""
    config = Config.load(config_dir)
    doc = artifacts.build_declaration(config, "a-vs-b", "uid1", games_played=2,
                                      started_at="2026-08-03T10:00:00+00:00")
    assert doc["declaration_type"] == "pre_game_declaration"
    assert doc["game_started_at"] and doc["game_ended_at"]
    assert set(doc["links"]) == {"declaration", "config", "log", "result"}
    assert set(doc["groups"]) == {"group_1", "group_2"}
    ours = next(g for g in doc["groups"].values() if g["group_id"] == "anrbj666")
    assert ours["counted_games_played"] == 2
    assert ours["hardware_spec"]["cpu_cores"] > 0
    assert ours["github_commit"] and ours["signature"].startswith("sha256:")
    assert doc["max_tokens_per_game"] == 200000
    assert doc["token_budget_per_series"] == 200000


def test_declaration_spans_the_whole_series(config_dir: Path, tmp_path: Path) -> None:
    """Reference semantics (demo emit_series): game_started_at/game_ended_at =
    FIRST settled sub-game start -> LAST settled end, across every visible
    results dir (own + read-only sibling); foreign-uid logs never widen."""
    import json

    own, sib = tmp_path / "own", tmp_path / "sib"
    own.mkdir(), sib.mkdir()

    def log(dirp: Path, n: int, uid: str, start: str, end: str) -> None:
        (dirp / f"log_a-vs-b_g{n:02d}.json").write_text(json.dumps(
            {"game_uid": uid, "summary": {"started_at": start, "ended_at": end}}),
            encoding="utf-8")

    log(own, 1, "uid1", "2026-08-08T10:00:00+00:00", "2026-08-08T10:00:30+00:00")
    log(sib, 2, "uid1", "2026-08-08T10:00:35+00:00", "2026-08-08T10:01:00+00:00")
    log(own, 3, "other", "2026-08-08T09:00:00+00:00", "2026-08-08T09:30:00+00:00")
    config = Config.load(config_dir)
    doc = artifacts.build_declaration(config, "a-vs-b", "uid1", 0,
                                      started_at="2026-08-08T10:00:35+00:00",
                                      results_dirs=[own, sib])
    assert doc["game_started_at"] == "2026-08-08T10:00:00+00:00"
    assert doc["game_ended_at"] == "2026-08-08T10:01:00+00:00"


def test_config_artifact_locks_terms_flat(config_dir: Path) -> None:
    """Both course example sets carry the agreed sections FLAT at top level
    (never nested under 'terms') — Imree diff 2026-08-03."""
    config = Config.load(config_dir)
    doc = artifacts.build_config_artifact(config, "a-vs-b", "uid1", 1)
    assert doc["config_sha256"] and "terms" not in doc
    for section, values in config.shared.items():
        assert doc[section] == values


def test_log_and_result_share_uid_and_emit(config_dir: Path, tmp_path: Path) -> None:
    config = Config.load(config_dir)
    report = {"outcome": "capture", "turns_completed": 5, "audit": "Verified OK",
              "end_state_digest": "d", "digest_match": True, "role": "police",
              "opponent_group_id": "rival"}
    log = artifacts.build_log(config, "a-vs-b", "uid1", 1, report, [], [])
    result = artifacts.build_result(config, "a-vs-b", "uid1", report, (20, 5), 0)
    assert log["game_uid"] == result["game_uid"] == "uid1"
    assert result["score"] == {"cop": 20, "thief": 5}
    path = artifacts.emit(result, tmp_path, "result_a-vs-b.json")
    assert path.is_file() and "tokens_total" in path.read_text()


def test_result_reports_not_comparable_digest_as_null(config_dir: Path) -> None:
    """A foreign-schema pair has no shared digest construction: the result
    must carry digest_match null — a report of non-comparability, not a
    false accusation (and not a silent false)."""
    import json

    config = Config.load(config_dir)
    report = {"outcome": "survival", "turns_completed": 35, "audit": "Verified OK",
              "end_state_digest": "d", "digest_match": None, "role": "police",
              "opponent_group_id": "rival"}
    result = artifacts.build_result(config, "a-vs-b", "uid1", report, (0, 10), 0)
    assert result["digest_match"] is None
    assert json.loads(json.dumps(result))["digest_match"] is None


def test_declaration_is_signed_and_carries_opponent(config_dir: Path) -> None:
    """Rules 24/37-38/49: hardware sealed, the opponent's declared identity
    fills its OWN group column, sign-then-insert verifiable by a third party."""
    config = Config.load(config_dir)
    opponent = {"group_id": "rival-88", "hardware_spec_sha256": "ab" * 32,
                "identity": {"repos": {"cop": "u1", "thief": "u2"},
                             "counted_games_played": 1}}
    doc = artifacts.build_declaration(config, "a-vs-b", "uid1", 2, opponent=opponent)
    ours = next(g for g in doc["groups"].values() if g["group_id"] == "anrbj666")
    theirs = next(g for g in doc["groups"].values() if g["group_id"] == "rival-88")
    assert ours["hardware_spec_sha256"]
    assert theirs["hardware_spec_sha256"] == "ab" * 32
    assert theirs["counted_games_played"] == 1
    assert theirs["repos"] == {"cop": "u1", "thief": "u2"}
    signed = dict(doc)
    signature = signed.pop("consensus_signature")
    assert artifacts.consensus_signature(signed) == signature


def test_result_winner_group_all_outcomes(config_dir: Path) -> None:
    config = Config.load(config_dir)
    gid = config.group_id
    cases = [  # (role, outcome, expected winner)
        ("police", "capture", gid), ("police", "survival", "rival-88"),
        ("thief", "survival", gid), ("thief", "capture", "rival-88"),
        ("police", "technical_loss", "rival-88"),
    ]
    for role, outcome, expected in cases:
        report = {"role": role, "outcome": outcome, "turns_completed": 1,
                  "end_state_digest": "d" * 64, "opponent_group_id": "rival-88"}
        doc = artifacts.build_result(config, "a-vs-b", "uid1", report, (0, 0), 0)
        assert doc["winner_group"] == expected, (role, outcome)
        assert doc["agreement"]["config_sha256"] and "mcp_servers" in doc
