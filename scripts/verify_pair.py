"""League pair-verifier CLI (offline; never touches a live game).

Verify that TWO teams' log artifacts of the same game are individually
untampered AND mutually consistent - usable by any third party on any
pair of logs that follow the artifact schema, not just ours.
Run: uv run python scripts/verify_pair.py <log_side_a.json> <log_side_b.json>
"""

import argparse
import sys

from p2p_police.report.pair_verify import verify_pair


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log_a", help="one side's log_<game_id>_gNN.json")
    parser.add_argument("log_b", help="the other side's log of the SAME game")
    args = parser.parse_args(argv)
    row = verify_pair(args.log_a, args.log_b)
    print(f"game_uid : {row['game_uid']}")
    print(f"sides    : {row['sides'][0]} / {row['sides'][1]}")
    print(f"per-side : {row['verdict_a']} / {row['verdict_b']}")
    for problem in row["problems"]:
        print(f"problem  : {problem}")
    print(f"overall  : {row['overall']}")
    return 0 if row["overall"] == "Verified OK" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
