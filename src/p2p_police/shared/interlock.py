"""Structural safety interlocks — never comment-based discipline.

Two guards that make rehearsal mistakes IMPOSSIBLE rather than discouraged:

* Lecturer-address interlock (rule 51 hygiene): email may address the
  league/lecturer ONLY when a counted game is doubly armed — `[email]
  counted = true` in config AND the `--counted` CLI flag on this very
  invocation. Rehearsals and friendlies structurally cannot reach the
  league inbox. Both sdk/reporting.maybe_email and the series email path
  route through here.
* Sparring posture assertion: `peer --sparring` refuses at load time any
  warm-up file that carries tuned play ([strategy] overrides / weight
  tables) or an armed email path.
"""

from p2p_police.shared.config import ConfigError

# The known league/lecturer base identity (documented in LEAGUE_RUNBOOK);
# [email] league_addresses in config EXTENDS this floor — omitting the key
# can never disarm the guard. Plus-aliases collapse onto the base, so the
# one base entry also covers the per-league tagged alias.
KNOWN_LEAGUE_ADDRESSES = ("rmisegal@gmail.com",)


class EmailInterlockError(Exception):
    """Refused: the recipient addresses the league but the counted-game
    interlock is not fully armed (config half + CLI half, both required)."""


def _base(address: str) -> str:
    """Normalized base identity: lowercase, +tag stripped from the local
    part — `x+anything@y` and `x@y` are the same inbox."""
    local, _, domain = address.strip().lower().partition("@")
    return f"{local.split('+', 1)[0]}@{domain}"


def league_hits(config, recipient: str) -> list[str]:
    """The comma-separated recipient parts that address the league."""
    listed = config.private.get("email", {}).get("league_addresses", ())
    bases = {_base(a) for a in (*KNOWN_LEAGUE_ADDRESSES, *listed)}
    return [part.strip() for part in str(recipient).split(",")
            if part.strip() and _base(part) in bases]


def counted_armed(config) -> bool:
    """BOTH halves: `[email] counted = true` in the config file AND the
    --counted CLI flag on this invocation (injected as counted_cli_armed)."""
    email_cfg = config.private.get("email", {})
    return bool(email_cfg.get("counted")) and bool(email_cfg.get("counted_cli_armed"))


def ensure_email_allowed(config, recipient: str) -> None:
    """The interlock gate: raise unless every league-addressed part of the
    recipient is covered by a doubly-armed counted game."""
    hits = league_hits(config, recipient)
    if hits and not counted_armed(config):
        raise EmailInterlockError(
            f"refusing to email the league/lecturer address {', '.join(hits)}: "
            "this run is not armed as a counted game - a rehearsal must never "
            "address the league (arm BOTH [email] counted = true AND the "
            "--counted CLI flag)")


def ensure_counted_posture(config) -> None:
    """--counted refusal gate (rules 32/51 + Table 18): a run ARMED as
    counted must be able to deliver the league report — else it plays ZERO
    games. Training runs (no --counted) never reach any of these checks and
    keep their private recipients untouched."""
    email_cfg = config.private.get("email", {})
    if not email_cfg.get("counted_cli_armed"):
        return
    problems = []
    if not email_cfg.get("counted"):
        problems.append("[email] counted is not true (config half unarmed)")
    if email_cfg.get("mode") != "send":
        problems.append(f"[email] mode = {email_cfg.get('mode', 'disabled')!r}"
                        " (a counted run owes the league a report)")
    if not league_hits(config, email_cfg.get("recipient", "")):
        problems.append("recipient list contains no league/lecturer address")
    if problems:
        raise EmailInterlockError(
            "counted run refused (zero games played): " + "; ".join(problems))


def assert_sparring_posture(private: dict) -> None:
    """--sparring load gate: the warm-up posture must be GENERIC — refuse a
    sparring file carrying tuned play or an armed email path (warm-ups must
    not leak our tuned play, and they never report anywhere)."""
    problems = []
    if "strategy" in private:
        problems.append("[strategy] present (class override / tuned weight tables)")
    mode = private.get("email", {}).get("mode", "disabled")
    if mode != "disabled":
        problems.append(f"[email] mode = {mode!r} (sparring never emails)")
    if problems:
        raise ConfigError("sparring posture refused: " + "; ".join(problems))
