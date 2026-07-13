"""Tests for shared.version — the startup config-compatibility gate."""

from p2p_police.shared.version import (
    CODE_VERSION,
    SUPPORTED_CONFIG_VERSIONS,
    is_supported_config,
)


def test_code_version_starts_at_1_00() -> None:
    assert CODE_VERSION == "1.00"


def test_supported_config_versions_are_nonempty() -> None:
    assert SUPPORTED_CONFIG_VERSIONS
    assert all(isinstance(v, str) for v in SUPPORTED_CONFIG_VERSIONS)


def test_supported_schema_is_accepted() -> None:
    assert is_supported_config(SUPPORTED_CONFIG_VERSIONS[0])


def test_unknown_schema_is_rejected() -> None:
    assert not is_supported_config("0.0")


def test_empty_schema_is_rejected() -> None:
    assert not is_supported_config("")
