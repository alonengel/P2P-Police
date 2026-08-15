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

## Addendum (2026-08-03, evening) — the Moodle item-4 instruction

The final-project Moodle page (the grader's own instructions, item 4)
says: "לספר זה מצורפים 4 תבניות של קובצי JSON שאותם הסוכן צריך לשלוח
למרצה בסיום המשחק שהם חתומים ומוסכמים על 2 הקבוצות" — send the lecturer
all four attached templates at game end. The book mandates emailing ONE
file (§9.3.3: the result is "הדוח המחייב הנשלח בדוא\"ל"; the p. 80 box
speaks of the email's attachment in the singular) and homes the other
three in GitHub (App ו §2 rule 4, §9.4). This is NOT a book-vs-example
conflict (the standing rule above does not apply): it is the grader's
assignment instruction — the channel the book itself arrives through —
and it extends, not contradicts.

**Resolution (superset, agreed with imreeyal):** the ONE series email
attaches all four template TYPES, every instance — declaration (1),
config g01..gNN, log g01..gNN, result (1); the result stays the report
and the body, so the book's mandate is untouched. "4 תבניות" reads as
four TYPES: the book's own Table-20 `g<NN>` naming makes configs and
logs per-window, and the attached 4-final-result references per-window
logs and commits. A partial evidence set is named and refused, never
sent (sdk/series_email.py).

**Same-day pair finding (both teams, same bug class):** the league
standings fields asserted counted-game facts in an UNCOUNTED friendly
(count bump + diversity reward). Fixed: `games_played_including_this`
bumps and `diversity_reward_applied` fires only when the series is
doubly ARMED as counted; a friendly passes the declared counts through
unbumped, reward all-false. `first_meeting_between_groups` stays
factual either way.

## Second addendum (2026-08-03, night) — attachment policy REVERTED to result-only

The superset above was implemented, mirrored by imreeyal, and proven
live (14 attachments, message 19fc816a25fac67a). It is now REVERTED to
the result as the single attachment, on new evidence about the author's
intent — the course's official chatbot (grounded in the book + the
reference repo), asked directly, answered:

> "In the emails sent by the system, only the final summary result
> report (result JSON) is included. The system does not attach the logs
> or configurations for each individual sub-game to the email."
> … "the final result report condenses the per-sub-game logs into an
> aggregate outcome … Rather than embedding the full contents of the
> logs or configurations, the final report simply includes references
> to them" (log_files, links). "While these files are essential for the
> Replay Viewer … they are not attached to the final automated email."

That matches the reference implementation (emit_series returns only the
result for emailing) and the book's design (the result REFERENCES the
other files). Moodle item 4 is accordingly read as loose prose meaning
the four templates are delivered across BOTH channels: the result by
email, the declaration + configs + logs via GitHub (§9.4 + App ו §2
rules 4-5 — committed and pushed per game, which we do). Precision
note: the bot's phrase "a single attached JSON file" paraphrases the
book's "מבנה JSON אחיד ומחייב" — אחיד means UNIFORM, not single; the
book itself never bounds the attachment count in either direction
(full audit: every exclusive word in the reporting surface targets the
address, the format, the per-side duty, or the OAuth scope).

Coordinated with imreeyal so both teams flip together; a forum
confirmation question to the lecturer remains the recommended closer,
and flipping back is a ten-minute change if he answers "all four".

## Third addendum (2026-08-03, late night) — mutual_agreement: the reference symmetric scope, jointly

Cross-diff of the 19:35 mails found imreeyal's `mutual_agreement.sha256`
IDENTICAL across two different windows. Investigated to the end: their
scope is the reference's `symmetric_outcome` VERBATIM (emit.py: "hash
only the symmetric outcome … never per-peer tokens or wall-clock
timestamps") — {game_id, aggregate, rows trimmed to number/roles/
result/winner/score}, sort_keys + spaced separators. We reproduced
their production value (42f2a1ba…) independently from their body AND
from OUR body — the two windows' outcome patterns were identical, so
the collision was legitimate, and the cross-side hashes are
byte-identical by construction.

ADOPTED on both sides for the counted series, replacing our
whole-body-minus-agreement signature: a field named mutual_agreement
carrying two permanently different per-side values (ours could never
equal theirs — it signed our own timestamps and token counts) is the
one shape a grader's diff can misread as "דיווח סותר" (rule 35). Under
the reference scope both teams' files carry THE SAME hash — the only
machine-checkable form of agreement. What the narrow scope omits stays
covered elsewhere: commits and repo links are plain fields diffed both
ways in both files; moves are bound by the commit-reveal chain the
audit re-proves; the uid identifies the series in every artifact.
A jointly-registered ENRICHED preimage (uid + commit columns) is
agreed as a post-counted upgrade, never a change the week of the game.

Step-0 `type` answered: theirs is `system_spec` (repo-set spelling);
ours stays `step_zero` (book-attached, the standing rule's canonical).
Both readers accept both spellings; recorded as a documented
divergence, invited to converge post-counted.

### Provenance note on 42f2a1ba… (2026-08-14, after kit PR #55)

Imree could not find `42f2a1ba…` in their tree while independently
verifying the kit's §6 scope drift (our report; fixed in kit PR #55).
Expected: that value is MAIL-BORNE — the 2026-08-03 19:35
validation-window mail bodies, where it appeared identically in both
windows because their outcome patterns were identical. It was never a
tree artifact on either side. The counted series' value (`0bcf3c07…`)
differs because the outcome pattern differs — the hash moving with the
outcome is the consensus-not-cache property this addendum verified.
Both values reproduce under the same 5-key reference scope.
