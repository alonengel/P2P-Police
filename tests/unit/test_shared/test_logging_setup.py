"""logging_setup: wires the versioned logging config; idempotent; stderr-only
console so stdout stays pure JSON for the CLI report."""

import json
import logging

from p2p_police.shared import logging_setup


def _spec(tmp_path, enabled=True):
    return {
        "version": "1.00", "level": "INFO",
        "format": "%(levelname)s %(name)s %(message)s",
        "file": {"enabled": enabled, "path": str(tmp_path / "logs" / "t.log"),
                 "max_bytes": 10_000, "backup_count": 1},
        "console": {"enabled": False},
    }


def _reset_root() -> None:
    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)
    if hasattr(root, logging_setup._CONFIGURED_FLAG):
        delattr(root, logging_setup._CONFIGURED_FLAG)


def test_setup_creates_rotating_file_and_logs_records(tmp_path) -> None:
    _reset_root()
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "logging_config.json").write_text(
        json.dumps(_spec(tmp_path)), encoding="utf-8")
    try:
        logging_setup.setup_logging(config_dir)
        logging.getLogger("p2p.test").info("hello trace")
        logging.getLogger().handlers[0].flush()
        assert "hello trace" in (tmp_path / "logs" / "t.log").read_text(encoding="utf-8")
    finally:
        _reset_root()


def test_setup_is_idempotent_and_survives_missing_config(tmp_path) -> None:
    _reset_root()
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "logging_config.json").write_text(
        json.dumps(_spec(tmp_path)), encoding="utf-8")
    try:
        logging_setup.setup_logging(config_dir)
        first = list(logging.getLogger().handlers)
        logging_setup.setup_logging(config_dir)  # second call: no new handlers
        assert logging.getLogger().handlers == first
    finally:
        _reset_root()
    logging_setup.setup_logging(tmp_path / "absent")  # no config: quiet no-op
    assert not getattr(logging.getLogger(), logging_setup._CONFIGURED_FLAG, False)
