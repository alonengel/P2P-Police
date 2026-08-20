# Opponent onboarding — kit conformance and how a pairing gets verified

Cross-team play is where this project's engineering was actually tested, and
the league's interop kit —
[copthief-league-protocol](https://github.com/Imreec/copthief-league-protocol)
— is the instrument that made it testable. This document records two things: our part in building that
instrument, and the checklist every opponent went through against it before we
played them. Each step names the real case that proved it necessary.

## The kit: co-authored, then proven by play

The conformance kit began as a two-team effort with Imree's team (imreeyal) and
grew into the league's shared contract — SPEC, byte-level vectors, behaviour
tables. Our contributions are credited in the SPEC itself:

- **`multiplicative_book_v1` scent registration PROMOTED** on our clean-room
  reproduction of the book's model — byte-exact on the kernel, every fixture
  case, zero tolerance — built from the book alone before the vectors existed.
- **The rule 46/47 capture-endings construction** (issue #37): the live
  reproduction of the forked-ending failure, the `caught: true`
  answer/concession distinction, and the corroboration rules — settled jointly
  and adopted by both independent engines.
- **The consensus-scope correction** (2026-08-13): the five-key
  `mutual_agreement` row proven against the reference's own filed artifacts
  after a six-key convention had sat wrong in every carrier for nine days —
  found by us, reproduced independently by imreeyal the same day, now pinned
  by a CI probe.
- **The `{}` convention, the empty-field checker rule and the zero-step-final
  exemption** (§7) — receiver-side behaviour that keeps honest peers from
  refusing each other, each found and fixed in our own client first.
- **The at-least-once delivery contract** (§7.1) and the **pairing
  declaration** (§7.2) — implemented independently by both teams, promoted on
  the live cross-team series evidence.
- **The tie-scope and `game_id` sort corrections** — settlement-layer
  divergences caught by cross-diffing real reports, fixed in the kit for every
  team downstream.

The kit was then validated the only way that counts: full series against
independent implementations — imreeyal (the co-author's engine, both counted
and a long friendly campaign), vibecode, uoh-sqak, best2934 and najamjad —
with mutual audits clean in both directions on every settled series.

## The checklist, per pairing

1. **Re-derive every hash they publish — through our own code, never by
   reading.** An opponent's terms digest, commit-reveal vector and scent-model
   sha are recomputed from our own canonical serializer before we reply.
   *Case: najamjad's 14-key terms hash `a284082d…` and commit vector
   `4047830b…` both reproduced byte-identically through our loader before we
   agreed to anything — and their published scent sha was verified against the
   kit's registry, which is how a locked-model conflict was caught at the
   document stage and resolved by a registry-sanctioned arrangement instead of
   a refused handshake.*

2. **Check their conformance against the kit**: commit construction, audit
   envelope, locked-model declarations, pairing declaration, delivery
   contract. Where something deviates, the deviation is named with evidence
   the other team can re-run themselves — file, line, recompute — before any
   game depends on it.
   *Case: best2934's step-0 was sealed under `merged_nonce_v1` while their
   negotiate declared `kit_pipe_v1` — established by recomputing published
   artifacts under every registered construction (19/19 vs 0/19) and pinned to
   the exact call site. Twelve voided windows explained, fixed by them,
   negative-controlled, and the pairing went on to settle clean.*

3. **Warm-ups before anything counted.** Friendlies exist to exercise the
   wire: negotiate, turns, audits, settlement — uncounted, no lecturer, reports
   operator-to-operator. No counted until a full six settles green end-to-end
   in both directions, audits included.
   *Case: seven best2934 series were played before the counted; five interop
   defects came off the wire in that window, every one fixed and verified
   before the series that mattered.*

4. **Settlement is verified before it is trusted.** The consensus digest is
   exchanged on the public thread before either team mails; report bytes are
   cross-diffed on an uncounted artifact first; delivery is proven by reading
   the receipt's `sent` field — never a filename — and posting the message id.
   *Case: the best2934 friendly-report exercise surfaced that neither of their
   counted filings had ever been delivered (a silent auth failure behind a
   receipt-exists guard) — found on an uncounted artifact, fixed before the
   counted relied on the same path. The same exercise with uoh-sqak (§5b
   digest acceptance test) is what first proved two independent settlement
   layers computing identical bytes.*

5. **Operator gates on both sides.** A counted series opens only on each
   operator's own written word on the public thread, after the time is named
   and before the first move. Config flips (`counted = true`, the lecturer
   address) are made in a joint pre-arm check, verified through the code path
   that reads them, and defused again after settlement.

6. **Clean trees or no game.** Declared step-0 commits must name the code that
   plays: pairing constitutions are committed and pushed before arming, and
   the report carries per-role, per-window commits (rule 53).
   *Case: cross-diffing best2934's report caught a single commit stamped
   across six two-process rows; the same standard applied to ourselves is why
   both twins were committed clean before our counted armed.*

## Where the evidence lives

- Per-pairing archives: `docs/evidence/counted_games/` and
  `docs/evidence/friendlies-*/` in both repos — logs, results, declarations at
  the heads that played.
- The public verification record: league kit issues #49, #45 and #37, and the
  kit SPEC's own credit lines.
- The kit conformance suite in this repo:
  `tests/unit/test_reference_conformance.py`.

The pattern underneath every step is the same one the twins are built on: an
assertion is evidence only when the checking code is independent of the
claiming code — an opponent's word, like our own, is a hypothesis until it
recomputes.
