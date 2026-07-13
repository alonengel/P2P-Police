"""Command-line entry point.

Thin by design: parses arguments and delegates to the SDK facade. Business
logic never lives here (SDK-architecture rule from the submission guidelines).
"""

import argparse

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
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Subcommands (peer, replay, selfplay) arrive with the SDK."""
    build_parser().parse_args(argv)
    return 0
