# Evidence — chaos drills (the live path under injected faults)

> Status: complete; re-run after every transport/peer behavior change:
> `uv run python scripts/chaos_drills.py d1 d2 d3 d4 tunnel`. The same four
> in-process drills re-run as slow tests in
> `tests/integration/test_chaos_drills.py` (evidence to tmp, never the repo).

## Setup

| Item | Value |
|---|---|
| Game | REAL games over HTTP MCP: our runtime vs an in-process scripted stub opponent — our OWN runtime in the rival role behind a second real FastMCP server on an ephemeral port (integration-test pattern; never the twin repo's code, ADR-0001) |
| Fault knobs | `config/game.toml [chaos]` (drill-scale budgets; league values untouched in game.json) |
| Evidence | `docs/evidence/drills/*.jsonl`, append-only, one observed event per line with stages start / inject / observe / classify / outcome — every line was emitted while the fault actually ran; nothing is synthesized |

## Drills — all PASS, 2026-07-21

| Drill | Fault | Proves (rulebook) | Observed |
|---|---|---|---|
| D1 duplicate-delivery | the stub's 2nd commit+reveal pair delivered TWICE (at-least-once resend after a lost HTTP ack) | rules 17-21 sealing + the `_consumed` dedup: a duplicate can never desync or become a technical loss | 2 duplicates really dropped (sealing debug log observed); game completed survival/35, digests identical, audits `Verified OK` both sides |
| D2 silent-opponent | stub sends nothing from its 3rd turn on | rules 4-6: bounded waits — a lapsed deadline is failure, not patience; rule 7 watchdog | classified `technical_loss` 4.02 s after the injection (budget 4 s) via `DeadlineExpiredError("opponent commit 6")`; heartbeats stopped with the loop, the watchdog fired ON ITS OWN after its 1.0 s window and persisted positions/turns/outcome; both threads exited — no zombie peer |
| D3 transport-flap-heal | opponent endpoint severed + refusing connections for 1.5 s mid-game (TCP proxy killed, restarted on the same port) | rule 6 retry-until-budget: a brief outage must heal, not forfeit | game froze at full turn 2 (0 turns progressed during the outage), then completed survival/35 with matching digests; the persistent MCP session held the in-flight call through the flap (0 outer retries needed — the outer retry loop is the backstop, exercised in D4) |
| D4 budget-exhaustion | endpoint dead PAST the whole turn budget | rules 4-6: clean classified technical loss, never a hang or crash | classified `technical_loss` 4.03 s after the kill (budget 4 s), 1 outer retry then `DeadlineExpiredError` from the in-flight cap; stub thread also exited cleanly |
| tunnel kill/heal | LIVE: `cloudflared` process killed mid-game, 6 s downtime, restarted (named tunnel `copthief` → stable hostnames) | the D3 property over the real public edge | full public game `cop-mcp.alon.website` ⇄ `thief-mcp.alon.website`; killed at full turn 2, healed, completed survival/35 in 22.7 s from the kill, digests identical, audit `Verified OK`, 2 transport retries |

The classification detail the drills pinned down: the phase machine's book table
only has a TECHNICAL_LOSS edge from COMPUTING_MOVE and AWAITING_REVEAL, so when
a failure lands elsewhere (e.g. mid-COMMITTING) the FSM legally holds its phase
and the classification lives in the engine outcome + typed error — which is
exactly what `run_peer`'s rule-32 net reports.

## Field finding (fixed here): Cloudflare 530

The first live tunnel run failed fast: with the tunnel down, the Cloudflare
edge answers **HTTP 530**, which `_is_connection_flavored` did not treat as
retryable (only 502-504 were listed) — a rival's brief tunnel drop would have
become our immediate technical loss instead of a retry-until-budget wait
(rule 6). Added the `"530"` marker to `infra/mcp_client.py`; the recorded
kill/heal run above is the proof the fix works end-to-end.

## What this does NOT prove

The stub is scripted and deterministic (seeded RandomBrains), the faults are
single-machine, and the tunnel drill is self-play over the real edge. Rival
peers can misbehave in ways no self-drill enumerates; these drills prove OUR
side's contract — bounded waits, dedup, classification, watchdog — holds under
each injected failure class.
