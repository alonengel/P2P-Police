"""Outbound-duplicate drill (D5): OUR sender resends every turn push; the
receiving side's dedup absorbs all of it and the mutual audit still verifies
— proven on BOTH wire shapes (bookletter lockstep and hidden reference-v3)."""

import json
import random
import sys
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import chaos_drills  # noqa: E402
from chaos_lib import EvidenceLog  # noqa: E402
from hidden_helpers import RecordingTransport, build_runtime, hidden_config  # noqa: E402

from p2p_police.domain.primitives import Role  # noqa: E402
from p2p_police.infra.duplicate_transport import (  # noqa: E402
    DuplicatingTransport,
    JsonlEvidence,
)
from p2p_police.infra.mcp_server import PeerInboxes  # noqa: E402
from p2p_police.strategy.brain_base import RandomBrain  # noqa: E402


@pytest.mark.slow
def test_d5_duplicate_sending_game_verifies_and_records_evidence(tmp_path: Path) -> None:
    path = tmp_path / "d5.jsonl"
    row = chaos_drills.drill_d5(chaos_drills.load_config(), EvidenceLog(path))
    assert row["passed"], row
    assert row["audit"] == "Verified OK" and row["digest_match"]  # dedup absorbed it
    lines = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    duplicates = [line for line in lines if line["stage"] == "duplicate"]
    assert len(duplicates) == row["outbound_duplicates"] >= 2  # every resend evidenced
    # every duplicate the receiver read was dropped (the final one may rest
    # unconsumed: the receiver stops draining after the game-ending message)
    assert row["duplicates_dropped"] >= row["outbound_duplicates"] - 1


def test_hidden_wire_duplicate_sending_still_verifies(config_dir: Path, tmp_path: Path) -> None:
    config = hidden_config(config_dir)
    police_in, thief_in = PeerInboxes(), PeerInboxes()
    wire_log: list = []
    evidence_path = tmp_path / "hidden_duplicates.jsonl"
    mine = DuplicatingTransport(RecordingTransport(thief_in, wire_log),
                                JsonlEvidence(evidence_path))
    police = build_runtime(Role.POLICE, config, mine, police_in,
                           RandomBrain(Role.POLICE, random.Random(7)))
    thief = build_runtime(Role.THIEF, config, RecordingTransport(police_in, wire_log),
                          thief_in, RandomBrain(Role.THIEF, random.Random(99)))
    reports: dict = {}
    threads = [threading.Thread(target=lambda n=n, r=r: reports.update({n: r.play()}))
               for n, r in (("police", police), ("thief", thief))]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)
    assert set(reports) == {"police", "thief"}, "a hidden runtime deadlocked"
    assert reports["police"]["audit"] == "Verified OK"
    assert reports["thief"]["audit"] == "Verified OK"  # our duplicates were absorbed
    assert mine.duplicated >= 1
    lines = [json.loads(line)
             for line in evidence_path.read_text(encoding="utf-8").splitlines()]
    assert len([line for line in lines if line["stage"] == "duplicate"]) == mine.duplicated
