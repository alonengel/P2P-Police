"""Config-loader tests: version gate at startup, JSON-overrides-TOML,
mandatory sections, typed accessors (guidelines section 7-8 + Appendix B)."""

import json
from pathlib import Path

import pytest

from p2p_police.shared.config import Config, ConfigError


def test_valid_pair_loads(config_dir: Path) -> None:
    config = Config.load(config_dir)
    assert config.grid_size == 7
    assert config.cop_start == (0, 0)
    assert config.thief_start == (3, 3)
    assert config.group_id == "anrbj666"
    assert config.my_port == 18902
    assert config.opponent_url.endswith(":18901/mcp")
    assert config.response_timeout_sec == 30.0
    assert config.retry_backoff_sec == 5.0


def test_typed_rule_set_and_score_table(config_dir: Path) -> None:
    config = Config.load(config_dir)
    assert config.rule_set().max_barriers == 14
    assert config.score_table().capture_cop == 20


def test_unsupported_schema_version_is_refused(config_dir: Path, shared_terms: dict) -> None:
    shared_terms["schema_version"] = "9.9"
    (config_dir / "game.json").write_text(json.dumps(shared_terms), encoding="utf-8")
    with pytest.raises(ConfigError, match="schema_version"):
        Config.load(config_dir)


def test_missing_section_is_refused(config_dir: Path, shared_terms: dict) -> None:
    del shared_terms["pheromones"]
    (config_dir / "game.json").write_text(json.dumps(shared_terms), encoding="utf-8")
    with pytest.raises(ConfigError, match="pheromones"):
        Config.load(config_dir)


def test_missing_files_are_refused(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="missing config file"):
        Config.load(tmp_path)


def test_invalid_json_is_refused(config_dir: Path) -> None:
    (config_dir / "game.json").write_text("{not json", encoding="utf-8")
    with pytest.raises(ConfigError, match="invalid JSON"):
        Config.load(config_dir)


def test_shared_terms_violation_is_refused_at_load(config_dir: Path, shared_terms: dict) -> None:
    shared_terms["scoring"]["capture_cop"] = 99
    (config_dir / "game.json").write_text(json.dumps(shared_terms), encoding="utf-8")
    with pytest.raises(Exception, match="FIXED"):
        Config.load(config_dir)


def test_json_overrides_toml_on_key_overlap(config_dir: Path) -> None:
    """A private top-level key colliding with a signed one is dropped."""
    toml_text = (config_dir / "game.toml").read_text(encoding="utf-8")
    (config_dir / "game.toml").write_text(
        toml_text + '\n[scoring]\ncapture_cop = 999\n', encoding="utf-8"
    )
    config = Config.load(config_dir)
    assert "scoring" not in config.private
    assert config.score_table().capture_cop == 20
