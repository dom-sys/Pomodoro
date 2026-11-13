

import csv
import math
import time
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import font as tkfont
from tkinter import messagebox, ttk

# --------------------------------------------------------------------------
# Settings (change these to taste)
# --------------------------------------------------------------------------
WORK_MIN = 60
BREAK_MIN = 5
LONG_BREAK_MIN = 15      # taken after every LONG_BREAK_EVERY focus sessions
LONG_BREAK_EVERY = 4
LOG_FILE = Path(__file__).resolve().with_name("pomodoro_log.csv")
LOG_FIELDS = ["activity", "completed_at", "duration_minutes"]

# --------------------------------------------------------------------------
# Palette
# --------------------------------------------------------------------------
BG = "#ffe9ef"
DARK = "#4a1a2c"
RED = "#e63950"
RED_D = "#b8213f"
RED_LIGHT = "#ff8fa3"
SEED = "#ffd84d"
GREEN = "#58b368"
GREEN_D = "#2e8b4f"
LEAF_OUT = "#1d4d2b"
STEM = "#7a4b2a"
CREAM = "#fff6dc"
EMPTY_BAR = "#e8d9bf"
ORANGE = "#ff9f45"
PURPLE = "#9b7ede"

# --------------------------------------------------------------------------
# 3x5 pixel font (each glyph is 5 rows of 0/1)
# --------------------------------------------------------------------------
GLYPHS = {
    "A": ("010", "101", "111", "101", "101"),
    "B": ("110", "101", "110", "101", "110"),
    "C": ("011", "100", "100", "100", "011"),
    "D": ("110", "101", "101", "101", "110"),
    "E": ("111", "100", "110", "100", "111"),
    "F": ("111", "100", "110", "100", "100"),
    "G": ("011", "100", "101", "101", "011"),
    "H": ("101", "101", "111", "101", "101"),
    "I": ("111", "010", "010", "010", "111"),
    "J": ("001", "001", "001", "101", "010"),
    "K": ("101", "101", "110", "101", "101"),
    "L": ("100", "100", "100", "100", "111"),
    "M": ("101", "111", "111", "101", "101"),
    "N": ("110", "101", "101", "101", "101"),
    "O": ("010", "101", "101", "101", "010"),
    "P": ("110", "101", "110", "100", "100"),
    "Q": ("010", "101", "101", "110", "011"),
    "R": ("110", "101", "110", "101", "101"),
    "S": ("011", "100", "010", "001", "110"),
    "T": ("111", "010", "010", "010", "010"),
    "U": ("101", "101", "101", "101", "111"),
    "V": ("101", "101", "101", "101", "010"),
    "W": ("101", "101", "111", "111", "101"),
    "X": ("101", "101", "010", "101", "101"),
    "Y": ("101", "101", "010", "010", "010"),
    "Z": ("111", "001", "010", "100", "111"),
    "0": ("111", "101", "101", "101", "111"),
    "1": ("010", "110", "010", "010", "111"),
    "2": ("110", "001", "010", "100", "111"),
    "3": ("110", "001", "010", "001", "110"),
    "4": ("101", "101", "111", "001", "001"),
    "5": ("111", "100", "110", "001", "110"),
    "6": ("011", "100", "111", "101", "111"),
    "7": ("111", "001", "010", "010", "010"),
    "8": ("111", "101", "111", "101", "111"),
    "9": ("111", "101", "111", "001", "110"),
    ":": ("0", "1", "0", "1", "0"),
    "-": ("000", "000", "111", "000", "000"),
    "!": ("1", "1", "1", "0", "1"),
    ".": ("0", "0", "0", "0", "1"),
    " ": ("00", "00", "00", "00", "00"),
}


def text_size(text, px):
    """Pixel width/height of `text` drawn with the pixel font at `px` scale."""
    text = text.upper()
    if not text:
        return 0, 5 * px
    units = sum(len(GLYPHS.get(ch, GLYPHS[" "])[0]) for ch in text) + (len(text) - 1)
    return units * px, 5 * px


