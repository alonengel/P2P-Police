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
- [x] Push to origin (CI verification on GitHub pending gh auth)

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
- [ ] infra/mcp_server: 4 tools → thread-safe queues; port-busy fail-fast
- [ ] infra/mcp_client: retry-until-opponent-up transport
- [ ] shared/config: JSON-overrides-TOML, version gate wired to startup
- [ ] domain/negotiation: byte-identity + config_sha256 + commit-order pinning
- [ ] peer/deadline: expiry on every awaited request
- [ ] Milestone: geometric game vs P2P-Thief process over localhost

## Phase 3 — Blind strategy (PRD_03)
- [ ] strategy/brain_base (BrainBase seam, [strategy] toml override)
- [ ] strategy/police_brain: pursuit + barrier placement on full information
- [ ] Self-play arena harness; milestone: beats random thief

## Phase 4 — Language + scent (PRD_04)
- [ ] domain/belief: Bayesian update from scent + hints; (1-rho) lie detection
- [ ] strategy/hints: truth/lie intent policy, <=15-word enforcement
- [ ] strategy/talk_providers + infra/llm_provider (template/ollama/claude_api/claude_cli/openrouter) behind gatekeeper
- [ ] shared/gatekeeper + rate_limiter (token bucket, quota, DOS lock)

## Phase 5 — Tunneling (PRD_05)
- [ ] Cloudflare quick tunnel flow + named tunnel docs (DEPLOYMENT.md)
- [ ] peer/watchdog + reconnect hardening
- [ ] Milestone: full game over public URL

## Phase 6 — Crypto (PRD_06)
- [ ] domain/crypto: canonical JSON (pinned field set incl. hint/verdict/step/role/sub_game), SHA-256 commit/verify, secrets nonce
- [ ] peer/sealing + peer/handshake (step-0: hardware, commit hash, game count)
- [ ] peer/audit: full nonce reveal + recompute + verdict
- [ ] Tamper-injection test → TAMPERED

## Phase 7 — Reporting + GUI (PRD_07)
- [ ] report/schemas + emit: declaration/config/log/result (game_uid naming)
- [ ] report/result_report: agreement handshake; infra/email_sender (gmail.send only, real send)
- [ ] gui/live_view: belief heatmap + YOUR TURN/LOCKED banner (LOCAL TRUTH ONLY)
- [ ] gui/replay: per-step re-verification → Verified OK / TAMPERED
- [ ] Screenshots of every screen/state → assets/

## Phase 8 — Submission
- [ ] README: user manual + academic report (Dec-POMDP 8-tuple, FastMCP dilemmas, strategy, RL curves if used, screenshots, sibling link, ISO 25010 mapping, course-connection anchors L02/L04/L05/L08/L09/L11)
- [ ] docs/UI.md (Nielsen 10, per-state screenshots, workflow, accessibility)
- [ ] notebooks/analysis.ipynb (sensitivity: decay/board/lookahead) + COST.md
- [ ] docs/LEAGUE_RUNBOOK.md (manual league-day duties incl. commit-ID email per game)
- [ ] Optional RL experiment + learning curves
- [ ] scripts/check_submission.py PASS; v1.0-submission annotated tag pushed
- [ ] Moodle: form PDF (unaltered fields), per-member submission, team code anrbj666
