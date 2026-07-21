# PROMPTS — prompt-engineering log (submission guidelines §8.3)

Every significant prompt used to build this project, with context, goal, outcome,
and lessons. Newest entries last.

---

## 2026-07-13 — Session 1: requirements extraction & master plan

**Context.** Project kickoff. Inputs: the 160-page rulebook PDF, the 39-page
submission-guidelines PDF, the official demo repo, and our prior course work.

**Prompt pattern — parallel exhaustive extraction.** We fanned out reading
agents over page ranges of the rulebook with the instruction: *"Your report
must be EXHAUSTIVE — this project is graded against this book and nothing may
be missed. Distinguish MANDATORY (חובה/אסור) vs RECOMMENDED (מומלץ) vs
EXAMPLE-ONLY; note every square-bracketed parameter; report formulas, protocol
flows, state machines precisely, with page numbers."*
**Outcome.** Complete requirements dossier: 55 mandatory rules, the Appendix ו
parameter table with fixed/minimum/negotiable statuses, config architecture,
submission checklists.

**Prompt pattern — adversarial verification.** After drafting the plan, we ran
independent verifier agents per page range: *"Go SENTENCE BY SENTENCE. Report
ONLY (a) requirements missing from the plan; (b) requirements stated
incorrectly; (c) nuances that could cause disqualification."*
**Outcome / lesson.** The adversarial pass caught real errors a single reading
missed — e.g. rule 27 mistranslated ("library protocols" instead of the actual
ban on numeric-coordinate dialogue), the game-count declaration wrongly labeled
trust-based, the sealed commit record being richer than the 4 core fields, and
the missing intra-turn commit-order agreement. Lesson: **extract, then attack
the extraction with fresh agents; never trust one pass over a graded spec.**

**Prompt pattern — design under constraints.** A planner agent received the
dossier plus hard constraints (two repos, 150-line files, 85% coverage, uv-only,
many commits) and returned the module map, phase plan, and risk register that
seeded PLAN.md/TODO.md.

**Key clarifications asked of the humans (never assumed):** repo code-sharing
strategy, tunneling tool (ex6 evidence: free ngrok unreliable → Cloudflare),
LLM provider scope (all four modes + OpenRouter), team identity (anrbj666),
strategy ambition (strongest per role + optional RL).

---

## 2026-07-13 — Session 2: Phase 1 (base game logic), TDD in paired slices

**Context.** First code phase; everything under `domain/` is parity-locked with
the twin repo.

**Prompt pattern — spec-quoting tests.** Each test module opens by quoting the
rulebook rule it encodes (e.g. "rules 13-14", "rule 47") and test names state
the rule (`test_barrier_beyond_quota_is_rejected`,
`test_stay_does_not_rescue_a_surrounded_cell`). This keeps the suite readable
as a compliance checklist, not just a regression net.

**Prompt pattern — golden vectors as the twin contract.** Instead of trusting
two codebases to "look the same", we generated `physics_vectors.json` from the
implementation once (kernel, 0.9→0.81→0.729 decay series, corner clipping,
two-turn evolution) and copied it byte-identically to the sibling; both suites
assert exact equality. Lesson: **behavioral identity is a test artifact, not a
code-review promise.**

**Workflow lesson.** The pre-commit parity hook (correctly) blocked a commit
made before the sibling port — the paired-commit order is: port to sibling's
working tree FIRST, commit here, then commit sibling. Recorded in the
workspace rules.

**Audit.** A spec-auditor agent re-read the dossier sections (board, pheromones,
state machine) against every domain file before the phase was closed.

---

## 2026-07-13 — Session 2 (cont.): Phase 2 MCP infra + first cross-repo game

**Pattern — probe the installed API before writing against it.** One tiny
script confirmed fastmcp 3.4.4's run()/Client surface before mcp_server.py
was written; zero API-mismatch rework.