def draw_text(canvas, cx, cy, text, px, color, tag="", shadow=None):
    """Draw centred pixel text. shadow=(dx, dy, color) adds a drop shadow."""
    text = text.upper()
    w, h = text_size(text, px)
    passes = []
    if shadow:
        passes.append((shadow[0], shadow[1], shadow[2]))
    passes.append((0, 0, color))
    for dx, dy, col in passes:
        x = cx - w / 2 + dx
        y = cy - h / 2 + dy
        for ch in text:
            glyph = GLYPHS.get(ch, GLYPHS[" "])
            for r, row in enumerate(glyph):
                for c, bit in enumerate(row):
                    if bit == "1":
                        canvas.create_rectangle(
                            x + c * px, y + r * px,
                            x + (c + 1) * px, y + (r + 1) * px,
                            fill=col, outline="", tags=tag)
            x += (len(glyph[0]) + 1) * px


def lighten(hexcolor, amt):
    r, g, b = (int(hexcolor[i:i + 2], 16) for i in (1, 3, 5))
    r, g, b = (int(v + (255 - v) * amt) for v in (r, g, b))
    return f"#{r:02x}{g:02x}{b:02x}"


# --------------------------------------------------------------------------
# Pixel-style widgets
# --------------------------------------------------------------------------
class PixelLabel(tk.Canvas):
    def __init__(self, parent, text="", px=3, color=DARK, bg=BG):
        super().__init__(parent, bg=bg, highlightthickness=0, bd=0)
        self.px = px
        self.fg = color
        self.set(text)

    def set(self, text):
        self.delete("all")
        w, h = text_size(text, self.px)
        self.configure(width=w + 4, height=h + 4)
        draw_text(self, (w + 4) / 2, (h + 4) / 2, text, self.px, self.fg)


class PixelButton(tk.Canvas):
    DEPTH = 5

    def __init__(self, parent, text, command, color, width=98, height=48, bg=BG):
        super().__init__(parent, width=width, height=height, bg=bg,
                         highlightthickness=0, bd=0, cursor="hand2")
        self.label = text
        self.on_click = command
        self.face_color = color
        self.bw, self.bh = width, height
        self.pressed = False
        self.hover = False
        self.bind("<ButtonPress-1>", self._press)
        self.bind("<ButtonRelease-1>", self._release)
        self.bind("<Enter>", lambda e: self._set_hover(True))
        self.bind("<Leave>", lambda e: self._set_hover(False))
        self._draw()

    def set_text(self, text):
        self.label = text
        self._draw()

    def set_color(self, color):
        self.face_color = color
        self._draw()

    def _set_hover(self, value):
        self.hover = value
        self._draw()

    def _press(self, _event):
        self.pressed = True
        self._draw()

    def _release(self, event):
        was_pressed = self.pressed
        self.pressed = False
        self._draw()
        if was_pressed and 0 <= event.x <= self.bw and 0 <= event.y <= self.bh:
            self.on_click()

    def _notched(self, x0, y0, x1, y1, n, fill):
        pts = [x0 + n, y0, x1 - n, y0, x1 - n, y0 + n, x1, y0 + n,
               x1, y1 - n, x1 - n, y1 - n, x1 - n, y1, x0 + n, y1,
               x0 + n, y1 - n, x0, y1 - n, x0, y0 + n, x0 + n, y0 + n]
        self.create_polygon(pts, fill=fill, outline=fill)

    def _draw(self):
        self.delete("all")
        d = self.DEPTH
        off = d - 1 if self.pressed else 0
        top, bottom = off, self.bh - d + off
        face = lighten(self.face_color, 0.15) if self.hover and not self.pressed \
            else self.face_color
        if not self.pressed:
            self._notched(0, d, self.bw, self.bh, 4, DARK)       # 3D "base"
        self._notched(0, top, self.bw, bottom, 4, DARK)           # outline
        self._notched(3, top + 3, self.bw - 3, bottom - 3, 3, face)
        self.create_rectangle(6, top + 3, self.bw - 6, top + 6,
                              fill=lighten(face, 0.35), outline="")
        draw_text(self, self.bw / 2, (top + bottom) / 2, self.label, 3, CREAM,
                  shadow=(2, 2, DARK))


