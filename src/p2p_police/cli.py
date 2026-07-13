"""Command-line entry point.

Thin by design: parses arguments and delegates to the SDK facade. Business
logic never lives here (SDK-architecture rule from the submission guidelines).
"""

import argparse
import json

from p2p_police import __version__


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser; kept separate so tests can exercise it directly."""
    parser = argparse.ArgumentParser(
        prog="p2p-police",
        description="Police (Cop) agent for the P2P Cops-and-Robbers game.",
    )
    parser.add_argument(
        "--version", action="version", version=f"p2p-police {__version__}"
    )
    subcommands = parser.add_subparsers(dest="command")
    peer = subcommands.add_parser(
        "peer", help="run one geometric game against the configured opponent"
    )
    peer.add_argument("--config-dir", default="config", help="config directory")
    peer.add_argument("--seed", type=int, default=None, help="policy RNG seed")
    verify = subcommands.add_parser(
        "verify-log", help="recompute every sealed record in a saved game log"
    )
    verify.add_argument("--log", required=True, help="path to a log_*.json artifact")
    replay = subcommands.add_parser("replay", help="step through a saved game with verification")
    replay.add_argument("--log", required=True, help="path to a log_*.json artifact")
    replay.add_argument("--screenshot", default=None, help="save a PNG and exit")
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point: dispatch to the SDK, print the report as JSON."""
    args = build_parser().parse_args(argv)
    if args.command == "peer":
        from p2p_police.sdk.sdk import SimulationSdk

        report = SimulationSdk(args.config_dir).run_peer(seed=args.seed)
        print(json.dumps(report, indent=2))
        return 0 if report.get("digest_match") else 1
    if args.command == "verify-log":
        from p2p_police.sdk.sdk import SimulationSdk

        verdict = SimulationSdk.verify_log(args.log)
        print(verdict)
        return 0 if verdict == "Verified OK" else 1
    if args.command == "replay":
        from p2p_police.gui.replay import ReplayApp

        app = ReplayApp(args.log)
        if args.screenshot:
            app.screenshot(args.screenshot)
            print(f"screenshot saved: {args.screenshot}")
            return 0
        app.run()
        return 0
    return 0
