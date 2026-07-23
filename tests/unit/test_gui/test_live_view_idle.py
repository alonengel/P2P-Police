"""Idle-state paint (live-session finding): the window shows the empty
board and OUR OWN start cell from the moment it opens — never a black void
until the first snapshot. Structural only: no Tk object is created here."""

from p2p_police.gui.live_view import idle_snapshot

IDLE_KEYS = {"idle", "turn", "my_cell", "belief", "barriers",
             "my_turn", "hint", "outcome", "game_over"}


def test_idle_snapshot_paints_the_empty_board_and_own_start():
    snap = idle_snapshot(7, (0, 0))
    assert set(snap) == IDLE_KEYS
    assert snap["idle"] is True
    assert snap["turn"] == 0
    assert snap["my_cell"] == (0, 0)
    assert snap["belief"] == [[0.0] * 7 for _ in range(7)]
    assert snap["barriers"] == []
    assert snap["my_turn"] is False and snap["game_over"] is False
    assert snap["outcome"] == "ongoing" and snap["hint"] == ""


def test_idle_snapshot_is_local_truth_only():
    """Rules 8-9 hold before the game too: only OUR start cell appears;
    the key set has no field a rival position could ride in."""
    snap = idle_snapshot(9, [4, 2])
    assert snap["my_cell"] == (4, 2)  # list input normalized to a cell tuple
    assert not (set(snap) - IDLE_KEYS)
    banned = {"rival", "opponent", "positions", "thief", "police"}
    assert not (set(snap) & banned)
