# Review process — how a change earns its way into main

Every change walks the same pipeline; nothing merges on trust.

1. **Authoring** — AI-assisted (Claude Code) under human direction; TDD
   red-green-refactor; one concern per conventional commit.
2. **Automated gates** (pre-commit + CI, all blocking): ruff zero-violations,
   pytest with coverage >=85% branch, the 150-code-line file cap, twin-repo
   physics parity, gitleaks secret scan, and the rule-guard suite
   (tests/unit/test_rule_guards.py - five disqualification-class book rules
   enforced as invariants).
3. **Subagent review** (.claude/agents, committed): `code-reviewer` (harsh,
   before stage-end commits), `spec-auditor` (the 55 rules, at stage ends),
   `guidelines-auditor` (submission rubric, before milestones/tags),
   `test-designer` (red phase), `physics-parity` (after domain/ changes).
   Findings are VERIFIED against the primary sources, not obeyed - the
   rulebook + Appendix VI outrank any reviewer, human or model.
4. **Human adjudication** — every league-facing decision (interop byte-forms,
   wire shape, scent lock, outbound messages, gitignore changes, anything
   irreversible) is approved by a human BEFORE it executes; experiment
   promotions go through gates coded before the results exist (see the four
   rejected promotions in results/experiments/).
5. **Evidence** — substantive claims land with a regenerable artifact
   (results/experiments/*.json) and, for milestones, a narrative in
   docs/evidence/ (setup / provenance / observed / what-it-does-NOT-prove).

Cross-team review: our protocol contributions were reviewed by a rival team
and vice versa (interop kit issues #1/#6); their claims were independently
re-verified here before we cited them - the same standard both directions.
