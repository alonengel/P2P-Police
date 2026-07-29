"""replay_verdict must NAME reduced assurance, never silently pass it off
as a fully verified game (rule 20): a lost config artifact or a digest-less
summary reads 'Verified OK (seals only - ...)', not plain 'Verified OK'."""

import json

from p2p_police.report import lookup
from p2p_police.report.artifacts import git_commit_hash


def test_missing_config_artifact_is_named(tmp_path) -> None:
    doc = {"game_id": "aaaa1111-vs-bbbb2222", "sub_game_number": 1,
           "summary": {"end_state_digest": "ab" * 32}}
    verdict = lookup.replay_verdict(doc, tmp_path / "results" / "log.json")
    assert verdict.startswith("Verified OK (seals only")
    assert "config artifact" in verdict


def test_missing_summary_digest_is_named(tmp_path) -> None:
    game_id, sub = "aaaa1111-vs-bbbb2222", 1
    games = tmp_path / "config" / "games"
    games.mkdir(parents=True)
    (games / f"config_{game_id}_g{sub:02d}.json").write_text(
        json.dumps({"terms": {"board_and_agents": {}}}), encoding="utf-8")
    log_path = tmp_path / "results" / f"log_{game_id}_g{sub:02d}.json"
    doc = {"game_id": game_id, "sub_game_number": sub, "summary": {}}
    verdict = lookup.replay_verdict(doc, log_path)
    assert verdict.startswith("Verified OK (seals only")
    assert "end_state_digest" in verdict


def test_dirty_working_tree_is_named_in_commit_hash(monkeypatch) -> None:
    """Rule 53: the declared commit must not silently pretend a dirty tree
    is the committed code."""
    from types import SimpleNamespace

    from p2p_police.report import code_identity

    def fake_run(args, capture_output, text, timeout):  # noqa: ARG001
        if args[:2] == ["git", "rev-parse"]:
            return SimpleNamespace(stdout="abc123\n")
        return SimpleNamespace(stdout=" M src/file.py\n")

    monkeypatch.setattr(code_identity.subprocess, "run", fake_run)
    assert git_commit_hash() == "abc123-dirty"


def test_clean_tree_keeps_the_bare_hash(monkeypatch) -> None:
    from types import SimpleNamespace

    from p2p_police.report import code_identity

    def fake_run(args, capture_output, text, timeout):  # noqa: ARG001
        if args[:2] == ["git", "rev-parse"]:
            return SimpleNamespace(stdout="abc123\n")
        return SimpleNamespace(stdout="")

    monkeypatch.setattr(code_identity.subprocess, "run", fake_run)
    assert git_commit_hash() == "abc123"
