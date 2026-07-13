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
