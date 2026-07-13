"""Version tracking (submission guidelines section 8).

Why: the application must validate at startup that the configuration files it
loads belong to a schema generation it knows how to interpret; the graders also
check that explicit versions exist and start at 1.00.
"""

CODE_VERSION = "1.00"

# Shared-config schema generations this code can load (config/game.json
# "schema_version"). The lineage follows the course rulebook's signed-config
# examples, which is why it does not restart at 1.00 (see docs/adr/0002).
SUPPORTED_CONFIG_VERSIONS = ("1.2", "1.3")


def is_supported_config(schema_version: str) -> bool:
    """Return True when a shared-config schema version can be loaded safely."""
    return schema_version in SUPPORTED_CONFIG_VERSIONS
