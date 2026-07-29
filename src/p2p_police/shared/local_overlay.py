"""Gitignored `<name>.local.toml` private overlay (split from config.py for
the 150-code-line cap).

Per-session local overrides — e.g. the sparring partner's tunnel URL of the
day — deep-merge OVER the committed private baseline, so the repo never
hard-codes another team's infrastructure. Private side only: the SIGNED
game.json still wins every overlap downstream.
"""

import tomllib
from pathlib import Path


def apply_local_overlay(directory: Path, private_file: str, private: dict) -> dict:
    """Merge `<stem>.local.toml` over `private` when it exists."""
    local_path = directory / f"{Path(private_file).stem}.local.toml"
    if not local_path.is_file():
        return private
    return _deep_merge(private, tomllib.loads(local_path.read_text(encoding="utf-8")))


def _deep_merge(base: dict, overlay: dict) -> dict:
    """Overlay wins leaf-by-leaf; nested tables merge instead of replacing
    wholesale, so a one-key [network] overlay keeps the section's other keys."""
    merged = dict(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged
