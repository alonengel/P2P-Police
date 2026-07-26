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
- [x] Screenshots: both mandatory images captured (live belief map + replay Verified OK); per-state shots (YOUR TURN, LOCKED, TAMPERED demo) captured with docs/UI.md (assets/live_your_turn.png, assets/live_locked.png, assets/replay_tampered_demo.png; reproducible via scripts/capture_ui_states.py)

## Phase 8 — Submission
- [x] README: user manual + academic report complete (all six mandatory components + ISO 25010 + course anchors; screenshots embedded)
- [x] docs/UI.md
- [x] docs/LEAGUE_RUNBOOK.md + docs/DEPLOYMENT.md (tunnel URLs per agent, token-expiry gotcha, per-game commit-ID email duty)
- [x] RL experiment: linear-FA Q-learning + learning curves (1.00 vs random; 0.00 vs perfect evader - theory-confirming negative result in README)
- [x] scripts/check_submission.py PASS; [ ] v1.0-submission tag AFTER league games
- [ ] Moodle: form PDF (unaltered fields), per-member submission, team code anrbj666

## Phase 8 status (2026-07-13)
- [x] Series support: --sub-game override + series-result aggregator (per-group totals, sub-games won, tie at tie_score); 2-sub-game local series proven end-to-end
- [x] notebooks/analysis.ipynb + docs/COST.md (see Phase 8 status)
- [ ] v1.0-submission annotated tags (AFTER the real league games)
- [ ] REAL league games: >=2 counted vs different teams (LEAGUE_RUNBOOK.md)

## Final tri-audit fixes (2026-07-13, full PDF re-validation)
- [x] BLOCKER: technical loss now still emits artifacts + email (rules 32/35)
- [x] BLOCKER: TAMPERED/failed audit voids the game -> technical_loss score (rule 19)
- [x] MAJOR: opponent nonces persisted into the log; verify-log + replay verify BOTH halves (rules 20/36)
- [x] MAJOR: counted_games_played from config (rules 37-38) - update per counted game
- [x] Gatekeeper queue-not-reject + concurrency semaphore (guidelines 5.1/5.3); ADR-0003 scopes the peer channel out
- [x] PLAN module map synced to the shipped tree (re-synced 2026-07-21: sdk/domain/peer/strategy/shared/report rows now cover every shipped module)
- [ ] League day: share private repos with lecturer (rmisegal) OR make public; flip [email] mode=send; update counted_games_played each game

## Hardening & measured strategy (2026-07-21)
- [x] Chaos-drill suite (D1-D4 + LIVE tunnel kill/heal) with committed JSONL evidence; HTTP 530 retry fix proven over the real public edge (docs/evidence/chaos-drills.md)
- [x] Config-range fuzzer: 40/40 sampled Appendix-VI-legal configs pass every invariant (docs/evidence/config-fuzz.md)
- [x] Crash-resume: per-half-turn snapshots + --resume path; kill-and-resume drill recovers in 45 ms, mutual audits Verified OK (docs/evidence/crash-resume.md)
- [x] Self-mirror deception policy: lies 18.0 -> 2.0 per game vs the honesty coin, thief tracking error 2.36 -> 1.43 — ON (docs/evidence/deception.md)
- [x] Keep-gated endgame solver + info-gain term: honest negative results (0 solver fires in 160 games; capture rate unmoved at every weight) — both ship OFF (docs/evidence/cop-strength.md)
- [x] Third-party pair verifier (one game, two logs, one verdict) + committed-artifact guard over every committed log pair (report/pair_verify.py)
- [x] Buffer-ahead sealing fix: a split commit+reveal pair no longer reads as desync (peer/sealing.py)

