# Self-grade — code quality only (rule 55)

Per Appendix ה rule 55, this grade covers **code quality alone — never
league results**. Basis: the measurable gates this repo enforces on every
commit, verifiable by running `make`-equivalent commands from the README.

## Grade: 96 / 100

| Criterion | Evidence | Self-assessment |
|---|---|---|
| Test discipline | 765 tests, TDD red-green history in git, branch coverage 94.1% (gate ≥85%) | 20/20 |
| Code hygiene | ruff zero violations; ≤150 code lines per file, CI-enforced; no hardcoded game values (all tunables from config) | 19/20 |
| Architecture | SDK single-entry facade; domain/wire/peer/report layering; parity-locked twin physics with golden vectors; two registered wire shapes behind one seam | 20/20 |
| Robustness | chaos drills D1–D4 + live tunnel kill/heal, crash-resume on both wires, watchdog + deadlines everywhere, gatekeeper triad on every external call | 19/20 |
| Documentation & evidence | full academic README, 10 PRDs, 12 ADRs incl. documented book contradictions, per-experiment evidence files with honest negative results, prompt log | 18/20 |

The four points withheld: residual GUI code paths are exercised more
thinly than the engine core (coverage is branch-weighted toward domain/
wire), and two documented cosmetic divergences from the course example
sets remain by decision rather than by accident (ADR-0012).

*Assessed by team `anrbj666` (Alon Engel, Renat Karimov), 2026-08-03.*
