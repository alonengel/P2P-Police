# Uncounted rehearsal series vs imreeyal (2026-07-26)

The full six-sub-game rehearsal that preceded the counted series: the
first two captures ever recorded between the two implementations, and
the postmortem that drove the doctrine rebuild. Real evidence, kept.

**Why it lives here and not in `results/`.** `sdk/series.collect_logs`
votes on a consensus `game_uid` across every `results/log_<game_id>_g*.json`
and refuses on a tie. These logs carry the pre-fix uid
(`2f0c25a9-...`, derived from the raw config rather than the flat
negotiated terms - see ADR-0010), so beside a counted series' logs they
would either deadlock the settlement or win the vote outright. Moved,
never regenerated: rewriting them under the corrected derivation would
be fabricating a record of a game that was played the other way.

Files: `.game_uid_anrbj666-vs-imreeyal`, `config_anrbj666-vs-imreeyal_g01.json`, `config_anrbj666-vs-imreeyal_g03.json`, `config_anrbj666-vs-imreeyal_g05.json`, `declaration_anrbj666-vs-imreeyal.json`, `log_anrbj666-vs-imreeyal_g01.json`, `log_anrbj666-vs-imreeyal_g03.json`, `log_anrbj666-vs-imreeyal_g05.json`, `result_anrbj666-vs-imreeyal.json`
