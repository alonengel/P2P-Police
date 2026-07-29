"""Gitignored `<name>.local.toml` overlay: per-session private overrides
(e.g. a sparring partner's tunnel URL) deep-merge over the committed
baseline — the repo never hard-codes another team's infrastructure and the
SIGNED game.json still wins every overlap."""

from pathlib import Path

from p2p_police.shared.config import Config


def test_local_overlay_overrides_one_key(config_dir: Path) -> None:
    (config_dir / "game.local.toml").write_text(
        '[network]\nopponent_url = "https://partner.example.com/mcp"\n',
        encoding="utf-8")
    config = Config.load(config_dir)
    assert config.opponent_url == "https://partner.example.com/mcp"
    # sibling keys of the overlaid section survive the merge
    assert config.my_port == 18902


def test_absent_overlay_changes_nothing(config_dir: Path) -> None:
    config = Config.load(config_dir)
    assert config.opponent_url.endswith(":18901/mcp")


def test_overlay_is_scoped_to_its_private_file(config_dir: Path) -> None:
    """game.local.toml must not leak into a sparring.toml load."""
    (config_dir / "game.local.toml").write_text(
        '[network]\nopponent_url = "https://partner.example.com/mcp"\n',
        encoding="utf-8")
    (config_dir / "sparring.toml").write_text(
        (config_dir / "game.toml").read_text(encoding="utf-8"), encoding="utf-8")
    config = Config.load(config_dir, private_file="sparring.toml")
    assert config.opponent_url.endswith(":18901/mcp")