## League-grade hidden wire & cross-team rehearsal (2026-07-22..25)
- [x] Reference-v3 hidden client behind the negotiated wire_shape lock (src wire/ + sdk/hidden.py; ADR-0007 addendum + ADR-0008; mechanism PRD: docs/PRD_09_hidden_wire.md)
- [x] Registered flat-terms handshake + role/sub-game pairing declarations + dedup-safe agreement re-push + typed bystander tolerance (PairingRefusalError)
- [x] Claim-mediated capture + foreign-fair audit tiers (alignment by commit; Board-physics reconstruction; digest not-comparable, never false)
- [x] Reference-conformant series result + rule-35 settlement guard; league-day runner with email preflight, auto-close and the doubly-armed lecturer-address interlock
- [x] REAL cross-team play: warm-up games audits Verified OK on both sides + full 6-sub-game counted-format rehearsal (47-47 structural tie); mutually discarded evidence relocated to docs/evidence/discarded-series/ (outside the aggregation path, still committed history)
- [x] Documentation-fidelity pass (2026-07-25): README Part II (dual wire, cross-team verification subsection, hidden replay witness assets/replay_hidden_verified.png, counts 619 tests / 93.16%), PRD_09, matrix PRD_01..09, this ledger

## Perception counter-build: reach-decoded evidence stack (2026-07-26)
- [x] domain/evidence.py (parity-locked, paired commit): every trail reading decodes to a REACH ball via kernel-rung hypotheses (ring rungs accepted fresh-only); observe_scent spreads evidence over the ball, so stale plateaus thin out while fresh readings spike — the posterior follows a mover instead of locking onto a camp's afterglow (pinned: tests/unit/test_domain/test_evidence.py)
- [x] observe_barrier: a declared placement pins the placer to the wall's passable orthogonal neighbors (law of barriers) — wired through Perception on BOTH wires, redelivery-safe (tests/unit/test_peer/test_barrier_perception.py)
- [x] observe_region + gazetteer parsing tier: place-name talk (config/gazetteer.json, private per-peer, fractional bands for any grid) lands as region observations under the same profiler weights and scent lie check; strictly inbound — rule 27 untouched on the wire
- [x] AgedBeliefTrapCop arena benchmark: belief-led early pounce + gain-gated surgical walls, blind by construction (rule-25 decision-module guard extended)
- [x] Gates: 646 tests green, branch coverage 93.27%, ruff 0, 150-line caps OK, physics parity green both directions

## DoD-observed ledger (measured evidence per completed phase)

Every "done" above is backed by a regenerable artifact; the deep narratives
live in `docs/evidence/`:

