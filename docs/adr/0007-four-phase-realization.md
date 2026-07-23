# ADR-0007 — Ch. 5's four phases realized as sequential half-turns

Date: 2026-07-20. Status: accepted. Scope: both repos (mirrored twins).

## Context

The book's ch. 5 draws Commit -> Acknowledge -> Reveal -> Audit per game
step, with an acknowledge that locks both commitments before any reveal —
a simultaneous-turn picture. Our game is strictly turn-alternating
(negotiated commit_order, default police_first), so simultaneity has no
cheating surface to protect: the mover commits AND reveals within its own
half-turn, before the opponent acts at all.

## Decision

- COMMIT: the sealed hash is sent; the opponent's application-level ack
  (the MCP tool's accepted response, which the transport blocks on) IS the
  lock — a real acknowledgment, not a fiction.
- REVEAL: sent immediately after the ack, minus the nonce and the intent
  verdict (both stay sealed until the audit; revealing the verdict live
  would hand the rival the lie bit).
- AUDIT: end-of-game mass verification, per the book.
Anti-peek protection comes from turn order + nonce withholding, not from a
mutual simultaneous lock. Rule 11's "byte-for-byte" config identity is
implemented as canonical-hash equality (whitespace-insensitive, semantically
stronger) - disclosed here for the same completeness reason. Context for
that reading: the official reference implementation compares the agreed
terms by DICT EQUALITY (weaker than our canonical hash), so a literal
file-bytes reading of rule 11 would flag the instructor's own tooling
before ours; our mechanism sits strictly between the reference's practice
and the rule's letter, and the runbook still instructs exchanging one
identical file.

## Consequences

All four phases occur, per step, in order; the deviation from the book's
simultaneous framing is this documented interpretation. A pairing that
demands the deferred-Reveal (hidden) realization is a different wire shape
(issue-#6 registration) and out of this ADR's scope.

## Addendum (2026-07-23): each wire shape carries its registered handshake

Live warm-up finding: rule 11's lock has two REGISTERED realizations — the
config_sha256 substitution (a bookletter-v3 property) and the reference's
literal flat-terms form (`terms` 14-key + `nonce` + `signature =
SHA256(canonical(terms)|nonce)`, pinned by the league kit's terms_signature
CORE vector). Our client now speaks each shape's own registered handshake:
bookletter negotiates by config hash, reference-v3 by flat terms with
key-by-key value equality and a diagnostic naming every differing key. Model
locks (scent/wire/info) ride alongside in both. Substance of rule 11 —
identical agreed values, cryptographically locked — is satisfied in both
forms; neither is a deviation, each is its shape's registration.
