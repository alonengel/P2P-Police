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
    config = Config.load(config_dir)
    doc = artifacts.build_declaration(config, "a-vs-b", "uid1", games_played=2)
    group = doc["group"]
    assert group["group_id"] == "anrbj666"
    assert group["counted_games_played"] == 2
    assert group["hardware_spec"]["cpu_cores"] > 0
    assert group["github_commit"]
    assert doc["token_budget_per_series"] == 200000


def test_config_artifact_locks_terms(config_dir: Path) -> None:
    config = Config.load(config_dir)
    doc = artifacts.build_config_artifact(config, "a-vs-b", "uid1", 1)
    assert doc["config_sha256"] and doc["terms"] == config.shared


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
