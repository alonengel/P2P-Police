"""Runtime-diagnostics logging, wired from config/logging_config.json.

Two log concepts stay strictly separate (book ch. 8: the Log Manager owns the
official record): the AUDITABLE game artifacts live in results/ (committed
evidence), while THIS module wires the ephemeral runtime trace - a rotating
file under gitignored logs/ plus stderr - so internal events (gatekeeper
calls, duplicate drops, watchdog fires) leave a trace without ever polluting
the official record. Console output goes to stderr: stdout stays pure JSON.
"""

import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

_CONFIGURED_FLAG = "_p2p_logging_configured"


def setup_logging(config_dir: str | Path = "config") -> None:
    """Idempotent root-logger setup from the versioned logging config."""
    path = Path(config_dir) / "logging_config.json"
    root = logging.getLogger()
    if getattr(root, _CONFIGURED_FLAG, False) or not path.is_file():
        return  # already wired, or diagnostics unconfigured: games still run
    spec = json.loads(path.read_text(encoding="utf-8"))
    setattr(root, _CONFIGURED_FLAG, True)
    root.setLevel(spec.get("level", "INFO"))
    formatter = logging.Formatter(
        spec.get("format", "%(asctime)s %(levelname)s %(name)s %(message)s")
    )
    file_spec = spec.get("file", {})
    if file_spec.get("enabled"):
        target = Path(file_spec.get("path", "logs/p2p.log"))
        target.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            target,
            maxBytes=int(file_spec.get("max_bytes", 1_048_576)),
            backupCount=int(file_spec.get("backup_count", 3)),
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)
    console_spec = spec.get("console", {})
    if console_spec.get("enabled"):
        console = logging.StreamHandler()  # stderr by default - NOT stdout
        console.setLevel(console_spec.get("level", "INFO"))
        console.setFormatter(formatter)
        root.addHandler(console)
