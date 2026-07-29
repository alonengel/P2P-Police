"""The information regime, declared at the handshake as a locked-doc hash.

Two peers can both say "belief" and mean different things. Hashing the
REGISTERED definition pins the semantics, so the counted-series posture is
checkable on the record rather than promised in correspondence.

File-presence is the opt-in on purpose. The bytes must match the registry's
exactly - a locally invented envelope would hash differently and refuse an
honest peer at the handshake, which is worse than not declaring at all.
"""

import json

import pytest

from p2p_police.domain.errors import GameRuleError
from p2p_police.wire import lock


def _armed(config_dir, doc=None):
    path = config_dir / "info_mode_lock.json"
    path.write_text(json.dumps(doc or {"family": "info_mode", "name": "belief"}),
                    encoding="utf-8")
    return path


def test_no_canonical_document_declares_nothing(config_dir, monkeypatch) -> None:
    monkeypatch.setattr(lock, "_INFO_MODE_PATH", config_dir / "absent.json")
    assert lock.info_mode_sha256() is None
    agreement = lock.extend_agreement({}, _reference(config_dir))
    assert "info_mode_sha256" not in agreement


def test_the_declaration_is_the_hash_of_the_registered_document(
    config_dir, monkeypatch
) -> None:
    monkeypatch.setattr(lock, "_INFO_MODE_PATH", _armed(config_dir))
    agreement = lock.extend_agreement({}, _reference(config_dir))
    assert agreement["info_mode_sha256"] == lock.info_mode_sha256()


def test_matching_declarations_pass_and_differing_ones_refuse(
    config_dir, monkeypatch
) -> None:
    monkeypatch.setattr(lock, "_INFO_MODE_PATH", _armed(config_dir))
    mine = lock.extend_agreement({}, _reference(config_dir))
    lock.verify_info_mode(mine, dict(mine))  # same registered definition
    with pytest.raises(GameRuleError, match="info_mode"):
        lock.verify_info_mode(mine, dict(mine, info_mode_sha256="f" * 64))


def test_omission_on_either_side_never_refuses(config_dir, monkeypatch) -> None:
    """A peer that holds no registered document must stay playable - the
    check exists to catch two DIFFERENT definitions, not to punish silence."""
    monkeypatch.setattr(lock, "_INFO_MODE_PATH", _armed(config_dir))
    mine = lock.extend_agreement({}, _reference(config_dir))
    lock.verify_info_mode(mine, {})
    lock.verify_info_mode({}, mine)


def _reference(config_dir):
    from p2p_police.shared.config import Config

    config = Config.load(config_dir)
    config.private.setdefault("network", {})["wire_shape"] = "reference"
    return config
