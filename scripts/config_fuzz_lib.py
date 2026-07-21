"""Helpers for the legal-config-range fuzzer (scripts/config_fuzz.py):
sampling, wiring, invariants, evidence. Split so each file honors the cap."""

import copy
import json
import random
import tempfile
from pathlib import Path

import chaos_net  # roundtrip-pattern peer servers, reused read-only

from p2p_police.domain.engine import GameEngine
from p2p_police.domain.negotiation import FIXED_TERMS, validate_shared_terms
from p2p_police.domain.primitives import Role
from p2p_police.infra.mcp_client import McpTransport
from p2p_police.peer.deadline import Deadline
from p2p_police.peer.runtime import GeometricRuntime
from p2p_police.shared.config import Config

ROOT = Path(__file__).resolve().parents[1]


def _lookup(shared: dict, dotted: str):
    node = shared
    for key in dotted.split("."):
        node = node[key]
    return node


def sample_shared(rng: random.Random, base: dict, knobs: dict) -> dict:
    """One LEGAL config: minimums raised at random, FIXED terms untouched."""
    shared = copy.deepcopy(base)
    grid = rng.randint(7, int(knobs["grid_size_max"]))
    moves = rng.randint(35, int(knobs["max_moves_max"]))
    board, limits = shared["board_and_agents"], shared["movement_and_barriers"]
    board["grid_size"] = grid
    limits["max_barriers"] = rng.randint(14, int(knobs["max_barriers_max"]))
    limits["max_moves"] = limits["survival_threshold"] = moves
    cop = (rng.randrange(grid), rng.randrange(grid))
    thief = cop
    while thief == cop:  # valid AND distinct start cells
        thief = (rng.randrange(grid), rng.randrange(grid))
    board["cop_start"], board["thief_start"] = list(cop), list(thief)
    assert_legal(shared, base)
    return shared


def assert_legal(shared: dict, base: dict) -> None:
    """The sampler must NEVER fuzz a FIXED term (disqualification risk)."""
    for dotted, expected in FIXED_TERMS.items():
        actual = _lookup(shared, dotted)
        if actual != expected or actual != _lookup(base, dotted):
            raise AssertionError(f"fuzzer touched FIXED term {dotted}: {actual!r}")
    validate_shared_terms(shared)  # Appendix-VI gate: fixed + minimums


def load_config(shared: dict, turn_timeout: float) -> Config:
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "game.json").write_text(json.dumps(shared), encoding="utf-8")
        (Path(tmp) / "game.toml").write_text(
            (ROOT / "config" / "game.toml").read_text(encoding="utf-8"), encoding="utf-8")
        config = Config.load(tmp)
    config.private["network"]["turn_timeout_seconds"] = turn_timeout
    return config


def wire_pair(retry_backoff: float) -> dict:
    """Two real FastMCP servers on ephemeral ports (roundtrip pattern), reused
    across samples; the transports are pinged up-front as the ready wait."""
    my_in, my_port = chaos_net.start_inbox_server("fuzz_mine")
    stub_in, stub_port = chaos_net.start_inbox_server("fuzz_stub")
    mine_t = McpTransport(f"http://127.0.0.1:{stub_port}/mcp", retry_backoff)
    stub_t = McpTransport(f"http://127.0.0.1:{my_port}/mcp", retry_backoff)
    for transport in (mine_t, stub_t):
        transport.send_control({"kind": "ping"}, Deadline(15))
    return {"my_in": my_in, "stub_in": stub_in, "mine_t": mine_t, "stub_t": stub_t}


def build_runtime(role: Role, config: Config, transport, inboxes, brain) -> GeometricRuntime:
    ph = config.pheromones
    engine = GameEngine(config.grid_size, config.cop_start, config.thief_start,
                        config.rule_set(), center_intensity=ph["pheromone_center_intensity"],
                        decay=ph["pheromone_decay"], kernel_size=ph["pheromone_grid_size"])
    return GeometricRuntime(role, config, engine, transport, inboxes, brain)


def check_invariants(shared: dict, boxes: dict, mine: GeometricRuntime) -> list[str]:
    failures = []
    for name in ("mine", "stub"):
        if "report" not in boxes[name]:
            failures.append(f"{name} did not complete: {boxes[name].get('error', 'hung')}")
    if failures:
        return failures
    ours, theirs = boxes["mine"]["report"], boxes["stub"]["report"]
    limits = shared["movement_and_barriers"]
    if ours["outcome"] not in ("capture", "survival"):
        failures.append(f"illegal outcome {ours['outcome']!r}")
    if ours["outcome"] != theirs["outcome"]:
        failures.append(f"outcome split: {ours['outcome']} vs {theirs['outcome']}")
    if not (ours["digest_match"] and theirs["digest_match"]):
        failures.append("end-state digests diverged")
    if len(ours.get("end_state_digest", "")) != 64:
        failures.append("digest not computable")
    if ours["audit"] != "Verified OK" or theirs["audit"] != "Verified OK":
        failures.append(f"audit failed: {ours['audit']} / {theirs['audit']}")
    if ours["turns_completed"] > limits["max_moves"]:
        failures.append(f"turns {ours['turns_completed']} exceed max_moves")
    if len(mine.engine.board.barriers) > limits["max_barriers"]:
        failures.append(f"barrier quota exceeded: {len(mine.engine.board.barriers)}")
    return failures


def write_evidence(summary: dict, path: Path) -> None:
    outcomes = [r["outcome"] for r in summary["results"]]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join([
        "# Config-range fuzz evidence (E5)",
        "",
        f"- Run: {summary['generated_utc']} | role: {summary['role']} | "
        f"seed `{summary['seed']}` (reproducible) | samples: {summary['samples']}",
        f"- Result: **{summary['passed']} passed / {summary['failed']} failed**",
        f"- Sampled bounds (Appendix-VI minimums raised, FIXED terms asserted "
        f"untouched every sample): {json.dumps(summary['bounds'])}",
        f"- Outcomes: {outcomes.count('capture')} captures, "
        f"{outcomes.count('survival')} survivals",
        "- Invariants per sample: game completes, one legal shared outcome, "
        "digests match, mutual audits Verified OK, turns <= max_moves, "
        "barrier quota respected.",
        "- Full rows + any failing config verbatim: `results/experiments/config_fuzz.json`",
        "- Rerun: `uv run python scripts/config_fuzz.py` "
        "(knobs in `config/game.toml [fuzz]`).", ""]), encoding="utf-8")
