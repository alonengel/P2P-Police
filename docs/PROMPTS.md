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
