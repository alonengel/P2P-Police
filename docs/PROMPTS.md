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

## 2026-07-21 — Session 12: public pair-verifier & the stale artifact it caught

**Prompt (paraphrased).** *"Extend the replay verifier into a league tool:
verify ANY two teams' logs of the same game — each side alone, then mutual
consistency (uid, end digest, record-for-record commit equality). Offline
over files only; never touches a live game."*

**Outcome.** `report/pair_verify.py` + `scripts/verify_pair.py`, TDD (6
tests: consistent pair, tampered record, uid/digest mismatch, missing step
in the rival's view, forged commit swap, tolerated pre-audit verdict
absence). First run on our own committed artifacts immediately caught a
real defect: the g02 self-play logs were sealed under the PRE-migration
commit byte-form and read TAMPERED to any grader. Regenerated via a fresh
cross-repo match and added a guard test that replay-verifies EVERY
committed log artifact, so stale evidence can never linger silently again.

**Lesson.** Point new verification tooling at your own artifacts first —
the tool paid for itself before it ever saw a rival's log.

## 2026-07-22 — Session 13: reference-v3 hidden-information wire (phase 1)

**Prompt (paraphrased).** *"Build phase 1 of a reference-v3 (hidden-
information) wire client as an ADDITIONAL mode behind a config/negotiation
seam: own-state engine (rival position structurally unknown), demo-shaped
TurnMessage codec (smell_grid transmitted, commit per step, reveals
deferred to the audit), capture-claim flow with a structurally-enforced
truth duty, a hidden-mode runtime reusing the hardened receiver machinery,
audit-time physics reconstruction, and guard tests for every rule-sensitive
surface (rules 8-9, 18, 21-22, 25, 27). Bookletter stays the untouched
default; wire_shape declared via the registry lock-doc hash under the
both-declare rule. Mirror across both repos; never touch domain/."*

**Outcome.** New `wire/` package (9 modules, mirrored twin): `own_state`
(engine duck-type whose `positions` dict simply has no rival key — belief-
only play enforced by shape), `codec` (closed demo key set: step/sender/
hint/smell_grid/commit/timestamp + the four claim fields; unknown keys
rejected so a position can never ride along), `claims` (truth duty as pure
functions of own state — no strategy parameter exists), `hidden_exchange`
(SealedExchange subclass: commit-only live wire, reveals verified at audit
against the live-received commits), `lock` (registry doc pinned to
sha 229ae648…, both-declare refusal table), `hidden_runtime`/`hidden_turns`
(the loop; thief's boundary before its snapshot ships), `audit` (replay on
Board physics with an explicit truth-duty check). 76 new tests per repo
(byte-exact book-model scent fixtures incl. the ordering probe; dedup/
reorder/flood on the hidden wire; full in-process games: random, survival,
landing-claim capture, barrier-on-thief — all ending in clean verified
audits; hidden logs verify through the existing replay machinery
unchanged). One shared edit: `peer/sealing.py` duplicate-branch lookup made
payload-tolerant (`r.get("payload", {})`) so the subclass can reuse the
hardened receiver — bookletter semantics byte-identical, full suite green.

**Lesson.** The engine-replay audit was wrong for this wire: a thief that
steps onto the cop's cell is unobservable live (capture is claim-mediated),
so an instant-capture reconstruction would flag honest games as TAMPERED.
The audit now proves exactly what the wire can prove — captures created by
the cop's own action, concessions forced by the truth duty — and the
documented deviation is itself the strongest argument for keeping the
reconstruction in wire/, not domain/.

## 2026-07-22 — Session 14: reference-v3 hidden wire (phase 2: SDK, artifacts, resume, live E2E)

**Prompt (paraphrased).** *"Build phase 2 of the reference-v3 hidden-
information wire client: route `sdk.run_peer` (and the CLI peer command)
between HiddenRuntime and GeometricRuntime off `wire_shape(config)`; adapt
the watchdog state provider and technical-loss reporting to a runtime that
exposes `own`, not `engine`; emit the four league artifacts from a hidden
game so the log verifies through the existing verify-log AND the pair
verifier; extend the crash-resume pattern to the hidden wire (snapshot
own-state + exchange records; the resume offer re-sends the last commit —
reveals never ride live) with a real-events JSONL drill; run a REAL
two-process cross-repo hidden game over local HTTP MCP and archive its
artifacts without touching the g01/g02 bookletter evidence; write ADR-0008.
Nothing weakened, bookletter untouched, no domain/ edits, mirror both repos."*

**Outcome.** `sdk/hidden.py` (runtime assembly behind the wire-shape seam;
run_peer stays the single entry) + `sdk/reporting.py` grew a runtime-agnostic
watchdog provider (the hidden dump's positions dict structurally lacks a
rival key — rules 8-9 hold in post-mortems) and an own-state technical-loss
digest. Hidden logs carry `"wire_shape": "reference"`; `verify_log`'s physics
half moved intact into `report/lookup.py:replay_verdict`, which routes marked
logs through the audit reconstruction (ADR-0008) and everything else through
the byte-identical engine replay — guard tests prove relabeling in EITHER
direction can only invalidate a log, never launder one. `wire/hidden_resume.py`
snapshots what this peer truly holds (own cell/barriers, boundary-cell
history for a deterministic scent replay, clock+token, the rival's last scent
snapshot, sealed records incl. our never-transmitted nonces) atop the
geometric recorder via an injected builder; the resume_offer answer re-sends
the last COMMIT-bearing TurnMessage only (rule 18 survives E6, guard-tested).
Kill-and-resume drill on the hidden wire: crash after 6 half-turns, restored
in 0.062 s, game finished 35-turn survival, both audits Verified OK
(docs/evidence/drills/hidden_resume_recovery_2026-07-22.jsonl, real events).
LIVE cross-repo E2E: two CLI peers (ports 8802/8801), temp config override
(committed game.toml default untouched), sub-game 3: 35-turn survival, both
audits Verified OK, identical digest f5b6837b…33eaa, 35 sealed records per
side, `scripts/verify_pair.py` over the two repos' logs → overall Verified OK
in both directions; artifacts archived as results/log_…_g03.json +
config/games/config_…_g03.json (+ declaration/result under
results/hidden_e2e_g03/ so the bookletter g01/g02 evidence stays pristine).
15 new tests per repo; coverage 92%; ruff 0; both suites green; parity OK.

**Lesson.** The verifier had to become wire-aware WITHOUT a second code
path a grader must trust separately: moving the existing physics recompute
verbatim behind one dispatch keeps bookletter verification byte-identical
while making "which replay applies" a property of the sealed log itself —
and the guard tests that relabel logs both ways are what turn that marker
from a loophole into a commitment.

## 2026-07-23 — Session 15: reference-v3 flat-terms negotiate handshake

**Prompt (paraphrased).** *"The registered reference-v3 wire shape uses the
REFERENCE's literal negotiate form — a flat 14-key `terms` dict + `nonce` +
`signature = SHA256(canonical(terms)+'|'+nonce)` (league-kit CORE vector
terms_signature.json) — not the bookletter agreement's config_sha256
substitution, which is registered as a bookletter-v3 property. Build the
flat-terms derivation FROM the signed game.json (derive, never duplicate),
byte-test it against the kit vector, switch HiddenRuntime.negotiate to send
{terms, nonce, signature} with our model-hash declarations
(scent_model_sha256, wire_shape_sha256, info_mode) riding alongside, verify
the rival's signature AND value-equality key-by-key with a diagnostic that
names every differing key and both values, keep the both-declare lock
verification unchanged, and keep the bookletter path byte-untouched."*

