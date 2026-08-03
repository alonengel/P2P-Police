# ADR-0012 — Two course example sets: precedence and the shape-vs-content rule

Date: 2026-08-03. Status: accepted (jointly with counterparty imreeyal —
their record carries the same rule verbatim). Scope: both repos.

## Context

The course ships TWO different example-artifact sets, discovered when the
counterparty pulled the book's attached examples from the course chatbot
and both teams diffed their chains against them:

- **Repo set** — the professor repo's `docs/sample-run` (the reference
  implementation's own emissions; our workspace copy under
  `../docs/DemoExamples`). Its step-0 record is `type: "system_spec"`
  carrying hardware + model + `code_version` and NO `github_commit`; its
  result carries no league-standings fields; its commit columns read
  "unknown".
- **Book-attached set** — the four files §9.3.3 references as attached to
  the book (workspace copy: `../docs/googleBotMissingFiles`). Step-0 is
  `type: "step_zero"` carrying `github_commit` (varying per sub-game);
  the result carries `games_played_including_this`,
  `first_meeting_between_groups`, `diversity_reward_applied`; the
  declaration is symmetric `group_1`/`group_2` with game times.

The sets contradict each other, and the book-attached set also contradicts
ITSELF and the book: its log contains diagonal moves (`MOVE:NE`/`NW` —
illegal under the movement table), a cop-role summary wrapping thief-role
prompts, `steps: 4` over 3 records, a `config_name` that contradicts its
own `links` block, legacy `police_match_*` log_files names, and a
`declaration_ref` naming the book's generic filename instead of the
Table-20 name.

## Decision (the standing rule, agreed with imreeyal)

1. **Between the sets: the book-attached set wins** — it is the one the
   book text references ("מצורפים לספר"), so it defines the KEY SETS.
2. **Shape vs content: key sets from the attached examples; values,
   counts and filenames from the book + Appendix ו** (workspace iron rule
   9 unchanged: on any example-vs-book conflict the book wins). Concretely:
   filenames stay Table-20 everywhere (incl. `declaration_ref` values),
   moves stay orthogonal, full 40-char commit hashes are kept where the
   example abbreviates to 7 (`-dirty` marking preserved).
3. **Superset stays legal**: our additive evidence fields (consensus
   seal, `hardware_spec_sha256`, `counted_games_played` per group,
   `report_type`) ride alongside the example key sets.
4. **Two commit channels by construction**: the sealed step-zero record
   AND the negotiate identity both declare the commit id; either side's
   mismatch between its own two channels is a recorded finding
   (`step_zero_mismatch` on the report). The series report prefers the
   SEALED copy for the rival's column.
5. **Documented divergences, not chased** (both teams): signature format
   (per-team; ours `sha256:` over the canonical group block), the repo
   set's `system_spec` step-0 naming, the example's legacy log_files
   values.

## Consequences

- Implemented 2026-08-03 across both repos: `step_zero` sealed record +
  reader, role-aware commit columns, the three league fields, result
  `mutual_agreement` = `{sha256, confirmed}`, flat config artifact
  (back-compat reader for pre-flatten artifacts), book-attached
  declaration shape (`report/declaration.py`), truthful hardware/llm
  declarations.
- The g01–g06 friendly artifacts predate these shapes and stay as
  committed history; the next uncounted window validates the new chain
  live before the counted game.
