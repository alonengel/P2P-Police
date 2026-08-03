"""The rival-facing identity declaration (split from config.py for the
150-code-line cap).

Mirrors the block the book's sample DECLARATION holds per team, so a peer can
fill OUR column of its own declaration from the handshake alone. Nobody can
source the opponent's identity locally, which is exactly how a report-diff
ends up with one column of nulls (2026-08-01, with imreeyal).
"""

from p2p_police.shared.sysinfo import hardware_spec


def identity_block(private: dict, group_id: str) -> dict:
    """Rules 37-38/49 + rule 24: who we are, what we run, what we play on.

    Also rule 53 + the book's p. 40 חובה box (§5.5): the Step-0 declaration
    must name the EXACT commit id the declaring side runs — it is the only
    way the rival can fill our column of its own declaration, and the series
    report reads the rival's commit from exactly this block."""
    from p2p_police.report.code_identity import git_commit_hash

    game = private.get("game", {})
    return {
        "repos": game.get("repos", {}),
        "mcp_servers": game.get("mcp_servers", {}),
        "counted_games_played": int(game.get("counted_games_played", 0)),
        "group_name": game.get("group_name", group_id),
        "members": game.get("members", []),
        "llm_model": private.get("llm", {}).get("model", "template"),
        "hardware_spec": hardware_spec(),
        "github_commit": git_commit_hash(),
    }
