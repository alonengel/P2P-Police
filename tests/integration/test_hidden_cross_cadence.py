"""Two-runtime cross-cadence proof (live-interop regression): police and
thief runtimes as REAL counterparts. The thief opens (demo runtime seeds
the thief's turn before its receive-respond loop), each side numbers its
OWN steps 1, 2, 3... (demo own_state.apply_move), the mutual audit verifies
with a consistent reconstruction, and the live-GUI perception feed fires on
BOTH sides with local truth only — the live-session thief window stayed
black precisely because that callback never fired."""

import threading

import pytest
from hidden_helpers import RecordingTransport, ScriptedBrain, build_runtime, hidden_config, move

from p2p_police.domain.primitives import Role
from p2p_police.infra.mcp_server import PeerInboxes

SNAPSHOT_KEYS = {"turn", "my_cell", "my_role", "belief", "barriers",
                 "my_turn", "hint", "outcome", "game_over"}


def _steps(wire_log, sender: str) -> list[int]:
    return [p["step"] for kind, p in wire_log if kind == "turn" and p["sender"] == sender]


@pytest.mark.slow
def test_cross_cadence_per_sender_steps_to_a_verified_audit(config_dir):
    config = hidden_config(config_dir)
    police_in, thief_in = PeerInboxes(), PeerInboxes()
    wire_log: list = []
    police = build_runtime(Role.POLICE, config,
                           RecordingTransport(thief_in, wire_log), police_in,
                           ScriptedBrain(Role.POLICE, [move("S"), move("E")]))
    thief = build_runtime(Role.THIEF, config,
                          RecordingTransport(police_in, wire_log), thief_in,
                          ScriptedBrain(Role.THIEF, [move("N"), move("W")]))
    feeds: dict[str, list] = {"police": [], "thief": []}
    police.perception.on_snapshot = feeds["police"].append
    thief.perception.on_snapshot = feeds["thief"].append
    reports: dict[str, dict] = {}
    threads = [threading.Thread(target=lambda n=n, r=r: reports.update({n: r.play()}))
               for n, r in (("police", police), ("thief", thief))]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)
    assert set(reports) == {"police", "thief"}, "a hidden runtime deadlocked"

    # The reference cadence: the thief's step 1 is the first turn message.
    first_turn = next(p for kind, p in wire_log if kind == "turn")
    assert first_turn["sender"] == "thief" and first_turn["step"] == 1

    # PER-SENDER numbering: each side counts its OWN steps 1, 2, 3...
    thief_steps, police_steps = _steps(wire_log, "thief"), _steps(wire_log, "police")
    assert thief_steps == list(range(1, len(thief_steps) + 1))
    assert police_steps == list(range(1, len(police_steps) + 1))
    # survival at the thief's own 35th step; the police never answers it
    assert reports["thief"]["outcome"] == "survival"
    assert thief_steps[-1] == 35 and len(thief_steps) == len(police_steps) + 1

    # Mutual audit: verified, and the reconstruction reproduces both games.
    for side in ("police", "thief"):
        assert reports[side]["audit"] == "Verified OK", reports[side]
        assert reports[side]["digest_match"] is True, reports[side]
    assert reports["police"]["outcome"] == reports["thief"]["outcome"]
    assert reports["police"]["end_state_digest"] == reports["thief"]["end_state_digest"]
    assert reports["police"]["turns_completed"] == reports["thief"]["turns_completed"] == 35

    # The live-GUI feed fired for BOTH roles (black-window regression) and
    # carries LOCAL truth only: the fixed key set has no rival-position slot.
    for side, runtime in (("police", police), ("thief", thief)):
        snaps = feeds[side]
        assert len(snaps) >= 1, f"the {side} live feed never fired"
        for snap in snaps:
            assert set(snap) == SNAPSHOT_KEYS
            assert snap["my_role"] == side
            row, col = snap["my_cell"]
            assert 0 <= row < config.grid_size and 0 <= col < config.grid_size
        assert snaps[-1]["my_cell"] == runtime.own.cell
        assert snaps[-1]["game_over"] is True
