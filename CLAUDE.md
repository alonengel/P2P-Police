# CLAUDE.md — P2P-Police (the Cop agent)

This repo is the **POLICE (Cop)** agent of team `anrbj666` (Alon Engel, Renat
Karimov). Sibling repo: **P2P-Thief** (`../P2P-Thief`, github.com/alonengel/P2P-Thief).
Master requirements dossier: `C:\Users\Alon\.claude\plans\ok-i-have-a-peppy-phoenix.md`.
Rulebook: `../docs/police_thief_p2p.pdf` (Appendix ו = only source of quantitative
truth; Appendix ה = 55 mandatory rules). Grading: `../docs/software_submission_guidelines-V3.pdf`.

## Golden rules (graded — do not break)

1. **≤150 CODE lines per file** (blanks/comments excluded) — `scripts/check_line_cap.py`.
2. **Nothing hardcoded** — every tunable comes from `config/` (game.json is the
   signed shared constitution; game.toml is private; JSON overrides TOML).
3. **SDK single entry** — business logic only behind `sdk/`; cli/gui are shells.
4. **All external calls through `shared/gatekeeper`** (rate limits from config).
5. **TDD** red-green-refactor; coverage ≥85% (branch); ruff 0 violations.
6. **uv only** — never pip / venv / python -m pip (hook-enforced).
7. **No secrets ever** — credentials.json/token.json/.env are gitignored; if one
   ever lands in a commit, rotate it.
8. **Conventional commits** with scopes; commit every green/refactor step.
9. **Log significant prompts** in `docs/PROMPTS.md` every working session.

## Mirrored-twin protocol (ADR-0001)

`src/p2p_police/domain/` and `tests/vectors/` must stay byte-identical with the
sibling (package name aside). Any change there → port to `../P2P-Thief` in the
SAME session (paired commit) → `uv run python scripts/check_physics_parity.py`
must pass. NEVER import across repos; duplication is deliberate and rule-driven.

## Game-rule tripwires (disqualification risks)

- Live UI shows LOCAL truth only — never the objective board.
- Moves are ALWAYS pure Python; the LLM writes hint text only (≤15 words).
- Dialogue is free natural language — never a numeric-coordinates protocol.
- Nonce stays secret until the end-of-game audit.
- The cop FORGOES his move to place a barrier (≤14 total, truthfully declared).
- Fixed params never change: scent 0.9/0.10/5×5; scoring 20/5/5/10/tie 2.

## Commands

```bash
uv sync                                        # deps
uv run pytest --cov -q                         # tests + coverage gate
uv run ruff check src tests scripts            # lint
uv run python scripts/check_line_cap.py        # 150-line cap
uv run python scripts/check_physics_parity.py  # twin parity
uv run p2p-police --version                    # CLI smoke
```

## Doc map

`docs/PRD.md` (+ `PRD_01..09_*.md` per stage) · `docs/PLAN.md` (architecture)
· `docs/TODO.md` (phase gates — keep statuses current) · `docs/PROMPTS.md`
(prompt log) · `docs/adr/` (decisions & documented contradictions).

## Subagents

`code-reviewer` (harsh, before stage-end commits) · `spec-auditor` (rulebook,
at stage ends) · `guidelines-auditor` (before milestones/tag) · `test-designer`
(red phase) · `physics-parity` (after domain/ changes).
