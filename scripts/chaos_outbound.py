"""D5 outbound-duplicate drill: WE are the duplicating sender (D1's twin).

Arms the same DuplicatingTransport that `peer --duplicate-outbound` uses in
a real game — every one of OUR outbound turn pushes goes out twice — and
proves in-process that a dedup-capable receiver (our own stub) absorbs all
of them: game completes, mutual audit Verified OK, digests match. Against a
foreign peer over a tunnel the identical wrapper demonstrates the sender
half of the duplicate-delivery drill live; point [network] opponent_url at
their MCP URL and run `uv run p2p-police peer --duplicate-outbound`.
Every duplicated send lands in the JSONL evidence as an observed event.
"""

import chaos_lib
from chaos_lib import EvidenceLog

from p2p_police.infra.duplicate_transport import DuplicatingTransport


def drill_d5(config, evidence: EvidenceLog) -> dict:
    name, chaos = "d5_outbound_duplicate", config.private["chaos"]
    dedup = chaos_lib.DedupObserver()  # counts the stub's REAL dedup drops
    box: dict = {}

    def wrap(transport):
        box["wrapper"] = DuplicatingTransport(transport, evidence)
        return box["wrapper"]

    net = chaos_lib.wire_pair(config, chaos, my_wrap=wrap)
    evidence.event(name, "start", turn_timeout_sec=chaos["turn_timeout_seconds"])
    thread, stub_box = chaos_lib.play_in_thread(net["stub"], name)
    mine = chaos_lib.run_classified(net["mine"])
    thread.join(timeout=chaos["turn_timeout_seconds"] * 3)
    dedup.detach()
    duplicated = box["wrapper"].duplicated
    evidence.event(name, "observe", outbound_duplicates=duplicated,
                   duplicates_dropped=dedup.dropped)
    row = chaos_lib.finish_row(evidence, name, mine, stub_box,
                               {"outbound_duplicates": duplicated,
                                "duplicates_dropped": dedup.dropped})
    # The receiver stops draining its inbox once the game-ending message
    # lands, so the duplicate of the FINAL send can rest unconsumed: every
    # duplicate that was actually read must have been dropped (-1 tolerance).
    row["passed"] = (row["outcome"] != "technical_loss" and row["digest_match"]
                     and row["audit"] == "Verified OK" and duplicated >= 2
                     and dedup.dropped >= duplicated - 1)
    return row
