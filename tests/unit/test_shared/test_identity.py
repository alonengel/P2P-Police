"""Step-0 identity declaration (rules 24/37-38/49/53): the handshake block
must carry the exact code identity — the book's p. 40 חובה box puts the
commit id IN the agreement declaration, beside the hardware spec."""

from p2p_police.report.code_identity import git_commit_hash
from p2p_police.shared.identity import identity_block

PRIVATE = {
    "game": {
        "repos": {"cop": "https://example.com/cop", "thief": "https://example.com/thief"},
        "mcp_servers": {"cop": "http://c/mcp", "thief": "http://t/mcp"},
        "counted_games_played": 2,
        "group_name": "anrbj666",
        "members": ["A", "B"],
    },
    "llm": {"model": "template"},
}


def test_identity_declares_the_exact_commit_id() -> None:
    block = identity_block(PRIVATE, "anrbj666")
    commit = block["github_commit"]
    assert commit == git_commit_hash()  # the declared id IS the code identity
    # best-effort surface: a real bare hash or the named fallback
    assert commit == "unknown" or len(commit.split("-")[0]) == 40


def test_identity_keeps_the_declaration_fields() -> None:
    block = identity_block(PRIVATE, "anrbj666")
    assert block["repos"]["cop"].endswith("/cop")
    assert block["members"] == ["A", "B"]
    assert block["counted_games_played"] == 2
    assert block["llm_model"] == "template"
    assert "hardware_spec" in block


def test_empty_llm_model_declares_the_provider_not_an_empty_string() -> None:
    """[llm] model = "" means the zero-token template chain runs — the
    declaration names the PROVIDER (Imree diff 2026-08-03), never ''."""
    private = dict(PRIVATE, llm={"model": ""}, trash_talk={"provider": "template"})
    assert identity_block(private, "anrbj666")["llm_model"] == "template"
    private["trash_talk"] = {"provider": "ollama"}
    assert identity_block(private, "anrbj666")["llm_model"] == "ollama"