**Pattern — integration test as coverage strategy.** Instead of omitting the
transports from coverage (demo's approach), a slow-marker test drives a REAL
FastMCP server on an ephemeral port; both transport modules stay in the 85%
gate.

**Debugging lesson — shutdown races are protocol design.** First cross-repo
run: police exited immediately after receiving the thief's audit, killing its
server mid-HTTP-session; the thief's final send died with httpx.ReadError.
Fixes: classify read/write/closed errors as retryable, make the audit send
best-effort, add a shutdown grace period. Lesson: **the last message of a P2P
session needs the same engineering care as the first.**

---

## 2026-07-13 — Sessions 3-5: phases 3-8 (compressed log)

Patterns that repeated and paid off: (1) spec-quoting tests named after rules;
(2) port-to-sibling-BEFORE-commit (the parity hook blocks the wrong order);
(3) probe-the-API-first before writing infra; (4) field failures became
design notes the same hour (proxy session churn -> persistent sessions;
expired OAuth tokens -> runbook warning; DPI-skewed screenshots -> aware
mode). (5) The 150-line cap forced two genuinely better extractions
(Perception, SealedExchange). (6) A "SUBMISSION READY" claim was challenged
by the user - a fresh audit against the dossier found two unwired MUSTs
(watchdog rule 7, auto-email rule 32) and missing PRD files: **checklists
verify what you told them to; the dossier is the contract.**

---

## 2026-07-18 — Session 6: reference byte-form alignment (interop)

Prompt (paraphrased): *"Review a friend team's interop kit repo + its GitHub
issues; adopt only what doesn't evade the rules — and show me everything
before doing anything. Rule for adopting: only if BOTH the official demo AND
the kit have it. Tag a rollback checkpoint first."*

Process: deep-compared the kit's vectors against our crypto, then verified
its central claim directly against the official reference in
`../docs/DemoExamples` (never trust a third party's claim about a source you
hold yourself). Confirmed the reference uses `ensure_ascii=False`, a
pipe-appended-nonce commit preimage, a terms-derived game_uid, and a SECOND
(spaced) serialization for the settlement consensus signature. Our forms were
legal (the book is self-contradictory and permits a documented choice) but
non-interoperable — rule 19 makes byte-agreement existential. Adopted the
reference forms (ADR-0004), kept the book-faithful scent model (book beats
example), and imported the kit's vectors (MIT, attributed) as a
foreign-conformance suite so the alignment is *proven*, not assumed.

Lessons: (1) "correct" and "able to play" diverge when the ecosystem
standardizes on the example, not the spec; (2) a rollback tag + pre-release
before a breaking alignment makes the decision cheap to reverse; (3) verify
counterparty claims against primary sources — the kit was right, but now we
KNOW rather than believe.

---

## 2026-07-18 — Session 7: logging, verifier, and the deep-RL arms race

Prompts (paraphrased): *"How is my Q-learning support? Use agents to see how
to improve"* → *"We should have loggings, no? See how the demo and book do
it"* → *"Go deep learning or something even harder, I want us to be the
best"* → *"Does it take barriers into account? Training for both roles,
separately?"* → *"Improve it even more, adjust the weights and such."*

Process: two review agents audited RL and logging against the guidelines;
research agent pinned the demo/book logging conventions (runtime traces are
gitignored diagnostics, game artifacts are the committed record — book ch. 8
Log Manager split). Implemented: wired logging_config.json, timestamped
single-instance gatekeeper, physics-recomputing verifier (verify-log now
proves "untampered AND physics-legal"), config-true replay geometry. Then
the RL campaign: pure-Python MLP Q-networks (no new deps), Double-DQN with
replay + target nets, barrier actions for the cop, a two-round arms race via
weight-DATA crossover between the twins (never code imports), a 6-config
hyperparameter sweep, and two gated promotion attempts — both correctly
REJECTED by gates coded before the results existed.

Lessons: (1) put promotion gates in code before running the experiment —
twice an exciting intermediate number (a trivially-passing gate at smoke, a
0.82 at short budget) would have shipped a worse model on vibes; (2)
negative results recorded as artifacts (from-scratch collapse, robustness
collapse, knife-edge information dependence, the structural 0.74 ceiling
confirmed by three independent runs) carry more academic weight than the
positive ones; (3) specialist vs generalist is a real trade — the 1.00
evader is blind-fragile (0.00 under belief noise), which became the
evidence-backed case for keeping the robust hand-coded brain as league
default; (4) the 150-line cap and pre-commit hooks caught real drift
repeatedly — friction that pays.

## 2026-07-21 — Session 8: deception engineering (self-mirror lie policy)

Prompt (paraphrased): *"Upgrade the deception engineering: replace the
truth/lie coin in the runtime with a policy that lies exactly when it pays.
Build a SelfMirror (a second belief filter fed only by our own emissions,
estimating what the rival can infer about US), a DeceptionClock (lie budget
+ cooldown), and a DeceptionPolicy (lie only when exposed AND the rival is
believed close AND the clock allows). Decoys point away from the true
heading. All tunables in a private [deception] config table; roles flipped
from the sibling — the cop lies conservatively, while closing in, to mask
the approach; prove the receiving-side profiler still counters it; measure
policy-vs-coin."*

Process: TDD both repos (16 unit tests + 1 runtime-integration test each,
red first). The mirror reuses the rival's exact BeliefMap pipeline pointed
at our own role — no duplicated math; the runtime feeds it at the precise
point the rival's Perception observes us (pre-boundary for the cop who
opens every round). Numeric prototyping BEFORE pinning assertions caught
two traps: corner diffusion shifts the argmax off the true cell, and the
cop's pre-boundary scent lag caps its exposure (~0.45), which made a 0.5
threshold silently inert — probed the live exposure/distance distributions
during pursuit and set the default to 0.4.

