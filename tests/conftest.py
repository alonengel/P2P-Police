"""Shared fixtures: a valid config pair on tmp_path, mutable per test."""

import json
from pathlib import Path

import pytest

VALID_SHARED = {
    "schema_version": "1.3",
    "agreed_between": ["anrbj666-police", "anrbj666-thief"],
    "board_and_agents": {
        "grid_size": 7,
        "num_agents": 2,
        "thief_start": [3, 3],
        "cop_start": [0, 0],
        "axis_origin_corner": "top-left",
        "axis_start_index": 0,
    },
    "world": {"map_area": "New York", "hint_max_words": 15},
    "movement_and_barriers": {
        "move_set": ["N", "S", "E", "W", "STAY"],
        "max_barriers": 14,
        "max_moves": 35,
        "survival_threshold": 35,
    },
    "scoring": {
        "capture_cop": 20,
        "capture_thief": 5,
        "survival_cop": 5,
        "survival_thief": 10,
        "tie_score": 2,
        "technical_loss": 0,
    },
    "pheromones": {
        "pheromone_center_intensity": 0.9,
        "pheromone_decay": 0.1,
        "pheromone_grid_size": 5,
        "min_center_intensity": 0.5,
    },
    "network_and_league": {
        "response_timeout_sec": 30,
        "watchdog_timeout_sec": 60,
        "num_games": 1,
        "diversity_reward": 10,
        "min_games_to_pass": 2,
        "max_games_per_team": 10,
        "token_budget_per_series": 200000,
    },
    "rate_limiter_gatekeeper": {
        "requests_per_minute": 30,
        "concurrent_requests": 2,
        "retry_backoff_sec": 5,
        "max_retries": 3,
        "queue_depth": 100,
    },
}

VALID_PRIVATE_TOML = """
version = "1.10"

[game]
group_name = "anrbj666"
group_id = "anrbj666"
sub_game_number = 1
members = ["Alon Engel", "Renat Karimov"]

[network]
my_port = 18902
opponent_url = "http://127.0.0.1:18901/mcp"
turn_timeout_seconds = 5

[trash_talk]
provider = "template"

[email]
recipient = "nobody@example.com"
mode = "disabled"
"""


@pytest.fixture
def shared_terms() -> dict:
    return json.loads(json.dumps(VALID_SHARED))  # deep copy


@pytest.fixture
def config_dir(tmp_path: Path, shared_terms: dict) -> Path:
    (tmp_path / "game.json").write_text(json.dumps(shared_terms, indent=2), encoding="utf-8")
    (tmp_path / "game.toml").write_text(VALID_PRIVATE_TOML, encoding="utf-8")
    return tmp_path
