# ADR-0002: Version lineage — guidelines "1.00" vs rulebook schema "1.2/1.3"

Status: accepted · Date: 2026-07-13

## Context

The submission guidelines (§8) require explicit version tracking **starting at
1.00** for code and configuration. The rulebook's signed shared-config examples
carry `schema_version: "1.2"` (book, Appendix B) and `"1.3"` (official demo),
and `game.toml` `version = "1.10"` — a lineage that is negotiated and locked
with opponents, not freely resettable. The rulebook's own front-matter rule
says contradictions between sources must be documented with a reasoned choice.

## Decision

- **Code version** starts at `CODE_VERSION = "1.00"` (`shared/version.py`),
  satisfying the guidelines. Packaging metadata uses PEP 440 `1.0.0`.
- **Shared config** keeps the rulebook lineage: we pin `schema_version: "1.3"`
  (the demo's current generation, which adds `min_center_intensity`).
  `SUPPORTED_CONFIG_VERSIONS = ("1.2", "1.3")` gates loading at startup.
- **Private game.toml** keeps its book-example lineage `version = "1.10"`.
- Our own JSON files (rate_limits.json, logging_config.json) start at "1.00"
  per the guidelines.

## Consequences

Startup validates config-schema compatibility (guidelines requirement); league
opponents see the schema generation they expect from the book; graders see
1.00-based versioning where we own the lineage. Related: ADR-0001 (parity),
future ADR on config naming (game.json supersedes the guidelines' generic
setup.json example — the rulebook's config architecture is mandatory for this
project).
