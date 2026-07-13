# REQUIREMENTS MATRIX — rulebook traceability (Appendix ה rules 1-55 + App ו)

One row per mandatory rule: where it lives, what proves it. Status legend:
IMPL (code+tests) · OPER (human league-day duty, runbook-documented) · N/A.
(Format adopted from Renat Karimov's scaffold; evidence re-verified against
this repo by the pre-league MUST-coverage audit.)

| Rule | Requirement (short) | Module / evidence | Tests / proof | Status |
|---|---|---|---|---|
| 1 | Two separate processes | twin repos; sdk MY_ROLE; ports 8801/8802 | cross-match runs | IMPL |
| 2 | No shared memory/live-state | duplicated domain/ (ADR-0001); MCP-only channel | parity script | IMPL |
| 3 | Orchestrator single entry | sdk/sdk.py facade | test_sdk_* | IMPL |
| 4-5 | State machine, illegal transitions rejected | domain/state_machine.py; wired in peer/runtime.py | test_state_machine | IMPL |
| 6 | Deadline on every await | peer/deadline.py; in-flight timeouts in mcp_client | test_deadline; integration | IMPL |
| 7 | Watchdog | peer/watchdog.py (+NullWatchdog); wired in sdk | test_watchdog | IMPL |
| 8-9 | Live UI local truth only | peer/perception.py gate; gui/live_view.py | test_sealing_perception | IMPL |
| 10 | Public tunnel | Cloudflare named tunnel; results/public_bidirectional_e2e | live E2E evidence | IMPL+OPER |
| 11 | Config byte-identity + crypto lock | domain/negotiation.py config_sha256 | test_negotiation | IMPL |
| 12 | Fixed exact / minimums upward | negotiation FIXED/MINIMUM maps + game.schema.json | test_negotiation, test_game_schema | IMPL |
| 13-14 | Orthogonal only, no diagonals | domain/primitives.Move; board.apply_move | test_primitives, test_board | IMPL |
| 15-16 | Barriers declared, truthful | sealed barrier actions in log | test_rules, replay reconstruction | IMPL |
| 17 | SHA-256 commit-reveal | domain/crypto.py; peer/sealing.py | test_crypto, test_sealing | IMPL |
| 18 | Nonce secret until audit | sealing (reveal omits nonce+verdict) | test_sealing (secrecy asserts) | IMPL |
| 19 | Hash mismatch = technical loss | crypto.audit_records; sdk voids on TAMPERED | tamper tests | IMPL |
| 20 | Replay + verification | gui/replay.py; verify-log CLI; both halves verified | live TAMPERED demo | IMPL |
| 21-22 | Truthful capture, no false claims | replicated-engine capture (claim impossible to fake) | test_engine capture paths | IMPL |
| 23 | Scent model locked pre-game | scent_model_sha256 in agreement; scent_model_spec() | test_negotiation | IMPL |
| 24 | Hardware declaration sealed | hardware_spec sha in agreement; declaration artifact | test_artifacts | IMPL |
| 25 | LLM never decides moves | brains pure Python; TalkChain text-only | test_brains; SECURITY.md | IMPL |
| 26-27 | Free language, no numeric protocol | strategy/hints.py prose; hints in reveals | test_hints | IMPL |
| 28-29 | Token bucket + DOS for Gmail | shared/rate_limiter.py triad + queue | test_gatekeeper | IMPL |
| 30 | Send-only Gmail scope | email_sender SEND_SCOPE; gmail_auth.py mints send-only | live send E2E | IMPL |
| 31 | Min games vs different teams | LEAGUE_RUNBOOK.md | league day | OPER |
| 32 | Automatic Gmail report | sdk reporting funnel (even on ANY failure) | live email E2E (msg id) | IMPL |
| 33-34 | Valid JSON report, never plaintext | report/artifacts.py; JSON attachments | test_artifacts | IMPL |
| 35-36 | Both sides report; mutual audit | audit exchange in runtime; we always send | cross-match audit Verified OK | IMPL+OPER |
| 37-38 | Truthful game count | counted_games_played from config into declaration | test_artifacts | IMPL+OPER |
| 39-40 | No secrets; gitignore | .gitignore-first; gitleaks CI; check_submission gate | git ls-files scan | IMPL |
| 41 | Annotated submission tag | after league games | git tag -a v1.0-submission | OPER |
| 42 | Academic README | README.md Part II (all components) | guidelines audit | IMPL |
| 43-44 | Form PDF; per-member Moodle | LEAGUE_RUNBOOK.md | submission day | OPER |
| 45 | 8-char team code | anrbj666 in game.toml | config | IMPL |
| 46-47 | Barrier-capture; trapped-capture | domain/rules.py + engine mid-round checks | test_rules, test_engine | IMPL |
| 48 | Score every scenario | domain/scoring.py from signed config | test_scoring | IMPL |
| 49 | Two repos + cross-links | READMEs; links in all artifacts | check_submission | IMPL |
| 50 | README/config/PRD/PLAN/TODO in repo | docs/ complete incl. PRD_01..07 | check_submission | IMPL |
| 51 | Reports to lecturer alias | game.toml recipient | live send path | IMPL+OPER |
| 52 | One counted game per rival | sdk/series.py; runbook counting rules | test_series | IMPL+OPER |
| 53 | Commit ID per game | declaration github_commit; manual email duty | runbook step 1 | IMPL+OPER |
| 54 | Token totals reported | TokenMeter -> result tokens_total | test_artifacts | IMPL |
| 55 | Code-quality self-rating only | README ISO-25010 section | submission form | IMPL+OPER |
| ו§2.1-2.5 | Lock values; per-game config names; archive; commit email | negotiation + game_ids + config/games/ | test_artifacts; runbook | IMPL+OPER |

Completion rule (adopted from Renat): a row is complete only when
implementation + tests + evidence all exist. Full file:line evidence for
every row lives in the pre-league MUST-coverage audit (2026-07-13).
