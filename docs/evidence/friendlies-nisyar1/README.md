# nis-yar1 friendlies — 2026-08-10 (uncounted, fully cross-verified)

Two settled 6/6 friendly series against `nis-yar1` (Nissim Deri, Yarden
Tziar; qwen3:14b hints, ngrok static-domain path-split transport), both swept
**6–0, 90–30** by anrbj666. FRIENDLY posture throughout: reports emailed to
the two team inboxes only, never the lecturer; no rule-52 counter moved.

| Series | T (IL) | Seed base | Per-game | Report email |
|--------|--------|-----------|----------|--------------|
| `20260810-2016-first-series/` | 20:16 | 3830 | captures in 8 (g01/g03/g05), survivals 35 (g02/g04/g06) | `19fecaf5c92fd4d5` |
| `20260810-2118-rehearsal/` | 21:18 | 3840 | captures in 12, survivals 35 | `19fece82ee5cdbd4` |
| `20260811-1429-third-friendly/` | 2026-08-11 14:29 | 3860 | captures g01 (10t), their thief survived g03/g05; our thief 3x35t. 4-2, 60-40 | `19ff09bbc2e6eb0b` |
| `20260811-1525-fourth-friendly-unsettled/` | 2026-08-11 15:25 | 3870 | their same-day rebuild: quiet sealer caught our thief 13t (g02/g04); g05/g06 technical (their transport) | none (unsettled) |
| `20260811-1715-fifth-friendly/` | 2026-08-11 17:15 | 3890 | 1-5, 45-85: interception cop converted g05 (23t, live validation); their sealer swept our pre-fix thief | `19ff133014a12501` |

Each folder holds THIS repo's role artifacts verbatim (odd windows here;
even windows in the sibling repo). `game_uid` (locked pre-series):
`bc77e467-4522-c355-cf69-868515ecc8a7`.

The third friendly broke the sweeps: their RUNNER thief (perimeter loops,
landmark-lying prose) survived g03/g05 against our cop - 4-2, 60-40, our
thief still 3/3 survivals. The loss tapes became the cop rehearsal
(tests/unit/test_strategy/test_league_rehearsal_nisyar1_cop.py) that
produced the sharp-mass wall gate + never-wall-out clock rule
(police repo commit e51fbb8): g03 runner 0/5 -> 5/5 captured.

Cross-verification (documented in the workspace `docs/docsVersusNisYar1/`
dossier): artifact bundles exchanged both directions after each series;
all outcomes/scores/turns byte-agree; audits clean both ways
(`Verified OK` here, `passed: true, forgery: false` there);
`mutual_agreement.sha256 =`
`7f688ab05ae7e19de14969e17dd6d96a5ae8b842664191a6dda60debe1e06ef2`
independently recomputed by BOTH teams from their own rows (ADR-0012
symmetric-outcome scope) — machine-checkable agreement, `confirmed: true`
on six clean audits per series.

`digest_match` is `null` in these friendlies: both sides emit honest
end-state digests but over different serializations. A shared recipe
(compact canonical JSON over positions/sorted barriers/turns/outcome —
our `domain/protocol.end_state_digest` form) was agreed with nis-yar1 on
2026-08-10 for the upcoming counted game.

The five failed attempts that preceded the first completed series (four
generations of rival-side infrastructure bugs: proxy response framing,
restricted-shell egress, crash-on-first-contact, scent-lock mismatch) are
archived with root-cause analyses in
[`../discarded-series/nisyar1-burned-attempts/`](../discarded-series/nisyar1-burned-attempts/).

The rehearsal set is also the working set in [`results/`](../../../results/) +
[`config/games/`](../../../config/games/); the first-series set survives only
here (the runner auto-archives superseded artifacts to the gitignored
`results/local/archived-series/`).
