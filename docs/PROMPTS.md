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
