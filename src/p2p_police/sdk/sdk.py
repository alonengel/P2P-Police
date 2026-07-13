"""SimulationSdk — the single business entry point (guidelines section 4).

Every consumer (CLI now; GUI and league tooling later) goes through here.
Assembles config, engine, transport and runtime; owns no game logic itself.
"""

import random
import time

from p2p_police.domain.engine import GameEngine
from p2p_police.domain.primitives import Role
from p2p_police.infra.mcp_client import McpTransport
from p2p_police.infra.mcp_server import PeerInboxes, build_peer_server, start_peer_server
from p2p_police.peer.runtime import GeometricRuntime
from p2p_police.shared.config import Config
from p2p_police.strategy.brain_base import resolve_brain

MY_ROLE = Role.POLICE  # this repo IS the police agent (twin repo: thief)
SHUTDOWN_GRACE_SEC = 1.5  # let the opponent's final MCP session close cleanly


class SimulationSdk:
    """Facade over the peer's flows.

    Input: a config directory. Output: end reports as plain dicts.
    Setup: `SimulationSdk(config_dir)`; heavy resources start per call.
    """

    def __init__(self, config_dir: str = "config") -> None:
        self.config = Config.load(config_dir)

    def build_engine(self) -> GameEngine:
        pheromones = self.config.pheromones
        return GameEngine(
            self.config.grid_size,
            self.config.cop_start,
            self.config.thief_start,
            self.config.rule_set(),
            center_intensity=pheromones["pheromone_center_intensity"],
            decay=pheromones["pheromone_decay"],
            kernel_size=pheromones["pheromone_grid_size"],
        )

    def run_peer(self, seed: int | None = None) -> dict:
        """Start our MCP server, connect to the opponent, play one geometric
        game to completion, and return the end report."""
        inboxes = PeerInboxes()
        server = build_peer_server(inboxes, name=f"p2p_{MY_ROLE.value}_peer")
        start_peer_server(server, self.config.my_port)
        transport = McpTransport(
            self.config.opponent_url,
            self.config.retry_backoff_sec,
            self.config.response_timeout_sec,
        )
        runtime = GeometricRuntime(
            MY_ROLE,
            self.config,
            self.build_engine(),
            transport,
            inboxes,
            resolve_brain(self.config, MY_ROLE, random.Random(seed)),
        )
        report = runtime.play()
        # Shutdown grace: our daemon server dies with the process; give the
        # opponent's in-flight final exchange a moment to complete cleanly.
        time.sleep(SHUTDOWN_GRACE_SEC)
        return report
