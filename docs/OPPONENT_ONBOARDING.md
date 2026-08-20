# Opponent onboarding — how a pairing gets verified before we play it

Every league opponent went through the same process before a single game, and
the process is itself part of this submission: cross-team interop is where the
project's engineering actually gets tested, and "verify, never assume" is the
only stance that survived the league. Each step below names the real case that
proved it necessary.

## The checklist, per pairing

1. **Re-derive every hash they publish — through our own code, never by
   reading.** An opponent's terms digest, commit-reveal vector and scent-model
   sha are recomputed from our own canonical serializer before we reply.
   *Case: najamjad's 14-key terms hash `a284082d…` and commit vector
   `4047830b…` both reproduced byte-identically through our loader before we
   agreed to anything — and their published scent sha was verified against the
   interop kit's registry, which is how the model conflict was caught at the
   document stage instead of at a refused handshake.*

2. **Check their conformance against the league interop kit** (the
   copthief-league-protocol SPEC we co-authored): commit construction, audit
   envelope, locked-model declarations, pairing declaration, delivery
   contract. Where they deviate, the deviation is named with evidence before
   any game.
   *Case: best2934's step-0 was sealed under `merged_nonce_v1` while their
   negotiate declared `kit_pipe_v1` — found by recomputing their own published
   artifacts under all registered constructions (19/19 vs 0/19), then pinned
   to the exact call site in their tree. Twelve voided windows explained by
   one missing argument, twice.*

3. **Scout their public artifacts and replay their play.** Committed logs are
   move scripts; our rehearsal harness replays them against our live brains
   (tape tests in `tests/unit/test_strategy/`), and where their code is
   public, their actual brain modules are imported and played against ours in
   a scratch harness — never inside the twins (ADR-0001).
   *Case: best2934's counted loss to gal-roy1 gave their thief's full script;
   our cop converted it at turn 10 across every seed, which is the exact turn
   the real counted series then produced, three windows out of three.*

4. **Friendlies before anything counted, at reduced strength, disarmed.** The
   warm-up exists to exercise the wire, not the strategy: decoy brains play,
   the counted interlock stays cold, reports go operator-to-operator only.
   No counted until a full six settles green end-to-end in both directions —
   audits included.
   *Case: seven best2934 series were played before the counted; five bugs
   (theirs) came off the wire in that window, every one fixed and
   negative-controlled before the series that mattered.*

5. **Settlement is verified before it is trusted.** The consensus digest is
   exchanged on the public thread before either team mails; the report bytes
   are cross-diffed on an uncounted artifact first; delivery is proven by
   reading the receipt's `sent` field — never a filename — and posting the
   message id.
   *Case: the best2934 friendly-report exercise surfaced that neither of
   their counted filings had ever been delivered (silent OAuth failure behind
   a receipt-exists guard) — found on an uncounted artifact, fixed before the
   counted relied on the same path.*

6. **Operator gates on both sides.** A counted series opens only on each
   operator's own written word on the public thread, after the time is named
   and before the first move. Config flips (`counted = true`, the lecturer
   address) are made in the joint pre-arm check, verified through the code
   path that reads them, and defused again after settlement.

7. **Clean trees or no game.** Declared step-0 commits must name the code
   that plays: pairing constitutions are committed and pushed before arming,
   and the report carries per-role, per-window commits (rule 53).
   *Case: our own audit of best2934's report caught a single commit stamped
   across six two-process rows; the same standard applied to ourselves is why
   both twins were committed clean before the counted armed.*

## Where the evidence lives

- Per-pairing archives: `docs/evidence/counted_games/` and
  `docs/evidence/friendlies-*/` in both repos — logs, results, declarations
  at the heads that played.
- The public verification record: league kit issue #49 (best2934 pairing,
  end to end) and #45/#37 (interop findings credited in the kit SPEC itself).
- The kit conformance suite: `tests/unit/test_reference_conformance.py` and
  the tape rehearsals under `tests/unit/test_strategy/`.

The pattern underneath all seven steps is the same one the twins are built on:
an assertion is evidence only when the checking code is independent of the
claiming code — an opponent's word, like our own, is a hypothesis until it
recomputes.
