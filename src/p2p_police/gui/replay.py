"""Replay viewer (rulebook ch. 7) — the retrospective witness.

Loads a log artifact, re-verifies every sealed record (the same math as
`verify-log`), and steps through the reconstructed game. The verdict banner
is binary: green "Verified OK" or red "TAMPERED - game void". Post-game the
log is revealed evidence, so showing both agents here breaks no rule (the
LIVE view is the one restricted to local truth).
"""

import json
import tkinter as tk
from pathlib import Path

from p2p_police.domain import crypto

CELL = 52
COLORS = {"police": "#1f6feb", "thief": "#d29922", "barrier": "#484f58"}


def load_steps(log_path: str) -> tuple[dict, list[dict], str]:
    """Merge own+opponent records into step order; verdict from own seals."""
    doc = json.loads(Path(log_path).read_text(encoding="utf-8"))
    verdict = "Verified OK"
    verifiable = doc.get("records", []) + [
        r for r in doc.get("opponent_records", []) if "nonce" in r
    ]
    for record in verifiable:
        if not crypto.verify_commit(record["payload"], record["nonce"], record["commit"]):
            verdict = "TAMPERED"
    merged = [r["payload"] for r in doc.get("records", [])]
    merged += [r["payload"] for r in doc.get("opponent_records", [])]
    merged.sort(key=lambda p: p["step"])
    return doc, merged, verdict


def replay_states(steps: list[dict], grid: int, cop, thief) -> list[dict]:
    """Reconstruct (positions, barriers, hint) after every half-turn."""
    positions = {"police": tuple(cop), "thief": tuple(thief)}
    barriers: set = set()
    deltas = {"N": (-1, 0), "S": (1, 0), "E": (0, 1), "W": (0, -1), "STAY": (0, 0)}
    states = [{"positions": dict(positions), "barriers": set(), "hint": "", "actor": "-"}]
    for payload in steps:
        action, actor = payload["action"], payload["role"]
        if action["type"] == "barrier":
            barriers.add(tuple(action["cell"]))
        else:
            dr, dc = deltas[action["move"]]
            row, col = positions[actor]
            positions[actor] = (row + dr, col + dc)
        states.append(
            {"positions": dict(positions), "barriers": set(barriers),
             "hint": payload.get("hint", ""), "actor": actor}
        )
    return states


class ReplayApp:
    """Input: a log artifact + board geometry. Output: an auditable replay."""

    def __init__(self, log_path: str, grid=None, cop=None, thief=None) -> None:
        try:  # align Tk logical coords with physical pixels for ImageGrab
            import ctypes

            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
        self.doc, steps, self.verdict = load_steps(log_path)
        # Geometry comes from the game's OWN archived config artifact (rule 20:
        # a third party must replay negotiated terms, not our defaults).
        from p2p_police.report import lookup

        auto_grid, auto_cop, auto_thief = lookup.geometry(
            lookup.terms_for_log(self.doc, log_path))
        grid = grid or auto_grid
        cop, thief = cop or auto_cop, thief or auto_thief
        self.states = replay_states(steps, grid, cop, thief)
        self.grid, self.index = grid, len(self.states) - 1
        self.root = tk.Tk()
        self.root.title(f"Replay - {Path(log_path).name}")
        ok = self.verdict == "Verified OK"
        self.banner = tk.Label(
            self.root, font=("Segoe UI", 14, "bold"), fg="white", pady=6,
            bg="#2ea043" if ok else "#da3633",
            text=f"{self.verdict}  ({len(self.states) - 1} sealed steps)"
            if ok else f"{self.verdict} - game void",
        )
        self.banner.pack(fill="x")
        self.canvas = tk.Canvas(self.root, width=grid * CELL, height=grid * CELL, bg="#0d1117")
        self.canvas.pack(padx=8, pady=4)
        self.info = tk.Label(self.root, font=("Segoe UI", 10), justify="left")
        self.info.pack(fill="x", padx=8)
        controls = tk.Frame(self.root)
        controls.pack(pady=6)
        for text, step in (("<< first", -10**6), ("< prev", -1), ("next >", 1), ("last >>", 10**6)):
            tk.Button(controls, text=text, command=lambda s=step: self.jump(s)).pack(
                side="left", padx=4
            )
        self.draw()

    def jump(self, delta: int) -> None:
        self.index = max(0, min(len(self.states) - 1, self.index + delta))
        self.draw()

    def draw(self) -> None:
        state = self.states[self.index]
        self.canvas.delete("all")
        for row in range(self.grid):
            for col in range(self.grid):
                x, y = col * CELL, row * CELL
                fill = COLORS["barrier"] if (row, col) in state["barriers"] else "#161b22"
                self.canvas.create_rectangle(
                    x + 1, y + 1, x + CELL - 1, y + CELL - 1, fill=fill, outline="#30363d"
                )
        for role, mark in (("police", "C"), ("thief", "T")):
            row, col = state["positions"][role]
            x, y = col * CELL + CELL // 2, row * CELL + CELL // 2
            self.canvas.create_oval(
                x - 16, y - 16, x + 16, y + 16, fill=COLORS[role], outline="white"
            )
            self.canvas.create_text(x, y, text=mark, fill="white", font=("Segoe UI", 12, "bold"))
        self.info.config(
            text=f"step {self.index}/{len(self.states) - 1}   actor: {state['actor']}   "
            f'hint: "{state["hint"]}"'
        )

    def screenshot(self, out_path: str) -> None:
        """Render once and save the window as PNG (submission evidence)."""
        import time

        from PIL import ImageGrab

        self.root.attributes("-topmost", True)  # win the z-order for the grab
        self.root.update_idletasks()
        self.root.update()
        time.sleep(0.5)  # let the compositor actually paint us
        self.root.update()
        x, y = self.root.winfo_rootx(), self.root.winfo_rooty()
        w, h = self.root.winfo_width(), self.root.winfo_height()
        ImageGrab.grab(bbox=(x, y, x + w, y + h)).save(out_path)

    def run(self) -> None:
        self.root.mainloop()
