"""Series-runner helpers: email preflight + auto-close (split out of
league_series.py for the 150-code-line cap).

Preflight: a posture that OWES a report ([email] mode = send) must prove
deliverability BEFORE window 1 — recipient non-empty and a live refresh
against the OAuth TOKEN endpoint only, reusing infra/email_sender's token
logic (no Gmail scope is touched here and no mail moves). A posture that
cannot deliver refuses the whole run with zero games played.

Auto-close: when this runner's last window settles and every sub-game log
of the series is visible across BOTH results dirs (ours + the sibling
repo's — read-only FILE access, never a cross-repo import), the existing
`series-result` aggregation runs with --email. An incomplete series names
exactly who is missing and closes nothing: the sibling runner owning the
final window performs the close, and the settlement guard inside the
aggregation stays the backstop either way.
"""

from pathlib import Path

from p2p_police.domain.game_ids import log_name
from p2p_police.shared.config import Config


def email_preflight(config_dir: Path) -> str | None:
    """Refusal message when the send posture cannot deliver, else None."""
    try:
        config = Config.load(config_dir)
    except Exception as error:
        return f"config unusable ({type(error).__name__}: {error})"
    email_cfg = config.private.get("email", {})
    if email_cfg.get("mode") != "send":
        return None  # this posture owes no report: nothing to prove
    if not str(email_cfg.get("recipient", "")).strip():
        return "[email] mode = send but recipient is empty"
    from p2p_police.infra import email_sender

    try:  # token loads + refreshes against the OAuth token endpoint ONLY
        email_sender._access_token(email_sender._load_token())
    except Exception as error:
        return (f"token refresh against the OAuth endpoint failed "
                f"({type(error).__name__}: {error}) - fix the credentials "
                "before any window plays")
    return None


def find_series_game_id(results: Path) -> str | None:
    """game_id of the NEWEST sub-game log this runner produced."""
    logs = sorted(results.glob("log_*_g*.json"), key=lambda p: p.stat().st_mtime)
    if not logs:
        return None
    name = logs[-1].name  # log_<game_id>_gNN.json
    return name[len("log_"):name.rfind("_g")]


def missing_logs(dirs: list[Path], game_id: str, num_games: int) -> list[str]:
    """Named sub-game logs visible in NO results dir (slots 1..num_games)."""
    return [f"s{n} ({log_name(game_id, n)})" for n in range(1, num_games + 1)
            if not any((d / log_name(game_id, n)).is_file() for d in dirs)]


def close_series(root: Path, sibling_results: Path, cli: str, runner,
                 counted: bool = False) -> int:
    """Aggregate when complete; else name the gaps and close NOTHING."""
    results = root / "results"
    game_id = find_series_game_id(results)
    if game_id is None:
        print("close: no sub-game logs under results/ - nothing to aggregate")
        return 1
    num_games = int(Config.load(root / "config")
                    .shared["network_and_league"]["num_games"])
    missing = missing_logs([results, sibling_results], game_id, num_games)
    if missing:
        print(f"close: series {game_id} not complete - missing "
              + ", ".join(missing)
              + f" across {results} and {sibling_results}; NOT aggregating "
              "(the runner owning the last window closes; the settlement "
              "guard backs this up)")
        return 1
    command = ["uv", "run", cli, "series-result", "--game-id", game_id,
               "--results-dir", str(results), "--results-dir",
               str(sibling_results), "--email"] + (["--counted"] if counted else [])
    print(f"close: all {num_games} sub-game logs visible - running "
          + " ".join(command))
    return int(runner(command, cwd=root).returncode)
