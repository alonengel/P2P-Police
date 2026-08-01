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
from p2p_police.shared import tuning
from p2p_police.shared.info_modes import InfoModeError, resolve
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
    rate_limits: dict

    @classmethod
    def load(cls, config_dir: str | Path, private_file: str = "game.toml") -> "Config":
        # private_file seam: `peer --sparring` loads sparring.toml (generic
        # warm-up posture) against the SAME signed game.json constitution.
        directory = Path(config_dir)
        shared = _read_json(directory / "game.json")
        private = _read_toml(directory / private_file)
        from p2p_police.shared.local_overlay import apply_local_overlay

        private = apply_local_overlay(directory, private_file, private)
        limits_path = directory / "rate_limits.json"
        rate_limits = (_read_json(limits_path) if limits_path.is_file() else
                       {"services": {"default": dict(shared["rate_limiter_gatekeeper"])}})

        schema = shared.get("schema_version", "")
        if not is_supported_config(schema):
            raise ConfigError(f"unsupported game.json schema_version {schema!r}")
        for section in REQUIRED_SHARED_SECTIONS:
            if section not in shared:
                raise ConfigError(f"game.json missing mandatory section '{section}'")
        validate_shared_terms(shared)
        # The signed file always wins on key overlap (Appendix B rule).
        private = {k: v for k, v in private.items() if k not in shared}
        return cls(shared=shared, private=private, rate_limits=rate_limits)

    def rule_set(self) -> RuleSet:
        block = self.shared["movement_and_barriers"]
        return RuleSet(max_barriers=block["max_barriers"], max_moves=block["max_moves"],
                       survival_threshold=block["survival_threshold"])

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
        gid = self.private["game"]["group_id"]
        if len(gid) != 8 or " " in gid:  # rule 45: 8 chars, no spaces
            raise ConfigError(f"group_id must be exactly 8 chars, no spaces: {gid!r}")
        return gid

    def endgame(self) -> dict:
        """[strategy.endgame] exact-solver gates/caps (defaults: shared/tuning.py)."""
        return tuning.endgame_table(self.private)

    def info_gain(self) -> dict:
        """[strategy.info_gain] entropy-reduction blend (defaults: shared/tuning.py)."""
        return tuning.info_gain_table(self.private)

    def trap(self) -> dict:
        """[strategy.trap] barrier-gate thresholds (defaults: shared/tuning.py)."""
        return tuning.trap_table(self.private)

    def info_mode(self, wire_shape: str | None = None) -> str:
        """[strategy] info_mode, validated against the registry (ADR-0006).

        Pass the wire shape to have legality checked too: a regime the wire
        cannot serve is a startup error, never a silent downgrade."""
        name = self.private.get("strategy", {}).get("info_mode", "belief")
        try:
            return resolve(name, wire_shape).name
        except InfoModeError as error:
            raise ConfigError(str(error)) from error

    def opponent_group_id(self) -> str | None:
        """[game] opponent_group_id: the peer EXPECTED this session, or None."""
        # Optional. Set, it lets us derive the shared game_uid before the
        # handshake and DECLARE it, so a peer deriving it from a different
        # input is refused at negotiate instead of diverging silently for a
        # whole series. Unset (unknown opponent) declares nothing.
        return str(self.private.get("game", {}).get("opponent_group_id") or "") or None

    def deception(self) -> dict:
        """[deception] self-mirror lie-policy tunables (defaults: shared/tuning.py)."""
        return tuning.deception_table(self.private)

    def resume_enabled(self) -> bool:
        """[resume] enabled (default ON): per-half-turn crash-resume snapshots
        are pure local persistence (results/local/, no wire change) — there is
        no reason to play without them (E6)."""
        return bool(self.private.get("resume", {}).get("enabled", True))

    def identity_block(self) -> dict:
        """Rival-facing identity declaration (shared/identity.py)."""
        from p2p_police.shared.identity import identity_block

        return identity_block(self.private, self.group_id)

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
