# PRD — P2P-Police (Cop agent)

## 1. Overview

Autonomous **Police (Cop)** agent for the distributed Cops-and-Robbers final project:
a pursuit game on a bounded grid (7×7 default) played **peer-to-peer over FastMCP**
with no central server and no judge. Each peer holds only local truth; integrity is
guaranteed by a SHA-256 commit-reveal protocol, a mutual end-of-game audit, and a
cryptographically locked shared configuration. The user problem: run complete,
verifiable, league-countable games against rival teams' agents while maximizing the
cop's score under the mandatory scoring table.

Normative sources (in priority order):
1. Course rulebook `police_thief_p2p.pdf` — Appendix ו is the single source of truth
   for every quantitative value; Appendix ה lists the 55 mandatory rules.
2. Software submission guidelines V3 (grading standard).
3. Official demo repo (learning reference only, attribution in LICENSE).

## 1b. Grade-aligned priorities (effort allocation)

Where the effort deliberately went, in order — mirroring how the rubric
weighs it:

1. **Interop-reliability floor** — a game that cannot start, audit, or
   settle scores zero regardless of brains: byte-form alignment, the
   conformance suite, persistent transport, deadline/watchdog discipline.
2. **Integrity as enforcement, not prose** — commit-reveal, the
   physics-recomputing verifier, and the rule-guard tests that turn
   disqualification-class rules into CI invariants.
3. **Strategy depth with evidence** — hand-tuned league defaults backed by
   the full RL campaign (positive AND negative results, all gated).
4. **League operations** — runbook, tunneling hardening, reporting funnel:
   the human-error surface minimized before it can cost points.
5. **Evidence layer** — every substantive claim regenerates from a
   committed script into a committed artifact (docs/evidence/).

Audience: the course grader first (traceability to the 55 rules +
guidelines), rival teams second (interop specs they can build against),
future-us third (runbooks that survive a stressful league day).

## 2. Goals & KPIs

| Goal | KPI / acceptance criterion |
|---|---|
| Legal play | 100% of moves legal (orthogonal/STAY, barrier quota ≤14); zero technical losses caused by us |
| Integrity | Every game's audit passes; replay shows "Verified OK"; zero TAMPERED verdicts |
| League participation | ≥2 counted games vs different teams (passing condition); reports sent by us for every game |
| Competitive strength | Cop captures the reference (random/heuristic) thief in self-play arena at a target rate ≥80% |
| Engineering quality | ruff 0 violations; coverage ≥85%; all files ≤150 code lines; CI green |
| Cost | Full series playable at 0 LLM tokens (template provider); token meter sealed and reported |

## 3. Functional requirements

- FR1 Game engine: board, orthogonal+STAY movement, barrier placement (cop forgoes
  move; quota enforced; truthful public declaration), captures (landing+claim,
  barrier-on-thief, fully-blocked), survival threshold, scoring table.
- FR2 Pheromone physics: 5×5 radial emission (center 0.9), decay ρ=0.10 once per
  full turn; cryptographically locked before a series.
- FR3 P2P communication: own FastMCP server (port 8802) + client to opponent URL;
  tools: negotiate, receive_turn, submit_audit, receive_control.
- FR4 Commit-reveal: 4 phases per step (Commit→Acknowledge→Reveal→Audit); canonical
  JSON sealing; nonce secret until end-of-game audit.
- FR5 Strategy: Bayesian belief map (scent + hint lie-detection) feeding a pursuit
  brain with lookahead and barrier tactics; moves ALWAYS algorithmic.
- FR6 Verbal layer: free-language hints (≤15 words) with truth/lie intent flag;
  providers template/ollama/claude_api/claude_cli/openrouter behind the gatekeeper.
- FR7 Reliability: orchestrator + strict state machine, deadline tracker on every
  awaited request, watchdog with state persistence.
- FR8 Reporting: four JSON artifacts per game (declaration/config/log/result),
  result agreement with opponent, automatic Gmail send (gmail.send scope only).
- FR9 Observability: live GUI (local truth only — belief heatmap + turn banner) and
  a replay viewer that re-verifies every record (Verified OK / TAMPERED).

## 4. Non-functional requirements

SDK-first architecture (single business entry), API gatekeeper for ALL external
calls, config-driven (zero hardcoded values), versioned code+configs, TDD with
≥85% branch coverage, ≤150 code lines/file, thread-safe queues for cross-thread
handoff, DOS/quota protection on Gmail, no secrets in the repository ever.

## 5. User stories

- As a league operator, I start the peer with one command and it negotiates,
  plays, audits and reports without manual intervention.
- As a grader, I load any archived game log in the replay viewer and see a
  cryptographic Verified-OK verdict per step.
- As the team, we watch the live belief heatmap to understand the cop's reasoning
  without ever seeing the opponent's true state.

## 6. Constraints & assumptions

- Two separate repos (this + P2P-Thief), duplicated physics, no shared live state.
- Windows dev machines; Python ≥3.13; uv-only; Cloudflare tunnel for public play.
- LLM never decides moves (rulebook default; no exception negotiated).
- Out of scope: any UI showing the objective board during live play (forbidden).

## 7. Milestone timeline (per-mechanism PRDs)

| Stage | PRD file | Milestone gate |
|---|---|---|
| 1 | PRD_01_base_logic.md | Full local game crash-free; quota-excess barrier rejected |
| 2 | PRD_02_mcp_infra.md | Geometric game over localhost vs the twin repo |
| 3 | PRD_03_blind_strategy.md | Cop beats random thief on full information |
| 4 | PRD_04_language_scent.md | Belief map demonstrably drives moves; lie detection works |
| 5 | PRD_05_tunneling.md | Full game over a public URL |
| 6 | PRD_06_crypto.md | Audit passes; tamper injection yields TAMPERED |
| 7 | PRD_07_reporting_gui.md | 4 artifacts + email + Verified-OK screenshots |
| 8 | (submission) | v1.0-submission tag; all checklists PASS |