**What was built.** `wire/terms.py`: `terms_from_shared` derives the
reference's exact 14-key set from game.json (max_steps maps from
survival_threshold — the reference's own overlay — with a refuse-guard if
max_moves ever diverges, since the flat form has one step field);
`sign_terms` reproduces the kit CORE vector byte-for-byte (canonical form
AND signature, pinned by test from a config patched to the vector's
values); `build_negotiate_message` assembles the wire payload (identity
block + hardware seal + locked-model hashes ride as extras a reference
peer ignores; `config_sha256` never appears); `verify_terms_message`
enforces signature-recompute + key-by-key value equality, refusing with
EVERY differing key and both values named (interop debugging quality);
`verify_declarations` applies the registry both-declare rule to
scent/info_mode (wire_shape stays in wire/lock.py, called unchanged);
`peer_group_id` reads our top-level id or the reference's identity.group_id
— also adopted by hidden_resume.rearm. HiddenRuntime.negotiate now sends
and verifies this shape; a minimal reference-form message (terms + nonce +
signature + identity only) negotiates cleanly (omission is never refusal).
Derived-terms audit vs the kit example: 13/14 values identical; `setting`
differs (ours 'New York', kit example 'Haifa') — the official demo's own
default is 'New York', so a reference-DEFAULT team value-matches on all 14;
the kit example's setting is synthetic. 43 new tests per repo (kit-vector
bytes, 14-key refusal matrix, garbled-message guards, both-declare truth
table, in-process negotiate round-trip, minimal-reference acceptance,
named-diagnostic refusal drill); full suite 492 green, coverage 92%, ruff
0, line cap OK, physics parity OK (domain/ and tests/vectors/ untouched).

**Lesson.** A handshake meant for foreign peers is defined by what it
REFUSES and how it says so: signing their exact bytes back at them and
naming every diverging term turns a dead game into a one-line fix on
either side — and the derive-don't-duplicate rule (terms are a projection
of the signed config, never a second copy) is what keeps the wire shape
honest when the constitution changes.

## 2026-07-23 — Session 16: live-interop fixes — per-sender steps, thief opener, watchdog liveness

**Prompt (paraphrased).** *"Fix three live-interop defects in the
reference-v3 hidden wire, verified against the official demo before
coding. (1) Step numbering: we numbered turns with a GLOBAL half-turn
counter (our messages arrived as steps 1, 3, 5...) while the reference
numbers PER-SENDER — step_number increments only on your OWN move (demo
own_state.apply_move), each side sending 1, 2, 3...; align, and check
every consumer: dedup keys when both senders reuse the same numbers,
audit reconstruction ordering, resume snapshots, codec validation.
(2) Thief opening turn: our thief handshook then never sent — root-cause
against the demo's round flow (its runtime SEEDS the thief's turn before
the receive-respond loop) and align who awaits whom, keeping
deadline/watchdog/FSM discipline. (3) Watchdog liveness: a rival mid-game
outage held an in-flight MCP await ~60s without beating — the watchdog
killed us (controlled) at 60s instead of letting the 180s deadline
classify; make EVERY wait path beat every few seconds so only the
deadline judges the rival, tested with a fake clock and a hung transport.
Plus: a two-runtime cross-cadence integration test asserting the live-GUI
perception feed fires for BOTH roles (the live thief window stayed black),
and an idle-state paint in the GUI at window-open. No commits — main
session reviews."*

**What was built.** Root causes, each pinned to the demo: (1)
`hidden_runtime.play` drove ONE global step counter through both halves —
the demo's `own_state.apply_move` (line 51) increments `step_number` only
on own moves and `peer/sealing.build_turn_message` sends
`state.step_number`, so numbering is per-sender; (2) `wire/own_state.py`
seeded `next_actor = Role.POLICE` (bookletter lockstep habit) while the
demo's `runtime.run` (lines 92-93) has the THIEF `take_turn` BEFORE the
receive-respond loop — our thief waited for a police message that a
reference police (which waits to receive first) would never send:
mutual starvation, 0 turns, rival timeout; (3) `mcp_client._submit`
awaited `future.result(timeout≤30s)` in ONE block and the backoff sleep
in another — legal per-iteration waits chain into ~37s+ silent gaps, and
a coroutine-raised TimeoutError could be mistaken for a slice timeout.
Fixes: per-sender clocks `my_step`/`their_step` on HiddenRuntime (the
halves own their increments — no desync possible), thief-opener token,
audit reconstruction ordered by `(step, thief-before-police)`, resume
snapshots persist/restore both clocks (older snapshots refuse cleanly),
codec requires step ≥ 1, and the receive adapter now (a) DROPS echoes of
our own role (same-number collisions are the price of per-sender
numbering; an echo must never be lethal) and (b) keys any caught=True
final to the LIVE expectation — the demo's `send_final` re-uses the
sender's LAST step number (no apply_move before it), which our dedup
would otherwise drop as an at-least-once duplicate, hanging the win we
are owed. Survival stays demo-timed automatically: the thief's step ticks
the round clock, so `survival_reached()` fires at its OWN 35th step and
the win_claim rides that very message. `_submit` now waits in beat-sized
slices (default 2s, injectable) with a done-future guard, the retry
backoff sleeps in slices, and the chaos duplicate-wrapper forwards `beat`
to the inner transport it had been silently stranding. GUI: `live_view`
paints an idle local-truth snapshot (empty board + OWN start cell) at
window-open. New tests: two-runtime cross-cadence game to a verified
audit (per-sender wire assertions, thief-opens, 35-step survival,
perception.on_snapshot fired for BOTH roles with the closed local-truth
key set), demo-style final re-use consumption, own-echo drop, hung
transport + fake-clock backoff + coroutine-timeout liveness, idle
snapshot. Full suite 502 green (police) / 500 (thief), coverage 92%,
ruff 0, line cap OK, physics parity OK (domain/ and vectors untouched);
every change mirrored byte-identically.

**Lesson.** Interop bugs hide in the counters nobody signs: the wire
schema matched the reference perfectly while the NUMBERS on it spoke a
different dialect, and the deadlock needed no bug on either side — just
two correct implementations of two different cadences. The demo's code is
the contract; read the loop, not the message shape. And liveness is a
property of every await individually: a chain of legal 30s waits is an
illegal 60s silence.

---

## 2026-07-24 — Session 17: GUI-mode outage defects — the zombie window & the spurious watchdog

**Context.** Two live cross-team GUI runs (sparring, reference wire) died the
same way: the rival's edge went 502/530, ~60s later the watchdog logged "no
heartbeat for 60.0s — controlled shutdown", then NOTHING — no report JSON,
four OS processes alive forever. Never in headless runs, never in local GUI
games that complete. Mid-session a second report landed: in the next
cross-team attempt both our peers "negotiated cleanly then went silent" — the
thief never opened, the police never answered the rival thief's step 1.

**Prompt pattern — logs before hypotheses.** The brief named suspects
(unbeaten wait paths, beat wiring order, the GUI feed queue). Before touching
code we read logs/p2p_police.log + logs/p2p_thief.log + both watchdog dumps
from the live runs and rebuilt the timeline to the second. Every suspect was
innocent: the transport beat through the whole outage (530 retries every 5s
for the full 180s budget; no firing DURING the wait). The real chain: the GUI
worker thread classifies technical_loss at its deadline → the worker DIES with
the report boxed → beats stop → `view.run()` (Tk mainloop) never exits because
the exception path skips `perception.emit`, so no game_over snapshot ever
reaches the view → run_peer's `finally: watchdog.stop()` is unreachable → the
still-armed watchdog fires exactly +60s after worker death (defect A) and the
report stays trapped behind the mainloop forever (defect B). Both dumps agree:
outcome was ALREADY "technical_loss" at fire time.

**Root causes (pre-fix lines).** sdk/sdk.py:141 `view.run()` returns only when
gui/live_view.py:102-103 set `_done` on a game_over SNAPSHOT — and no failure
path emits one; nothing stops the watchdog when the worker ends, so the
monitor outlives the game it monitors.

**Fix (mirrored).** `play_into_box` gained a `finally`:
`runtime.watchdog.stop()` (the game is classified the moment the worker ends)
plus `view.finish(outcome)` — a thread-safe sentinel through the snapshot
queue that flips the banner to GAME OVER and releases the mainloop.
`NullWatchdog` grew the matching `stop()`; the GUI path now also forwards
`start_turn` (GUI + --resume no longer re-negotiates a resumed game).

**Repro-first (TDD).** tests/integration/test_gui_outage.py drives
`_play_with_gui` with a stubbed LiveView (real mainloop semantics — run()
blocks until told the game ended, hard-capped so a red run FAILS instead of
hanging) against a scripted rival whose tunnel dies mid-game (retries in
beat-sized slices until the deadline — the committed McpTransport outage
contract), on the hidden wire AND the geometric path. Red reproduced the live
runs exactly (watchdog FIRED after worker death, view never released); green
asserts no firing while the deadline runs, technical_loss classified, the
report returned in-time, the mainloop released.