# --------------------------------------------------------------------------
# Strawberry geometry (grid of S-pixel cells)
# --------------------------------------------------------------------------
S = 10                      # size of one art pixel on screen
GW, GH = 32, 35             # grid size of the berry canvas
BODY_TOP, BODY_ROWS = 7, 28
SCREEN = (6, 13, 26, 25)    # x0, y0, x1, y1 (cells, end exclusive) - the "LCD"
FACE_BOX = (7, 26, 24, 31)  # x0, y0, x1, y1 inclusive - kept free of seeds
HIGHLIGHT = [(8, 9), (9, 9), (7, 10), (7, 11)]
N4 = ((1, 0), (-1, 0), (0, 1), (0, -1))

# Left half of the leaf crown (mirrored to make the right half)
CROWN_HALF = [
    "........LT",
    "........LT",
    "..L....LGG",
    ".LGL..LGGg",
    "LGGGLLGGgg",
    ".LGGGGGGgg",
    "..LLGGGGgg",
    "....LLGGgg",
]
CROWN_COLORS = {"L": LEAF_OUT, "G": GREEN, "g": GREEN_D, "T": STEM}


def berry_cells():
    """Return (set of cells inside the berry, half-width per row)."""
    inside, half = set(), {}
    for y in range(BODY_TOP, BODY_TOP + BODY_ROWS):
        t = (y - BODY_TOP + 0.5) / BODY_ROWS
        if t < 0.4:
            hw = 15 * (1 - ((0.4 - t) / 0.4) ** 2.4) ** (1 / 2.4)
        else:
            u = (t - 0.4) / 0.6
            hw = 15 * (1 - u ** 1.7) ** 0.6
        half[y] = hw
        for x in range(GW):
            if abs(x + 0.5 - 16) <= hw:
                inside.add((x, y))
    return inside, half


# --------------------------------------------------------------------------
# Log helpers
# --------------------------------------------------------------------------
def read_log():
    if not LOG_FILE.exists():
        return []
    try:
        with open(LOG_FILE, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))
    except OSError:
        return []


