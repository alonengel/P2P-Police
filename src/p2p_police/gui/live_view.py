"""Live GUI (rulebook ch. 7): belief heatmap + turn banner - LOCAL TRUTH ONLY.

Shows my cell, my belief about the rival (deeper red = higher probability),
publicly declared barriers, and the received hint. The rival's true position
is never available here (rules 8-9). Tk owns the main thread; the runtime
plays in a worker thread and feeds snapshots through a queue.
"""

import queue
import tkinter as tk

CELL = 52


def heat_color(value: float, peak: float) -> str:
    """Black -> deep red ramp; the belief argmax burns brightest."""
    intensity = 0 if peak <= 0 else min(1.0, value / peak)
    red = int(22 + 210 * intensity)
    return f"#{red:02x}1620"


def idle_snapshot(grid_size: int, start_cell) -> dict:
    """The pre-game view painted at window-open: the empty board and OUR
    OWN start cell — local truth only, no belief yet, no rival data (the
    live feed replaces it at the first perception snapshot)."""
    return {
        "idle": True,
        "turn": 0,
        "my_cell": tuple(start_cell),
        "belief": [[0.0] * grid_size for _ in range(grid_size)],
        "barriers": [],
        "my_turn": False,
        "hint": "",
        "outcome": "ongoing",
        "game_over": False,
    }


class LiveView:
    """Input: snapshot dicts from the runtime queue. Output: the live window."""

    def __init__(self, grid_size: int, role: str, start_cell=None) -> None:
        try:  # physical-pixel alignment for screenshots
            import ctypes

            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
        self.grid = grid_size
        self.snapshots: queue.Queue[dict] = queue.Queue()
        self.root = tk.Tk()
        self.root.title(f"{role.upper()} - live (local truth only)")
        self.banner = tk.Label(self.root, font=("Segoe UI", 14, "bold"), fg="white", pady=6)
        self.banner.pack(fill="x")
        self.canvas = tk.Canvas(
            self.root, width=grid_size * CELL, height=grid_size * CELL, bg="#0d1117"
        )
        self.canvas.pack(padx=8, pady=4)
        self.info = tk.Label(self.root, font=("Segoe UI", 10), justify="left")
        self.info.pack(fill="x", padx=8, pady=(0, 8))
        self._screenshot_path: str | None = None
        self._done = False
        if start_cell is not None:  # never a black void before the first
            self._render(idle_snapshot(grid_size, start_cell))  # snapshot

    def feed(self, snapshot: dict) -> None:
        """Called from the runtime thread - queue is the only shared state."""
        self.snapshots.put(snapshot)

    def finish(self, outcome: str) -> None:
        """Thread-safe end-of-game signal: release the mainloop even when no
        game_over snapshot was ever fed - technical-loss paths emit none (the
        2026-07-24 live hang: window open forever, report never printed)."""
        self.snapshots.put({"final_outcome": outcome})

    def _poll(self) -> None:
        try:
            while True:
                snap = self.snapshots.get_nowait()
                if "final_outcome" in snap:
                    self.banner.config(bg="#8957e5",
                                       text=f"GAME OVER - {snap['final_outcome']}")
                    self._done = True
                else:
                    self._render(snap)
        except queue.Empty:
            pass
        if self._done:
            if self._screenshot_path:
                self._grab(self._screenshot_path)
            self.root.after(1200, self.root.destroy)
            return
        self.root.after(100, self._poll)

    def _render(self, snap: dict) -> None:
        belief = snap["belief"]
        peak = max(max(row) for row in belief)
        barriers = {tuple(c) for c in snap["barriers"]}
        self.canvas.delete("all")
        for row in range(self.grid):
            for col in range(self.grid):
                x, y = col * CELL, row * CELL
                fill = "#484f58" if (row, col) in barriers else heat_color(belief[row][col], peak)
                self.canvas.create_rectangle(
                    x + 1, y + 1, x + CELL - 1, y + CELL - 1, fill=fill, outline="#30363d"
                )
        row, col = snap["my_cell"]
        x, y = col * CELL + CELL // 2, row * CELL + CELL // 2
        self.canvas.create_oval(x - 16, y - 16, x + 16, y + 16, fill="#1f6feb", outline="white")
        self.canvas.create_text(x, y, text="ME", fill="white", font=("Segoe UI", 10, "bold"))
        if snap.get("idle"):
            self.banner.config(bg="#6e7681", text="WAITING - game starting")
        elif snap["game_over"]:
            self.banner.config(bg="#8957e5", text=f"GAME OVER - {snap['outcome']}")
            self._done = True
        elif snap["my_turn"]:
            self.banner.config(bg="#2ea043", text="YOUR TURN")
        else:
            self.banner.config(bg="#6e7681", text="LOCKED - opponent moving")
        self.info.config(
            text=f"turn {snap['turn']}   belief peak: {peak:.3f}   "
            f'rival hint: "{snap["hint"]}"'
        )

    def _grab(self, path: str) -> None:
        import time

        from PIL import ImageGrab

        self.root.attributes("-topmost", True)
        self.root.update_idletasks()
        self.root.update()
        time.sleep(0.5)
        self.root.update()
        x, y = self.root.winfo_rootx(), self.root.winfo_rooty()
        w, h = self.root.winfo_width(), self.root.winfo_height()
        ImageGrab.grab(bbox=(x, y, x + w, y + h)).save(path)
        print(f"screenshot saved: {path}")

    def run(self, screenshot_path: str | None = None) -> None:
        self._screenshot_path = screenshot_path
        self.root.after(100, self._poll)
        self.root.mainloop()
