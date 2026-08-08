# config/games/ — per-sub-game config artifacts (Table 20, kind 2)

**Top level: COUNTED series only.** One config artifact per counted sub-game,
per pairing (rule 52 allows one counted series per rival) — currently the
imreeyal and vibecode counted sets, the exact signed constitution each window
played under (`config_sha256` locks it). These pair with the logs/results in
`results/` and the immutable archives in `docs/evidence/counted_games/`.

**`friendlies/`: uncounted sets, kept as evidence.** Warm-up and friendly
series configs move here after their series settles — no counter moved, no
league report, nothing in the rule-52 ledger. Same schema, different stakes.

Housekeeping rule: the runner writes every new series' configs to the top
level; after an UNCOUNTED series is settled and its evidence committed, move
its configs into `friendlies/` so the top level keeps meaning "counted".