# --------------------------------------------------------------------------
# Main application
# --------------------------------------------------------------------------
class PomodoroApp:
    def __init__(self, root):
        self.root = root
        root.title("Strawberry Pomodoro")
        root.configure(bg=BG)
        root.resizable(False, False)

        # Fonts: use "Press Start 2P" if installed, otherwise Courier.
        families = set(tkfont.families(root))
        if "Press Start 2P" in families:
            self.ui_font = ("Press Start 2P", 8)
            self.entry_font = ("Press Start 2P", 10)
        else:
            self.ui_font = ("Courier", 11, "bold")
            self.entry_font = ("Courier", 15, "bold")
        self._setup_styles()

        # State
        self.mode = "focus"           # "focus" or "break"
        self.break_is_long = False
        self.state = "idle"           # "idle", "running", "paused"
        self.total = WORK_MIN * 60
        self.remaining = float(self.total)
        self.end_time = None
        self.after_id = None
        self.session_title = ""
        self.focus_count = 0
        self.today_count = self._count_today()
        self.log_win = None
        self.tree = None
        self.log_total = None

        self._build_ui()
        self._redraw()

    # ---------------------------------------------------------------- UI
    def _setup_styles(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("Retro.Treeview", background=CREAM, fieldbackground=CREAM,
                        foreground=DARK, rowheight=26, borderwidth=0,
                        font=self.ui_font)
        style.configure("Retro.Treeview.Heading", background=RED, foreground="white",
                        relief="flat", font=self.ui_font)
        style.map("Retro.Treeview",
                  background=[("selected", RED_LIGHT)],
                  foreground=[("selected", DARK)])
        style.map("Retro.Treeview.Heading", background=[("active", RED_D)])
        style.configure("Retro.Vertical.TScrollbar", background=RED,
                        troughcolor=CREAM, bordercolor=DARK, arrowcolor="white",
                        lightcolor=RED, darkcolor=RED_D)

    def _build_ui(self):
        self.canvas = tk.Canvas(self.root, width=GW * S, height=GH * S, bg=BG,
                                highlightthickness=0, bd=0)
        self.canvas.pack(padx=20, pady=(14, 0))
        self._draw_berry()

        wrap = tk.Frame(self.root, bg=BG)
        wrap.pack(fill="x", padx=20, pady=(8, 0))

        PixelLabel(wrap, "ACTIVITY", px=3, color=DARK).pack(anchor="w", pady=(0, 4))
        border = tk.Frame(wrap, bg=DARK, padx=3, pady=3)
        border.pack(fill="x")
        self.entry = tk.Entry(border, font=self.entry_font, relief="flat", bd=0,
                              bg=CREAM, fg=DARK, insertbackground=DARK,
                              disabledbackground="#f1e2bd", disabledforeground=DARK,
                              highlightthickness=0)
        self.entry.pack(fill="x", ipady=6, ipadx=4)
        self.entry.bind("<Return>", lambda e: self.start() if self.state == "idle" else None)
        self.entry.focus_set()

        row = tk.Frame(wrap, bg=BG)
        row.pack(pady=(14, 6))
        self.btn_main = PixelButton(row, "START", self.toggle, GREEN)
        self.btn_main.grid(row=0, column=0, padx=(0, 8))
        self.btn_reset = PixelButton(row, "RESET", self.reset, ORANGE)
        self.btn_reset.grid(row=0, column=1, padx=8)
        self.btn_log = PixelButton(row, "LOG", self.open_log, PURPLE)
        self.btn_log.grid(row=0, column=2, padx=(8, 0))

        self.status = PixelLabel(self.root, f"TODAY: {self.today_count} DONE", px=3,
                                 color=RED_D)
        self.status.pack(pady=(2, 14))

    def _draw_berry(self):
        c = self.canvas
        inside, half = berry_cells()

        def cell(x, y, color, tag="berry"):
            c.create_rectangle(x * S, y * S, (x + 1) * S, (y + 1) * S,
                               fill=color, outline="", tags=tag)

        def interior(x, y):
            return (x, y) in inside and all((x + dx, y + dy) in inside for dx, dy in N4)

        # Body: outline, base colour, right-hand shading
        for (x, y) in inside:
            edge = any((x + dx, y + dy) not in inside for dx, dy in N4)
            if edge:
                color = DARK
            elif (x + 0.5 - 16) >= 0.55 * half[y]:
                color = RED_D
            else:
                color = RED
            cell(x, y, color)

        # Highlight
        for (x, y) in HIGHLIGHT:
            if interior(x, y):
                cell(x, y, RED_LIGHT)

        # Seeds (skip the LCD area and the face area)
        sx0, sy0, sx1, sy1 = SCREEN
        fx0, fy0, fx1, fy1 = FACE_BOX

        def blocked(x, y):
            if sx0 - 1 <= x < sx1 + 1 and sy0 - 1 <= y < sy1 + 1:
                return True
            return fx0 <= x <= fx1 and fy0 <= y <= fy1

        for y in range(9, 34, 3):
            for x in range(4 + ((y // 3) % 2) * 2, 29, 4):
                cells = [(x, y), (x, y + 1)]
                if all(interior(a, b) and not blocked(a, b) and (a, b) not in HIGHLIGHT
                       for a, b in cells):
                    for a, b in cells:
                        cell(a, b, SEED)

        # LCD screen: dark frame, cream face, rounded corners
        c.create_rectangle(sx0 * S, sy0 * S, sx1 * S, sy1 * S, fill=DARK, outline="")
        c.create_rectangle((sx0 + 1) * S, (sy0 + 1) * S, (sx1 - 1) * S, (sy1 - 1) * S,
                           fill=CREAM, outline="")
        for (x, y) in ((sx0, sy0), (sx1 - 1, sy0), (sx0, sy1 - 1), (sx1 - 1, sy1 - 1)):
            cell(x, y, RED)

        # Leaf crown + stem (mirrored from the left half)
        for r, half_row in enumerate(CROWN_HALF):
            full = half_row + half_row[::-1]
            for i, ch in enumerate(full):
                if ch in CROWN_COLORS:
                    cell(6 + i, r, CROWN_COLORS[ch])

    # ----------------------------------------------------- dynamic drawing
    def _mode_color(self):
        return RED_D if self.mode == "focus" else GREEN_D

    def _mode_label(self):
        if self.state == "paused":
            return "PAUSED"
        if self.mode == "break":
            return "LONG BREAK" if self.break_is_long else "BREAK"
        return "FOCUS" if self.state == "running" else "READY"

    def _draw_screen(self):
        c = self.canvas
        c.delete("screen")
        cx = (SCREEN[0] + SCREEN[2]) / 2 * S
        color = self._mode_color()

        draw_text(c, cx, 158, self._mode_label(), 3, color, "screen")

        secs = max(0, math.ceil(self.remaining - 1e-9))
        mm, ss = divmod(secs, 60)
        draw_text(c, cx, 196, f"{mm:02d}:{ss:02d}", 8, color, "screen",
                  shadow=(3, 3, EMPTY_BAR))

        # Segmented progress bar
        frac = 1 - self.remaining / self.total if self.total else 0
        filled = int(round(frac * 16))
        x0 = cx - 79
        for i in range(16):
            c.create_rectangle(x0 + i * 10, 226, x0 + i * 10 + 8, 234,
                               fill=color if i < filled else EMPTY_BAR,
                               outline="", tags="screen")

    def _draw_face(self):
        c = self.canvas
        c.delete("face")

        def cell(x, y, color):
            c.create_rectangle(x * S, y * S, (x + 1) * S, (y + 1) * S,
                               fill=color, outline="", tags="face")

        for ex in (11, 20):
            if self.state == "paused":                 # sleepy "- -"
                cell(ex - 1, 28, DARK)
                cell(ex, 28, DARK)
            elif self.mode == "break":                 # happy "^ ^"
                cell(ex - 1, 28, DARK)
                cell(ex, 27, DARK)
                cell(ex + 1, 28, DARK)
            else:                                      # focused eyes
                cell(ex, 27, DARK)
                cell(ex, 28, DARK)
        for x, y in ((8, 29), (9, 29), (22, 29), (23, 29)):
            cell(x, y, RED_LIGHT)                      # blush
        for x, y in ((14, 29), (15, 30), (16, 30), (17, 29)):
            cell(x, y, DARK)                           # smile

    def _redraw(self):
        self._draw_screen()
        self._draw_face()
        if self.state == "running":
            secs = max(0, math.ceil(self.remaining - 1e-9))
            self.root.title(f"{secs // 60:02d}:{secs % 60:02d} - Strawberry Pomodoro")
        else:
            self.root.title("Strawberry Pomodoro")

    # ----------------------------------------------------------- timer logic
    def _enter_mode(self, mode, long_break=False):
        self.mode = mode
        self.break_is_long = long_break
        if mode == "focus":
            self.total = WORK_MIN * 60
        else:
            self.total = (LONG_BREAK_MIN if long_break else BREAK_MIN) * 60
        self.remaining = float(self.total)

    def _lock_entry(self, locked):
        self.entry.config(state="disabled" if locked else "normal")

    def _cancel_tick(self):
        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
            self.after_id = None

    def toggle(self):
        if self.state == "running":
            self.pause()
        else:
            self.start()

    def start(self):
        if self.state == "running":
            return
        if self.state == "idle" and self.mode == "focus":
            self.session_title = self.entry.get().strip() or "Untitled"
        self._lock_entry(self.mode == "focus")
        self.state = "running"
        self.end_time = time.monotonic() + self.remaining
        self.btn_main.set_text("PAUSE")
        self.btn_main.set_color(ORANGE)
        self._cancel_tick()
        self._redraw()
        self._tick()

    def pause(self):
        if self.state != "running":
            return
        self._cancel_tick()
        self.remaining = max(0.0, self.end_time - time.monotonic())
        self.state = "paused"
        self.btn_main.set_text("RESUME")
        self.btn_main.set_color(GREEN)
        self._redraw()

    def reset(self):
        self._cancel_tick()
        self.state = "idle"
        self._enter_mode("focus")
        self._lock_entry(False)
        self.btn_main.set_text("START")
        self.btn_main.set_color(GREEN)
        self._redraw()

    def _tick(self):
        if self.state != "running":
            return
        left = self.end_time - time.monotonic()
        if left <= 0:
            self.remaining = 0.0
            self._redraw()
            self._complete()
            return
        self.remaining = left
        self._redraw()
        self.after_id = self.root.after(200, self._tick)

    def _complete(self):
        self.after_id = None
        self.state = "idle"
        self._alert()
        if self.mode == "focus":
            self.focus_count += 1
            self.log_session(self.session_title, WORK_MIN)
            self.today_count += 1
            self.status.set(f"TODAY: {self.today_count} DONE")
            self._enter_mode("break", long_break=(self.focus_count % LONG_BREAK_EVERY == 0))
            self.start()                      # breaks start automatically
        else:
            self._enter_mode("focus")
            self._lock_entry(False)
            self.btn_main.set_text("START")
            self.btn_main.set_color(GREEN)
            self._redraw()

    def _alert(self):
        self.root.bell()
        self.root.after(250, self.root.bell)
        try:
            self.root.deiconify()
            self.root.lift()
            self.root.attributes("-topmost", True)
            self.root.after(1500, lambda: self.root.attributes("-topmost", False))
        except tk.TclError:
            pass

    # --------------------------------------------------------------- logging
    def _count_today(self):
        today = datetime.now().strftime("%Y-%m-%d")
        return sum(1 for r in read_log() if (r.get("completed_at") or "").startswith(today))

    def log_session(self, title, minutes):
        is_new = not LOG_FILE.exists() or LOG_FILE.stat().st_size == 0
        try:
            with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                if is_new:
                    writer.writerow(LOG_FIELDS)
                writer.writerow([title, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), minutes])
        except OSError as exc:
            messagebox.showerror("Could not save session",
                                 f"Your session could not be written to\n{LOG_FILE}\n\n{exc}")
        self.refresh_log()

    # ------------------------------------------------------------ log viewer
    def open_log(self):
        if self.log_win is not None and self.log_win.winfo_exists():
            self.log_win.deiconify()
            self.log_win.lift()
            self.refresh_log()
            return

        win = tk.Toplevel(self.root)
        win.title("Past Sessions")
        win.configure(bg=BG)
        win.geometry("560x420")
        win.minsize(460, 300)
        self.log_win = win

        PixelLabel(win, "PAST SESSIONS", px=4, color=RED_D).pack(pady=(14, 10))

        holder = tk.Frame(win, bg=DARK, padx=3, pady=3)
        holder.pack(fill="both", expand=True, padx=16)
        inner = tk.Frame(holder, bg=CREAM)
        inner.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(inner, columns=("when", "activity", "min"),
                                 show="headings", style="Retro.Treeview")
        self.tree.heading("when", text="DATE & TIME")
        self.tree.heading("activity", text="ACTIVITY")
        self.tree.heading("min", text="MIN")
        self.tree.column("when", width=170, anchor="w", stretch=False)
        self.tree.column("activity", width=260, anchor="w")
        self.tree.column("min", width=60, anchor="center", stretch=False)
        scroll = ttk.Scrollbar(inner, orient="vertical", command=self.tree.yview,
                               style="Retro.Vertical.TScrollbar")
        self.tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)

        self.log_total = PixelLabel(win, "", px=3, color=DARK)
        self.log_total.pack(pady=12)
        self.refresh_log()

    def refresh_log(self):
        if self.log_win is None or not self.log_win.winfo_exists():
            return
        rows = read_log()
        self.tree.delete(*self.tree.get_children())
        total_min = 0
        for r in reversed(rows):                          # newest first
            minutes = r.get("duration_minutes", "")
            try:
                total_min += int(float(minutes))
            except (TypeError, ValueError):
                pass
            self.tree.insert("", "end", values=(r.get("completed_at", ""),
                                                r.get("activity", ""), minutes))
        if not rows:
            self.tree.insert("", "end", values=("", "No sessions logged yet", ""))
        self.log_total.set(f"SESSIONS: {len(rows)}   FOCUS: {total_min} MIN")


def main():
    root = tk.Tk()
    PomodoroApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
