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


def test_commit_hash_is_the_bare_head(monkeypatch) -> None:
    """Rule 53 wants THE commit id: a plain hash a grader can rev-parse
    (pair decision with imreeyal 2026-08-03 — no dirty qualifier; a series
    rewrites its own tracked artifacts mid-run, so the marker fired on
    every window after the first artifact commit and meant nothing)."""
    from types import SimpleNamespace

    from p2p_police.report import code_identity

    def fake_run(args, capture_output, text, timeout):  # noqa: ARG001
        assert args[:2] == ["git", "rev-parse"]  # exactly one probe, no status call
        return SimpleNamespace(stdout="abc123\n")

    monkeypatch.setattr(code_identity.subprocess, "run", fake_run)
    assert git_commit_hash() == "abc123"


def test_commit_hash_degrades_to_unknown_without_git(monkeypatch) -> None:
    from p2p_police.report import code_identity

    def fake_run(*args, **kwargs):  # noqa: ARG001
        raise OSError("git not available")

    monkeypatch.setattr(code_identity.subprocess, "run", fake_run)
    assert git_commit_hash() == "unknown"
