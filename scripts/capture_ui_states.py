"""Render the live view's turn states with synthetic snapshots and save PNGs
(guidelines section 10: a screenshot of every screen/state).

Run: uv run python scripts/capture_ui_states.py
"""

from p2p_police.gui.live_view import LiveView


def snapshot(my_turn: bool, turn: int) -> dict:
    belief = [[0.01] * 7 for _ in range(7)]
    belief[5][5], belief[5][4], belief[4][5] = 0.18, 0.09, 0.09
    return {
        "turn": turn,
        "my_cell": (2, 2),
        "my_role": "police",
        "belief": belief,
        "barriers": [(0, 0), (3, 1)],
        "my_turn": my_turn,
        "hint": "Slipping south past the docks.",
        "outcome": "ongoing",
        "game_over": False,
    }


def capture(my_turn: bool, out_path: str) -> None:
    view = LiveView(7, "police")
    view._render(snapshot(my_turn, 12))
    view._grab(out_path)
    view.root.destroy()


if __name__ == "__main__":
    capture(True, "assets/live_your_turn.png")
    capture(False, "assets/live_locked.png")
