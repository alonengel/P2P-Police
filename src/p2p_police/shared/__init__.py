"""Cross-cutting utilities: configuration, versioning, gatekeeper, rate limiting."""

from p2p_police.shared.version import CODE_VERSION, SUPPORTED_CONFIG_VERSIONS

__all__ = ["CODE_VERSION", "SUPPORTED_CONFIG_VERSIONS"]
