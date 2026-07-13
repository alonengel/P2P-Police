# P2P-Police — the Cop agent

Autonomous **Police (Cop)** agent for the distributed Cops-and-Robbers game played
peer-to-peer over FastMCP — no central server, no judge. Integrity is enforced by a
SHA-256 commit-reveal protocol and a mutual end-of-game audit.

> Sibling repository (the Thief agent of team `anrbj666`):
> **https://github.com/alonengel/P2P-Thief**

Team: Alon Engel, Renat Karimov · Course: Orchestration of AI Agents (Univ. of Haifa)

## Status

Bootstrap phase — project scaffold, quality gates, and planning documents.
This README will grow into the full user manual + academic report as development
progresses (see `docs/PLAN.md` and `docs/TODO.md`).

## Quick start (will be expanded)

```bash
uv sync
uv run p2p-police --help
```

## Repository map

| Path        | Purpose                                              |
|-------------|------------------------------------------------------|
| `src/`      | Source (SDK-first architecture, files ≤150 code lines)|
| `tests/`    | Unit + integration tests (TDD, coverage ≥85%)         |
| `docs/`     | PRD / PLAN / TODO / PROMPTS / ADRs                    |
| `config/`   | Shared signed `game.json` + private `game.toml`       |
| `data/` `results/` `assets/` `notebooks/` | Inputs, run artifacts, figures, analysis |

## License & credits

MIT — see [LICENSE](LICENSE), including third-party attribution to the official
course example repository.
