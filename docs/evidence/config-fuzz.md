# Config-range fuzz evidence (E5)

- Run: 2026-07-21T18:42:10+00:00 | role: police | seed `20260721` (reproducible) | samples: 40
- Result: **40 passed / 0 failed**
- Sampled bounds (Appendix-VI minimums raised, FIXED terms asserted untouched every sample): {"grid_size": [7, 11], "max_barriers": [14, 24], "max_moves_and_survival": [35, 60]}
- Outcomes: 40 captures, 0 survivals
- Invariants per sample: game completes, one legal shared outcome, digests match, mutual audits Verified OK, turns <= max_moves, barrier quota respected.
- Full rows + any failing config verbatim: `results/experiments/config_fuzz.json`
- Rerun: `uv run python scripts/config_fuzz.py` (knobs in `config/game.toml [fuzz]`).
