#!/usr/bin/env python3
"""Kanji terminal start screen — ASCII art glyph + meaning + example words."""

from __future__ import annotations

import argparse
import colorsys
import json
import math
import os
import random
import select
import shutil
import sys
import termios
import time
import tty
import unicodedata
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# ── paths ──────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_DATA = SCRIPT_DIR / "kanji.json"

# Prefer clean Japanese faces; fall back through a short list.
FONT_CANDIDATES = [
    "/usr/share/fonts/opentype/ipafont-mincho/ipam.ttf",
    "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf",
    "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
]

# Density ramps (light → dark). Braille-ish blocks look dense; classic ASCII is coarser.
RAMPS = {
    "blocks": " ·░▒▓█",
    "ascii": " .:-=+*#%@",
    "dots": " ․‥…●",
}

# Truecolor vertical gradients per style (top → bottom). Hue-shifted at runtime.
# Kept for --style / backward compat; live ink color uses COLOR_CYCLE.
STYLE_RGB: dict[str, list[tuple[int, int, int]]] = {
    "ember": [
        (255, 55, 40),
        (255, 100, 45),
        (255, 145, 55),
        (255, 185, 70),
        (255, 215, 95),
        (255, 235, 130),
    ],
    "ocean": [
        (30, 120, 255),
        (25, 150, 230),
        (20, 175, 210),
        (30, 200, 200),
        (60, 220, 220),
        (120, 240, 255),
    ],
    "sakura": [
        (255, 140, 180),
        (255, 160, 195),
        (255, 180, 205),
        (255, 195, 215),
        (255, 215, 230),
        (255, 240, 245),
    ],
    "mono": [
        (200, 200, 200),
        (220, 220, 220),
        (235, 235, 235),
        (245, 245, 245),
        (250, 250, 250),
        (255, 255, 255),
    ],
    "moss": [
        (40, 100, 50),
        (55, 130, 60),
        (70, 155, 75),
        (95, 175, 90),
        (130, 195, 110),
        (170, 215, 140),
    ],
}

# Kanji ink colors — cycle with key `c` (rich → pastel per hue)
# Order: red, pastel-red, orange, pastel-orange, … purple, pastel-purple
COLOR_CYCLE: list[tuple[str, list[tuple[int, int, int]]]] = [
    (
        "red",
        [
            (160, 20, 25),
            (200, 30, 35),
            (235, 45, 45),
            (255, 70, 65),
            (255, 105, 95),
            (255, 140, 130),
        ],
    ),
    (
        "pastel-red",
        [
            (210, 130, 135),
            (225, 150, 155),
            (235, 170, 170),
            (245, 190, 190),
            (250, 210, 210),
            (255, 225, 225),
        ],
    ),
    (
        "orange",
        [
            (180, 70, 15),
            (220, 95, 20),
            (245, 120, 30),
            (255, 145, 50),
            (255, 170, 80),
            (255, 195, 120),
        ],
    ),
    (
        "pastel-orange",
        [
            (220, 160, 110),
            (230, 175, 130),
            (240, 190, 150),
            (245, 205, 170),
            (250, 220, 190),
            (255, 235, 210),
        ],
    ),
    (
        "yellow",
        [
            (170, 140, 20),
            (200, 170, 25),
            (230, 200, 35),
            (250, 220, 50),
            (255, 235, 90),
            (255, 245, 140),
        ],
    ),
    (
        "pastel-yellow",
        [
            (220, 205, 120),
            (230, 215, 145),
            (240, 225, 165),
            (245, 235, 185),
            (250, 245, 205),
            (255, 250, 220),
        ],
    ),
    (
        "green",
        [
            (25, 100, 45),
            (35, 130, 55),
            (45, 160, 70),
            (60, 185, 90),
            (90, 205, 115),
            (130, 225, 150),
        ],
    ),
    (
        "pastel-green",
        [
            (130, 185, 145),
            (150, 200, 160),
            (170, 215, 180),
            (190, 225, 195),
            (210, 235, 215),
            (225, 245, 230),
        ],
    ),
    (
        "blue",
        [
            (25, 70, 170),
            (35, 95, 200),
            (45, 120, 230),
            (60, 150, 245),
            (95, 180, 255),
            (140, 205, 255),
        ],
    ),
    (
        "pastel-blue",
        [
            (130, 165, 215),
            (150, 180, 225),
            (170, 195, 235),
            (190, 210, 240),
            (210, 225, 245),
            (225, 235, 250),
        ],
    ),
    (
        "purple",
        [
            (90, 35, 150),
            (115, 50, 180),
            (140, 70, 210),
            (165, 95, 230),
            (190, 130, 245),
            (215, 165, 255),
        ],
    ),
    (
        "pastel-purple",
        [
            (175, 145, 205),
            (190, 165, 215),
            (205, 185, 225),
            (220, 200, 235),
            (230, 215, 245),
            (240, 230, 250),
        ],
    ),
]
COLOR_NAMES = [name for name, _ in COLOR_CYCLE]
COLOR_PALETTES: dict[str, list[tuple[int, int, int]]] = {
    name: palette for name, palette in COLOR_CYCLE
}
DEFAULT_COLOR = COLOR_NAMES[0]  # red

# Hue motion (fraction of the color wheel; keep the glyph calm)
HUE_AMPLITUDE = 0.025         # fade-in settle bias
SHIMMER_HUE_AMP = 0.028       # ongoing global hue (subtle)
SHIMMER_HUE_FAST = 0.010      # tiny secondary ripple
FADE_FRAMES = 18
FADE_SECONDS = 0.85
SHIMMER_FPS = 18
DEFAULT_NOISE = 0.45          # mostly controls particle intensity; body stays mild

# Animation effects (cycle with key `a` or --effect)
EFFECTS = ("embers", "starlight", "sakura", "sunrays", "grass")
DEFAULT_EFFECT = "embers"

# Rising edge sparks (embers)
SPARK_CHARS = ("·", "˙", "+", "*", "°", "·")
# life 1 → 0 : white-hot → amber → deep ember
SPARK_COLORS = (
    (255, 250, 220),
    (255, 220, 120),
    (255, 160, 50),
    (255, 100, 30),
    (180, 50, 15),
)

# Starlight twinkles (width-1 only — wide glyphs shift layout)
STAR_CHARS = (".", "*", "+", "o", "'", ",")
STAR_COLORS = (
    (180, 195, 255),
    (210, 220, 255),
    (240, 245, 255),
    (255, 255, 255),
    (255, 250, 230),
)

# Cherry blossoms — MUST be display-width 1 only.
# Wide chars (e.g. ゜) change line width and jitter the centered kanji each frame.
BLOSSOM_CHARS = (".", "*", "+", "o", "'", ",")
BLOSSOM_COLORS = (
    (255, 182, 193),  # light pink
    (255, 160, 180),
    (255, 140, 170),
    (255, 200, 210),
    (255, 220, 225),  # pale
)

# Sunrays
RAY_CHARS = (".", "·", "/", "╱", "|", "│")
RAY_COLORS = (
    (255, 220, 120),
    (255, 200, 80),
    (255, 240, 180),
    (255, 250, 220),
    (255, 180, 60),
)

# Windblown grass field
GRASS_CHARS = ("│", "|", "/", "\\", "╱", "╲", ",", ";", "'", "`", ".")
GRASS_COLORS = (
    (40, 90, 45),
    (55, 120, 55),
    (70, 140, 65),
    (90, 160, 75),
    (110, 175, 85),
    (130, 190, 100),
)


# ── ANSI helpers ───────────────────────────────────────────────────────────
class C:
    """Terminal colors; no-ops when stdout is not a TTY or --no-color."""

    enabled = True

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    UNDERLINE = "\033[4m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"
    FG = "\033[38;5;{n}m"  # 256-color (chrome / non-art)
    FG_RGB = "\033[38;2;{r};{g};{b}m"
    HIDE_CURSOR = "\033[?25l"
    SHOW_CURSOR = "\033[?25h"
    # Full clear + home (J alone only clears below the cursor)
    CLEAR_SCREEN = "\033[2J\033[H"
    # Alternate buffer: animation frames never pile up in scrollback
    ALT_SCREEN_ON = "\033[?1049h"
    ALT_SCREEN_OFF = "\033[?1049l"

    @classmethod
    def paint(cls, text: str, *codes: str) -> str:
        if not cls.enabled or not codes:
            return text
        return "".join(codes) + text + cls.RESET

    @classmethod
    def hyperlink(cls, uri: str, text: str) -> str:
        """OSC 8 hyperlink (Kitty: ctrl+shift+click). No-op when color is off."""
        if not cls.enabled:
            return text
        return f"\033]8;;{uri}\033\\{text}\033]8;;\033\\"


# Keys handled while the splash is up (any terminal — no click required)
KEY_NEW = "n"
KEY_LIST = "l"
KEY_DAILY = "d"
KEY_FX = "a"      # cycle animation effect
KEY_COLOR = "c"   # cycle kanji ink color
KEY_QUIT = "q"


def shortcuts_footer() -> str:
    """Keyboard shortcut legend for the panel footer."""
    return (
        f"({KEY_NEW}) new  ·  ({KEY_LIST}) list  ·  "
        f"({KEY_DAILY}) daily  ·  ({KEY_FX}) anim  ·  "
        f"({KEY_COLOR}) color  ·  ({KEY_QUIT}) quit"
    )


def next_color(name: str) -> str:
    try:
        i = COLOR_NAMES.index(name)
    except ValueError:
        return DEFAULT_COLOR
    return COLOR_NAMES[(i + 1) % len(COLOR_NAMES)]


def resolve_entry_color(entry: dict) -> str:
    """
    Default ink color for a kanji entry.
    Uses entry['color'] when set to a known palette name;
    if missing/null/random (too abstract), pick a random cycle color.
    """
    c = entry.get("color")
    if isinstance(c, str) and c.lower() in ("", "random", "none", "null"):
        c = None
    if c in COLOR_PALETTES:
        return c
    return random.choice(COLOR_NAMES)


def resolve_entry_effect(entry: dict) -> str:
    """
    Default animation for a kanji entry.
    Uses entry['effect'] when set to a known effect name;
    if missing/null/random (no clear association), pick a random effect.
    """
    fx = entry.get("effect")
    if isinstance(fx, str) and fx.lower() in ("", "random", "none", "null"):
        fx = None
    if fx in EFFECTS:
        return fx
    return random.choice(EFFECTS)


