"""War Dogs mortar/artillery range finder. Watches the clipboard for in-game
'mark coordinates' pastes (x98.43, y110.38) and shows the distance to target."""

import math
import re
import socket
import sys
import tkinter as tk
from pathlib import Path

COORD = re.compile(r"x\s*(-?\d+(?:\.\d+)?)\s*,?\s*y\s*(-?\d+(?:\.\d+)?)", re.I)
UNITS_TO_METERS = 100
LOCK_PORT = 49731  # ponytail: single instance via a bound port, no lockfile to clean up
POS_FILE = Path(__file__).with_name(".window-pos")

BG = "#12160f"
FG = "#c8d6b0"
DIM = "#6c7a5a"
HOT = "#e8b04b"


def parse(text):
    """First 'x<num>, y<num>' in the text, or None."""
    m = COORD.search(text)
    return (float(m.group(1)), float(m.group(2))) if m else None


def distance(a, b):
    """Meters between two map coordinates."""
    return math.hypot(a[0] - b[0], a[1] - b[1]) * UNITS_TO_METERS


def weapon(meters):
    if meters <= 700:
        return "MORTAR", FG
    if meters < 750:
        return "TOO FAR FOR MORTAR, TOO CLOSE FOR ARTY", HOT
    if meters <= 2630:
        return "ARTILLERY", FG
    return "OUT OF RANGE", HOT


class App:
    def __init__(self, root):
        self.root = root
        self.self_pos = None
        self.target = None
        self.last_clip = None

        root.title("War Dogs Range")
        root.configure(bg=BG)
        root.attributes("-topmost", True)
        root.geometry(POS_FILE.read_text().strip() if POS_FILE.exists() else "320x170+40+40")
        root.protocol("WM_DELETE_WINDOW", self.close)

        self.self_label = self._row("SELF", "waiting for copy...")
        self.target_label = self._row("TARGET", "-")

        self.range_label = tk.Label(root, text="--", bg=BG, fg=HOT, font=("Consolas", 40, "bold"))
        self.range_label.pack(pady=(8, 0))
        self.weapon_label = tk.Label(root, text="", bg=BG, fg=DIM, font=("Consolas", 9))
        self.weapon_label.pack()

        tk.Button(
            root, text="Clear Self", command=self.clear_self, bg=BG, fg=DIM,
            font=("Consolas", 8), relief="flat", activebackground=BG, activeforeground=FG,
        ).pack(pady=(6, 0))

        self.poll()

    def _row(self, name, value):
        line = tk.Frame(self.root, bg=BG)
        line.pack(fill="x", padx=10)
        tk.Label(line, text=name, bg=BG, fg=DIM, font=("Consolas", 9), width=7, anchor="w").pack(side="left")
        label = tk.Label(line, text=value, bg=BG, fg=FG, font=("Consolas", 9), anchor="w")
        label.pack(side="left")
        return label

    def poll(self):
        try:
            clip = self.root.clipboard_get()
        except tk.TclError:
            clip = None
        if clip and clip != self.last_clip:
            self.last_clip = clip
            coords = parse(clip)
            if coords:
                self.accept(coords)
        self.root.after(300, self.poll)

    def accept(self, coords):
        if self.self_pos is None:
            self.self_pos = coords
        else:
            self.target = coords
        self.render()

    def clear_self(self):
        self.self_pos = self.target = self.last_clip = None
        self.render()

    def render(self):
        fmt = lambda c: f"x{c[0]:g}, y{c[1]:g}"
        self.self_label.config(text=fmt(self.self_pos) if self.self_pos else "waiting for copy...")
        self.target_label.config(text=fmt(self.target) if self.target else "-")
        if self.self_pos and self.target:
            meters = int(distance(self.self_pos, self.target))
            text, color = weapon(meters)
            self.range_label.config(text=f"{meters} m")
            self.weapon_label.config(text=text, fg=color)
        else:
            self.range_label.config(text="--")
            self.weapon_label.config(text="")

    def close(self):
        POS_FILE.write_text(self.root.geometry())
        self.root.destroy()


def claim_single_instance():
    """Hold a local port for the process lifetime. False if one is already running."""
    lock = socket.socket()
    try:
        lock.bind(("127.0.0.1", LOCK_PORT))
    except OSError:
        return False
    globals()["_lock"] = lock
    return True


def selftest():
    assert parse("x98.43, y110.38") == (98.43, 110.38)
    assert parse("TEAM x94.53, y109.03") == (94.53, 109.03)
    assert parse("x98.43 y110.38") == (98.43, 110.38)
    assert parse("gg wp 12 nice") is None
    assert parse("") is None
    assert int(distance((98.43, 110.38), (94.53, 109.03))) == 412
    assert int(distance((10, 10), (10, 10))) == 0
    assert weapon(412)[0] == "MORTAR"
    assert weapon(1500)[0] == "ARTILLERY"
    assert weapon(3000)[0] == "OUT OF RANGE"
    print("ok")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    elif not claim_single_instance():
        sys.exit()
    else:
        root = tk.Tk()
        App(root)
        root.mainloop()