Lessons: (1) the reputation economy measures beautifully — same outcomes at
2.0 vs 18.0 lies/game: truth is cheap when it buys credibility; (2) a
policy whose trigger never fires is a silent bug — measure trigger rates,
not just end results; (3) sealed intent flags make deception audit-honest:
the verdict trail the audit reveals IS the policy's decision log, asserted
verbatim in the integration test.

## 2026-07-21 — Session 9: chaos-drill suite (live-path robustness evidence)

Prompt (paraphrased): *"Build a chaos-drill harness proving the robustness of
the live path, with committed append-only JSONL evidence. Drills over REAL
HTTP MCP games (our runtime vs an in-process scripted stub opponent): D1
duplicate delivery (sealing dedup absorbs an at-least-once resend), D2 silent
opponent (deadline -> clean technical loss + watchdog persist), D3 transport
flap that heals inside the retry budget, D4 endpoint dead past the whole
budget (classified, never a hang). Plus a LIVE public-tunnel drill: kill
cloudflared mid-game and heal on the named tunnel's stable hostnames. Every
evidence line must be a really-observed event — never fabricated; mirror the
whole suite in the twin repo."*

Process: reused the integration-test machinery (two real FastMCP servers on
ephemeral ports) plus a tiny TCP proxy that severs live connections and
rebinds the same port; all knobs in a private `[chaos]` config table; the
drills re-run as slow marker-gated tests with evidence redirected to tmp.
Two wrong assumptions died on contact with reality: (1) the FSM does NOT
always end in TECHNICAL_LOSS — the book's table has no edge from COMMITTING
or WAITING_FOR_OPPONENT, so the classification lives in the engine outcome +
typed error; (2) a severed endpoint does not fail fast — the persistent MCP
session holds the in-flight call (SDK-internal reconnect) and the outer
retry loop is the backstop, so D3 asserts the game FROZE and completed
rather than counting retries.

Lessons: (1) the first live tunnel run found a real gap — a downed Cloudflare
tunnel answers HTTP 530, which `_is_connection_flavored` did not retry
(only 502-504): one marker line fixed it and the recorded kill/heal game is
the end-to-end proof; (2) chaos drills earn their keep by breaking the
author's model of the system, not the system itself; (3) pass criteria must
encode observed mechanisms, or the drill tests the assumption, not the code.

## 2026-07-21 — Session 10: competitive audit & the interop decision brief

**Context.** Ahead of the cross-team wire-shape negotiation, we audited a
rival league team's PUBLIC repos (their code being public is the league's
mutual-audit culture; ours is read the same way) and turned the findings
into build directives for our own repos.

**Prompt pattern — three-axis adversarial audit.** Parallel agents, one per
rival repo: *"Audit on three axes: (1) rule compliance/evasion — shared live
state, UI truth leaks, LLM-in-the-move-path, coordinate protocols, Gmail
scope, secrets, fixed-parameter drift, and anything sneaky (privileged info
reaching a brain, timeout farming, test rigging); (2) quality vs the course
guidelines every team is graded on; (3) honest head-to-head vs OUR repo —
where are they better? Flag DISQUALIFYING/SERIOUS/MINOR with file:line
evidence; if you can't confirm something, say so explicitly."*
**Outcome.** No violation found (their compliance engineering is excellent) —
but the head-to-head axis produced our work list: their committed live-drill
evidence and 1000-line prompt log exceeded ours; our submission artifacts,
book-default physics, and RL narrative exceeded theirs. One real cross-team
protocol hazard surfaced (at-least-once delivery vs strict step continuity)
that our sealing dedup already handles — it became a joint-ADR agenda item.

**Lessons.** (1) Audit the rival to find YOUR gaps: every "they're ahead
here" line converted directly into a same-day build (chaos drills, deception
policy, this log's depth). (2) Insist on the honesty clause in audit prompts
— "if you can't confirm, say so" is what kept shallow-clone history limits
from becoming false assurances. (3) Severity-tagged, evidence-cited findings
are immediately actionable; untagged prose audits are not.

