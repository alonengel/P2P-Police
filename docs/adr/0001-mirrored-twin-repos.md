# ADR-0001: Mirrored-twin repositories with duplicated physics

Status: accepted · Date: 2026-07-13

## Context

The rulebook requires (a) two separate GitHub repos — cop and thief — each a
complete standalone project (rule 49-50), and (b) total runtime separation: two
processes, and it is strictly forbidden to share memory, **import a shared
module holding live state**, or read shared variables — violation disqualifies
the solution even if the game "works". Meanwhile the game physics (board,
scent, crypto, protocol) must behave identically on both sides because the
shared config is byte-locked and every step is mutually audited.

## Decision

Each repo is a standalone package (`p2p_police` / `p2p_thief`) with an
identical `domain/` (physics) module set that is **duplicated, never imported
across repos**. Identity is enforced socially and mechanically:
1. paired commits — any `domain/` change is ported to the sibling in the same
   session;
2. `scripts/check_physics_parity.py` — hashes physics files against the sibling
   checkout (role tokens canonicalized);
3. `tests/vectors/physics_vectors.json` — byte-identical golden vectors both
   test suites assert against, so drift fails CI even without the sibling.
Only `strategy/`, configs, and narrative docs diverge by role.

## Alternatives considered

- **Shared core package / third repo (submodule):** rejected — weakens the
  "two standalone repos" submission story and walks the line of the forbidden
  shared-module rule; a third repo is not part of the submission contract.
- **Sync script copying an engine into both repos:** rejected — mechanical
  commit history, and the repos stop telling independent development stories.
- **Intentionally divergent implementations:** rejected — doubles work and
  maximizes the risk of physics mismatch → failed mutual audit → 0.

## Consequences

Duplication is deliberate and rule-driven (documented here so reviewers do not
read it as a DRY violation); the parity gate makes divergence loud; each repo
carries its own full commit history as required.
