# ADR-0009 — The official match report is the four-artifact set (no Hebrew-keyed fifth report)

Date: 2026-07-25. Status: accepted. Scope: both repos (mirrored twins).

## Context

Book-fidelity review of the report layer. The course reference kit still
ships `report/report_writer.py`, whose docstring calls its output "the
official Hebrew JSON match report" and says "Schema follows the game
book (section 8)" — a per-match report with Hebrew keys (סוג_דוח,
תפקיד_מדווח, לוג_צעדים_מאומת, חתימת_קונסנזוס_משותפת, ...) that our
repos never emit. If the book mandated that schema, our four-artifact
layer would hide a graded gap; if it did not, adopting it would drift
from the book's canonical file vocabulary. Per our method (primary
source first), we re-read the full reporting surface before touching
code: ch. 8 (pp. 61-68), ch. 9 (pp. 69-81), Appendix ה (pp. 126-134),
Appendix ו (pp. 135-143).

## Findings (rulebook v3.0.0, printed page numbers)

- p. iv (הבהרה): the default is NON-binding — "ברירת המחדל היא שאין
  כלל מחייב, אלא אם נכתב במפורש שהוא כלל מחייב"; examples and code
  snippets illustrate. Appendix ו is the sole quantitative truth.
- §9.3 (p. 71, חובה box): at the end of every counted game both agents
  auto-send the end report to [כתובת דיווחי הסוכן].
- §9.3.3 "מבנה הדיווח: JSON חתום ומחייב" (p. 78): the report is a
  uniform, signed, machine-readable JSON attachment; both teams must
  agree on the result and EACH sends its own separate report, else that
  side takes 0 for the game. The format itself is delegated to attached
  examples: "למעשה מצורפים לספר ארבעה קובצי JSON לדוגמה ... שם-המשתנה
  של כל אחד מהם מוגדר בטבלת המשתנים שבנספח ו".
- p. 79, the only field-level mandate on report content: "השדות
  המחייבים בדוח כוללים את קישורי ה-GitHub של שתי הקבוצות, את מזהה
  הקומיט של כל משחקון (פרק 5), ואת סך הטוקנים שנצרכו"; plus the
  iron-rules box: structured machine-readable JSON attachment only —
  plaintext reports are rejected. p. 80 box: the end-of-game JSON shows
  all four repo links (two per team).
- Appendix ה rules 32-36 (p. 131), 51 (p. 133), 53-54 (p. 134):
  automatic Gmail reporting, standard JSON structure, no plaintext,
  agreed result + two separate reports after the mutual log audit, sent
  to [כתובת דיווחי הסוכן], commit hash declared per game, token totals
  in the final JSON. None of the 55 rules names report fields.
- Appendix ו §3, Table 20 (p. 141) — the complete attached-file set:
  `declaration_<game_id>.json`, `config_<game_id>_g<NN>.json`,
  `log_<game_id>_g<NN>.json`, `result_<game_id>.json` — "ואלה השמות
  שבהם משתמש הספר בכל מקום", derived from game_id and <NN>. Exactly
  four files. The book defines no fifth per-sub-game report anywhere,
  and no Hebrew key schema anywhere.
- Ch. 8 (pp. 61-68) — the reference docstring's "section 8" — is agent
  architecture (orchestrator, state machine, watchdog, deadline
  tracker). It contains no report schema in book v3.0.0; that docstring
  citation is stale.
- The reference kit itself has moved on: its four-artifact builders
  cite "book Appendix F", its canonical sample run emits the four files
  with English snake_case keys end to end, and its sdk retains
  `build_report` only under the comment "legacy Hebrew log
  (back-compat)", written to `{role}_match.json` — the ch. 7
  replay-viewer input (p. 56), not a league report.

## Decision

Build no Hebrew per-sub-game report. The official match report IS the
four-artifact set plus the emailed result JSON, and that layer already
exists here: `domain/game_ids.py` derives the four Table-20 filenames
byte-exact; `sdk/reporting.py` (emit_artifacts) writes
declaration/config/log/result at every settlement;
`report/series_doc.py` builds the series result the email carries. The
pp. 79-80 mandatory content is covered: the series result carries both
teams' identity blocks with all four GitHub repo links and both sides'
MCP addresses, per-sub-game `github_commit` (ours from git, theirs from
the negotiated identity; rules 24/49/53), `tokens_total` per sub-game
and per series (rule 54), scores, the config/scent seals, and the
sign-then-insert `consensus_signature` (ADR-0004). Where the reference
and the book diverge, the book + Appendix ו win (workspace iron rule 9)
— the Hebrew-keyed report is reference-legacy illustration, not book
canon.

## Consequences

- No fifth filename beside the four canonical names — nothing for a
  counterparty or grader to mistake for book vocabulary.
- Hebrew stays where the book puts it: in free-language VALUES (hints,
  dialogue), preserved native by `ensure_ascii=False`. Interop with a
  counterparty that DOES emit Hebrew-keyed report bodies stays proven:
  `tests/vectors/foreign/report_consensus.json` locks our consensus
  signature over Hebrew keys byte-exact.
- If a future book revision or league instruction publishes a binding
  field-by-field report schema, it lands in `report/` (outside the
  parity-locked `domain/`) beside the four builders; until then a
  Hebrew-report module would be unfalsifiable guesswork against a
  schema the book never states.

## Addendum (2026-08-03) — one report email, at series close only

Re-verification for the imreeyal friendly settled the email cadence: the
book mandates exactly ONE report email per game (= the series) — §9.3.3
p. 79 names the result file "הדוח המחייב הנשלח בדוא"ל", rule 32's "תוצאות
המשחק" uses the book's series-level vocabulary (Table 18: a משחק holds 6
משחקונים), and the reference kit's own `run_peer` sends a single
series-result email. Our per-sub-game email (sdk/reporting.maybe_email)
was an extra beyond the book; it is now REMOVED — sub-game settlement
writes artifacts only, and `sdk/series.maybe_email_series` remains the
sole sender (rule 34 kept: the report rides as an attached JSON file,
where the reference sends body-text only — the book wins). The four
artifacts must reach GitHub instead: commit + push per game (App ו §2
rules 4-5, runbook "Per counted game" step 5).
