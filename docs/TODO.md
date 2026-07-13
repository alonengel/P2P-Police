# TODO — P2P-Police

Legend: `[ ]` pending · `[~]` in progress · `[x]` done.
Every stage ends with: spec-auditor pass + code-review pass + TODO update commit.
Definition of done per stage = the binary milestone from PRD.md §7.

## Phase 0 — Bootstrap
- [x] Repo init: LICENSE (MIT + attribution), .gitignore (secrets first), README stub
- [x] uv scaffold: pyproject (ruff, pytest, coverage 85 branch), .python-version 3.13
- [x] shared/version.py (CODE_VERSION 1.00, config-version gate) + tests
- [x] Thin CLI with --version + tests
- [x] config/: game.json (Appendix VI values), game.toml (identity), rate_limits.json, logging_config.json, config/games/
- [x] Required dirs: data/ results/ assets/ notebooks/
- [x] CI (gitleaks, line cap, ruff, coverage, smoke) + pre-commit + gate scripts
- [x] Docs skeletons: PRD, PLAN, TODO, PROMPTS, ADRs 0001-0002
- [x] Claude tooling: .claude/agents (code-reviewer, spec-auditor, guidelines-auditor, test-designer, physics-parity), hooks, CLAUDE.md
- [x] Pushed to origin continuously; CI green (verified via gh)

## Phase 1 — Base logic (PRD_01)
- [x] domain/board: grid, barriers, legality (orthogonal+STAY, no diagonals)
- [x] domain/rules: captures (landing/barrier-on-thief/blocked), survival ≥35, quota-excess rejection
- [x] domain/scoring: 20/5/5/10/tie 2/technical 0
- [x] domain/scent: 5×5 radial emission (0.9), decay 0.10 once per FULL turn
- [x] domain/state_machine: legal transitions only, TECHNICAL_LOSS terminal
- [x] domain/engine: cop-first rounds, barrier-forgoes-move, mid-round captures
- [x] Golden physics vectors (tests/vectors/physics_vectors.json — byte-identical with twin)
- [x] Self-play driver test: full local game crash-free (20 seeds, both endings)
- [x] Spec-auditor pass on Phase 1 deliverables

## Phase 2 — MCP infra (PRD_02)
- [x] infra/mcp_server: 4 tools → thread-safe queues; port-busy fail-fast
- [x] infra/mcp_client: retry-until-opponent-up transport (+shutdown-race hardening)
- [x] shared/config: JSON-overrides-TOML, version gate wired to startup
- [x] domain/negotiation: byte-identity + config_sha256 + commit-order pinning + Appendix-VI limit enforcement
- [x] peer/deadline: expiry on every awaited request
- [x] domain/protocol + peer/runtime + sdk + cli peer subcommand
- [x] Milestone: geometric game vs P2P-Thief process over localhost — MILESTONE OK (results/cross_match_prd02_2026-07-13.json)
- [x] Spec-audit of Phase 2 done — fixes applied: move_set + technical_loss + league constants added to FIXED_TERMS; in-flight MCP calls bounded by response_timeout_sec (rule 6); COMMIT_ORDER/SHUTDOWN_GRACE noted for config promotion
- [x] (done in Phase 6) GamePhaseMachine wired into the runtime; failures route to TECHNICAL_LOSS

## Phase 3 — Blind strategy (PRD_03)
- [x] strategy/brain_base (BrainBase seam, [strategy] toml override, loud bad-spec failure)
- [x] strategy/police_brain: BFS pursuit + surgical trap barriers (+ThiefForArena sparring partner)
- [x] Self-play arena; MILESTONE: pursuit brain captures >=20/25 random thieves

## Phase 4 — Language + scent (PRD_04)
- [x] domain/belief: diffuse x scent x hint posterior; (1-rho) lie detection (book p.30 example encoded)
- [x] strategy/hints: template provider (0 tokens), truth/lie claims + intent flag, word cap on every path
- [x] infra/llm_provider registry (ollama/claude_api/claude_cli/openrouter) + TalkChain (every_n_steps, unconditional template fallback, TokenMeter)
- [x] Hints+belief wired into the runtime (hint rides the turn message; diffuse->scent->hint belief update on receive)
- [x] Belief-driven brains + blind MILESTONE passed; live blind cross-match: thief survived 35 turns (vs capture-in-13 under full info) - uncertainty works as designed
- [x] shared/gatekeeper + rate_limiter (token bucket, daily quota threshold, DOS circuit breaker)

