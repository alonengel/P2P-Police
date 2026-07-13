"""Configuration loader (rulebook Appendix B + submission guidelines section 7).

Two files, one bright line: `game.json` holds everything both sides agreed and
signed; `game.toml` holds only private/local choices. On any key overlap the
SIGNED side wins - the private file can never weaken an agreed term. The
schema_version is gated against SUPPORTED_CONFIG_VERSIONS at load (startup
version-compatibility check, guidelines section 8).
"""

import json
import tomllib
from dataclasses import dataclass
from pathlib import Path

from p2p_police.domain.negotiation import validate_shared_terms
from p2p_police.domain.rules import RuleSet
from p2p_police.domain.scoring import ScoreTable
from p2p_police.shared.version import is_supported_config

REQUIRED_SHARED_SECTIONS = (
    "board_and_agents",
    "world",
    "movement_and_barriers",
    "scoring",
    "pheromones",
    "network_and_league",
    "rate_limiter_gatekeeper",
)


class ConfigError(Exception):
    """Configuration missing, malformed, or violating the signed contract."""


@dataclass(frozen=True)
class Config:
    """Loaded, validated configuration pair.

    Input: a config directory. Output: typed accessors over agreed terms.
    Setup: `Config.load(config_dir)`.
    """

    shared: dict
    private: dict

    @classmethod
    def load(cls, config_dir: str | Path) -> "Config":
        directory = Path(config_dir)
        shared = _read_json(directory / "game.json")
        private = _read_toml(directory / "game.toml")

        schema = shared.get("schema_version", "")
        if not is_supported_config(schema):
            raise ConfigError(f"unsupported game.json schema_version {schema!r}")
        for section in REQUIRED_SHARED_SECTIONS:
            if section not in shared:
                raise ConfigError(f"game.json missing mandatory section '{section}'")
        validate_shared_terms(shared)
        # The signed file always wins on key overlap (Appendix B rule).
        private = {k: v for k, v in private.items() if k not in shared}
        return cls(shared=shared, private=private)

    def rule_set(self) -> RuleSet:
        block = self.shared["movement_and_barriers"]
        return RuleSet(
            max_barriers=block["max_barriers"],
            max_moves=block["max_moves"],
            survival_threshold=block["survival_threshold"],
        )

    def score_table(self) -> ScoreTable:
        return ScoreTable(**self.shared["scoring"])

    @property
    def grid_size(self) -> int:
        return self.shared["board_and_agents"]["grid_size"]

    @property
    def cop_start(self) -> tuple[int, int]:
        return tuple(self.shared["board_and_agents"]["cop_start"])

    @property
    def thief_start(self) -> tuple[int, int]:
        return tuple(self.shared["board_and_agents"]["thief_start"])

    @property
    def pheromones(self) -> dict:
        return self.shared["pheromones"]

    @property
    def group_id(self) -> str:
        return self.private["game"]["group_id"]

    @property
    def my_port(self) -> int:
        return self.private["network"]["my_port"]

    @property
    def opponent_url(self) -> str:
        return self.private["network"]["opponent_url"]

    @property
    def turn_timeout_seconds(self) -> float:
        return float(self.private["network"]["turn_timeout_seconds"])

    @property
    def response_timeout_sec(self) -> float:
        return float(self.shared["network_and_league"]["response_timeout_sec"])

    @property
    def retry_backoff_sec(self) -> float:
        return float(self.shared["rate_limiter_gatekeeper"]["retry_backoff_sec"])


def _read_json(path: Path) -> dict:
    if not path.is_file():
        raise ConfigError(f"missing config file: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ConfigError(f"invalid JSON in {path}: {error}") from error


def _read_toml(path: Path) -> dict:
    if not path.is_file():
        raise ConfigError(f"missing config file: {path}")
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as error:
        raise ConfigError(f"invalid TOML in {path}: {error}") from error