## 2026-07-21 — Session 11: config-range fuzzer + crash-resume (E5/E6)

Prompt (paraphrased): *"Two infrastructure features, mirrored in both repos.
(E5) A legal-config-range fuzzer: sample the space a counterparty may LEGALLY
propose — Appendix-VI minimums raised (board 7-11, barriers 14-24,
max_moves=survival 35-60, valid distinct starts), FIXED values never fuzzed
(assert it) — and run a full in-process self-play game per sample over the
roundtrip HTTP-MCP machinery, checking invariants (legal shared outcome,
matching digests, clean audits, turn/barrier bounds). 40+ samples committed
to results/experiments/ + docs/evidence/. (E6) Crash-resume: per-half-turn
atomic snapshots (records incl. nonces, action log, agreement) under
results/local/, ON by default; a resume path that replays through
protocol.apply_action and re-arms the SealedExchange; a resume_offer control
handshake answered by re-sending the last sealed pair (dedup absorbs
duplicates); a kill-and-resume drill with real JSONL evidence."*

Process: TDD against the loopback-pair pattern from the runtime tests; the
runtime sat at 149/150 code lines, so ALL resume logic went to a new
peer/resume.py and the runtime gained only four hook lines (docstrings paid
the rent). The drill's first run failed honestly: the reused chaos helper
always calls play() fresh, so the resumed peer re-negotiated into a void and
ate a deadline — the drill needed its own classified runner that continues
from the re-armed turn. Deliberate scope line: snapshots are half-turn
atomic; a crash between commit-send and reveal-send loses that half-turn's
nonce and MUST NOT be re-committed differently, so recovery is defined from
the last completed half-turn (documented in docs/evidence/crash-resume.md).

Lessons: (1) a resume feature is really a replay feature — reusing the one
true apply_action path made engine fidelity a one-line digest assert;
(2) the at-least-once dedup we built for lost HTTP acks is EXACTLY the
mechanism that makes resume handshakes safe — new capability, zero new wire
rules; (3) fuzzing the negotiable ranges (40/40 green) is the cheap proof
that "nothing hardcoded" is true in the physics, not just in the config
loader. Fuzzer found no real bug; nothing in domain/ needed touching.

## 2026-07-21 — Session 11: exact endgame solver + info-gain term (keep-gated)

Prompt (paraphrased): *"Build two cop-strength features: (1) an exact endgame
solver — when the subproblem is small (belief support ≤ K cells, bounded
horizon) run memoized adversarial search and play the forcing line's first
action; (2) an information-gain move term rewarding expected belief-entropy
reduction from the scent reading at each candidate landing. BELIEF-CORRECT
semantics are rule-critical: a forced capture must hold against EVERY thief
cell carrying non-negligible mass and every legal reply — never read the
rival's true cell (add a guard test). Compute hard-capped; tunables in
[strategy.endgame]/[strategy.info_gain]. Then MEASURE with a keep-gate: ≥60
seeded games/arm (baseline / +endgame / +info_gain / +both) vs the evader
pool; keep a feature ONLY if it raises capture rate, else default OFF and
record the negative result honestly."*

Process: solver = win/loss minimax with memoization (exists/forall early
exits ARE alpha-beta for boolean payoffs) over (cop, candidate thief,
barrier delta, turns left), on lightweight `_View` boards — domain stays
read-only. The first physics-adjudicated rollout test caught a real bug:
returning ANY forcing action lets the cop dance forever (many actions
"force within h" every turn without progress; observed 34-turn capture on a
2-turn coffin). Fix: iterative deepening — return the SHALLOWEST forcing
depth, which strictly decreases along the line. Guards: source scan (no
`Role.THIEF` in the solver) + a `GuardedPositions` proxy that trips if the
blind decide path ever reads the rival's key.

Lessons: (1) the keep-gate did its job — BOTH features failed honestly:
the scent-floor belief keeps support at 7–10 cells (top-3 ≈ 41% of mass),
so sound forced-capture windows never occur (0 solver fires in 160 games,
still 0 at K=8), and the info-gain sweep (w=0.5–4.0) moved capture rate not
at all; defaults shipped OFF with the probes written up in
docs/evidence/cop-strength.md. (2) Measure the GATE before the feature:
one support-size histogram would have predicted the negative result before
a line of solver code. (3) Adversarial-search tests must adjudicate via the
engine, not via the search's own logic — the dance bug was invisible to
every unit test and obvious to the rollout.
