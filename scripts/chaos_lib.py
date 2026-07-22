"""Chaos-drill plumbing: in-process stub peer, fault injection, JSONL evidence.

Split from chaos_drills.py (150-line cap; sockets live in chaos_net.py). The
stub opponent is OUR OWN runtime playing the rival role in-process over real
HTTP MCP (the integration-test pattern) — never the twin repo's code
(ADR-0001). Every evidence line is a really-observed event with a real
timestamp; nothing here fabricates data.
"""

import json
import logging
import random
import threading
import time
from datetime import UTC, datetime
from pathlib import Path

import chaos_net

from p2p_police.domain.engine import GameEngine
from p2p_police.domain.primitives import Role
from p2p_police.infra.mcp_client import McpTransport
from p2p_police.peer.deadline import DeadlineExpiredError
from p2p_police.peer.runtime import GeometricRuntime
from p2p_police.sdk.reporting import technical_loss_report
from p2p_police.strategy.brain_base import RandomBrain

MY_ROLE = Role.POLICE  # this repo drills the police live path (twin: thief)


class EvidenceLog:
    """Append-only JSONL evidence: one observed event per line (thread-safe)."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def event(self, drill: str, stage: str, **fields) -> dict:
        record = {"ts": datetime.now(UTC).isoformat(timespec="milliseconds"),
                  "drill": drill, "stage": stage, **fields}
        with self._lock, self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, default=str) + "\n")
        return record


def build_runtime(role: Role, config, transport, inboxes, seed: int) -> GeometricRuntime:
    pheromones = config.pheromones
    engine = GameEngine(
        config.grid_size, config.cop_start, config.thief_start, config.rule_set(),
        center_intensity=pheromones["pheromone_center_intensity"],
        decay=pheromones["pheromone_decay"],
        kernel_size=pheromones["pheromone_grid_size"],
    )
    return GeometricRuntime(role, config, engine, transport, inboxes,
                            RandomBrain(role, random.Random(seed)))


def run_classified(runtime: GeometricRuntime) -> dict:
    """Play to the end; on ANY failure return the SDK's rule-32 classification."""
    started = time.perf_counter()
    try:
        report, error = runtime.play(), None
    except Exception as failure:  # noqa: BLE001 - mirrors sdk.run_peer's net
        report = technical_loss_report(runtime.role, runtime, failure)
        error = f"{type(failure).__name__}: {failure}"
    return {"report": report, "elapsed": round(time.perf_counter() - started, 3),
            "phase": runtime.fsm.state.value, "error": error}


def play_in_thread(runtime: GeometricRuntime, label: str) -> tuple[threading.Thread, dict]:
    box: dict = {}
    thread = threading.Thread(target=lambda: box.update(run_classified(runtime)),
                              name=f"chaos-{label}", daemon=True)
    thread.start()
    return thread, box


def wire_pair(config, chaos, stub_wrap=None, use_proxy: bool = False, my_wrap=None) -> dict:
    """Two real FastMCP servers + transports; mine optionally via the proxy
    and/or wrapped (my_wrap) for sender-side fault injection (D5)."""
    my_in, my_port = chaos_net.start_inbox_server(f"chaos_{MY_ROLE.value}")
    stub_in, stub_port = chaos_net.start_inbox_server(f"chaos_{MY_ROLE.rival.value}_stub")
    proxy, target = None, f"http://127.0.0.1:{stub_port}/mcp"
    if use_proxy:
        proxy = chaos_net.FlappyProxy(stub_port)
        proxy.start()
        target = proxy.url
    counter = chaos_net.RetryCounter()
    mine_t = McpTransport(target, chaos["retry_backoff_sec"],
                          config.response_timeout_sec, sleep=counter.sleep)
    stub_t = McpTransport(f"http://127.0.0.1:{my_port}/mcp", chaos["retry_backoff_sec"],
                          config.response_timeout_sec)
    return {"mine": build_runtime(MY_ROLE, config, my_wrap(mine_t) if my_wrap else mine_t,
                                  my_in, chaos["my_seed"]),
            "stub": build_runtime(MY_ROLE.rival, config,
                                  stub_wrap(stub_t) if stub_wrap else stub_t,
                                  stub_in, chaos["stub_seed"]),
            "proxy": proxy, "retries": counter, "mine_t": mine_t}


def finish_row(evidence: EvidenceLog, name: str, mine: dict, stub_box: dict,
               extra: dict | None = None) -> dict:
    """Record the classify + outcome stages; return the summary row."""
    report = mine["report"]
    evidence.event(name, "classify", classification=report["outcome"],
                   phase=mine["phase"], error=mine["error"])
    row = {"drill": name, "outcome": report["outcome"], "phase": mine["phase"],
           "turns_completed": report["turns_completed"], "digest_match": report["digest_match"],
           "audit": report["audit"], "steps_sealed": report["steps_sealed"],
           "elapsed_sec": mine["elapsed"], "stub_outcome": stub_box.get("report", {}).get("outcome"),
           **(extra or {})}
    evidence.event(name, "outcome", **{k: v for k, v in row.items() if k != "drill"})
    return row


class DedupObserver(logging.Handler):
    """Counts the sealing layer's REAL 'duplicate delivery dropped' records."""

    def __init__(self) -> None:
        super().__init__(level=logging.DEBUG)
        self.dropped = 0
        self._logger = logging.getLogger("p2p_police.peer.sealing")
        self._prior_level = self._logger.level
        self._logger.setLevel(logging.DEBUG)
        self._logger.addHandler(self)

    def emit(self, record: logging.LogRecord) -> None:
        if "duplicate delivery dropped" in record.getMessage():
            self.dropped += 1

    def detach(self) -> None:
        self._logger.removeHandler(self)
        self._logger.setLevel(self._prior_level)


class FaultyStubTransport:
    """Wraps the stub's real McpTransport; injects exactly one drill fault.

    duplicate_turn: resend the stub's Nth commit+reveal pair unchanged (the
    at-least-once double delivery a lost HTTP ack produces).
    silent_from_turn: from the stub's Nth own turn on, send NOTHING more.
    """

    def __init__(self, inner, duplicate_turn: int | None = None,
                 silent_from_turn: int | None = None, on_inject=None) -> None:
        self._inner = inner
        self._duplicate_turn, self._silent_from_turn = duplicate_turn, silent_from_turn
        self._on_inject = on_inject or (lambda kind, payload: None)
        self._own_turns = 0

    def send_agreement(self, payload: dict, deadline) -> dict:
        return self._inner.send_agreement(payload, deadline)

    def send_turn(self, payload: dict, deadline) -> dict:
        if payload.get("kind") == "commit":
            self._own_turns += 1
        if self._silent_from_turn and self._own_turns >= self._silent_from_turn:
            self._on_inject("silent", payload)
            raise DeadlineExpiredError("drill fault: stub went silent mid-game")
        ack = self._inner.send_turn(payload, deadline)
        if self._duplicate_turn == self._own_turns:
            self._inner.send_turn(payload, deadline)  # the duplicate delivery
            self._on_inject("duplicate", payload)
        return ack

    def send_audit(self, payload: dict, deadline) -> dict:
        return self._inner.send_audit(payload, deadline)
