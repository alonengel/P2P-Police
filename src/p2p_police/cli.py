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
        "peer", help="run one game against the configured opponent "
                     "(wire shape from config: bookletter lockstep or hidden reference-v3)"
    )
    peer.add_argument("--config-dir", default="config", help="config directory")
    peer.add_argument("--seed", type=int, default=None, help="policy RNG seed")
    peer.add_argument("--gui", action="store_true", help="show the live local-truth view")
    peer.add_argument("--gui-screenshot", default=None, help="save the final GUI frame as PNG")
    peer.add_argument("--sub-game", type=int, default=None, help="override sub_game_number")
    peer.add_argument("--resume", action="store_true",
                      help="continue a crashed game from the local resume snapshot")
    peer.add_argument("--sparring", action="store_true",
                      help="uncounted warm-up posture: load config/sparring.toml "
                           "(shipped baseline brain, deception disarmed, no email)")
    peer.add_argument("--counted", action="store_true",
                      help="counted league game: arms the CLI half of the lecturer-"
                           "address interlock ([email] counted = true is the other half)")
    peer.add_argument("--wire-shape", choices=("bookletter", "reference"), default=None,
                      help="override [network] wire_shape for this run")
    peer.add_argument("--opponent-group", default=None,
                      help="the peer's 8-char group code for this session; lets us "
                           "DECLARE the derived game_uid at the handshake so a peer "
                           "deriving it differently is refused in seconds instead of "
                           "diverging silently for a whole series")
    peer.add_argument("--duplicate-outbound", action="store_true",
                      help="chaos drill: send every outbound turn push twice "
                           "(receiver-dedup demo; JSONL evidence recorded)")
    verify = subcommands.add_parser(
        "verify-log", help="recompute every sealed record in a saved game log"
    )
    verify.add_argument("--log", required=True, help="path to a log_*.json artifact")
    replay = subcommands.add_parser("replay", help="step through a saved game with verification")
    replay.add_argument("--log", required=True, help="path to a log_*.json artifact")
    replay.add_argument("--screenshot", default=None, help="save a PNG and exit")
    series = subcommands.add_parser("series-result", help="aggregate sub-game logs into the series result")
    series.add_argument("--game-id", required=True)
    series.add_argument("--results-dir", action="append", default=None,
                        help="directory holding sub-game logs; repeat the flag to pool "
                             "BOTH role repos' results (default: results)")
    series.add_argument("--config-dir", default="config")
    series.add_argument("--email", action="store_true",
                        help="after a SUCCESSFUL emit, auto-send the one series report "
                             "email (fires only when [email].mode == 'send'; a refused "
                             "series never emails)")
    series.add_argument("--counted", action="store_true",
                        help="counted league series: arms the CLI half of the lecturer-"
                             "address interlock for the series email")
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point: dispatch to the SDK, print the report as JSON."""
    args = build_parser().parse_args(argv)
    from p2p_police.shared.logging_setup import setup_logging

    setup_logging(getattr(args, "config_dir", "config"))
    if args.command == "peer":
        from p2p_police.sdk.sdk import SimulationSdk

        sdk = SimulationSdk(args.config_dir,
                            private_file="sparring.toml" if args.sparring else "game.toml")
        if args.sparring:  # load-time posture gate: generic play, no email
            from p2p_police.shared.interlock import assert_sparring_posture

            assert_sparring_posture(sdk.config.private)
        if args.counted:  # CLI half of the lecturer-address interlock
            sdk.config.private.setdefault("email", {})["counted_cli_armed"] = True
        if args.sub_game is not None:
            sdk.config.private["game"]["sub_game_number"] = args.sub_game
        if args.wire_shape is not None:
            sdk.config.private.setdefault("network", {})["wire_shape"] = args.wire_shape
        if args.opponent_group is not None:
            sdk.config.private.setdefault("game", {})["opponent_group_id"] = args.opponent_group
        if args.duplicate_outbound:
            sdk.config.private.setdefault("chaos", {})["duplicate_outbound_sends"] = True
        report = sdk.run_peer(seed=args.seed, gui=args.gui,
                              gui_screenshot=args.gui_screenshot, resume=args.resume)
        print(json.dumps(report, indent=2))
        return 0 if report.get("digest_match") else 1
    if args.command == "verify-log":
        from p2p_police.sdk.sdk import SimulationSdk

        verdict = SimulationSdk.verify_log(args.log)
        print(verdict)
        # a qualified "Verified OK (seals only - ...)" still exits clean:
        # the seals are intact; the qualifier names the reduced assurance
        return 0 if verdict.startswith("Verified OK") else 1
    if args.command == "replay":
        from p2p_police.gui.replay import ReplayApp

        app = ReplayApp(args.log)
        if args.screenshot:
            app.screenshot(args.screenshot)
            print(f"screenshot saved: {args.screenshot}")
            return 0
        app.run()
        return 0
    if args.command == "series-result":
        from pathlib import Path

        from p2p_police.domain.game_ids import result_name
        from p2p_police.report.artifacts import emit, git_commit_hash
        from p2p_police.sdk.counted_ledger import record_counted, refuse_repeat_counted
        from p2p_police.sdk.series import (
            SeriesSettlementError,
            aggregate_series,
            maybe_email_series,
        )
        from p2p_police.shared.config import Config

        config = Config.load(args.config_dir)
        if args.counted:  # CLI half of the lecturer-address interlock
            config.private.setdefault("email", {})["counted_cli_armed"] = True
        dirs = args.results_dir or ["results"]
        ours = {"group_id": config.group_id, "github_commit": git_commit_hash(),
                "members": config.private["game"].get("members", []),
                **config.identity_block()}
        try:
            doc, excluded = aggregate_series(
                dirs, args.game_id, config.score_table(),
                config.shared["network_and_league"]["num_games"], ours)
            if args.counted:  # rule 52: one counted series per rival pairing
                refuse_repeat_counted(dirs[0], args.game_id, doc["game_uid"])
        except SeriesSettlementError as error:
            print(f"REFUSED: {error}")
            return 1
        print("".join(f"excluded: {note}\n" for note in excluded), end="")
        path = emit(doc, Path(dirs[0]), result_name(args.game_id))
        print(json.dumps(doc["final_result"], indent=2))
        print(f"written: {path}")
        if args.email:
            from p2p_police.shared.interlock import EmailInterlockError

            try:
                message_id = maybe_email_series(config, doc, path)
            except EmailInterlockError as error:
                print(f"EMAIL REFUSED: {error}")
                return 1
            if message_id and args.counted:  # ledger remembers league reports
                record_counted(dirs[0], args.game_id, doc["game_uid"], message_id)
            if message_id:
                print(f"emailed: {message_id}")
        return 0
    return 0
