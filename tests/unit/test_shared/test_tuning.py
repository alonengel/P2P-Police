"""[strategy.endgame] / [strategy.info_gain] / [strategy.trap]: defaults, TOML
override merge with type coercion, and the Config accessors that expose them."""

from pathlib import Path

from p2p_police.shared.config import Config
from p2p_police.shared.tuning import (
    ENDGAME_DEFAULTS,
    INFO_GAIN_DEFAULTS,
    TRAP_DEFAULTS,
    endgame_table,
    info_gain_table,
    trap_table,
)


def test_empty_private_config_yields_the_shipped_defaults() -> None:
    assert endgame_table({}) == ENDGAME_DEFAULTS
    assert info_gain_table({}) == INFO_GAIN_DEFAULTS
    assert trap_table({}) == TRAP_DEFAULTS


def test_toml_block_overrides_and_coerces_types() -> None:
    private = {"strategy": {"endgame": {"node_cap": 5.0, "enabled": False,
                                        "unknown_key": 1}}}
    table = endgame_table(private)
    assert table["node_cap"] == 5 and isinstance(table["node_cap"], int)
    assert table["enabled"] is False
    assert "unknown_key" not in table  # never smuggle unvetted knobs in
    assert table["max_horizon_turns"] == ENDGAME_DEFAULTS["max_horizon_turns"]


def test_config_accessors_read_the_strategy_tables(config_dir: Path) -> None:
    toml_path = config_dir / "game.toml"
    toml_path.write_text(
        toml_path.read_text(encoding="utf-8")
        + "\n[strategy.endgame]\nmax_horizon_turns = 7\n"
        + "\n[strategy.info_gain]\nweight = 2.5\nenabled = false\n",
        encoding="utf-8",
    )
    config = Config.load(config_dir)
    assert config.endgame()["max_horizon_turns"] == 7
    assert config.endgame()["enabled"] == ENDGAME_DEFAULTS["enabled"]
    assert config.info_gain() == {**INFO_GAIN_DEFAULTS, "weight": 2.5, "enabled": False}


def test_trap_gate_is_config_driven_not_hardcoded(config_dir: Path) -> None:
    """The barrier gate is a swept play-strength knob, so it must be readable
    from the private config rather than frozen in the brain's source."""
    toml_path = config_dir / "game.toml"
    toml_path.write_text(
        toml_path.read_text(encoding="utf-8") + "\n[strategy.trap]\nrange = 5\n",
        encoding="utf-8",
    )
    config = Config.load(config_dir)
    assert config.trap() == {**TRAP_DEFAULTS, "range": 5}
