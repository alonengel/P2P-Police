# PLAN — Architecture & technical planning (P2P-Police)

## 1. C4: Context

Two autonomous agents — this Cop and a rival Thief — play over the public
internet. External systems: the opponent's FastMCP endpoint (the ONLY thing we
know about them), Gmail API (automatic league reports), GitHub (submission +
per-game commit IDs), a Cloudflare tunnel (public exposure), optional LLM
providers (verbal layer only). There is **no game server**: state lives locally
in each peer and truth is established cryptographically.

## 2. C4: Containers

One Python process per game role. This repo ships the Police process:
Tkinter GUI (local truth only) + CLI → **SDK facade** → domain services →
infrastructure (MCP server/client, LLM providers, Gmail). The Thief process
lives in the sibling repo **P2P-Thief** and must never share live state with
this one (rulebook binding separation rule: no shared memory, no imported
live-state module, no shared variables — twins are DUPLICATED code, two
processes, two repos).

## 3. C4: Components (module map)

| Layer | Modules | Responsibility |
|---|---|---|
| sdk | sdk, series | Single business entry: run_peer/replay/verify_log; sub-game series + role alternation |
| domain (physics, PURE — parity-locked with twin) | board, rules, scoring, scent, belief, crypto, protocol, negotiation, state_machine, game_ids | Grid+barriers, captures/survival, score table, pheromone emission+decay, Bayesian belief, canonical-JSON SHA-256 commit/verify, message dataclasses, config identity+locks, legal-transition FSM, artifact naming |
| peer | runtime, handshake, turn_taker, turn_receiver, sealing, deadline, watchdog, audit | Orchestrator (coordinates, never executes), step-0 declaration, my-turn/opponent-turn flows, record sealing, timeouts, freeze recovery, end-of-game mutual audit |
| strategy (role-specific) | brain_base, police_brain, hints, talk_providers | BrainBase seam ([strategy] override), pursuit + barrier tactics, truth/lie hint policy (≤15 words), provider selection |
| infra | mcp_server, mcp_client, llm_provider, email_sender | FastMCP tools→thread-safe queues; outbound transport w/ retry-until-up; 5 providers behind gatekeeper; gmail.send-only reporting |
| shared | config, gatekeeper, rate_limiter, version, sysinfo | JSON-overrides-TOML loader + version gate, single doorway for ALL external calls, token bucket+quota+DOS lock, versions, hardware spec |
| report | schemas, emit, result_report | The four game artifacts; result agreement handshake |
| gui | window, board_view, live_view, replay, replay_data, replay_controls | Belief heatmap + YOUR TURN/LOCKED banner; replay with per-step SHA-256 re-verification |

## 4. Key flows

1. **Negotiation**: exchange config SHA-256 → byte-identity check → lock scent
   model + intra-turn commit order → step-0 sealed declarations (hardware,
   commit hash, game count).
2. **Turn**: WAITING_FOR_OPPONENT → COMPUTING_MOVE → COMMITTING →
   AWAITING_REVEAL → VERIFYING → (loop) | TECHNICAL_LOSS (terminal). Deadline on
   every await; watchdog heartbeat around the loop.
3. **Audit**: reveal all nonces → recompute every sealed record → verdict →
   agree result → emit 4 artifacts → email report.

## 5. ADR index

Numbered records in `docs/adr/`. ADRs document all decisions AND every
book/guidelines contradiction with rationale (rulebook front-matter rule).

## 6. Deployment

Dev: two localhost processes (8802 police / 8801 thief). League: Cloudflare
tunnel (quick tunnel for ad-hoc, named tunnel for stable URL) exposing the
FastMCP endpoint; free ngrok explicitly rejected (proven unreliable — conn-rate
cap + idle drops). Bearer-token protection; 401 for unauthenticated probes.

## 7. Concurrency model

I/O-bound → **threading**, not multiprocessing: the MCP server runs in a daemon
thread and hands messages to the game loop through `queue.Queue` (thread-safe,
no shared mutable state); LLM/email calls run under the gatekeeper's
concurrency cap. No locks beyond queue semantics — single-writer game state.

## 8. Risks

Canonicalization asymmetry (→ golden vectors, pinned field set), twin physics
drift (→ parity script + paired commits), turn deadlock (→ FSM + deadlines +
watchdog), tunnel drops (→ retry-until-up, warm-up games), Gmail 429/suspension
(→ token bucket + quota + backoff), secret leakage (→ gitignore-first +
gitleaks CI).
