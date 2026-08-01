# Cross-team series rehearsal vs imreeyal — 2026-08-01 (uncounted)

Six-window series under the real league-day machinery (both repos'
`league_series.py` runners, T-protocol, tempo waits, settlement guard,
aggregation + one series email). This repo drove the ODD windows (s1/s3/s5,
our cop vs their thief); the twin drove s2/s4/s6.

Artifacts promoted here by hand (`report/archive.py` header: evidence worth
keeping is a decision, not a side effect) — the aggregation path in
`results/` gets swept before the next series.

| | |
|---|---|
| Reported score | imreeyal 60 — anrbj666 40 |
| **Corrected score** | **anrbj666 85 — imreeyal 45** (see below) |
| Audits | 6/6 `Verified OK`, both `info_mode_sha256` declarations matched at every handshake |
| Scent refusals | 0 (the concede exemption held against their advancing final) |
| Email | per-game + series reports, warm-up recipients only |

## The rule-47 finding (s1, s3, s5 — identical in all three)

Our cop walled **(5,6)** at its step 11 and **(6,5)** at step 12 while their
thief sat at **(6,6)** — the SE corner, whose only two on-board neighbours are
exactly those cells. Rule 47: captured at step 12. Their thief played **23
more steps** and claimed survival.

Both implementations define it the same way — ours `board.is_surrounded`
(all four orthogonal neighbours impassable, off-board included), theirs
`copthief_core/domain/rules.py:53` ("every orthogonal escape blocked, barrier
or board edge"). Their cop consumes the predicate inside its search; their
thief never runs it on itself. Their own sealed states carry
`self=[6,6]; barriers=[[5,6],[6,5]]`.

**Our half of the failure**: under hidden information the cop cannot see that
its wall sealed the thief — a barrier capture is only ever self-declared by
the sealed side. The reveal settles it, and our audit was not looking:
reference-schema payloads skip the strict reconstruction and degraded to
hash + continuity + movement checks. Fixed in `cff211d`
(`audit_foreign.unconceded_capture` → `disputed_capture` evidence block:
evidence for the logs to settle, never a unilateral outcome rewrite).

**Tactical consequence** (`8ac5b45`): a barrier capture depends on the
rival's own check; a LANDING capture is claim-mediated and enforceable. The
cop now steps onto a believed cell when it can — except inside
`landing_deadline_turns`, where an unrecoverable miss costs more than the
wall does.

## Other findings

- **Their thief is deterministic** — move-for-move identical across all three
  games: (3,3) → E,E,S,S,S,E to the corner by turn 6, then STAY for 27 turns.
- **Our cop was deterministic too** (identical in s1/s3/s5) — a replay-scouting
  rival can exploit that; per-window seeds are the fix.
- **Their hints were honest** in all 186 payloads (`intent: "truth"`), and
  their landmark vocabulary decodes their true zone.
- s2 (their win, 13 turns) is the model of a claim-mediated kill: herd, cut
  the column exit, seal the gates, force the honest concession.
