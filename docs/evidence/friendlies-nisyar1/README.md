# nis-yar1 friendlies — 2026-08-10 (uncounted, fully cross-verified)

Two settled 6/6 friendly series against `nis-yar1` (Nissim Deri, Yarden
Tziar; qwen3:14b hints, ngrok static-domain path-split transport), both swept
**6–0, 90–30** by anrbj666. FRIENDLY posture throughout: reports emailed to
the two team inboxes only, never the lecturer; no rule-52 counter moved.

| Series | T (IL) | Seed base | Per-game | Report email |
|--------|--------|-----------|----------|--------------|
| `20260810-2016-first-series/` | 20:16 | 3830 | captures in 8 (g01/g03/g05), survivals 35 (g02/g04/g06) | `19fecaf5c92fd4d5` |
| `20260810-2118-rehearsal/` | 21:18 | 3840 | captures in 12, survivals 35 | `19fece82ee5cdbd4` |

Each folder holds THIS repo's role artifacts verbatim (odd windows here;
even windows in the sibling repo). `game_uid` (locked pre-series):
`bc77e467-4522-c355-cf69-868515ecc8a7`.

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
