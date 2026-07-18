# Foreign conformance vectors (third-party, MIT)

Source: `Imreec/copthief-league-protocol` — a cross-team interop conformance kit
by Team ImreEyal (Imree Cohen, Eyal Shtinmetz), MIT License, which pins the
official reference implementation's byte-level hash constructions with
independently generated test vectors. Copied unmodified; consumed by
`tests/unit/test_reference_conformance.py` to prove OUR crypto reproduces the
reference bytes (ADR-0004).

Deliberately NOT copied:

- `pheromone.json` — the reference's scent model (subtractive decay, linear
  falloff) deviates from the rulebook's printed multiplicative formula and
  Gaussian kernel; we implement the book's model (ADR-0004 "NOT adopted").
- `derive_starts.json`, `joint_seed.json` — opt-in kit enhancements absent
  from both the book and the reference implementation; not adopted.