| Claim | Measured | Evidence |
|---|---|---|
| Public P2P games work end-to-end | 35-turn sealed games over the tunnel, identical digests, audits Verified OK both directions | `docs/evidence/public-games.md`, `results/public_bidirectional_e2e_*.json` |
| Reference interop is proven, not assumed | 13/13 conformance tests over the league kit's vectors; counterparty package re-verified 35/35 | `docs/evidence/interop-alignment.md`, `tests/unit/test_reference_conformance.py` |
| Disqualification rules are enforced | 5 rule-guard invariants in CI + tamper drills read TAMPERED | `docs/evidence/rule-guards.md`, `tests/unit/test_rule_guards.py` |
| Strategy claims are measured | full RL campaign incl. four gated promotions (all held) and the wire-shape balance tables | `docs/evidence/rl-campaign.md`, `results/experiments/*.json` |
| Faults are survived, not hoped away (2026-07-21) | chaos drills D1-D4 + LIVE tunnel kill/heal all PASS: dedup, bounded waits, clean technical-loss classification, healed public game | `docs/evidence/chaos-drills.md`, `docs/evidence/drills/*.jsonl` |
| Any legal config plays clean (2026-07-21) | fuzzer: 40/40 sampled legal configs complete with matching digests + Verified OK audits | `docs/evidence/config-fuzz.md`, `results/experiments/config_fuzz.json` |
| A killed game recovers (2026-07-21) | resume drill: snapshot restored in 45 ms, 6 half-turns replayed, mutual audits Verified OK | `docs/evidence/crash-resume.md`, `docs/evidence/drills/resume_recovery_2026-07-21.jsonl` |
| Lying is a policy, not a coin (2026-07-21) | 2.0 lies/game vs the coin's 18.0; thief tracking error 2.36 -> 1.43 | `docs/evidence/deception.md`, `results/experiments/deception_policy.json` |
| Negative results ship honestly (2026-07-21) | endgame solver 0 fires in 160 games; info-gain capture rate unmoved — both OFF by keep-gate | `docs/evidence/cop-strength.md`, `results/experiments/cop_strength.json` |
| The hidden wire is league-grade end-to-end (2026-07-22) | reference-v3 phase 2: sdk wire-shape routing, hidden artifacts verify (verify-log + pair verifier, both directions), hidden kill-and-resume drill restored in 0.062 s, LIVE cross-repo g03 game: 35-turn survival, identical digests, pair-verify Verified OK | `docs/adr/0008-hidden-audit-reconstruction.md`, `docs/evidence/drills/hidden_resume_recovery_2026-07-22.jsonl`, `results/log_anrbj666-vs-anrbj666_g03.json` |
| The counted format is rehearsed against a real rival (2026-07-24) | warm-up games: full 35 turns, audits Verified OK on BOTH sides, digest_match honestly null across per-team constructions; then all six sub-games of the counted format, roles alternating, every audit Verified OK, the predicted 47-47 structural tie + the ONE series email; the discarded series is committed history OUTSIDE the aggregation path | `docs/evidence/discarded-series/`, `config/games/config_anrbj666-vs-imreeyal_g*.json` |
| One game, two logs, one third-party verdict (re-run 2026-07-25) | `verify_pair` on the committed twin logs: g01 (bookletter) and g03 (hidden) both `overall: Verified OK`; per-side `verify-log` on the rival-game logs: Verified OK in both repos; the hidden replay witness PNG regenerated from the committed CLI | `scripts/verify_pair.py`, `results/log_anrbj666-vs-anrbj666_g0*.json`, `assets/replay_hidden_verified.png` |
| The belief tracks movers, not memories (2026-07-26) | reach-decoded evidence: posterior peak 3 cells behind an 8-step escapee and clear of the abandoned camp (raw-intensity weighting: 6 behind, still camp-anchored); a declared wall localizes its placer (>0.6 origin mass); landmark talk parses to regions | `tests/unit/test_domain/test_evidence.py`, `tests/unit/test_peer/test_barrier_perception.py`, `src/p2p_police/domain/evidence.py` |

## Dwell-plateau localization and the re-opened keep-gates (2026-07-26)
- [x] domain/evidence.py `plateau_origin` + `BeliefMap.observe_plateau` (parity-locked, paired commit): a dweller saturates 21 of the 25 kernel offsets (fixed point delta/rho vs the clamp) and stamps its own window, so fitting that SHAPE back inverts to its cell where per-cell reach-decoding ties flat. Localization 7% -> 89% exact, 2.42 -> 0.11 cells (mechanism PRD: docs/PRD_10_plateau_localization.md)
- [x] Abstention gates (min cells / min fit / margin) + golden vectors covering the three REFUSALS as well as the pin — parity hashing catches twin drift, vectors catch a change made identically in both
- [x] Thief `lethal_gate`: a landing any believed hunter can END next turn ranks below every landing none can; closes the herded-corner walk-in (survival 0.900 -> 1.000, 150 games)
- [x] Barrier gate lifted out of frozen constants into `[strategy.trap]` and swept (2/3/4/5 -> 3); the policy had been placing 0.00 walls/game, starved of information rather than badly designed
- [x] Keep-gates RE-MEASURED on the shipped Perception pipeline (the arena harnesses had been bypassing it): endgame solver and info-gain both re-opened and flipped ON as a PAIR (pool capture 0.625 -> 0.983); thief survival certificate re-opened (0 -> 120 fires, survival-neutral, kept for proof over coincidence); area-denial herding measured byte-identical to shipped and REJECTED
- [x] Live E2E on the reference wire, both sub-games: capture on turn 15 with three barriers spent, both sides Verified OK with matching end-state digests
- [ ] Team #2 outreach for the second counted series (passing condition; the only open item that is not code)
