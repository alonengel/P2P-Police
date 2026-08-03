"""Submission gate: PASS/FAIL against the rulebook + guidelines checklists.

Run before tagging: uv run python scripts/check_submission.py
"""

import subprocess
import sys
from pathlib import Path

CHECKS: list[tuple[str, object]] = []


def check(name):
    def wrap(fn):
        CHECKS.append((name, fn))
        return fn
    return wrap


@check("README: sibling cross-link + both mandatory screenshots embedded")
def _readme() -> bool:
    text = Path("README.md").read_text(encoding="utf-8")
    return ("github.com/alonengel/P2P-" in text and "live_belief_map.png" in text
            and "replay_verified_ok.png" in text and "Dec-POMDP" in text)


@check("docs: PRD/PLAN/TODO/PROMPTS + runbooks + UI + COST + ADRs")
def _docs() -> bool:
    need = ["PRD.md", "PLAN.md", "TODO.md", "PROMPTS.md", "DEPLOYMENT.md",
            "LEAGUE_RUNBOOK.md", "UI.md", "COST.md", "adr/0001-mirrored-twin-repos.md"]
    return all((Path("docs") / n).is_file() for n in need)


@check("assets: mandatory screenshots present")
def _assets() -> bool:
    need = ["live_belief_map.png", "replay_verified_ok.png", "replay_tampered_demo.png"]
    return all((Path("assets") / n).is_file() for n in need)


@check("config: game.json + game.toml + rate_limits + archived games")
def _config() -> bool:
    base = all((Path("config") / n).is_file()
               for n in ["game.json", "game.toml", "rate_limits.json"])
    # played-game configs count wherever they are archived: the live
    # config/games/ (current series), the per-window friendly snapshots,
    # or the dev-history archive (top level starts EMPTY before a counted
    # series so its artifacts arrive as pure adds, 2026-08-04)
    archived = (any(Path("config/games").glob("config_*.json"))
                or any(Path("results/friendlies").rglob("config_*.json"))
                or any(Path("results/dev-history/config/games").glob("config_*.json")))
    return base and archived


@check("notebook + experiment data present")
def _research() -> bool:
    return Path("notebooks/analysis.ipynb").is_file() and any(
        Path("results/experiments").glob("*.json"))


@check("no secrets tracked by git")
def _secrets() -> bool:
    tracked = subprocess.run(["git", "ls-files"], capture_output=True, text=True).stdout
    bad = ("credentials.json", "token.json", ".env\n", ".pem", ".key\n")
    return not any(marker in tracked for marker in bad)


@check("quality gates: ruff + line-cap + tests+coverage")
def _gates() -> bool:
    commands = [
        ["uv", "run", "ruff", "check", "src", "tests", "scripts"],
        ["uv", "run", "python", "scripts/check_line_cap.py"],
        ["uv", "run", "pytest", "--cov", "-q"],
    ]
    return all(subprocess.run(c, capture_output=True).returncode == 0 for c in commands)


@check("twin physics parity")
def _parity() -> bool:
    result = subprocess.run(
        ["uv", "run", "python", "scripts/check_physics_parity.py"], capture_output=True
    )
    return result.returncode == 0


@check("rule 55: explicit code-quality self-grade in the repo")
def _self_grade() -> bool:
    path = Path("SELF_GRADE.md")
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8")
    return "Grade:" in text and "code quality" in text.lower()


@check("v1.0-submission tag (WARN until league games played)")
def _tag() -> bool:
    tags = subprocess.run(["git", "tag"], capture_output=True, text=True).stdout
    return "v1.0-submission" in tags


def main() -> int:
    failures = 0
    for name, fn in CHECKS:
        ok = bool(fn())
        warn_only = "WARN" in name
        mark = "PASS" if ok else ("WARN" if warn_only else "FAIL")
        failures += (not ok) and not warn_only
        print(f"[{mark}] {name}")
    print("SUBMISSION READY" if failures == 0 else f"{failures} blocking failure(s)")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
