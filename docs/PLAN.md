# PLAN — Architecture & technical planning (P2P-Police)

## 1. C4: Context

Two autonomous agents — this Cop and a rival Thief — play over the public
internet. External systems: the opponent's FastMCP endpoint (the ONLY thing we
know about them), Gmail API (automatic league reports), GitHub (submission +
per-game commit IDs), a Cloudflare tunnel (public exposure), optional LLM
providers (verbal layer only). There is **no game server**: state lives locally
in each peer and truth is established cryptographically.

## 1b. C4 diagrams

```mermaid
C4Context
  title System context - Police peer (one of two mirrored twins)
  Person(operator, "Team operator", "Runs games, league duties")
  System(peer, "Police peer", "FastMCP server + client, replicated engine")
  System_Ext(opponent, "Thief / rival peer", "Only its MCP URL is known")
  System_Ext(gmail, "Gmail API", "send-only automatic reports")
  System_Ext(tunnel, "Cloudflare tunnel", "public exposure (rule 10)")
  Rel(operator, peer, "CLI / GUI")
  Rel(peer, opponent, "negotiate, turns, audit", "MCP over HTTPS")
  Rel(peer, gmail, "end-of-game report", "gatekeeper-gated")
  Rel(peer, tunnel, "exposed via")
```

```mermaid
flowchart LR
  subgraph shells [Shells]
    CLI --> SDK
    GUI --> SDK
  end
  SDK[sdk/ single entry] --> RT[peer/runtime orchestrator]
  RT --> DOM[domain/ physics+crypto - parity-locked]
  RT --> PER[peer/perception belief]
  RT --> BR[strategy/ brain seam]
  RT --> SEAL[peer/sealing commit-reveal]
  SEAL --> MCPC[infra/mcp_client persistent session]
  MCPS[infra/mcp_server 4 tools] --> RT
  SDK --> REP[report/ artifacts+email]
  REP --> GK[shared/gatekeeper triad]
```

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
| peer | runtime, perception, sealing, deadline, watchdog | Orchestrator turn loop + FSM, local-truth belief/snapshots, 4-phase sealed exchange + mutual audit, timeouts, freeze recovery |
| strategy (role-specific) | brain_base, police_brain, hints, talk_providers | BrainBase seam ([strategy] override), pursuit + barrier tactics, truth/lie hint policy (≤15 words), provider selection |
| infra | mcp_server, mcp_client, llm_provider, email_sender | FastMCP tools→thread-safe queues; outbound transport w/ retry-until-up; 5 providers behind gatekeeper; gmail.send-only reporting |
| shared | config, gatekeeper, rate_limiter, version, sysinfo | JSON-overrides-TOML loader + version gate, single doorway for ALL external calls, token bucket+quota+DOS lock, versions, hardware spec |
| report | artifacts | The four Table-20 game artifacts (declaration/config/log/result) |
| gui | live_view, replay | Belief heatmap + YOUR TURN/LOCKED/GAME OVER banner; replay witness with full-log SHA-256 re-verification |

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

## 9. Milestone evidence

- **PRD-02 (2026-07-13):** first cross-repo game — `p2p-police peer` (port 8802)
  vs `p2p-thief peer` (port 8801), two processes from the two repos over
  localhost FastMCP. Config sha verified, commit order agreed, 20 full turns,
  outcome `capture` on BOTH sides, end-state digests identical
  (`results/cross_match_prd02_2026-07-13.json`). Runner:
  workspace `run_cross_match.ps1`.
- **PRD-05 (2026-07-13):** full BLIND game over the PUBLIC INTERNET - police
  connected to the thief through `https://mcp.alon.website/mcp` (Cloudflare
  NAMED tunnel -> localhost:8801). 35 turns, survival, identical digests
  (`results/public_tunnel_prd05_2026-07-13.json`). Required fix en route:
  ONE persistent MCP session per transport - per-call sessions are terminated
  by the proxy (ex6's connection-reuse lesson, re-learned live).
