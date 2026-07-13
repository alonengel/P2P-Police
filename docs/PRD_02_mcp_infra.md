# PRD 02 — FastMCP infrastructure (rulebook ch. 2, stage 2 of 7)

## Goal

Two independent processes — this peer and the twin-repo peer — exchange game
actions over FastMCP on localhost. Still "geometric": payloads carry serial
coordinates/moves (the book's stage-2 shape; free language replaces them in
stage 4 — rule 27 governs real games, not this dev stage).

## Scope

| Module | Contract |
|---|---|
| shared/config | Load `config/game.json` (signed shared terms) + `config/game.toml` (private); **JSON overrides TOML on any key overlap**; schema_version gated by SUPPORTED_CONFIG_VERSIONS at startup; typed accessors (RuleSet, ScoreTable, pheromones, network, identity) |
| domain/negotiation (parity-locked) | Canonical serialization of the shared terms → `config_sha256`; validation of the Appendix-VI limits (fixed values exact, minimums not lowered — rule 12); the agreement payload incl. **intra-turn commit order pinning** (cop acts first — the PRD-01 assumption made an explicit agreed term) |
| peer/deadline | Monotonic-clock deadline on EVERY awaited request (rule 6 / ch. 8: a lapsed deadline is failure, not patience); injectable clock for tests |
| infra/mcp_server | Own FastMCP server exposing 4 tools — `negotiate`, `receive_turn`, `submit_audit`, `receive_control` — each dropping payloads into thread-safe inbox queues; port-busy fail-fast; daemon thread |
| infra/mcp_client | `McpTransport` calling the opponent's tools by URL; retry-until-opponent-up (peers start seconds apart) bounded by a deadline |
| peer/runtime (minimal) | Geometric lockstep: negotiate (sha + commit order) → turn loop driving the SAME GameEngine on both sides → end-state cross-check |
| sdk + cli | `run_peer(config_dir, seed)` behind the SimulationSdk facade; `p2p-police peer` subcommand |

## Binding requirements encoded as tests

- Config: unsupported schema_version refused at load; game.json wins over
  game.toml on overlap; missing mandatory sections refused.
- Negotiation: byte-different shared terms → different sha (rule 11); fixed
  Appendix-VI values altered → rejected; minimums lowered → rejected (rule 12);
  raised minimums accepted; commit-order mismatch → no agreement.
- Deadline: expiry computed on a monotonic clock; awaiting past expiry raises.
- Server: second bind on a busy port fails fast with a clear message.
- Transport: opponent-down connection errors retried with the configured
  backoff until the deadline, then surfaced.
- Integration (slow, real HTTP on an ephemeral localhost port): a payload sent
  through McpTransport arrives in the peer's inbox intact.

## Milestone (definition of done)

`p2p-police peer` and `p2p-thief peer` (two processes, two repos) complete a
full geometric game over localhost: identical config sha verified, commit
order agreed, every move applied to both engines, and both sides finish with
the SAME outcome, positions, turn count and barrier set (end-state digest
match). Evidence recorded in PLAN.md.
