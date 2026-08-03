# Development-history evidence (pre-league)

Relics of the build, moved out of the grader-facing results/ top level:
self-play scaffold series (anrbj666-vs-anrbj666, the mirrored-twin dev
loop), an early session before the peer declared a group id
(anrbj666-vs-unknown), and one-off E2E / tunnel / watchdog drill dumps.
All are real runs kept as honest history; none belong to the cross-team
series evidence, whose files are keyed by game_id and never mix with
these (Table 20 remark).

Laid out as a mini repo root (results/ + config/games/) so verify-log
still finds each archived log's config artifact and the crypto+physics
audit passes against the archive unchanged:
uv run p2p-XXX verify-log --log results/dev-history/results/log_anrbj666-vs-anrbj666_g01.json