def load_font(size: int) -> ImageFont.FreeTypeFont:
    for path in FONT_CANDIDATES:
        if not os.path.isfile(path):
            continue
        try:
            # TTC collections: index 0 is usually JP-capable for Noto CJK
            return ImageFont.truetype(path, size=size)
        except OSError:
            continue
    # Last resort — may not render CJK
    return ImageFont.load_default()


def kanji_to_ascii(
    char: str,
    *,
    cols: int = 40,
    rows: int | None = None,
    ramp_name: str = "blocks",
    invert: bool = False,
) -> list[str]:
    """Render a single kanji glyph into ASCII/block-art lines."""
    if rows is None:
        # Monospace cells are taller than wide; bias height a bit lower
        rows = max(12, int(cols * 0.55))

    ramp = RAMPS.get(ramp_name, RAMPS["blocks"])
    if invert:
        ramp = ramp[::-1]

    # Render large, then sample down for smoother edges
    scale = 4
    img_w, img_h = cols * scale, rows * scale
    img = Image.new("L", (img_w, img_h), color=0)
    draw = ImageDraw.Draw(img)

    # Font size ~80% of the shorter dimension so the glyph has padding
    font_size = int(min(img_w, img_h) * 0.85)
    font = load_font(font_size)

    # Center the glyph using its ink bbox
    bbox = draw.textbbox((0, 0), char, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (img_w - tw) // 2 - bbox[0]
    y = (img_h - th) // 2 - bbox[1]
    draw.text((x, y), char, fill=255, font=font)

    # Optional slight blur-like downscale (box filter via resize)
    small = img.resize((cols, rows), Image.Resampling.LANCZOS)

    lines: list[str] = []
    pixels = small.load()
    n = len(ramp) - 1
    for y in range(rows):
        row_chars = []
        for x in range(cols):
            v = pixels[x, y] / 255.0
            idx = int(round(v * n))
            row_chars.append(ramp[idx])
        lines.append("".join(row_chars))
    return lines


def strip_empty_rows(lines: list[str]) -> list[str]:
    """Drop fully blank rows at top/bottom; keep internal spacing."""

    def blank(s: str) -> bool:
        return not s.strip()

    while lines and blank(lines[0]):
        lines = lines[1:]
    while lines and blank(lines[-1]):
        lines = lines[:-1]
    return lines


def apply_fade(lines: list[str], ramp: str, fade: float) -> list[str]:
    """Thin the glyph by mapping ramp indices toward empty as fade → 0."""
    fade = max(0.0, min(1.0, fade))
    if fade >= 0.999:
        return lines
    if fade <= 0.001:
        return [" " * len(line) for line in lines]

    index = {ch: i for i, ch in enumerate(ramp)}
    n = len(ramp) - 1
    out: list[str] = []
    for line in lines:
        row = []
        for ch in line:
            i = index.get(ch, 0)
            if not i:
                row.append(ramp[0])
                continue
            # Scale density; a light bias keeps the silhouette readable mid-fade
            ni = int(round(i * (0.15 + 0.85 * fade)))
            row.append(ramp[min(max(ni, 0), n)])
        out.append("".join(row))
    return out


def apply_noise(
    lines: list[str],
    ramp: str,
    *,
    amount: float,
    t: float,
) -> list[str]:
    """
    Minor grain on the glyph body only — rare ±1 density steps.
    (Edge drama lives in the rising spark system, not here.)
    """
    amount = max(0.0, min(1.0, amount))
    if amount <= 0.001:
        return lines

    index = {ch: i for i, ch in enumerate(ramp)}
    n = len(ramp) - 1
    # Keep this quiet even at amount=1
    chance = 0.03 + 0.07 * amount
    out: list[str] = []
    for y, line in enumerate(lines):
        row: list[str] = []
        for x, ch in enumerate(line):
            i = index.get(ch, 0)
            if i <= 0:
                row.append(ramp[0] if ch in index else ch)
                continue

            field = math.sin(x * 1.3 + y * 1.8 + t * 2.8)
            roll = (math.sin(x * 9.1 + y * 6.3 + t * 2.1) + 1.0) * 0.5
            if roll < chance and abs(field) > 0.35:
                step = 1 if field >= 0 else -1
                i = max(1, min(n, i + step))
            row.append(ramp[i])
        out.append("".join(row))
    return out


def pad_art(
    lines: list[str],
    *,
    top: int = 3,
    bottom: int = 1,
    left: int = 2,
    right: int = 2,
) -> list[str]:
    """Add empty margin so rising sparks have room above/around the glyph."""
    if not lines:
        return lines
    width = max(len(line) for line in lines)
    padded = [line.ljust(width) for line in lines]
    inner_w = width + left + right
    blank = " " * inner_w
    out = [blank] * top
    for line in padded:
        out.append((" " * left) + line + (" " * right))
    out.extend([blank] * bottom)
    return out


def is_ink(ch: str) -> bool:
    return bool(ch.strip())


def find_edge_cells(lines: list[str]) -> list[tuple[int, int]]:
    """Ink cells that touch empty space (silhouette outline)."""
    if not lines:
        return []
    h = len(lines)
    w = max(len(line) for line in lines)
    grid = [line.ljust(w) for line in lines]
    edges: list[tuple[int, int]] = []
    for y in range(h):
        for x in range(w):
            if not is_ink(grid[y][x]):
                continue
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nx, ny = x + dx, y + dy
                if nx < 0 or ny < 0 or nx >= w or ny >= h or not is_ink(grid[ny][nx]):
                    edges.append((x, y))
                    break
    return edges


def spark_color(life: float, heat: float) -> tuple[int, int, int]:
    """Map remaining life (1→0) and heat bias to an ember RGB."""
    # Prefer hotter colors when young
    t = max(0.0, min(1.0, 1.0 - life))  # age fraction
    t = t * (0.65 + 0.35 * (1.0 - heat))  # hot sparks stay bright longer
    pos = t * (len(SPARK_COLORS) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(SPARK_COLORS) - 1)
    frac = pos - lo
    c0, c1 = SPARK_COLORS[lo], SPARK_COLORS[hi]
    r = int(c0[0] + (c1[0] - c0[0]) * frac)
    g = int(c0[1] + (c1[1] - c0[1]) * frac)
    b = int(c0[2] + (c1[2] - c0[2]) * frac)
    # Fade out near death
    fade = max(0.15, min(1.0, life * 1.2))
    return int(r * fade), int(g * fade), int(b * fade)


def spark_char(life: float) -> str:
    if life > 0.75:
        return "*"
    if life > 0.5:
        return "+"
    if life > 0.28:
        return "·"
    return "˙"


def next_effect(name: str) -> str:
    try:
        i = EFFECTS.index(name)
    except ValueError:
        return EFFECTS[0]
    return EFFECTS[(i + 1) % len(EFFECTS)]


def apply_breath(
    lines: list[str],
    ramp: str,
    breath: float,
) -> list[str]:
    """
    Soft density pulse on the glyph body.
    breath ~0.88–1.12: below 1 thins ink slightly, above 1 densifies.
    """
    breath = max(0.75, min(1.2, breath))
    if abs(breath - 1.0) < 0.01:
        return lines
    index = {ch: i for i, ch in enumerate(ramp)}
    n = len(ramp) - 1
    out: list[str] = []
    for line in lines:
        row: list[str] = []
        for ch in line:
            i = index.get(ch, 0)
            if i <= 0:
                row.append(ramp[0] if ch in index else ch)
                continue
            ni = int(round(i * breath))
            ni = max(1, min(n, ni))
            row.append(ramp[ni])
        out.append("".join(row))
    return out


def breath_level(t: float) -> float:
    """Slow inhale/exhale curve for starlight (~0.90–1.10)."""
    return 1.0 + 0.10 * math.sin(t * 1.15)


class EmberField:
    """Rising sparks that spawn around the glyph outline and drift upward."""

    def __init__(
        self,
        edges: list[tuple[int, int]],
        intensity: float = 0.45,
        *,
        width: int = 0,
        height: int = 0,
    ):
        self.edges = edges
        self.intensity = max(0.0, min(1.0, intensity))
        self.width = width
        self.height = height
        # each spark: x, y, life, max_life, speed, phase, heat
        self.sparks: list[list[float]] = []

    def update(self, dt: float) -> None:
        if self.intensity <= 0.001 or not self.edges:
            self.sparks.clear()
            return

        # Spawn rate: sparks per second, scales with outline size + intensity
        n_edge = len(self.edges)
        rate = (4.0 + 16.0 * self.intensity) * max(0.35, n_edge / 100.0)
        n_spawn = min(7, int(rate * dt + random.random() * self.intensity))
        lower = self.edges[len(self.edges) // 3 :] or self.edges
        for _ in range(n_spawn):
            # Prefer mid/lower outline (embers lift off the body)
            ex, ey = random.choice(lower if random.random() < 0.7 else self.edges)
            # Birth just outside the silhouette — favor above / beside, not on ink
            ox = random.choice((-1, -1, 0, 0, 1, 1))
            oy = random.choice((-1, -1, -1, 0))  # bias upward (smaller y)
            x = float(ex + ox) + random.uniform(-0.25, 0.25)
            y = float(ey + oy) + random.uniform(-0.2, 0.15)
            max_life = 0.6 + random.random() * 0.9
            speed = 2.2 + random.random() * 4.0  # rows per second upward
            phase = random.random() * math.pi * 2
            heat = 0.35 + random.random() * 0.65
            self.sparks.append([x, y, max_life, max_life, speed, phase, heat])

        alive: list[list[float]] = []
        for s in self.sparks:
            x, y, life, max_life, speed, phase, heat = s
            life -= dt
            if life <= 0:
                continue
            # Rise (smaller y) with a soft horizontal sway
            age = 1.0 - (life / max_life)
            y -= speed * dt
            x += math.sin(phase + age * 5.5) * (2.2 * dt)
            alive.append([x, y, life, max_life, speed, phase, heat])
        self.sparks = alive

    def stamp(
        self,
        lines: list[str],
    ) -> tuple[list[str], dict[tuple[int, int], tuple[int, int, int]]]:
        """
        Overlay spark characters onto empty cells around the glyph.
        Returns (new_lines, spark_rgb_by_cell).
        """
        if not lines:
            return lines, {}
        h = len(lines)
        w = max(len(line) for line in lines)
        grid = [list(line.ljust(w)) for line in lines]
        colors: dict[tuple[int, int], tuple[int, int, int]] = {}

        # Dimmer first; hotter / younger overwrite
        ordered = sorted(self.sparks, key=lambda s: s[2])
        for s in ordered:
            x, y, life, max_life, _speed, _phase, heat = s
            ix, iy = int(round(x)), int(round(y))
            if ix < 0 or iy < 0 or ix >= w or iy >= h:
                continue
            life_frac = life / max_life
            cell = grid[iy][ix]
            # Keep the kanji body clean — only empty / prior spark cells
            if is_ink(cell) and cell not in SPARK_CHARS:
                # Try one cell above (still rising past the edge)
                iy2 = iy - 1
                if iy2 < 0 or (is_ink(grid[iy2][ix]) and grid[iy2][ix] not in SPARK_CHARS):
                    continue
                iy = iy2
            grid[iy][ix] = spark_char(life_frac)
            colors[(ix, iy)] = spark_color(life_frac, heat)

        return ["".join(row) for row in grid], colors


class StarField:
    """
    Twinkling stars in empty space around the glyph.
    Spread around the full silhouette with minimum spacing (not a top cluster).
    """

    def __init__(
        self,
        lines: list[str],
        intensity: float = 0.45,
    ):
        self.intensity = max(0.0, min(1.0, intensity))
        self.t = 0.0
        # each star: x, y, phase, speed, cool (0 warm white → 1 cool blue)
        self.stars: list[list[float]] = []
        if not lines or self.intensity <= 0.001:
            return

        h = len(lines)
        w = max(len(line) for line in lines)
        grid = [line.ljust(w) for line in lines]

        ink = {
            (x, y)
            for y in range(h)
            for x in range(w)
            if is_ink(grid[y][x])
        }
        if not ink:
            return

        ink_list = list(ink)
        cx = sum(p[0] for p in ink_list) / len(ink_list)
        cy = sum(p[1] for p in ink_list) / len(ink_list)

        # Empty cells with a gap from the stroke; whole canvas margin is fair game
        # (x, y, dist_to_ink, angle around glyph center)
        candidates: list[tuple[int, int, int, float]] = []
        for y in range(h):
            for x in range(w):
                if is_ink(grid[y][x]):
                    continue
                dist = min(abs(x - ix) + abs(y - iy) for ix, iy in ink_list)
                # Keep clear of the ink; allow far margin stars for a full sky
                if dist < 2:
                    continue
                ang = math.atan2(y - cy, x - cx)
                candidates.append((x, y, dist, ang))

        if not candidates:
            return

        # Sparse constellation — fewer stars as intensity drops
        n_stars = int(4 + 10 * self.intensity)  # ~4–14
        n_stars = min(n_stars, max(1, len(candidates)))
        min_sep = 4  # Chebyshev gap between stars (cells)

        def far_enough(x: int, y: int, picked: list[tuple[int, int]]) -> bool:
            return all(max(abs(x - px), abs(y - py)) >= min_sep for px, py in picked)

        picked_xy: list[tuple[int, int]] = []

        # 1) One star per angular sector so they wrap the whole glyph
        n_sectors = 8
        sectors: list[list[tuple[int, int, int, float]]] = [[] for _ in range(n_sectors)]
        for c in candidates:
            si = int((c[3] + math.pi) / (2 * math.pi) * n_sectors) % n_sectors
            sectors[si].append(c)

        for sec in sectors:
            if len(picked_xy) >= n_stars:
                break
            # Prefer mid-range distance (not glued to the stroke, not only corners)
            sec_sorted = sorted(sec, key=lambda c: abs(c[2] - 4))
            random.shuffle(sec_sorted)
            # mix: try a few mid-distance first
            ordered = sec_sorted[: max(3, len(sec_sorted) // 3)] + sec_sorted
            for x, y, _d, _a in ordered:
                if far_enough(x, y, picked_xy):
                    picked_xy.append((x, y))
                    break

        # 2) Fill remaining slots with poisson-disk samples over all candidates
        pool = candidates[:]
        random.shuffle(pool)
        # slight preference for varied distances
        pool.sort(key=lambda c: (random.random(), abs(c[2] - 4)))
        for x, y, _d, _a in pool:
            if len(picked_xy) >= n_stars:
                break
            if far_enough(x, y, picked_xy):
                picked_xy.append((x, y))

        for x, y in picked_xy:
            self.stars.append(
                [
                    float(x),
                    float(y),
                    random.random() * math.pi * 2,  # phase
                    1.2 + random.random() * 2.8,  # twinkle speed
                    random.random(),  # cool bias
                ]
            )

    def update(self, dt: float) -> None:
        self.t += dt
        for s in self.stars:
            s[2] += s[3] * dt  # advance phase

    def _twinkle(self, phase: float) -> float:
        # Soft pulse with occasional sharper sparkle
        base = 0.35 + 0.45 * (0.5 + 0.5 * math.sin(phase))
        sparkle = 0.0
        if math.sin(phase * 0.37 + 1.7) > 0.92:
            sparkle = 0.35 * (0.5 + 0.5 * math.sin(phase * 4.0))
        return max(0.0, min(1.0, base + sparkle))

    def stamp(
        self,
        lines: list[str],
    ) -> tuple[list[str], dict[tuple[int, int], tuple[int, int, int]]]:
        if not lines or not self.stars:
            return lines, {}
        h = len(lines)
        w = max(len(line) for line in lines)
        grid = [list(line.ljust(w)) for line in lines]
        colors: dict[tuple[int, int], tuple[int, int, int]] = {}

        for x, y, phase, _spd, cool in self.stars:
            ix, iy = int(round(x)), int(round(y))
            if ix < 0 or iy < 0 or ix >= w or iy >= h:
                continue
            cell = grid[iy][ix]
            if is_ink(cell) and cell not in STAR_CHARS and cell not in SPARK_CHARS:
                continue
            tw = self._twinkle(phase)
            if tw < 0.12:
                continue  # fully blinked off this frame
            # Character by brightness
            if tw > 0.85:
                ch = "*"
            elif tw > 0.65:
                ch = "+"
            elif tw > 0.4:
                ch = "·"
            else:
                ch = "."
            # Color: cool blue-white ↔ soft gold-white
            c_lo = STAR_COLORS[int(cool * 2)]
            c_hi = STAR_COLORS[min(len(STAR_COLORS) - 1, 2 + int((1 - cool) * 2))]
            # Blend toward bright white with twinkle
            r = int(c_lo[0] + (c_hi[0] - c_lo[0]) * tw)
            g = int(c_lo[1] + (c_hi[1] - c_lo[1]) * tw)
            b = int(c_lo[2] + (c_hi[2] - c_lo[2]) * tw)
            r = min(255, int(r * (0.55 + 0.55 * tw)))
            g = min(255, int(g * (0.55 + 0.55 * tw)))
            b = min(255, int(b * (0.55 + 0.55 * tw)))
            grid[iy][ix] = ch
            colors[(ix, iy)] = (r, g, b)

        return ["".join(row) for row in grid], colors


class SakuraField:
    """
    Falling cherry blossoms with a sideways wind drift.
    Petals spawn above the canvas, tumble down, and recycle.
    """

    def __init__(
        self,
        lines: list[str],
        intensity: float = 0.45,
    ):
        self.intensity = max(0.0, min(1.0, intensity))
        self.t = 0.0
        self.h = len(lines) if lines else 1
        self.w = max((len(line) for line in lines), default=1) if lines else 1
        # petal: x, y, vy, phase, spin, tint, size
        self.petals: list[list[float]] = []
        n = int(6 + 16 * self.intensity)  # ~6–22
        for _ in range(n):
            self.petals.append(self._new_petal(spawn_anywhere=True))

    def _new_petal(self, *, spawn_anywhere: bool = False) -> list[float]:
        x = random.uniform(-1.0, self.w + 1.0)
        if spawn_anywhere:
            y = random.uniform(-2.0, self.h * 0.9)
        else:
            y = random.uniform(-3.0, -0.5)
        vy = 1.6 + random.random() * 2.8  # fall speed (rows/sec)
        phase = random.random() * math.pi * 2
        spin = 2.0 + random.random() * 4.5
        tint = random.random()  # pink shade
        size = 0.4 + random.random() * 0.6  # visual weight
        return [x, y, vy, phase, spin, tint, size]

    def update(self, dt: float) -> None:
        self.t += dt
        # Gusting wind — slow swell + quicker flutter
        wind = (
            math.sin(self.t * 0.7) * 2.8
            + math.sin(self.t * 1.9 + 0.8) * 1.2
        )
        alive: list[list[float]] = []
        for p in self.petals:
            x, y, vy, phase, spin, tint, size = p
            phase += spin * dt
            # Drift with wind + personal sway
            x += (wind + math.sin(phase) * 1.8) * dt
            y += vy * dt
            # Slight terminal-velocity wobble
            y += math.sin(phase * 0.5) * 0.15 * dt
            if y > self.h + 1.5 or x < -4 or x > self.w + 4:
                alive.append(self._new_petal(spawn_anywhere=False))
            else:
                alive.append([x, y, vy, phase, spin, tint, size])
        # Intensity may change mid-session — grow/shrink flock gently
        target = int(6 + 16 * self.intensity)
        while len(alive) < target:
            alive.append(self._new_petal(spawn_anywhere=False))
        if len(alive) > target + 2:
            alive = alive[:target]
        self.petals = alive

    def stamp(
        self,
        lines: list[str],
    ) -> tuple[list[str], dict[tuple[int, int], tuple[int, int, int]]]:
        if not lines:
            return lines, {}
        h = len(lines)
        w = max(len(line) for line in lines)
        self.h, self.w = h, w
        grid = [list(line.ljust(w)) for line in lines]
        colors: dict[tuple[int, int], tuple[int, int, int]] = {}

        # Freeze the original glyph mask. Density ramps use "·" etc., which also
        # appear in BLOSSOM_CHARS — treating those as free space caused kanji jitter.
        glyph = {
            (x, y)
            for y, line in enumerate(lines)
            for x, ch in enumerate(line.ljust(w))
            if ch.strip()
        }

        # Draw dimmer petals first
        ordered = sorted(self.petals, key=lambda p: p[6])  # size
        for x, y, _vy, phase, _spin, tint, size in ordered:
            ix, iy = int(round(x)), int(round(y))
            if ix < 0 or iy < 0 or ix >= w or iy >= h:
                continue
            if (ix, iy) in glyph:
                continue
            # Spin → character
            spin_i = int((phase / (math.pi * 2)) * len(BLOSSOM_CHARS)) % len(BLOSSOM_CHARS)
            if size > 0.75:
                ch = "*" if spin_i % 2 == 0 else "+"
            else:
                ch = BLOSSOM_CHARS[spin_i]
            ci = min(len(BLOSSOM_COLORS) - 1, int(tint * len(BLOSSOM_COLORS)))
            r, g, b = BLOSSOM_COLORS[ci]
            # Soft flutter brightness
            fl = 0.75 + 0.25 * (0.5 + 0.5 * math.sin(phase * 1.3))
            r, g, b = int(r * fl), int(g * fl), int(b * fl)
            grid[iy][ix] = ch
            colors[(ix, iy)] = (r, g, b)

        return ["".join(row) for row in grid], colors


class SunrayField:
    """
    Warm sunrays from the top-right, cascading over the kanji.
    Bright near the origin, fading out with distance.
    """

    def __init__(
        self,
        lines: list[str],
        intensity: float = 0.45,
    ):
        self.intensity = max(0.0, min(1.0, intensity))
        self.t = 0.0
        self.h = len(lines) if lines else 1
        self.w = max((len(line) for line in lines), default=1) if lines else 1
        # Origin: top-right corner (slightly outside the canvas)
        self.sun_x = self.w * 0.92
        self.sun_y = -1.2
        # How far light reaches before nearly vanishing (cells)
        self.falloff_len = max(14.0, (self.h + self.w) * 0.55)

        n_rays = int(5 + 7 * self.intensity)  # ~5–12 beams
        # Fan from top-right toward the glyph: down and left
        # angle 0 = straight down; negative = toward -x (left)
        self.rays: list[tuple[float, float, float]] = []  # angle, phase, width
        for i in range(n_rays):
            t = i / max(n_rays - 1, 1)
            # ~15° left of vertical through ~70° left (covers the glyph body)
            angle = -0.25 - 0.95 * t + random.uniform(-0.03, 0.03)
            phase = random.random() * math.pi * 2
            width = 0.35 + random.random() * 0.5
            self.rays.append((angle, phase, width))

    def update(self, dt: float) -> None:
        self.t += dt

    def stamp(
        self,
        lines: list[str],
    ) -> tuple[list[str], dict[tuple[int, int], tuple[int, int, int]]]:
        if not lines:
            return lines, {}
        h = len(lines)
        w = max(len(line) for line in lines)
        self.h, self.w = h, w
        # Keep sun pinned to top-right if canvas size changed
        self.sun_x = w * 0.92
        self.sun_y = -1.2
        self.falloff_len = max(14.0, (h + w) * 0.55)

        grid = [list(line.ljust(w)) for line in lines]
        glow: dict[tuple[int, int], float] = {}
        cascade_speed = 3.2  # cells per second along ray
        step_size = 0.55

        for angle, phase, width in self.rays:
            # Direction: 0 = straight down; negative angle → leftward
            dx = math.sin(angle)
            dy = math.cos(angle)
            x, y = self.sun_x, self.sun_y
            steps = int((h + w) * 2.0)
            for step in range(steps):
                x += dx * step_size
                y += dy * step_size
                # Distance from sun origin (for radial fade)
                dist = math.hypot(x - self.sun_x, y - self.sun_y)
                # Smooth falloff: full near origin → 0 past falloff_len
                # ease: (1 - t)^2 keeps a soft tail
                t_dist = dist / self.falloff_len
                if t_dist >= 1.0:
                    break
                radial = (1.0 - t_dist) ** 2

                ix, iy = int(round(x)), int(round(y))
                if iy < 0:
                    continue
                if iy >= h or ix < -1 or ix >= w + 1:
                    if iy >= h or ix < -2:
                        break
                    continue

                for ox in range(-1, 2):
                    nx = ix + ox
                    if nx < 0 or nx >= w or iy < 0 or iy >= h:
                        continue
                    lateral = abs(ox) / max(width * 2.2, 0.5)
                    if lateral > 1.0:
                        continue
                    # Cascading pulse along the beam
                    wave = 0.5 + 0.5 * math.sin(
                        step * 0.45 - self.t * cascade_speed + phase
                    )
                    wave *= 0.65 + 0.35 * (
                        0.5 + 0.5 * math.sin(self.t * 2.1 + phase + step * 0.1)
                    )
                    strength = (
                        (1.0 - lateral * 0.75)
                        * wave
                        * radial
                        * (0.55 + 0.45 * self.intensity)
                    )
                    # Near-origin boost so the top-right feels like the source
                    if dist < 4.0:
                        strength = min(1.0, strength * (1.15 + 0.1 * (4.0 - dist)))
                    key = (nx, iy)
                    if strength > glow.get(key, 0.0):
                        glow[key] = strength

        colors: dict[tuple[int, int], tuple[int, int, int]] = {}
        for (ix, iy), strength in glow.items():
            if strength < 0.10:
                continue
            cell = grid[iy][ix]
            on_ink = is_ink(cell) and cell not in RAY_CHARS and cell not in SPARK_CHARS
            if not on_ink:
                if strength > 0.7:
                    ch = "/"
                elif strength > 0.4:
                    ch = "·"
                else:
                    ch = "."
                grid[iy][ix] = ch
            ci = min(len(RAY_COLORS) - 1, int(strength * (len(RAY_COLORS) - 1)))
            r, g, b = RAY_COLORS[ci]
            boost = 0.45 + 0.55 * strength
            r = min(255, int(r * boost))
            g = min(255, int(g * boost))
            b = min(255, int(b * boost * 0.9))
            if on_ink:
                r = min(255, int(r * 0.85 + 40 * strength))
                g = min(255, int(g * 0.75 + 20 * strength))
                b = min(255, int(b * 0.45))
            colors[(ix, iy)] = (r, g, b)

        return ["".join(row) for row in grid], colors


# Little bugs that buzz above the meadow
BUG_CHARS = ("o", "°", "*", "·", "×")
BUG_COLORS = (
    (40, 35, 25),
    (90, 70, 30),
    (200, 180, 60),   # flash of wing / firefly glint
    (60, 50, 40),
)


class GrassField:
    """
    A grassy field along the bottom of the display, blades bending in wind,
    with a few little bugs buzzing just above the meadow.
    """

    def __init__(
        self,
        lines: list[str],
        intensity: float = 0.45,
    ):
        self.intensity = max(0.0, min(1.0, intensity))
        self.t = 0.0
        self.h = len(lines) if lines else 1
        self.w = max((len(line) for line in lines), default=1) if lines else 1
        # How tall the meadow band is (rows from the bottom)
        self.band = max(2, min(5, 2 + int(2.5 * self.intensity)))
        # blade: base_x, height (1..band), phase, bend_amp, tint
        self.blades: list[list[float]] = []
        # Spacing: denser with intensity, but leave gaps for a natural field
        step = 1 if self.intensity > 0.7 else 2
        dens = 0.45 + 0.50 * self.intensity  # chance per column
        for x in range(0, self.w, step):
            if random.random() > dens:
                continue
            height = 1 + int(random.random() * (self.band - 1 + 0.99))
            height = max(1, min(self.band, height))
            phase = random.random() * math.pi * 2
            bend = 0.55 + random.random() * 0.9
            tint = random.random()
            self.blades.append([float(x), float(height), phase, bend, tint])
            if step == 1 and random.random() < 0.25 * self.intensity and x + 1 < self.w:
                self.blades.append(
                    [
                        float(x) + 0.3,
                        float(max(1, height - 1)),
                        phase + 0.7,
                        bend * 0.85,
                        min(1.0, tint + 0.15),
                    ]
                )

        # Exactly 3 bugs: home_x, home_y, phase, buzz_speed, orbit, color_bias
        # They cruise just above the grass tops
        grass_top = self.h - self.band - 0.5
        self.bugs: list[list[float]] = []
        for i in range(3):
            home_x = self.w * (0.18 + 0.28 * i) + random.uniform(-1.5, 1.5)
            home_y = grass_top - random.uniform(0.8, 2.8)
            self.bugs.append(
                [
                    home_x,
                    home_y,
                    random.random() * math.pi * 2,
                    3.5 + random.random() * 3.0,  # buzz speed
                    1.2 + random.random() * 1.8,  # orbit radius
                    random.random(),
                ]
            )

    def update(self, dt: float) -> None:
        # Grass/wind a bit slower; bugs much calmer (readable buzz)
        grass_dt = dt * 0.75
        bug_dt = dt * 0.25
        self.t += grass_dt
        # Wind also pushes bugs a little
        wind = math.sin(self.t * 1.35) * 0.9
        for bug in self.bugs:
            home_x, home_y, phase, speed, orbit, bias = bug
            phase += speed * bug_dt
            # Slow wander of home along the field
            home_x += (
                wind * 0.35 + math.sin(phase * 0.15 + bias * 4) * 0.8
            ) * bug_dt
            # Wrap / bounce within horizontal bounds
            if home_x < 1.0:
                home_x = 1.0
            elif home_x > self.w - 2.0:
                home_x = self.w - 2.0
            # Bob home height gently
            grass_top = self.h - self.band - 0.5
            home_y += math.sin(phase * 0.4 + bias) * 0.15 * bug_dt
            home_y = max(grass_top - 4.0, min(grass_top - 0.4, home_y))
            bug[0], bug[1], bug[2] = home_x, home_y, phase

    def _bug_pos(self, bug: list[float]) -> tuple[float, float]:
        home_x, home_y, phase, _speed, orbit, bias = bug
        # Tight, jittery buzz (figure-eight-ish)
        x = (
            home_x
            + math.sin(phase * 2.1) * orbit
            + math.sin(phase * 5.3 + bias) * 0.45
        )
        y = (
            home_y
            + math.cos(phase * 1.7) * orbit * 0.55
            + math.sin(phase * 6.1) * 0.35
        )
        return x, y

    def _wind(self, x: float, phase: float) -> float:
        """Horizontal lean in cells; stronger higher up the blade (applied by caller)."""
        # Gust front moving across the field + local flutter
        gust = math.sin(self.t * 1.35 + x * 0.22)
        swell = math.sin(self.t * 0.55 + 0.4) * 0.65
        flutter = math.sin(self.t * 3.1 + phase) * 0.35
        return gust * 1.15 + swell + flutter

    def stamp(
        self,
        lines: list[str],
    ) -> tuple[list[str], dict[tuple[int, int], tuple[int, int, int]]]:
        if not lines:
            return lines, {}
        h = len(lines)
        w = max(len(line) for line in lines)
        self.h, self.w = h, w
        grid = [list(line.ljust(w)) for line in lines]
        colors: dict[tuple[int, int], tuple[int, int, int]] = {}
        base_y = h - 1

        for base_x, height, phase, bend_amp, tint in self.blades:
            height_i = int(height)
            wind = self._wind(base_x, phase)
            for row in range(height_i):
                # Tip leans more than the root
                frac = (row + 1) / max(height_i, 1)
                lean = wind * bend_amp * (frac ** 1.35)
                ix = int(round(base_x + lean))
                iy = base_y - row
                if ix < 0 or ix >= w or iy < 0 or iy >= h:
                    continue
                cell = grid[iy][ix]
                # Never overwrite the kanji body
                if is_ink(cell) and cell not in GRASS_CHARS and cell not in SPARK_CHARS:
                    continue
                # Character by lean direction
                if lean > 0.55:
                    ch = "/"
                elif lean < -0.55:
                    ch = "\\"
                elif abs(lean) > 0.25:
                    ch = "/" if lean > 0 else "\\"
                else:
                    ch = "|" if row > 0 else ","
                # Root row denser turf
                if row == 0 and abs(lean) < 0.35:
                    roots = (",", ";", "|", ",")
                    ch = roots[int(phase * 7) % len(roots)]

                ci = min(len(GRASS_COLORS) - 1, int(tint * (len(GRASS_COLORS) - 1)))
                r, g, b = GRASS_COLORS[ci]
                # Tips slightly lighter / sun-kissed
                lift = 0.85 + 0.20 * frac
                # Wind sheen
                sheen = 0.92 + 0.08 * (0.5 + 0.5 * math.sin(self.t * 2.0 + phase))
                r = min(255, int(r * lift * sheen))
                g = min(255, int(g * lift * sheen))
                b = min(255, int(b * lift * sheen * 0.95))
                grid[iy][ix] = ch
                colors[(ix, iy)] = (r, g, b)

        # Sparse seed heads on taller blades — nod harder in the wind
        for base_x, height, phase, bend_amp, tint in self.blades:
            if height < 2 or (int(phase * 10) % 3) != 0:
                continue
            wind = self._wind(base_x, phase)
            lean = wind * bend_amp * 1.15
            ix = int(round(base_x + lean))
            iy = base_y - int(height) + 1
            if 0 <= ix < w and 0 <= iy < h:
                cell = grid[iy][ix]
                if is_ink(cell) and cell not in GRASS_CHARS:
                    continue
                grid[iy][ix] = "'" if abs(lean) < 0.4 else ("`" if lean > 0 else ".")
                colors[(ix, iy)] = (180, 200, 100)

        # Three bugs buzzing above the grass
        for bug in self.bugs:
            x, y = self._bug_pos(bug)
            ix, iy = int(round(x)), int(round(y))
            if ix < 0 or ix >= w or iy < 0 or iy >= h:
                continue
            cell = grid[iy][ix]
            if is_ink(cell) and cell not in GRASS_CHARS and cell not in BUG_CHARS:
                continue
            phase = bug[2]
            bias = bug[5]
            # Wing-beat flicker of glyph
            beat = 0.5 + 0.5 * math.sin(phase * 2.0)
            if beat > 0.72:
                ch = "*"
            elif beat > 0.4:
                ch = "o"
            else:
                ch = "·"
            # Occasional bright wing glint
            if math.sin(phase * 3.7 + bias * 5) > 0.85:
                ch = "°"
                rgb = BUG_COLORS[2]
            else:
                ci = int(bias * (len(BUG_COLORS) - 1)) % len(BUG_COLORS)
                if ci == 2:
                    ci = 0
                rgb = BUG_COLORS[ci]
            grid[iy][ix] = ch
            colors[(ix, iy)] = rgb

        return ["".join(row) for row in grid], colors


def make_effect_field(
    name: str,
    *,
    canvas: list[str],
    edges: list[tuple[int, int]],
    intensity: float,
):
    """Build the particle field for the named animation effect."""
    if name == "starlight":
        return StarField(canvas, intensity=intensity)
    if name == "sakura":
        return SakuraField(canvas, intensity=intensity)
    if name == "sunrays":
        return SunrayField(canvas, intensity=intensity)
    if name == "grass":
        return GrassField(canvas, intensity=intensity)
    # default: embers
    return EmberField(
        edges,
        intensity=intensity,
        width=max((len(r) for r in canvas), default=0),
        height=len(canvas),
    )


def load_kanji(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list) or not data:
        raise SystemExit(f"No kanji entries in {path}")
    return data


def pick_entry(entries: list[dict], mode: str, char: str | None) -> dict:
    if char:
        for e in entries:
            if e["char"] == char:
                return e
        raise SystemExit(f"Kanji '{char}' not found in data file.")
    if mode == "daily":
        # Stable pick for the calendar day
        idx = date.today().toordinal() % len(entries)
        return entries[idx]
    return random.choice(entries)


def entry_keywords(entry: dict) -> list[str]:
    """Lowercased search terms: primary keyword first, then aliases."""
    primary = (entry.get("keyword") or "").strip()
    extra = entry.get("keywords") or []
    out: list[str] = []
    if primary:
        out.append(primary.lower())
    for k in extra:
        k = (k or "").strip().lower()
        if k and k not in out:
            out.append(k)
    return out


def find_by_keyword(entries: list[dict], query: str) -> list[dict]:
    """
    Match English keywords.
    Preference: exact keyword → prefix → substring (all case-insensitive).
    """
    q = query.strip().lower()
    if not q:
        return []

    exact: list[dict] = []
    prefix: list[dict] = []
    partial: list[dict] = []
    for e in entries:
        kws = entry_keywords(e)
        if not kws:
            continue
        if q in kws:
            exact.append(e)
        elif any(k.startswith(q) for k in kws):
            prefix.append(e)
        elif any(q in k for k in kws):
            partial.append(e)
    return exact or prefix or partial


def resolve_keyword(entries: list[dict], query: str) -> dict:
    """Resolve a keyword to one entry, or exit with a helpful message."""
    matches = find_by_keyword(entries, query)
    if not matches:
        raise SystemExit(
            f"No kanji matching '{query}'. Try: kanji-splash --list"
        )
    if len(matches) == 1:
        return matches[0]

    # Multiple hits — print them, prefer exact primary keyword
    q = query.strip().lower()
    primary_hits = [
        e for e in matches if (e.get("keyword") or "").lower() == q
    ]
    print(C.paint(f"Several kanji match '{query}':", C.BOLD, C.CYAN))
    for e in matches:
        kw = e.get("keyword") or "?"
        meaning = (e.get("meaning") or "").split(";")[0].strip()
        mark = " ←" if primary_hits and e is primary_hits[0] else ""
        print(
            f"  {C.paint(e['char'], C.BOLD, C.YELLOW)}  "
            f"{C.paint(kw, C.GREEN)}  {meaning}{mark}"
        )
    chosen = primary_hits[0] if primary_hits else matches[0]
    print(
        C.paint(
            f"Showing {chosen['char']} ({chosen.get('keyword', '?')}). "
            f"Use -c {chosen['char']} to pin it.",
            C.DIM,
        )
    )
    print()
    return chosen


def term_width(fallback: int = 80) -> int:
    return shutil.get_terminal_size((fallback, 24)).columns


def display_width(text: str) -> int:
    """Column width of text, treating fullwidth / wide CJK as 2 cells."""
    w = 0
    for ch in text:
        if unicodedata.east_asian_width(ch) in ("F", "W"):
            w += 2
        elif unicodedata.category(ch) == "Mn":
            continue
        else:
            w += 1
    return w


def primary_meaning(entry: dict) -> str:
    """Short poetic gloss — first clause of the meaning field."""
    raw = (entry.get("meaning") or "").strip()
    if not raw:
        return ""
    return raw.split(";")[0].strip()


def highlight_char(text: str, char: str, *, use_dim: bool) -> str:
    """Color every occurrence of char inside text (for haiku emphasis)."""
    if not char or char not in text:
        return C.paint(text, C.DIM if use_dim else C.BRIGHT_WHITE)
    if use_dim:
        return C.paint(text, C.DIM, C.WHITE)
    parts: list[str] = []
    segments = text.split(char)
    for i, piece in enumerate(segments):
        if i:
            parts.append(C.paint(char, C.BOLD, C.BRIGHT_YELLOW))
        if piece:
            parts.append(C.paint(piece, C.BRIGHT_WHITE))
    return "".join(parts)


def format_haiku_rows(entry: dict) -> list[tuple[str, str]]:
    """Haiku under the glyph as (plain, colored) rows — no section label."""
    haiku = entry.get("haiku")
    if not isinstance(haiku, dict):
        return []

    lines = haiku.get("lines") or []
    if not lines:
        return []

    char = entry.get("char", "")
    out: list[tuple[str, str]] = []

    for line in lines:
        out.append((line, highlight_char(line, char, use_dim=False)))

    author = haiku.get("author") or ""
    author_en = haiku.get("author_en") or ""
    if author or author_en:
        if author and author_en and author_en not in ("classical style",):
            by_plain = f"— {author}"
        elif author:
            by_plain = f"— {author}"
        else:
            by_plain = f"— {author_en}"
        out.append((by_plain, C.paint(by_plain, C.DIM, C.CYAN)))

    translation = haiku.get("translation") or ""
    if translation:
        t_plain = f"“{translation}”"
        out.append((t_plain, C.paint(t_plain, C.WHITE)))

    return out


def typewriter_take(
    rows: list[tuple[str, str]],
    n: int,
) -> list[tuple[str, str]]:
    """
    Reveal the first n plain characters across rows (typewriter).
    Empty rows count as 1 character so blank lines still pace the reveal.
    """
    if n < 0:
        return []
    out: list[tuple[str, str]] = []
    left = n
    for plain, colored in rows:
        if left <= 0:
            break
        if plain == "":
            out.append(("", ""))
            left -= 1
            continue
        if len(plain) <= left:
            out.append((plain, colored))
            left -= len(plain)
        else:
            partial = plain[:left]
            # Partial line: simple paint (full highlight would need re-split)
            out.append((partial, C.paint(partial, C.BRIGHT_WHITE)))
            left = 0
            break
    return out


def text_typewriter_budget(rows: list[tuple[str, str]]) -> int:
    """Total typewriter units for a list of (plain, colored) rows."""
    total = 0
    for plain, _ in rows:
        total += 1 if plain == "" else len(plain)
    return total


def shift_hue(
    rgb: tuple[int, int, int],
    hue_delta: float,
    *,
    brightness: float = 1.0,
) -> tuple[int, int, int]:
    """Rotate hue by hue_delta (fraction of the wheel) and scale value."""
    r, g, b = (c / 255.0 for c in rgb)
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    h = (h + hue_delta) % 1.0
    v = max(0.0, min(1.0, v * brightness))
    rr, gg, bb = colorsys.hsv_to_rgb(h, s, v)
    return int(rr * 255), int(gg * 255), int(bb * 255)


def colorize_art(
    lines: list[str],
    style: str = "ember",
    *,
    ink_color: str | None = None,
    hue_shift: float = 0.0,
    brightness: float = 1.0,
    noise: float = 0.0,
    noise_t: float = 0.0,
    spark_colors: dict[tuple[int, int], tuple[int, int, int]] | None = None,
) -> list[str]:
    """
    Tint non-space characters with a truecolor vertical gradient + hue shift.

    Body noise stays subtle. Cells in spark_colors get particle RGB instead.
    ink_color (from COLOR_CYCLE) overrides the legacy style palette when set.
    """
    if not C.enabled:
        return lines

    if ink_color and ink_color in COLOR_PALETTES:
        palette = COLOR_PALETTES[ink_color]
    else:
        palette = STYLE_RGB.get(style, STYLE_RGB["ember"])
    out = []
    h = max(len(lines), 1)
    last = len(palette) - 1
    noise = max(0.0, min(1.0, noise))
    spark_colors = spark_colors or {}

    for yi, line in enumerate(lines):
        ty = yi / max(h - 1, 1)
        # Interpolate between palette stops for smoother gradients
        pos = ty * last
        lo = int(pos)
        hi = min(lo + 1, last)
        frac = pos - lo
        c0, c1 = palette[lo], palette[hi]
        base = (
            int(c0[0] + (c1[0] - c0[0]) * frac),
            int(c0[1] + (c1[1] - c0[1]) * frac),
            int(c0[2] + (c1[2] - c0[2]) * frac),
        )
        colored = []
        for xi, ch in enumerate(line):
            if not ch.strip():
                colored.append(ch)
                continue

            if (xi, yi) in spark_colors:
                r, g, b = spark_colors[(xi, yi)]
                code = C.FG_RGB.format(r=r, g=g, b=b)
                colored.append(code + ch + C.RESET)
                continue

            cell_hue = hue_shift
            cell_bright = brightness
            if noise > 0.0:
                # Very mild body breath — no hot flashes on the kanji itself
                ph = xi * 1.1 + yi * 1.4 + noise_t * 2.2
                cell_hue += noise * 0.018 * math.sin(ph)
                cell_bright *= 1.0 + noise * 0.06 * math.sin(ph * 0.7 + 1.0)

            r, g, b = shift_hue(base, cell_hue, brightness=cell_bright)
            code = C.FG_RGB.format(r=r, g=g, b=b)
            colored.append(code + ch + C.RESET)
        out.append("".join(colored))
    return out


def build_text_rows(
    entry: dict,
    *,
    art_w: int,
    effect_name: str | None = None,
    ink_color: str | None = None,
    status_hint: str | None = None,
) -> list[tuple[str, str]]:
    """
    All chrome text around the glyph as (plain, colored) rows, in typewriter order:
    title → rule → meaning → haiku → rule → effect · color → shortcuts.
    """
    rule = "─" * min(term_width(), max(art_w + 4, 48))
    title = "◆  今日の漢字  ·  kanji splash  ◆"
    meaning = primary_meaning(entry)
    rows: list[tuple[str, str]] = []

    rows.append((title, C.paint(title, C.BOLD, C.BRIGHT_CYAN)))
    rows.append((rule, C.paint(rule, C.DIM)))
    rows.append(("", ""))

    if meaning:
        rows.append((meaning, C.paint(meaning, C.BOLD, C.BRIGHT_WHITE)))
        rows.append(("", ""))

    # Placeholder for glyph — not typewriter content; art is inserted by build_panel
    rows.append(("__ART__", ""))

    rows.append(("", ""))
    rows.extend(format_haiku_rows(entry))
    rows.append(("", ""))
    rows.append((rule, C.paint(rule, C.DIM)))

    if status_hint is not None:
        effect_line = status_hint
    else:
        bits = [b for b in (effect_name, ink_color) if b]
        effect_line = "  ·  ".join(bits)
    if effect_line:
        rows.append((effect_line, C.paint(effect_line, C.BOLD, C.BRIGHT_CYAN)))

    shortcuts = shortcuts_footer()
    rows.append((shortcuts, C.paint(shortcuts, C.WHITE)))
    return rows


def build_panel(
    entry: dict,
    art_lines: list[str],
    *,
    style: str,
    ramp: str,
    hue_shift: float = 0.0,
    fade: float = 1.0,
    show_details: bool = True,
    noise: float = 0.0,
    noise_t: float = 0.0,
    effect_field=None,
    breath: float = 1.0,
    body_grain: bool = True,
    effect_name: str | None = None,
    ink_color: str | None = None,
    status_hint: str | None = None,
    typewriter_chars: int | None = None,
) -> str:
    """
    Compose the splash panel.

    fade — only affects the kanji glyph density/brightness.
    typewriter_chars — if set, reveal that many text characters (None = full text).
    show_details=False — glyph + no text (intro fade phase).
    """
    width = term_width()
    faded = apply_fade(art_lines, ramp, fade)

    # Gentle breathing (starlight) — density pulse on the glyph body
    if abs(breath - 1.0) > 0.01 and fade > 0.4:
        faded = apply_breath(faded, ramp, breath)

    # Body grain: only for embers-style (kept mild)
    body_noise = noise * 0.35 if body_grain else 0.0
    if body_noise > 0.0 and fade > 0.5:
        faded = apply_noise(faded, ramp, amount=body_noise * fade, t=noise_t)

    spark_rgb: dict[tuple[int, int], tuple[int, int, int]] = {}
    if effect_field is not None and fade > 0.55:
        faded, spark_rgb = effect_field.stamp(faded)

    # Match ink brightness to fade + breath
    art_bright = (0.35 + 0.65 * fade) * max(0.8, min(1.15, breath))
    art = colorize_art(
        faded,
        style=style,
        ink_color=ink_color,
        hue_shift=hue_shift,
        brightness=art_bright,
        noise=body_noise * fade,
        noise_t=noise_t,
        spark_colors=spark_rgb,
    )
    art_w = max((len(line) for line in art_lines), default=0)

    def center_ansi(plain: str, colored: str) -> str:
        """Center using plain text display width."""
        pad = max(0, (width - display_width(plain)) // 2)
        return " " * pad + colored

    # Fixed pad for the art block (pre-particle width). Particle overlays must
    # never affect this — otherwise the kanji jitters horizontally each frame.
    art_layout_w = max((display_width(line) for line in art_lines), default=art_w)
    art_pad = max(0, (width - art_layout_w) // 2)
    art_pad_s = " " * art_pad

    parts: list[str] = []
    parts.append("")

    if not show_details and typewriter_chars is None:
        # Glyph-only (fade-in phase): keep vertical room calm
        for line, _raw in zip(art, faded):
            parts.append(art_pad_s + line)
        parts.append("")
        return "\n".join(parts)

    text_rows = build_text_rows(
        entry,
        art_w=art_w,
        effect_name=effect_name,
        ink_color=ink_color,
        status_hint=status_hint,
    )

    # Split around art placeholder
    try:
        art_idx = next(i for i, (p, _) in enumerate(text_rows) if p == "__ART__")
    except StopIteration:
        art_idx = len(text_rows)

    pre_rows = text_rows[:art_idx]
    post_rows = text_rows[art_idx + 1 :]

    # Typewriter reveals chrome only; glyph is already fully faded in
    if typewriter_chars is not None:
        pre_budget = text_typewriter_budget(pre_rows)
        if typewriter_chars < pre_budget:
            pre_rows = typewriter_take(pre_rows, typewriter_chars)
            post_rows = []
        else:
            post_rows = typewriter_take(post_rows, typewriter_chars - pre_budget)

    for plain, colored in pre_rows:
        parts.append(center_ansi(plain, colored if colored else plain))

    for line, _raw in zip(art, faded):
        parts.append(art_pad_s + line)

    for plain, colored in post_rows:
        parts.append(center_ansi(plain, colored if colored else plain))

    parts.append("")
    return "\n".join(parts)


def count_typewriter_chars(entry: dict, *, effect_name: str | None, ink_color: str | None) -> int:
    """Full typewriter length for chrome text (excluding the glyph)."""
    rows = build_text_rows(
        entry, art_w=40, effect_name=effect_name, ink_color=ink_color
    )
    # Exclude art placeholder from budget
    rows = [(p, c) for p, c in rows if p != "__ART__"]
    return text_typewriter_budget(rows)


def ease_out_cubic(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1.0 - (1.0 - t) ** 3


def shimmer_hue(elapsed: float, hue_direction: float) -> float:
    """Ongoing hue motion: slow sweep + faster ripple, biased by direction."""
    slow = math.sin(elapsed * 1.7) * SHIMMER_HUE_AMP
    fast = math.sin(elapsed * 4.8 + 1.1) * SHIMMER_HUE_FAST
    bias = hue_direction * (HUE_AMPLITUDE * 0.6)
    return slow + fast + bias


def _stdin_key_waiting(timeout: float = 0.0) -> bool:
    if not sys.stdin.isatty():
        return False
    ready, _, _ = select.select([sys.stdin], [], [], timeout)
    return bool(ready)


def _read_raw_key() -> str:
    """Read one key (or escape sequence); return a short string. '' if none."""
    if not sys.stdin.isatty():
        return ""
    try:
        data = os.read(sys.stdin.fileno(), 16)
    except OSError:
        return ""
    if not data:
        return ""
    # Escape / CSI — treat bare ESC as quit
    if data[0:1] == b"\x1b":
        if len(data) == 1:
            return KEY_QUIT
        return ""  # ignore arrows etc.
    try:
        return data.decode("utf-8", errors="ignore")[:1]
    except Exception:
        return ""


def normalize_action(key: str) -> str:
    """
    Map a raw key to an action: n / l / d / a / q.
    Unknown keys become q (dismiss / quit).
    """
    if not key:
        return KEY_QUIT
    k = key.lower()
    if k in (KEY_NEW, KEY_LIST, KEY_DAILY, KEY_FX, KEY_COLOR, KEY_QUIT):
        return k
    if key in ("\x03", "\x04"):  # Ctrl-C / Ctrl-D
        return KEY_QUIT
    return KEY_QUIT


def wait_for_action(*, timeout: float | None = None) -> str:
    """Block until a key (or timeout → quit). Returns n/l/d/a/q."""
    if not sys.stdin.isatty():
        return KEY_QUIT
    if timeout is None:
        while True:
            if _stdin_key_waiting(0.25):
                return normalize_action(_read_raw_key())
    else:
        if _stdin_key_waiting(timeout):
            return normalize_action(_read_raw_key())
        return KEY_QUIT


def animate_display(
    entry: dict,
    art_lines: list[str],
    *,
    style: str,
    ramp: str,
    hue_direction: float,
    fade_frames: int = FADE_FRAMES,
    fade_seconds: float = FADE_SECONDS,
    noise: float = DEFAULT_NOISE,
    shimmer: bool = True,
    shimmer_seconds: float = 0.0,
    wait_after: bool = True,
    effect: str = DEFAULT_EFFECT,
    ink_color: str = DEFAULT_COLOR,
) -> tuple[str, str, str]:
    """
    Fade the glyph in, then hold with the active animation effect.

    Returns (action, effect, ink_color).
    Toggle effect with 'a', ink color with 'c'.
    """
    if effect not in EFFECTS:
        effect = DEFAULT_EFFECT
    if ink_color not in COLOR_PALETTES:
        ink_color = DEFAULT_COLOR

    # Room on all sides so starlight can wrap the full glyph (not just the top)
    canvas = pad_art(art_lines, top=3, bottom=3, left=5, right=5)
    edges = find_edge_cells(canvas)
    field = make_effect_field(
        effect, canvas=canvas, edges=edges, intensity=noise
    )

    delay = fade_seconds / max(fade_frames, 1)
    fd = sys.stdin.fileno() if sys.stdin.isatty() else None
    old_term: list | None = None
    use_alt = sys.stdout.isatty()
    final_panel = ""
    action: str | None = None  # None until the user presses a session key

    def draw(panel: str) -> None:
        sys.stdout.write(C.CLEAR_SCREEN)
        sys.stdout.write(panel)
        sys.stdout.flush()

    def still_panel(*, status: str | None = None) -> str:
        return build_panel(
            entry,
            canvas,
            style=style,
            ramp=ramp,
            hue_shift=hue_direction * HUE_AMPLITUDE,
            fade=1.0,
            show_details=True,
            noise=0.0,
            effect_field=None,
            breath=1.0,
            body_grain=False,
            effect_name=effect,
            ink_color=ink_color,
            status_hint=status,
            typewriter_chars=None,
        )

    def live_panel(
        elapsed: float,
        *,
        fade: float = 1.0,
        show_text: bool = True,
        typewriter_chars: int | None = None,
    ) -> str:
        # Starlight: soft glyph breath; sunrays: tiny warm pulse
        if effect == "starlight":
            breath = breath_level(elapsed)
        elif effect == "sunrays":
            breath = 1.0 + 0.04 * math.sin(elapsed * 1.4)
        else:
            breath = 1.0
        # Mild body grain only for embers
        body_grain = effect == "embers"
        # Palette whispers per effect (subtle; ink_color is the main hue)
        hue = shimmer_hue(elapsed, hue_direction)
        if effect == "sunrays":
            hue -= 0.02
        elif effect == "sakura":
            hue += 0.015
        elif effect == "grass":
            hue += 0.03
        return build_panel(
            entry,
            canvas,
            style=style,
            ramp=ramp,
            hue_shift=hue if fade >= 1.0 else (
                hue_direction * HUE_AMPLITUDE * ease_out_cubic(min(1.0, fade))
                + math.sin(fade * math.pi * 2.0) * (SHIMMER_HUE_AMP * 0.4)
            ),
            fade=fade,
            show_details=show_text,
            noise=noise,
            noise_t=elapsed,
            effect_field=field if fade > 0.55 else None,
            breath=breath if fade > 0.4 else 1.0,
            body_grain=body_grain,
            effect_name=effect,
            ink_color=ink_color,
            typewriter_chars=typewriter_chars,
        )

    def switch_effect() -> None:
        nonlocal effect, field
        effect = next_effect(effect)
        field = make_effect_field(
            effect, canvas=canvas, edges=edges, intensity=noise
        )

    def switch_color() -> None:
        nonlocal ink_color
        ink_color = next_color(ink_color)

    def handle_toggle(act: str) -> bool:
        """Return True if act was a live toggle (keep animating)."""
        if act == KEY_FX:
            switch_effect()
            return True
        if act == KEY_COLOR:
            switch_color()
            return True
        return False

    def run_hold(start_elapsed: float = 0.0) -> str | None:
        """Phase 2: live effect loop. Returns n/l/d/q, or None if timed out."""
        nonlocal field
        if not shimmer:
            return None
        frame_dt = 1.0 / SHIMMER_FPS
        t0 = time.monotonic() - start_elapsed
        # Ensure field intensity is full for the hold
        if hasattr(field, "intensity"):
            field.intensity = noise

        while True:
            elapsed = time.monotonic() - t0
            if shimmer_seconds > 0 and elapsed >= shimmer_seconds:
                return None
            if _stdin_key_waiting(0.0):
                raw = _read_raw_key()
                if raw:
                    act = normalize_action(raw)
                    if handle_toggle(act):
                        continue
                    return act

            field.update(frame_dt)
            draw(live_panel(elapsed))

            if _stdin_key_waiting(frame_dt):
                raw = _read_raw_key()
                if raw:
                    act = normalize_action(raw)
                    if handle_toggle(act):
                        continue
                    return act

    sys.stdout.write(C.HIDE_CURSOR)
    if use_alt:
        sys.stdout.write(C.ALT_SCREEN_ON)
        sys.stdout.write(C.CLEAR_SCREEN)
    sys.stdout.flush()
    try:
        if fd is not None:
            old_term = termios.tcgetattr(fd)
            tty.setcbreak(fd)

        # ── phase 1: fade-in the kanji glyph only ──────────────────────
        for i in range(fade_frames):
            t = i / max(fade_frames - 1, 1)
            fade = ease_out_cubic(t)
            if fade > 0.6:
                if hasattr(field, "intensity"):
                    field.intensity = noise * ((fade - 0.6) / 0.4)
                field.update(delay)
            elif hasattr(field, "intensity"):
                field.intensity = 0.0

            draw(live_panel(t * 2.0, fade=fade, show_text=False))
            if _stdin_key_waiting(0.0):
                raw = _read_raw_key()
                if raw:
                    act = normalize_action(raw)
                    if handle_toggle(act):
                        pass  # keep fading
                    else:
                        action = act
                        break
            time.sleep(delay)

        # ── phase 1b: quick typewriter for title / meaning / haiku / footer
        if action is None:
            if hasattr(field, "intensity"):
                field.intensity = noise
            total_tw = count_typewriter_chars(
                entry, effect_name=effect, ink_color=ink_color
            )
            # ~2–4 chars per tick for a snappy typewriter
            tw_step = max(2, total_tw // 40)
            tw_delay = 0.018
            n = 0
            tw_t0 = time.monotonic()
            while n < total_tw and action is None:
                field.update(tw_delay)
                elapsed = (time.monotonic() - tw_t0) + fade_seconds
                draw(
                    live_panel(
                        elapsed,
                        fade=1.0,
                        show_text=True,
                        typewriter_chars=n,
                    )
                )
                if _stdin_key_waiting(0.0):
                    raw = _read_raw_key()
                    if raw:
                        act = normalize_action(raw)
                        if handle_toggle(act):
                            # color/effect change mid-typewriter — keep going
                            pass
                        else:
                            action = act
                            break
                n += tw_step
                time.sleep(tw_delay)
            # Ensure full text once
            if action is None:
                field.update(0.0)
                draw(
                    live_panel(
                        time.monotonic() - tw_t0 + fade_seconds,
                        fade=1.0,
                        show_text=True,
                        typewriter_chars=None,
                    )
                )

        # ── phase 2: live hold (re-enter if user toggles on still frame) ─
        while action is None:
            if shimmer:
                action = run_hold()
            if action is not None:
                break

            # Timed out or no shimmer — still frame, wait for key
            final_panel = still_panel()
            draw(final_panel)
            if not wait_after or fd is None:
                action = KEY_QUIT
                break
            act = wait_for_action()
            if handle_toggle(act):
                # Resume live animation with new effect/color
                action = None
                if hasattr(field, "intensity"):
                    field.intensity = noise
                continue
            action = act
            break

        if final_panel == "" or action not in (None,):
            final_panel = still_panel()
            draw(final_panel)

        return (action if action is not None else KEY_QUIT), effect, ink_color
    finally:
        if fd is not None and old_term is not None:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_term)
        if use_alt:
            sys.stdout.write(C.ALT_SCREEN_OFF)
        sys.stdout.write(C.SHOW_CURSOR)
        sys.stdout.flush()
        if use_alt and final_panel:
            sys.stdout.write(final_panel)
            if not final_panel.endswith("\n"):
                sys.stdout.write("\n")
            sys.stdout.flush()


def list_entries(entries: list[dict]) -> None:
    print(C.paint("Available kanji:", C.BOLD, C.CYAN))
    print(
        C.paint(
            "  kanji  keyword       meaning",
            C.DIM,
        )
    )
    # Sort by English keyword so scanning feels natural
    rows = sorted(
        entries,
        key=lambda e: (e.get("keyword") or "").lower(),
    )
    for e in rows:
        kw = e.get("keyword") or "?"
        meaning = e["meaning"].split(";")[0].strip()
        # Fixed-width keyword column (plain length; ASCII keywords only)
        pad = max(1, 12 - len(kw))
        print(
            f"  {C.paint(e['char'], C.BOLD, C.YELLOW)}  "
            f"{C.paint(kw, C.GREEN)}{' ' * pad}"
            f"{meaning}"
        )
    print()
    print(
        C.paint(
            "  lookup: kanji-splash <keyword>   e.g.  kanji-splash moon",
            C.DIM,
        )
    )
    print(C.paint(f"  {shortcuts_footer()}", C.DIM))


def render_static_panel(
    entry: dict,
    *,
    style: str,
    ramp: str,
    ramp_name: str,
    invert: bool,
    width: int,
    hue_direction: float,
) -> tuple[list[str], str]:
    """Build art + panel string for a single entry (no animation)."""
    tw = term_width()
    cols = width if width > 0 else max(28, min(48, tw - 8))
    art = kanji_to_ascii(
        entry["char"],
        cols=cols,
        ramp_name=ramp_name,
        invert=invert,
    )
    art = strip_empty_rows(art)
    canvas = pad_art(art, top=4, bottom=1, left=2, right=2)
    panel = build_panel(
        entry,
        canvas,
        style=style,
        ramp=ramp,
        hue_shift=hue_direction * HUE_AMPLITUDE if C.enabled else 0.0,
        fade=1.0,
        show_details=True,
        noise=0.0,
    )
    return art, panel


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Terminal start screen: ASCII kanji, meaning, and a haiku. "
            "Look up by English keyword: kanji-splash moon"
        )
    )
    parser.add_argument(
        "query",
        nargs="?",
        metavar="keyword",
        help="English keyword to find a kanji (e.g. moon, dream, rain).",
    )
    parser.add_argument(
        "-c", "--char",
        help="Show a specific kanji character (must exist in the data file).",
    )
    parser.add_argument(
        "-m", "--mode",
        choices=("random", "daily"),
        default="random",
        help="How to pick when --char is omitted (default: random).",
    )
    parser.add_argument(
        "-s", "--style",
        choices=tuple(STYLE_RGB.keys()),
        default="ember",
        help="Color gradient for the ASCII art.",
    )
    parser.add_argument(
        "-r", "--ramp",
        choices=tuple(RAMPS.keys()),
        default="blocks",
        help="Character ramp for the art.",
    )
    parser.add_argument(
        "-w", "--width",
        type=int,
        default=0,
        help="Art width in characters (0 = auto from terminal).",
    )
    parser.add_argument(
        "--data",
        type=Path,
        default=DEFAULT_DATA,
        help=f"Path to kanji JSON (default: {DEFAULT_DATA}).",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List kanji in the data file and exit.",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable ANSI colors.",
    )
    parser.add_argument(
        "--invert",
        action="store_true",
        help="Invert the density ramp.",
    )
    parser.add_argument(
        "--no-animate",
        action="store_true",
        help="Skip fade-in and shimmer; print the final frame once.",
    )
    parser.add_argument(
        "--no-shimmer",
        action="store_true",
        help="Play the fade-in only, then freeze (no ongoing shimmer).",
    )
    parser.add_argument(
        "--fade-ms",
        type=int,
        default=int(FADE_SECONDS * 1000),
        help=f"Fade-in duration in milliseconds (default: {int(FADE_SECONDS * 1000)}).",
    )
    parser.add_argument(
        "--shimmer-sec",
        type=float,
        default=0.0,
        help="Auto-stop shimmer after N seconds (0 = until any keypress).",
    )
    parser.add_argument(
        "--noise",
        type=float,
        default=DEFAULT_NOISE,
        metavar="0..1",
        help=f"Particle intensity 0..1 (embers / starlight, default: {DEFAULT_NOISE}).",
    )
    parser.add_argument(
        "--effect",
        choices=EFFECTS,
        default=DEFAULT_EFFECT,
        help=(
            f"Animation effect: {', '.join(EFFECTS)} "
            f"(default: {DEFAULT_EFFECT}). Toggle live with key '{KEY_FX}'."
        ),
    )
    parser.add_argument(
        "--color",
        choices=COLOR_NAMES,
        default=None,
        help=(
            f"Force kanji ink color: {', '.join(COLOR_NAMES)}. "
            f"Default: per-kanji color from data (or random if abstract). "
            f"Toggle live with key '{KEY_COLOR}'."
        ),
    )
    args = parser.parse_args(argv)

    C.enabled = (
        not args.no_color
        and sys.stdout.isatty()
        and os.environ.get("NO_COLOR") is None
        and os.environ.get("TERM") not in (None, "dumb")
    )

    entries = load_kanji(args.data)
    if args.list and not sys.stdin.isatty():
        list_entries(entries)
        return 0

    if args.query and args.char:
        raise SystemExit("Use either a keyword or -c CHAR, not both.")

    mode = args.mode
    forced_char: str | None = args.char
    if args.query:
        forced_char = resolve_keyword(entries, args.query)["char"]

    noise = max(0.0, min(1.0, args.noise))
    ramp = RAMPS.get(args.ramp, RAMPS["blocks"])
    if args.invert:
        ramp = ramp[::-1]

    interactive = sys.stdin.isatty() and sys.stdout.isatty()
    can_animate = (
        C.enabled
        and not args.no_animate
        and interactive
        and os.environ.get("TERM") not in (None, "dumb")
    )
    # CLI --effect / --color force only the next kanji pick; then entry defaults apply
    forced_effect: str | None = (
        args.effect if args.effect in EFFECTS else None
    )
    # argparse always sets --effect default to DEFAULT_EFFECT — treat as force only
    # if user explicitly passed it. Detect via sys.argv.
    if "--effect" not in (argv or sys.argv[1:]):
        forced_effect = None
    forced_color: str | None = (
        args.color if args.color in COLOR_PALETTES else None
    )
    current_effect = forced_effect or DEFAULT_EFFECT
    current_color = forced_color or DEFAULT_COLOR

    # --list from a TTY: show list then enter the key loop
    if args.list and interactive:
        list_entries(entries)
        print()
        action = KEY_LIST  # fall through to handle like an in-session list
    else:
        action = None

    while True:
        if action == KEY_LIST:
            # Already printed, or print now after a keypress mid-session
            if not args.list:
                print()
                list_entries(entries)
                print()
            args.list = False
            if not interactive:
                return 0
            # Wait for next command without re-listing immediately
            fd = sys.stdin.fileno()
            old = termios.tcgetattr(fd)
            try:
                tty.setcbreak(fd)
                action = wait_for_action()
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old)
            if action == KEY_LIST:
                list_entries(entries)
                print()
                continue
            if action == KEY_QUIT:
                return 0
            if action == KEY_FX:
                current_effect = next_effect(current_effect)
                forced_effect = current_effect  # user choice sticks this pick
                action = KEY_LIST  # stay on list, re-prompt
                continue
            if action == KEY_COLOR:
                current_color = next_color(current_color)
                forced_color = current_color  # user choice sticks this pick
                action = KEY_LIST
                continue
            # n or d → show a splash
            forced_char = None
            if action == KEY_NEW:
                mode = "random"
            elif action == KEY_DAILY:
                mode = "daily"
            action = None

        entry = pick_entry(entries, mode, forced_char)
        forced_char = None  # -c only applies to the first show
        hue_direction = random.choice((-1.0, 1.0))
        # Per-kanji defaults unless user forced via CLI / (a) / (c)
        if forced_effect is not None:
            current_effect = forced_effect
            forced_effect = None  # one-shot unless they press (a) again
        else:
            current_effect = resolve_entry_effect(entry)
        if forced_color is not None:
            current_color = forced_color
            forced_color = None  # one-shot unless they press (c) again
        else:
            current_color = resolve_entry_color(entry)

        art = kanji_to_ascii(
            entry["char"],
            cols=(
                args.width
                if args.width > 0
                else max(28, min(48, term_width() - 8))
            ),
            ramp_name=args.ramp,
            invert=args.invert,
        )
        art = strip_empty_rows(art)

        if can_animate:
            action, current_effect, current_color = animate_display(
                entry,
                art,
                style=args.style,
                ramp=ramp,
                hue_direction=hue_direction,
                fade_frames=FADE_FRAMES,
                fade_seconds=max(0.05, args.fade_ms / 1000.0),
                noise=noise,
                shimmer=not args.no_shimmer,
                shimmer_seconds=max(0.0, args.shimmer_sec),
                wait_after=interactive,
                effect=current_effect,
                ink_color=current_color,
            )
            # If user cycled color during the splash, remember it for re-shows
            # of the *same* entry only until n/d picks a new kanji
        else:
            canvas = pad_art(art, top=4, bottom=1, left=2, right=2)
            print(
                build_panel(
                    entry,
                    canvas,
                    style=args.style,
                    ramp=ramp,
                    hue_shift=(
                        hue_direction * HUE_AMPLITUDE if C.enabled else 0.0
                    ),
                    fade=1.0,
                    show_details=True,
                    noise=0.0,
                    effect_name=current_effect,
                    ink_color=current_color,
                )
            )
            if not interactive:
                return 0
            fd = sys.stdin.fileno()
            old = termios.tcgetattr(fd)
            try:
                tty.setcbreak(fd)
                action = wait_for_action()
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old)
            if action == KEY_COLOR:
                current_color = next_color(current_color)
                forced_color = current_color
                continue
            if action == KEY_FX:
                current_effect = next_effect(current_effect)
                forced_effect = current_effect
                continue

        if action == KEY_NEW:
            mode = "random"
            continue
        if action == KEY_DAILY:
            mode = "daily"
            continue
        if action == KEY_LIST:
            continue  # handled at top of loop
        # q or anything else → exit, leaving the last panel on screen
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
