# INTEROP — the cross-team determinism contract

(The hashing spec merged from Renat Karimov's INTEROPERABILITY.md; this is
what makes commit-reveal work against FOREIGN implementations.)

Any opponent implementation must reproduce our bytes exactly:

1. **Canonical JSON**: UTF-8, `sort_keys=true`, separators `(",", ":")`,
   `ensure_ascii=true`, no insignificant whitespace, no float formatting
   games (ints stay ints).
2. **Sealed record fields** (exactly these, no extras): `step`, `role`,
   `sub_game`, `state_digest`, `action`, `hint`, `verdict`.
3. **Commitment**: `SHA-256( canonical({"payload": <record>, "nonce": <hex>}) )`,
   nonce = 32 lowercase hex chars; commit(t) precedes reveal(t); nonces and
   verdicts disclosed ONLY in the end-of-game audit message.
4. **Timestamps**: ISO-8601 UTC with seconds precision.
5. **Scent model**: locked pre-series via `scent_model_sha256` over the spec
   in `domain/scent.py::scent_model_spec()` — includes the re-emission clamp.
6. **Config identity**: `config_sha256` over canonical game.json; validate
   against `config/game.schema.json` before proposing changes.
7. **Known interpretation disclosures** (state at negotiation): trapped-thief
   reading = all four orthogonal neighbours impassable by BOARD (barriers/
   edges); a cop-occupied neighbour is NOT counted as blocking - the thief
   may legally step into the cop (instant capture) or STAY, so capture lands
   one half-turn later with identical points. Reaching max_moves uncaptured
   counts as survival (defaults make the limits equal).