**Cross-team silence triage (which cause explains which symptom).**
(1) POLICE SILENT: the rival thief's step-1 tool call never REACHED our inbox
— the log shows its MCP session created at 13:28:27 with no CallToolRequest
ever processed, then their edge 502 at 13:31:23; our police correctly waited
its full 180s. Their literal message shape is NOT the cause:
tests/unit/test_wire/test_reference_message_fixture.py feeds the exact
ten-key / explicit-nulls / dense-25-cell / microsecond-timestamp message
through the receive path — parse, scent absorb, token pass all clean ("r,c"
keys match the demo emission; the closed key set still rejects unknowns).
(2) THIEF SILENT: the rival cop's negotiate never arrived in the live window —
our previous ZOMBIE process (defect B's downstream damage) had been acking
their negotiate retries at 13:23/13:25/13:27 into a queue nobody read, so the
rival believed the handshake done; the fresh 13:28 process waited 180s for an
agreement that never came. (3) THE HANG: defect B, fixed — and with the
process now exiting properly, the zombie-swallowing failure mode dies with it.
No regression in the session-16 batch.

**Gates.** 509 tests green (police) / 507 (thief), coverage 93% both, ruff 0,
line cap OK, physics parity OK (domain/ and vectors untouched); every change
mirrored.

**Lesson.** A watchdog that cannot be stopped by the thread it watches will
eventually bark at a corpse: disarm liveness monitors at CLASSIFICATION, not
at report emission. In GUI architectures the mainloop is a report gate —
every exit path of the game thread must message the UI, because the
"impossible" path (an exception before the first emit) is exactly the one a
dead tunnel takes. And read the live logs before believing any hypothesis:
the named suspects all had alibis written in httpx timestamps.

## 2026-07-24 — Session 18: fair audit of a FOREIGN-schema rival — the mutual-audit failure of the first full cross-team games

**Context.** Tonight's first complete cross-team games (35 turns, both
sides) ended with BOTH peers rendering the audit TAMPERED /
digest_match=false against an honest reference-shaped rival — and the
counterparty's side symmetrically rejected OUR audit envelope. The league
SPEC is explicit: the payload schema and the end-digest construction are
PER-TEAM choices; only canonical JSON and the commit construction
SHA256(canonical(payload)+"|"+nonce) are the shared contract.