## Phase 5 — Tunneling (PRD_05)
- [x] Persistent single-session McpTransport (dedicated loop thread, session rebuild on failure)
- [x] MILESTONE: full blind game over https://mcp.alon.website (named tunnel) - 35 turns, digests identical (results/public_tunnel_prd05_2026-07-13.json)
- [ ] DEPLOYMENT.md: named-tunnel runbook (config.yml ingress -> my_port), quick-tunnel fallback, bearer-token protection
- [x] peer/watchdog (rule 7) + persistent-session reconnect hardening
- [x] Milestone: full game over public URL (PRD-05 evidence)

## Phase 6 — Crypto (PRD_06)
- [x] domain/crypto: canonical JSON, pinned 7-field sealed record, SHA-256 commit/verify, secrets nonce, binary audit
- [x] peer/sealing: SealedExchange - 4-phase commit/ack/reveal/audit per half-turn
- [x] Step-0 data in the declaration artifact (hardware spec via sysinfo, git commit hash, counted-games; sealed exchange next to negotiation TBD for league)
- [x] peer/audit: nonces ride the end audit message; every rival record recomputed -> Verified OK/TAMPERED in the report
- [x] Tamper-injection tests -> TAMPERED (payload rewrite, wrong nonce, count mismatch)
- [x] FSM wired into the runtime (COMPUTING->COMMITTING->AWAITING_REVEAL->VERIFYING; failures -> terminal TECHNICAL_LOSS)
- [x] MILESTONE: cross-repo match fully sealed - 35 steps, audit Verified OK both sides

## Phase 7 — Reporting + GUI (PRD_07)
- [x] report/artifacts: all four Table-20 artifacts emitted per game (shared game_uid, game_id-derived names; config archived to config/games/ per rules 3-4)
- [x] infra/email_sender: Gmail REST over httpx, send-only scope, gatekeeper 'email' service, 429 backoff; REAL send verified (4 artifacts attached); scripts/gmail_auth.py mints send-only tokens
- [x] gui/live_view: belief heatmap + YOUR TURN/LOCKED/GAME OVER banner, snapshots via Perception (LOCAL TRUTH ONLY, rules 8-9); live screenshot captured from a real cross-repo game (assets/live_belief_map.png)
- [x] verify-log CLI: headless replay verification engine on saved logs (real-log Verified OK; tampered-log TAMPERED proven)
- [x] gui/replay viewer: verdict banner (Verified OK/TAMPERED), step-through board, hints shown; DPI-aware --screenshot; submission PNG captured (assets/replay_verified_ok.png)
- [~] Screenshots: both mandatory images captured (live belief map + replay Verified OK); remaining per-state shots (LOCKED banner, TAMPERED demo) with docs/UI.md in Phase 8

## Phase 8 — Submission
- [x] README: user manual + academic report complete (all six mandatory components + ISO 25010 + course anchors; screenshots embedded)
- [x] docs/UI.md
- [ ] notebooks/analysis.ipynb (sensitivity: decay/board/lookahead) + COST.md
- [x] docs/LEAGUE_RUNBOOK.md + docs/DEPLOYMENT.md (tunnel URLs per agent, token-expiry gotcha, per-game commit-ID email duty)
- [ ] Optional RL experiment + learning curves
- [x] scripts/check_submission.py PASS; [ ] v1.0-submission tag AFTER league games
- [ ] Moodle: form PDF (unaltered fields), per-member submission, team code anrbj666

## Phase 8 status (2026-07-13)
- [x] Series support: --sub-game override + series-result aggregator (per-group totals, sub-games won, tie at tie_score); 2-sub-game local series proven end-to-end
- [x] notebooks/analysis.ipynb + docs/COST.md (see Phase 8 status)
- [ ] docs/UI.md (Nielsen 10, per-state screenshots incl. TAMPERED demo)
- [ ] scripts/check_submission.py + final guidelines-auditor sweep
- [ ] v1.0-submission annotated tags (AFTER the real league games)
- [ ] REAL league games: >=2 counted vs different teams (LEAGUE_RUNBOOK.md)

## Final tri-audit fixes (2026-07-13, full PDF re-validation)
- [x] BLOCKER: technical loss now still emits artifacts + email (rules 32/35)
- [x] BLOCKER: TAMPERED/failed audit voids the game -> technical_loss score (rule 19)
- [x] MAJOR: opponent nonces persisted into the log; verify-log + replay verify BOTH halves (rules 20/36)
- [x] MAJOR: counted_games_played from config (rules 37-38) - update per counted game
- [x] Gatekeeper queue-not-reject + concurrency semaphore (guidelines 5.1/5.3); ADR-0003 scopes the peer channel out
- [x] PLAN module map synced to the shipped tree
- [ ] League day: share private repos with lecturer (rmisegal) OR make public; flip [email] mode=send; update counted_games_played each game