**Prompt pattern — judge by the contract, not by our schema.** The brief:
build a three-tier verdict for the rival's half — (a) the commit criterion
over every revealed record (the ONLY tamper test), (b) our strict physics
reconstruction ONLY when the rival's payloads parse as our schema, with a
graceful degrade to derivable checks (per-sender step continuity, revealed-
position movement legality) for foreign schemas, (c) digest comparison only
under one shared construction — otherwise digest_match=null, never false.
Plus two queued items: caught=True must not classify as capture unless the
sender is the THIEF (only the cop's claim flow produces our capture), and
our audit message must be the reference AuditPayload envelope EXACTLY
(sender/records/result_claim — their strict parser rejected ours for the
missing `sender`, and cls(**data) rejects any extra key).

**Root cause, read from the real artifacts + the reference source.** Three
schema couplings, all pre-flagged: (1) the reference reveal set carries a
step-0 system_spec record whose commit never crosses the live turn wire, so
our strict zip+length alignment could never match — tonight's logs prove
this tier aborted FIRST: opponent_records hold live commits only, no merged
payloads; (2) domain crypto's commit recompute demands OUR pinned field
set, so even aligned foreign payloads read TAMPERED; (3) reconstruct/
digest_match assumed our role/action keys and our digest construction.

**Fix.** New wire/audit_foreign.py (schema-agnostic commit_clean, reveal
alignment BY COMMIT with extra commit-clean records tolerated,
parses_as_ours gate, continuity_ok + movement_ok derivable checks, judge()
returning digest_match=null); hidden_exchange.audit_reveals delegates to
it; hidden_turns.finish routes strict-vs-foreign and sends the exact
reference envelope; their_half_turn gained the thief-only concession guard;
report/lookup.recompute_hidden degrades identically for saved logs;
sdk.verify_log checks the rival's records under the shared contract only;
pair_verify keys only same-schema payloads. Strict full reconstruction
unchanged for our own records and same-schema pairs; bookletter untouched;
domain/ and tests/vectors/ untouched.

**Proof on tonight's actual files.** tests use the REAL working-tree logs:
the cross-team game logs now replay "Verified OK" in both repos (foreign
schema tolerated, commit criterion intact — forging one sealed byte of the
same real log still convicts), reference-shaped reveal fixtures (the
rival's literal sealing field set) verify clean including the step-0 spec
record, a forged commit in the same set reads TAMPERED, digest
not-comparable lands as JSON null in the result artifact.

**Gates.** 531 tests green (police) / 529 (thief), coverage ~93% both,
ruff 0, line cap OK, physics parity OK; every change mirrored.

**Lesson.** An audit that encodes our own serialization habits as morality
will convict every honest stranger it meets: verify the CONTRACT (the
hash), derive what the revealed data actually supports, and say
"not comparable" when two constructions share no common frame — null is a
verdict too, and it is not "false".

## 2026-07-24 — Session 19: reference-conformant series result, settlement guard & sub-game handshake

**Context.** A live counterparty diffed our emitted series result against
the official demo's sample-run result and found the shape wrong: missing
game_uid (ours said null — the cross-team series identity BOTH reports
must match on), groups, links, mutual_agreement, _schema, schema_version,
report_type, timezone; sub_games keyed log_file/outcome/scores instead of
log_files/result/score; no roles, winner_group, github_commit, tokens,
tie, timestamps; final_result without tokens_total_series. Separately, a
live find: identical terms give identical game_uids across instances, so
a leftover rival instance from a previous window can pair into the WRONG
sub-game and nothing on the wire disambiguates.

**Prompt pattern — conform to the reference's key structure, refuse to
invent a game.** The brief: (1) rework series aggregation to emit the
reference-conformant document — real game_uid derived as the logs' shared
uid, both teams' identity blocks, all four GitHub links, both FastMCP
addresses, mutual-agreement confirmations from the per-game audits,
per-sub-game roles/result/winner/score/tokens/log_files/audit/timestamps,
tokens_total_series; (2) a SETTLEMENT GUARD — refuse to emit when any
sub-game 1..num_games lacks a settled audit-clean log, naming the gaps
(rule 35: a report that quietly completes a missing game endangers the
counterparty); (3) pool logs from BOTH role repos (repeatable
--results-dir) and exclude BY NAME any log whose game_uid or declared
num_games mismatches the series; (4) exchange sub_game_number at the
hidden-wire negotiate OUTSIDE the signed flat terms (like info_mode),
refusing only when both declare and they differ — omission tolerated,
reference peers never send it.

**Build.** sdk/series.py rewritten (collect_logs + consensus-uid guard +
require_settled + aggregate_series returning (doc, excluded)); NEW
report/series_doc.py shapes the document (key sets transcribed from the
demo sample, attribution in-file; sign-then-insert mutual_agreement);
cli series-result takes repeated --results-dir, prints named exclusions,
exits 1 with REFUSED on an unsettled series; wire/terms.py adds
sub_game_number to BOTH_DECLARE_FIELDS with a stale-instance hint in the
refusal; hidden_runtime declares it at negotiate and records started_at
for future logs. domain/ and tests/vectors/ untouched; every change
mirrored to the twin.

**Proof on the six real logs.** The full series_final set emits a clean
result — zero missing keys against the reference at every level, real
game_uid 2f0c25a9-...; with s6 (the mis-attributed game) excluded the
aggregator refuses: "s6: no settled log", exit 1.

**Gates.** 553 tests green (police) / 552 (thief), coverage ~93% both,
ruff 0, line cap OK, physics parity OK.

**Lesson.** A settlement document is a cross-team contract: its identity
field (game_uid) and its key layout are the counterparty's parsing
surface, and an aggregator that fills gaps instead of refusing turns a
missing game into a forged one. Conform to the reference's structure,
derive identity from evidence, and make every exclusion say its name.

## 2026-07-24 — Session 20: counted-series readiness — series email auto-fire & the league-day window runner

**Prompt (condensed).** "A counted series is one continuous run ending in
its report; today the email is manual. (1) `series-result --email`: after
a SUCCESSFUL conformant emit (settlement guard passed) send the ONE
series email exactly like the per-game auto-report — mode gate,
shared/gatekeeper, recipient from config, subject carrying game_id +
final score + series_tie/winner; a refusal must never email. (2) A
committed `scripts/league_series.py` per repo driving that repo's role
windows (police: odd, thief: even) via the real CLI in sequential
subprocesses, with a single-instance pid lockfile under results/local/
and honest per-window logging — a failed window is logged, never
fabricated. (3) Runbook: the counted-series procedure end to end."

**Build.** `sdk/series.py` gains `maybe_email_series` (mode gate →
gatekeeper → `infra/email_sender.send_report`; body = the full result
JSON, attachment = the emitted result file, subject =
`game_id - winner/series_tie - score`); it is reachable ONLY after
`aggregate_series` returned, so the rule-35 settlement guard structurally
precedes any email. `cli series-result --email` wires it and prints the
message id. NEW `scripts/league_series.py`: parses this repo's window
list (refusing wrong-parity windows — the book's alternation is not
negotiable), takes an O_EXCL pid lockfile (second instance refuses and
never deletes a lock it does not own), launches `uv run p2p-police peer
--sub-game N --seed base+N` per window sequentially, reports each exit
code verbatim and continues past failures with a non-zero final exit.
LEAGUE_RUNBOOK.md: new "Running the counted series (end to end)" section
(T-protocol launch, two --results-dir aggregation, --email auto-fire,
settlement-guard meaning, lock semantics, rule-53 manual commit-id email,
and the explicit counted-posture flip: league recipient restored +
mode=send armed vs the committed warm-up posture). Tests: fake sender
injected via monkeypatch — send-mode emits then emails once (recipient
from config, gatekeeper instance asserted); a refused series and
disabled mode send NOTHING; no flag = no email; runner parity/lock/
sequence/failure-continuation covered with an injected fake subprocess
runner. domain/ and tests/vectors/ untouched; everything mirrored to the
twin.

**Gates.** Full `uv run pytest -q` green: 563 tests (police) / 562
(thief); ruff 0 (src+tests+scripts) both; 150-code-line cap OK both;
physics parity OK (16 files identical) both.

**Lesson.** An auto-fired settlement email is only as honest as the guard
in front of it: make the send reachable exclusively through the code path
that already refused unsettled series, and "never email an invented
result" becomes a structural property instead of a convention.

## 2026-07-24 — Session 21: pre-series handshake hardening — mutual wire shape, agreement re-push & the settlement gate

**Context.** Final hardening before the counted series, from two live
findings. (1) The counterparty proposed an exact mutual negotiate shape
to interoperate first try: two extra TOP-LEVEL keys beside
identity/nonce/terms/signature, unsigned and outside terms —
`{"sub_game_number": N, "role": "police"|"thief"}` — with the kit's
locked-model refusal style. (2) A live-observed failure: a handshake
swallowed by the opponent's PREVIOUS sub-game peer, which acked into a
dead queue and exited; the faster side ran ahead and the series drifted
into a rule-35 shape.

**Prompt pattern — match the agreed shape byte-for-byte, then mirror
both halves of the swallowed-greeting failure.** The brief: (1) VERIFY
our `sub_game_number` spelling/level (already top-level — confirmed) and
ADD `role` with the inverted truth table: their role present and equal
to ours refuses loudly (peers must be complementary), either key absent
always proceeds (reference peers stay playable); (2) AGREEMENT RE-PUSH —
negotiate re-sends our agreement every [network] agreement_repush_sec
(config knob, dedup-safe: the SAME payload, same nonce) until the
rival's arrives or the turn deadline lapses, watchdog beats maintained;
(3) POST-SETTLEMENT INBOUND REFUSAL — once our own sub-game settles, our
four MCP tools answer {"accepted": false, "reason": "sub-game settled"}
instead of enqueueing into a queue nobody reads, so OUR dying peer can
never swallow THEIR next greeting.

**Build.** wire/terms.py: `build_negotiate_message(..., role=)` rides
`role` top-level unsigned; `verify_declarations` adds the inverted
role rule (equal-declared pair refuses, naming "complementary"). NEW
wire/repush.py: `push_agreement(rt, mine, clock)` — send, re-send
unchanged each interval (fake-clock injectable), overall deadline still
judges; hidden_runtime routes negotiate through it and declares
`role=self.role.value`. infra/mcp_server.py: `PeerInboxes.settled` +
`deliver()` settlement gate on all four tools; sdk.run_peer sets
`inboxes.settled = True` at settlement (finally) — BOTH wire shapes
(geometric and hidden) go through run_peer, so both got the gate.
game.toml documents agreement_repush_sec = 7.0. domain/ and
tests/vectors/ untouched; everything mirrored to the twin.

**Tests.** Role truth table (equal refuses, complementary/absent play);
exact top-level spelling of BOTH keys asserted on the emitted negotiate
payload (unit key-set + round-trip log + every re-pushed copy); re-push
with a ticking fake clock (re-sent until theirs arrives — 3 sends then
stop; 1 send when immediate; deadline still bounds the loop); settlement
gate before/after the flag (unit door, all four tools over real HTTP,
and a late greeting refused after a full run_peer e2e).

**Gates.** Full `uv run pytest --cov -q` green: 580 tests (police) /
579 (thief), coverage 93.26% / 93.21%; ruff 0 both; 150-code-line cap OK
both; physics parity OK (16 files identical) both.

**Lesson.** A dying peer is part of the wire contract: an ack into a
queue nobody will ever read is a lie to the counterparty. Refuse once
settled, re-push until answered, and let dedup make persistence free —
liveness then degrades into retries instead of series drift.

## 2026-07-25 — Session 22: report-layer book fidelity — no Hebrew match report is mandated (ADR-0009)

**Context.** Our own book-fidelity review of the report layer. The
course reference kit still ships `report/report_writer.py` — "the
official Hebrew JSON match report ... Schema follows the game book
(section 8)" — with Hebrew keys we never emit. If the book truly
mandates a per-sub-game Hebrew-keyed report, our four artifacts hide a
graded gap; if not, adopting it would drift from the book's canonical
file vocabulary. Primary source first, code second.

**Prompt (condensed).** "Re-read the reporting surface in full — ch. 8,
ch. 9, Appendix ה, Appendix ו — before touching code. Decide: does the
book define an official per-match Hebrew report schema, which fields,
and is it חובה or example? If mandated, build `report/hebrew.py` TDD
beside the four artifacts; if example-only or absent, build NOTHING and
write the ADR with page cites. Book over example either way."

**Finding.** The book mandates machine-readable JSON reporting but
names no Hebrew field anywhere: §9.3.3 (p. 78) delegates the format to
four attached example files, and Appendix ו Table 20 (p. 141) defines
exactly four — declaration/config/log/result, named from game_id +
g<NN>, "the names the book uses everywhere". The only field-level
mandate (pp. 79-80): both teams' GitHub links (all four), each
sub-game's commit id, token totals — all already carried by our
declaration/result artifacts and the emailed series result
(`report/series_doc.py`). Ch. 8 (pp. 61-68), the docstring's "section
8", is architecture only — a stale cite; the reference's canonical
sample run emits the four files with English snake_case keys, and its
own sdk keeps the Hebrew report only as "legacy Hebrew log
(back-compat)" feeding `{role}_match.json`, the ch. 7 replay input.

**Build.** Deliberately no code: NEW
`docs/adr/0010-official-match-report.md` (both repos, byte-identical)
records the reading with page cites and the rules 32-36/49/51/53-54
mapping, why the existing four-artifact layer IS the official report
set, and the revisit trigger (a future binding schema lands in
`report/`, never in parity-locked `domain/`). PROMPTS updated.
domain/, tests/vectors/ and all code untouched.

**Gates.** Docs-only session; suites re-run regardless: full
`uv run pytest --cov -q` exit 0 in both repos (thief re-run solo after
a parallel-run port flake in one chaos drill), 577 (police) / 575
(thief) tests, coverage 93.26% / 93.21%; ruff 0 both; 150-code-line
cap OK both; physics parity OK (16 files identical) both.

**Lesson.** A reference implementation is evidence of A reading, not
of THE rule: when its docstring points at a chapter that no longer
says what it implies, the book's own binding principle (p. iv: nothing
binds unless explicitly stated) decides. Recording the non-build in an
ADR is as load-bearing as code — it closes the gap permanently instead
of leaving it to be re-suspected at every audit.

---

## 2026-07-25 — Session: live-proven hardening batch (bystander-tolerant handshake, series bookends, port orphan guard, lecturer-address interlock)

**Prompt pattern — adopt a batch of live-proven hardening items.** After
the cross-team live sessions, a delegated agent received the observed
failure modes as a numbered batch with per-item severity, the exact
module map to touch, an explicit DO-NOT-TOUCH list (domain/, vectors,
report/ owned by a concurrent task), and the standing gates: *"Nothing
may evade the rulebook; every item below TIGHTENS compliance ... Tests:
bystander agreement (wrong index) then real one -> game proceeds,
refusal logged; fatal classes still fatal; deadline still bounds an
endless-bystander stream."* Naming the tolerated/fatal split IN the
prompt (pairing-class vs violation-class) is what kept the tolerance
from quietly weakening rule 6.

**Build.** wire/terms.py: `PairingRefusalError(GameRuleError)` — wrong
`sub_game_number` and role-equal refusals classify as bystanders;
locked-model mismatches stay plain-fatal. wire/repush.py:
`push_agreement(..., verify=)` verifies INSIDE the wait — a pairing
refusal is logged on the record ("agreement refused: wrong game, not
you" with both values) and the wait continues, still bounded by the ONE
overall deadline; hidden_runtime routes negotiate's three checks through
it. infra/mcp_server.py: connect-probe orphan guard — `ensure_port_free`
now refuses when the role port ANSWERS (`OrphanPeerError`; never
trial-bind: on Windows two binds can both succeed) and
`await_listening` proves our daemon server actually listens after
start. shared/interlock.py (new): lecturer-address interlock — email to
the league fires only when `[email] counted = true` AND `--counted`
(peer/series-result/league_series) are BOTH armed; plus-aliases collapse
onto the base identity; `assert_sparring_posture` refuses a tuned or
email-armed sparring file at load. sdk/reporting.maybe_email records an
interlock refusal ON the report (rule 32: the outcome still surfaces);
sdk/series + cli surface it as `EMAIL REFUSED` + exit 1.
scripts/league_close.py (new) + league_series.py: send-posture email
preflight BEFORE window 1 (OAuth token endpoint only, zero games played
on refusal, exit 2) and auto-close — aggregate with `--email` only when
all num_games logs are visible across BOTH repos' results dirs
(read-only file access, never a cross-repo import), else name who is
missing and close nothing. peer/sealing.py: `_PENDING_CAP` ->
config-owned `[network] inbound_buffer_limit` (default 8, floor 4) and
the duplicate absorption upgraded to a structured evidence event
(`inbound_tolerated kind=... turn=... reason=...`, INFO). Workspace-side
`rival_shape_drill.sh` (NOT committed, workspace root): a sequential
single-address six-window opponent from our sparring config, both
runners full-dress against it. domain/, tests/vectors/, report/
untouched; everything mirrored to the twin.

**Tests.** Bystander wrong-window and role-equal: refused-on-record then
the REAL counterpart pairs; endless-bystander stream still deadline-
bounded; terms drift / bad signature / scent-lock mismatch stay
first-offense fatal and never classify as pairing. Port guard with real
sockets on ephemeral ports (orphan answers -> named refusal, no thread
started; late listener -> await succeeds; nothing listens -> loud fail).
Interlock truth table (config-half only / CLI-half only / both / friendly
/ plus-alias / config-extended list), through maybe_email and the
series-result CLI. Preflight (owes-nothing skip, empty recipient, dead
token -> zero games) and close (complete -> aggregation command with both
dirs + --email; gaps named, nothing run). Cap floor + narrowed-cap flood
+ the structured absorption event.

**Gates.** Full `uv run pytest` green: 619 (police) / 617 (thief);
coverage 93.16% / 93.12% (gate 85%); ruff 0 both; 150-code-line cap OK
both; physics parity OK (16 files) both.

**Lesson.** Classify before you punish: the FIRST message to arrive at a
shared address is often somebody else's — a wire that treats "wrong
game, not you" like "you cheated" hands technical losses to the honest
side. Tolerance must be typed (a named exception class), logged as
evidence, and bounded by the same deadline as silence — then it tightens
rule 6 instead of weakening it.

## 2026-07-25 — Session: documentation-fidelity pass — Part II catches up with the hidden-wire arc; PRD_09

**Context.** README Part II still described a single-wire architecture,
"PRDs 01-08" and pre-arc test counts; the reference-v3 client, the
cross-team evidence, the series machinery and the interlocks were
undocumented at README level, and the hidden wire had no mechanism PRD.
Docs-and-evidence session only: src/, tests/ and config/ untouched.

**Prompt pattern — verify-then-write, and let the tools veto the draft.**
Every claim was re-derived from the tree before it entered a doc, and two
draft claims died on contact with reality: (1) the pair verifier was
re-run on the two repos' RIVAL-game logs and correctly answered
CROSS-MISMATCH — they are two different physical games whose foreign
halves share no digest construction — so the README's pair-verify claim
was pointed at the committed twin logs of ONE game instead (g01
bookletter, g03 hidden: both `overall: Verified OK`, re-run now), with
the rival games carried by per-side `verify-log` (Verified OK re-run in
both repos) exactly as ch. 7 defines; (2) a replay screenshot of the
rival-game log is impossible BY DESIGN — the replay witness reconstructs
from both halves' payloads and a foreign half fails our pinned-field
`verify_commit` — so the mandatory-screenshot addition uses the committed
hidden-wire twin game g03 (`replay --log results/log_anrbj666-vs-anrbj666_g03.json
--screenshot assets/replay_hidden_verified.png`, green "Verified OK (70
sealed steps)") and the README says precisely which pairs the byte-level
cross-check is defined over.

**Build.** README: Part I gains the series/league command block; Part II
§2 gains the dual-wire bullet (the ch. 5-vs-Ωᵢ self-contradiction,
ADR-0006/0007/0008, each shape's registered handshake, the
wire_shape_sha256 lock), the drilled-hardening bullet (chaos + resume +
anti-stall + bystander tolerance + orphan guard + email interlocks) and
a "Cross-team verification" subsection (pair verifier with the exact
command, the rival-league warm-up + 47-47 six-sub-game rehearsal with
the discarded-series evidence paths, the rule-35 settlement guard); §4
gains the hidden replay witness PNG; §5 counts move to PRDs 01-09 / 619
tests / 93.16% branch coverage. Rival-team naming scrubbed from prose —
league ids stay only in artifact filenames, which are league data. NEW
docs/PRD_09_hidden_wire.md in the house per-mechanism format
(description & theory, I/O contracts, cadence/claims/reconstruction,
settlement, performance, alternatives, success criteria pointing at the
real tests + evidence). REQUIREMENTS_MATRIX: row 50 → PRD_01..09, rules
21-22 row now cites the structural claim flow. TODO: dated 2026-07-22..25
section + two ledger rows. Everything mirrored to the twin (PRD_09
byte-identical but for the repo's own drill timing).

**Gates.** Docs + one PNG per repo only; full `uv run pytest --cov -q`
green both repos: 619 (police) / 617 (thief), coverage 93.16% / 93.12%;
ruff surfaces untouched; parity-locked files untouched.

**Lesson.** Documentation is a claim generator, and claims rot faster
than code: the only README statements that survived this pass unedited
were the ones a committed command can regenerate. Write the command next
to the claim, and stale docs become a failing check instead of a
discovered embarrassment.

## 2026-07-26 — Session: perception counter-build — the trail is a clock, walls betray their placer, place talk parses

**Context.** A replayed-loss review of our own game logs turned into a
failure-mode inventory of the belief stack, and three of the four modes
were PERCEPTION bugs, not strategy bugs: (1) `observe_scent` multiplied by
RAW intensity, so a long camp's saturated 5×5 plateau kept out-shouting the
rival's live trail after it moved — the posterior locked onto a memory;
(2) barrier declarations were consumed only as blocked cells, throwing away
the law-of-barriers fact that a placement pins the placer to ≤5 cells;
(3) `parse_claim` understood direction words only, so place-name hints
("by the harbor") parsed to None and the hint channel went blind.

**Prompt pattern — decode the physics, then let evidence land where the
rival can BE, not where it WAS.** The fix that carries the session: under
the fixed book model every reading is some kernel deposit K_d decayed
×(1-ρ) per turn, so a value inverts to a REACH radius d+age — the Manhattan
ball the emitter must occupy NOW. Spreading each reading's weight over its
reach ball (ring hypotheses accepted fresh-only, to stop rung aliasing from
re-anchoring stale plateaus) turns the mandatory transmitted trail into a
live tracker: measured on an 8-step escape from a 9-turn camp, the peak
runs 3 cells behind the walker and clear of the camp, where raw-intensity
weighting sat 6 behind and still camp-anchored. TDD throughout: the tracker
property, the barrier-origin localization (>0.6 mass on the origin cells,
duplicate-declaration-safe on the reference wire) and the gazetteer tier
(unique-landmark-only, fractional bands for any grid, inbound parsing only
— rule 27 untouched) each landed red first.

**Build.** Paired domain commit: `domain/evidence.py` (new, parity-locked)
+ `belief.py` (observe_scent over reach evidence; observe_barrier;
observe_hint generalized to observe_region + region_is_lie). Peer commit:
both runtimes hand freshly declared walls into `Perception.observe`.
Strategy commit: `hints.py` landmark tier + `config/gazetteer.json`.
Arena commit: `AgedBeliefTrapCop` — belief-led early pounce + gain-gated
surgical walls, the calibrated hunting ceiling this belief stack enables,
rule-25-guarded. Everything twin-shape with the sibling.

**Gates.** 646 tests green, branch coverage 93.27% (≥85), ruff 0, 150-line
caps OK (the decode split into `domain/evidence.py` exists BECAUSE of the
cap), physics parity green both directions, README §5 counts regenerated.

**Lesson.** The scent model transmits a clock, and we had been reading it
as a heat map. When a mandatory channel seems weak, re-derive what it
actually encodes before adding strategy on top: one likelihood function
rewritten beat any amount of downstream cleverness built over the wrong
posterior — and the pinned mirror-test relaxation (argmax ±1 under clamp
saturation) documents exactly what the clamp makes unknowable, so nobody
"fixes" it back into false certainty later.

---

## Session: the plateau decode and the lethal gate (2026-07-26)

**Prompt (verbatim).** "do all babe, and then run all" — following a
measurement session that had produced a survival/capture split and a
proposal to patch two specific kill lines.

**Context.** Offline replay had produced a per-turn ground-truth harness:
our real, unmodified brains in a closed loop against faithful local replicas
of a strong rival stack. That harness is the whole method here — every
number below is an A/B on 150 games with only one thing changed.

**What the measurement said, and what it was worth.** Two failures, each
with a single root cause, and neither was where intuition pointed:

1. Our thief survived 0.900 with *zero active captures* — every loss was one
   repeated line, at the same turn number. Reading the trace rather than the
   aggregate showed the score tuple, not the tactics, was wrong: the
   trap forecast already flagged the fatal landing and was outranked by the
   flee term. A promotion in the ordering, not a new heuristic.
2. Our cop captured 0.147 and placed **0.00 barriers per game** across 150
   games. That number is the tell: a policy that never fires is not a policy
   that needs tuning. Its gate was conditioned on knowing where the thief
   was, and the posterior was 7% exact / 2.42 cells off.

**Lesson (the one worth keeping).** Both fixes were *upstream* of the code
that looked broken. The temptation was to search harder — deeper lookahead,
a herding policy, more arms. The area-denial herding arm was built and
measured, and produced outcomes byte-identical to the shipped brain: it
never fired, for exactly the same reason the barrier policy never fired.
What actually worked was re-deriving what the mandatory channel encodes:
under re-emission the update rule saturates every kernel offset whose fixed
point clears the clamp, so a dwelling rival stamps its own kernel window on
the board — and fitting that SHAPE back inverts to its cell. Localization
7% -> 89% exact; capture rate 0.147 -> 0.847, with the pursuit score
untouched. Twice in this project now, a channel that "wasn't strong enough"
was a channel we were decoding wrong.

**Build.** Paired domain commit (`evidence.plateau_origin` +
`BeliefMap.observe_plateau`, byte-identical in both repos, wired last in
`Perception.observe` because physics the rival emitted about itself outranks
anything it chose to say). Thief commit: `lethal_gate` in the doctrine
ordering, plus a module split (`doctrine_signals.py`) forced by the line
cap. Cop commit: the barrier gate lifted out of frozen constants into
`[strategy.trap]` and re-swept (2/3/4/5 → 3 wins outright).

**Gates.** Both suites green, ruff 0, 150-line caps OK, physics parity green
both directions, branch coverage 93%+ each repo. Every keep-gate written up
in `docs/evidence/` including the negative result.

---

## 2026-07-29 — full-rulebook compliance audit + enforcement-gap fixes

**Prompt.** "Go over my code and verify everything isn't evading the rules —
if there are problems or uncertainty, let me know", then per-item fix
directives over the findings list (fix 1-4/6/7-counted-only/11; keep 5;
defend 9-10 in writing).

**Method.** Appendix ה (55 rules) + Appendix ו extracted from the book PDF
with page cites, then five independent adversarial verification passes
(physics, crypto/audit/truth, separation/architecture, language/LLM/
deception, email/reporting/config) over BOTH repos' code, each returning
violations/uncertainties/clean with file:line evidence.

**Verdict.** No rule evasion, no disqualification-grade violation; physics
numerics match Appendix ו exactly (kernel byte-for-byte vs Figure 4); no
nonce leak anywhere; hint-lying confirmed book-legal (ch. 4.4/5.3.1/6.5.1)
and audit-honest in code. Enforcement gaps found and fixed this session:

- audit now cross-checks LIVE public declarations (barrier cell, capture
  claim, hint) against the sealed reveals, and binds records to the current
  sub-game (wire/audit.verify_declared; hidden_exchange records `declared`).
- verify-log names reduced assurance ("Verified OK (seals only - ...)")
  instead of silently passing when the config artifact or summary digest is
  missing; replay viewer tolerates foreign-schema rival halves.
- declared commit hash marks a dirty working tree (`<hash>-dirty`).
- rule-52 structural guard: counted-series ledger under results/local/
  refuses a second league-reported series against the same pairing.
- LLM taunts digit-scrubbed + prompt forbids coordinates (rule 27).
- ADR-0011 records the five defended book-interpretation readings.

**Gates.** Both suites green (coverage ~93.9% each), ruff 0, 150-line caps
OK (two module splits: report/code_identity.py, sdk/counted_ledger.py),
physics parity green both directions.

**Round 2 (2026-07-30).** Prompt: "anything else we can improve?" → the five
open bugs from the original audit, each with a user constraint: emergency
audit must never fire on a completed game (audit_sent flag set by the normal
finishers), counted delivery gates must leave training postures untouched
(every check keys off --counted arming), num_games=6 enforced at game start
on counted runs only (COUNTED_FIXED_TERMS, not the standard validator),
live rival-barrier quota, rule-32 funnel hardening (sdk/settlement.py
split). Gates green both repos; parity green on the domain commit.

## 2026-08-03 - Report-email cadence verified against the book + demo repo

**Prompt (friendly vs imreeyal).** "Does the prof ask for per-sub-game
email? How many JSONs does he want and do we have the exact format today?
Check his example repo." Then: "Keep only the result email, drop the
per-sub-game one, and make sure the artifact JSONs actually get committed
and pushed."

**Method.** Primary source first: re-read section 9.3-9.3.3 (pp. 71-79),
Appendix He rules 31-38/51-54, Appendix Vav Table 20 (p. 141); then diffed
the professor's DemoExamples sample-run JSONs against our emitted g01-g06
artifacts, and read his sdk/email_sender (one series email, result JSON,
no per-sub-game email anywhere).

**Outcome.** Per-sub-game email removed (sdk/reporting.maybe_email +
settlement call + tests reworked); the series email in
sdk/series.maybe_email_series is now the sole sender, still behind the
lecturer-address interlock. ADR-0009 addendum records the reading.
Runbook step 4/5 rewritten: no per-game email; commit AND push the four
artifacts per game. Friendly artifacts committed in both repos.

**Round 2 (same day).** Prompt: verify the two book boxes (lie detection
p. 30, scent-model lock p. 31), section 5.3.1, and the p. 40 commit-id
box. First three verified implemented; the p. 40 box exposed a gap - the
Step-0 handshake identity omitted github_commit (series report filled the
rival column with "unknown"). Fixed: identity_block now declares
git_commit_hash() (incl. -dirty marking) in both repos, with tests.

## 2026-08-03 (2) - Book-attached example conformance (Imree round)

**Prompt.** Imree letter: the course chatbot serves the book's own four
attached example artifacts; their field-by-field diff vs both teams'
chains. "Take a look, challenge if needed" then "start the fixes".

**Method.** Pulled the four files (docs/googleBotMissingFiles), verified
every claim byte-level before coding; challenged two (the two-sets
contradiction: repo sample-run vs book-attached; the negotiate commit
channel stays); flagged content quirks nobody should mirror (diagonal
moves, role confusion, self-contradicting filenames).

**Outcome.** Six fixes, both repos, gates green + parity: sealed
step_zero record with github_commit (hidden wire only) + typed-record
tolerance across crypto/reconstruct/pair-verify; role-aware commit
columns; three league fields in final_result; mutual_agreement trimmed
to {sha256, confirmed}; flat config artifact (back-compat reader);
real hardware values + provider-named llm_model.

**Round 3 (same day).** Prompt: "anything we are missing?" -> four gaps
closed: the rival step-zero READER (two-channel mismatch finding), the
book-attached declaration shape (report/declaration.py), ADR-0012
(two example sets: precedence + shape-vs-content standing rule, agreed
with imreeyal), and the counted game.json draft
(docs/drafts/game.counted.json, agreed_between anrbj666/imreeyal).

**Round 4 (same day, evening).** Moodle item 4 (grader instruction:
send the lecturer the 4 signed templates at game end) resolved as
superset - the one series email now attaches every instance of all
four template types, partial sets refused; imreeyal concurred and
mirrors. Their diff of our 16:00 window caught the counted-record
fabrication bug class (league fields in a friendly) - fixed keyed on
the counted arming, both teams. VRAM now real via the driver registry.

**Round 5 (same day, night).** The course chatbot, asked about the
email contents, ruled result-only (logs/configs referenced, never
attached - matching the reference implementation). Attachment policy
REVERTED to the result as the single attachment; Moodle item 4 re-read
as two-channel delivery (email + GitHub). ADR-0012 second addendum
carries the quotes; flip coordinated with imreeyal.

**Round 6 (same day, late night).** Imree signature finding resolved:
their repeated sha256 is the reference symmetric_outcome scope, NOT a
cached value - we reproduced 42f2a1ba independently from their body and
from ours (identical outcome patterns across the two windows). Adopted
the reference scope jointly for mutual_agreement (byte-identical across
peers, machine-checkable agreement); step-0 reader accepts both type
spellings (system_spec answered). ADR-0012 third addendum.

**Round 7 (2026-08-03, late).** imreeyal audited OUR repos back. Their
finding #1 CONFIRMED by repro and fixed (unclaimed landing capture no
longer self-destructs an honest audit - disputed evidence instead,
ADR-0011 addendum); #4 fixed (counted ledger now committed + all-dirs
reads); #3 fixed (SELF_GRADE.md + submission gate); #5 CHALLENGED with
receipts (min_center_intensity IS read - wire/terms.py:64, one of the
kit's signed flat-term keys; their own app_f_table documents it);
#2 (always-send on technical loss) held for JOINT shape alignment as
they requested. Small items: limiter thresholds to config, engine
docstring two-wire note, inbound hint view-cap (earlier round).

**Round 8 (2026-08-04).** COUNTED series vs imreeyal played and reported:
prep audit (repo sync, no-op constitution adoption, empty ledger, armed
interlock, preflight-proven mail rail, tunnel probes), arming commits as
the declared hashes, T=01:00 launch with --counted through the runner,
6-0 / 90-30, all audits clean, one league email, rule-52 ledger
committed both repos, posture de-armed after. Pre-counted rounds the
same night: bare-hash validation friendly (23:25), evidence
reorganization (dev-history + per-window friendlies as mini repo roots,
empty top level = counted lands as pure adds), rule-53 correction (no
manual email - the artifacts carry the commit id), counted_games_played
0->1 after reporting. Contributed the pairing experience upstream:
PR #20 on Imreec/copthief-league-protocol (PAIRING-PLAYBOOK lifecycle
doc, E2E + connection contracts, generated 14-artifact example bundle
passing their check_artifacts gate).

## 2026-08-08 — vibecode friendly post-mortem (Claude Fable session)

**Prompt (operator):** "take a look in the logs regarding the other 3 games, see if
they actually won 2 of them, see their own repo and see if you can improve so we can
beat them more"

**Outcome:** verified g01/g02/g03 audits + reconstructed both paths from the sealed
records; found our cop reached the rival thief's cell (step 11, g01+g03) but never
fired a capture claim (belief below the 0.10 gate), and found the rival's hint
template announces its literal move ("moving s") while our direction vocabulary only
knew full words. Fix: padded single-letter compass tokens in DIRECTION_WORDS
(TDD, both twins) + per-opponent claim-threshold overlay (private config, uncommitted).
Rival repo check confirmed their thief is argmax-deterministic and open-loop.

## 2026-08-08 (evening) — vibecode convergence day + COUNTED series #2 (Claude Fable session)

**Operator prompts (sequence):** verify rival artifact sets ("check theirs.
everything, fields, timestamp, sha256 and more"); converge the two hash
preimages; "make sure we beat them"; five scheduled friendlies (18:37, 19:12,
19:40, 21:12 + the aborted attempts); "prepare us to a counted game"; freeze
decision ("don't do those changes unless 100% certain — just play without
changing"); token re-mint; "arm it for a counted game"; counted T set to 22:14;
post-game bookkeeping and evidence layout ("counted_games dir per team",
"config/games separation", stale-doc sweep).

**Outcomes:** motion-echo belief tier + claim-gate rehearsals (earlier entry)
carried five friendly wins (75-35, 90-30, 85-45, 75-35, 70-50); protocol
converged to zero-delta artifact diffs both directions (mutual_agreement
byte-identical, step-0 sealed AND on the wire both ways, whole-file
config_sha256 adopted from our game.json, series-span declarations); COUNTED
series #2 filed — 75-35, 5-1, league report 19fe2cdf49a26b0d, counters
{anrbj666: 2, vibecode: 1}, diversity flag to the winner; counters bumped,
friendly posture restored, permanent evidence archive created
(docs/evidence/counted_games/), README league record with commit links.

## 2026-08-10 (evening) — nis-yar1 debugging marathon + two 6-0 friendlies (Claude Fable session)

**Operator prompts (sequence):** launch-on-green vs nis-yar1's "fix pushed"
claim (probe list_tools, launch friendly six); "what is the game status
right now? if it failed again, send a detailed report explaining how to fix
it"; evidence-based rival debugging across four failure generations
("go over the logs, see everything makes sense", "check, and report, and
write a detailed message to them", "give me a markdown detailing how to fix
it on their side... explain in details the flow, the setup and all. give
examples"); scheduled friendlies at 19:46 -> "do 7:50 instead" -> 19:52 ->
20:05 -> 20:12 -> "it didn't open for them, do 20:16" (first settled series,
6-0); post-series checklist ("what's left to check regarding the reports and
jsons"); artifact cross-verification ("check his stuff: <zip>", "check ...
aligned ... the latest", "check ... aligned_v2"); "we should tell them what
to fix and give example of how it should be, no?"; rehearsal proposal ("one
more friendly, send to our own mail, validate the jsons, then counted");
T=21:16 -> launch 21:18 (rehearsal, 6-0); report-email format guide for the
rival ("their format is not ok, explain... json schema and values... even
let him copy our title"); their emailed report challenged ("validate it,
challenge it") — mutual_agreement.sha256 exposed as a pasted config-lock
prefix, correct value derived from THEIR OWN rows; "also recompute the
sha256, make sure its correct" (triple verification); bookkeeping pass.

**Outcomes:** four rival-side infrastructure generations diagnosed from our
wire evidence alone (proxy ACK-without-response framing; restricted-shell
egress block proven by a 0->2 tunnel-counter control experiment while their
endpoints returned 200s; crash-on-first-inbound-contact on BOTH their peers;
scent_model_sha256 mismatch refused by the both-declare rule in 6s/window)
— each with a written root-cause report to the rival; first settled series
vs nis-yar1 20:16 (90-30, 6-0, report 19fecaf5c92fd4d5) and dress rehearsal
21:18 (90-30, 6-0, report 19fece82ee5cdbd4); thief banked 6/6 35-turn
survivals — live debut of observe_claimed_cell + SHARP_BELIEF trap-forecast
gate vs the sealer cop that beat the pre-fix thief; artifact bundles
exchanged + cross-verified both directions (their v2 aggregation bug and
pasted mutual-agreement hash caught with reproducible-preimage analysis;
their consensus signature verified honest); mutual_agreement 7f688ab0...
independently recomputed by both teams; end-state digest recipe agreed for
the counted game; evidence archived (friendlies-nisyar1/ + burned-attempts
root-cause READMEs); email token re-minted to all three locations after the
7-day expiry (peers read repo-root token.json — runbook note).

## 2026-08-11 (afternoon-night) — the arms race day: losses, forensics, counter-build (Claude Fable session)

**Operator prompts (sequence):** friendlies at 14:27->14:29 (won 4-2), 15:23->15:25
(lost 1-5 after their same-day rebuild), 16:26/16:28 (burned: our port squatter),
17:15 (lost 1-5); "check the logs afterward... make sure it makes sense"; "can we
improve the cop window a bit more? I want to bully him"; "check why g2 failed! btw
I got their logs including g1"; "I think their hint is not ok... check what the
book says"; "what they are doing is legal? ... are they doing something not legal?"
(twice, answered with evidence both times); "check our old logs versus theirs";
"check the book, I think it's not ok to do those moves" (barrier legality —
resolved from the rulebook text); "we shouldn't wander there... we shouldn't
report the direction we go... prepare for counted game"; "keep the moves as
well, don't delete as you did — maybe the monitor should get those" (tape
vault + keeper born); "keep true on friendlies, and in the real game give the
same type of hints as they do"; "go over my code and improve it... Imree played
against them, check his repos" (collaborator access); "in friendlies do a dumb
brain... a lot of tricks"; "decoy of both, and a decoy that helps us learn — go
to specific locations to see how theirs behave... so we can learn from the
logs"; "check what they did in the game against imree"; "I need to see each
move of my cop/thief"; "if they tuned it versus us, we might want to change
the logic — think about it in more detail" (red-team pass).

**Outcomes:** interception cop (strategy/intercept.py — meet the runner, never
follow; their best recorded escape, which beat imreeyal's cop for 35 turns,
caught 8/8 at 16); room-first thief (imprisonment-is-capture scoring; their
13-turn seal broken, adaptive herder mimic 30/30); trail-head pin via the
transition-law emitter, then RED-TEAMED and physics-gated (claim-spam decoys
took the ungated pin 15/15->0/15; claims now pin only in emitter agreement,
emitter defers to truth-duty walls; zigzag anti-interception measured
self-defeating 15/15 caught); opaque hint mode both roles (distinct taunt
voices, overlay-gated — friendlies stay candid); decoy brains (yesterday's
shapes) + probe brains (waypoint tours / bearing stalks) overlay-selected;
rival trail telemetry in the live wire; forensics cleared nis-yar1 of every
suspicion raised (moves, barriers p.21-22, hints/intent flags, scent law,
their-logs-vs-ours 129 steps zero mismatch, per-opponent wire personalities
documented from the imreeyal jsonl); tape vault + keeper (append-only,
5-second sweep) after one tape was lost to a cleanup; GUI passthrough
(LEAGUE_GUI=1) for live local-truth viewing; imreeyal intel: their counted
6-0 pre-dates the rebuild that now beats them 4-2.


## 2026-08-17 (night) — uoh-sqak marathon: two 6-0 friendlies + COUNTED series #3 (Claude Fable session)

**Prompts:** "see the last chat we did, we are playing now against salah again"
+ their bind message (slot 22:20, single URL both roles, inverted parity — our
thief opens s1); "we shouldn't play with our real brain against them in
friendly, no?" (posture debate: real brains kept as a deliberate validation
slot); "keep the moves… we need the report of their moves" (series moves
report v2 — their wire shape reveals in payload.state.pos, lag-aligned
telemetry scoring); "check his repos" (intel review: ApexCop's only
conversion path needs edge+gap<=4+belief>=0.5, EvaderBrain corner-dives on a
defaulted w_reach, hints unparsed bluff_weight=0, email disabled); "is their
report ok or not" (settlement forensics x3: byte-agreed 46dfb429 every time —
identical outcomes sign identical bytes, the 5-key scope excluding
timestamps); "ask them if its ok to play the counted today"; "prepare
yourself to counted against salah"; "launch".

**Outcomes:** three 90-30 sweeps in one evening (friendlies #2-#3, then
COUNTED #3 — diversity reward earned on the first counted meeting);
LEAGUE_PARITY_FLIP runner override for role-inverted pairings; counted email
interlock exercised end-to-end (league address armed config+CLI, report
1a0115fdd83f0f4c filed to rmisegal+uoh26finalgame); cross-team interop
hardened in-flight — our step_zero/system_spec dual-read guided their reader
fix (e3d4d51), our per-row role-aware commit finding guided their aggregator
fix (ebb329b, independently confirmed on their side within the hour); first
fully complete filed artifact pair (both commit columns populated per window,
their sealed revision fetchable and byte-verified against play); their prose
counter slip ("yours 3 going in, filing as 4") caught pre-settlement, filed
correctly as {3,3}; evidence archived under docs/evidence/counted_games/uoh-sqak/.

## 2026-08-20 evening — the best2934 endgame (counted #4)

Operator-driven session, agent prompts logged in substance: (1) "make sure we
are ready against best2934 code wise" — full Salah-era config audit caught the
stale constitution minutes before T; (2) root-causing twelve TAMPERED windows:
recompute their published artifacts under every registered commit construction
(19/19 merged vs 0/19 pipe), then pin their step-0 seal to the exact call
sites (both of them, one fix apart); (3) "does it really sit on their side and
we don't drift?" — four-way no-drift proof (own records 35/35, their bytes
19/19 under merged, four passing rivals, their diff not touching the file);
(4) declared-form verifier shipped on our side (verify under the rival's
declared construction; refusals name the failed record and expected form);
(5) counted end-to-end: operator word transcribed, T slid once when their
readiness comment was late, joint pre-arm check (real loadout, interlock,
clean trees), 90-30 6-0 + diversity, digests matched digit-for-digit,
filings cross-forwarded; (6) docs: OPPONENT_ONBOARDING.md (kit co-authorship
+ conformance checklist), README/TODO brought current. Kit thread:
https://github.com/Imreec/copthief-league-protocol/issues/49

## 2026-08-22 afternoon - the token-truth fix (najamjad report diff)

Operator prompt: "lets fix the token bug. and then I'll send the message."
Agent prompts in substance: (1) locate every token-accounting site - the
series reader took peer tokens from the negotiate identity (a field that
never existed there) and coerced the miss to 0, filing najamjad's truthful
27,866 as zero; (2) decode their wire semantics from today's six logs:
step-zero tokens_total is CUMULATIVE usage at window start per role
process - the four checkable chain deltas (5010/4273/5073/4163) reproduce
their emailed per-window claims digit-for-digit; (3) TDD report/peer_tokens
- next same-role snapshot minus this one's, chain tails and gaps file null
(never a fabricated number), series total only when every window is known;
(4) declare our own side symmetrically - the step-zero seal and the window
summary now carry the real talk-meter total (we never declared; they filed
our 0 by assumption); (5) chasing a full-suite-only test failure landed on
a REAL latent bug unrelated to tokens: the endgame solver's 150ms
wall-clock cap starves under coverage tracing (seed-0 tape converting at
34 instead of 21) - the nisyar1 rehearsal now pins the cap out so only the
node budget bounds it, proven stash-independent before the pin. Paired-port
to the sibling in the same session.

## 2026-08-22 evening - imreeyal strategy study + counted hardening

Operator prompts: "see if we can use some strategy imree did to improve
our cop and thief" (owner permission for both private repos); "add all
you think we need... make sure it all absolutely works. so we will not
lose on stupid manner." Agent work in substance: (1) full teardown of the
champion's cop+thief decision layers (their code credits OUR doctrine as
"studied, no code copied" - convention returned); (2) triage vs our own
loadout: their fresh-peak decode ~= our law-solved emitter pin, their
room-first thief ~= our doctrine (skip both); adopt three: floored-
residue tolerance (closes the najamjad-floor latch hazard - validated on
the day's sealed frames: 4 refusals -> 4 floored-notes, 0 refusals),
safe-region compression term (tape sweep positive on runners but percher mimics 0/10 under it - kept DEFAULT OFF, per-pairing option only; the drill matrix vetoed the sweep), barrier reserve=2 (the endgame seal stays affordable); (3) ADR-
0013 records adoption + attribution; knobs default off in code, armed in
game.toml beside the sweep evidence.
