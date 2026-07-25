#!/usr/bin/env python3
"""Build orange-cat half-block logo assets for InvestPilot v0.2.2.

Outputs two artifacts:

1. ``src/investpilot/interface/_logo_assets.py`` — Python constants
   ``PALETTE`` (hex strings + ``None``), ``BIG_HEAD`` (32 cols × 36 rows of
   palette indices), and ``SMALL_FRAMES`` (dict of 5 animation names × 4
   frames, each 16 cols × 18 rows).

2. ``docs/iterations/v0.2.2/preview/*.png`` — human-review PNGs.

Run with ``uv run python tools/build_logos.py``. Idempotent.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
ASSETS_PY = ROOT / "src" / "investpilot" / "interface" / "_logo_assets.py"
PREVIEW_DIR = ROOT / "docs" / "iterations" / "v0.2.2" / "preview"

# ---------------------------------------------------------------------------
# Palette + grid geometry (mirrored in SPEC §3)
# ---------------------------------------------------------------------------

PALETTE: tuple[str | None, ...] = (
    None,           # 0 transparent
    "#F2B675",      # 1 orange (body/face)
    "#E89B4A",      # 2 darker orange (ear edges, base shading)
    "#FCE3C8",      # 3 light cream (inner ears, cheek highlights)
    "#3B2A20",      # 4 dark brown (mouth, whiskers)
    "#221814",      # 5 near-black (eyes, pupils)
)

PAL_HEX = {idx: c for idx, c in enumerate(PALETTE) if c is not None}


def _hex(rgb: str) -> tuple[int, int, int]:
    rgb = rgb.lstrip("#")
    return (int(rgb[0:2], 16), int(rgb[2:4], 16), int(rgb[4:6], 16))


PAL_RGB = {idx: _hex(c) for idx, c in PAL_HEX.items()}

# Targets in CELL grid (32 × 18 big, 16 × 9 small).  Each cell encodes
# two stacked pixels via half-block characters at render time, so the
# PIL canvas height equals ``cells_h * 2`` in base pixels.
BIG_CELLS_W, BIG_CELLS_H = 32, 18
SMALL_CELLS_W, SMALL_CELLS_H = 16, 9

# Source pixel scale per cell for PIL drawing (lets anti-aliasing look nice).
SCALE = 8
BIG_W = BIG_CELLS_W * SCALE
BIG_H = BIG_CELLS_H * SCALE * 2  # 2 rows of pixels per cell
SMALL_W = SMALL_CELLS_W * SCALE
SMALL_H = SMALL_CELLS_H * SCALE * 2


# ---------------------------------------------------------------------------
# Drawing primitives
# ---------------------------------------------------------------------------

def _filled_rect(canvas: Image.Image, x0: int, y0: int, x1: int, y1: int, idx: int) -> None:
    ImageDraw.Draw(canvas).rectangle(
        [x0, y0, max(x0, x1 - 1), max(y0, y1 - 1)],
        fill=PAL_RGB[idx],
    )


def draw_big(base_only: bool = False) -> Image.Image:
    """Draw the big 32×18-cell orange cat head. Returns PIL RGB image.

    Coordinates below are in *pixel* units on a ``BIG_W × BIG_H`` canvas.
    Each cell is ``SCALE`` pixels wide and ``2*SCALE`` pixels tall.
    """

    img = Image.new("RGB", (BIG_W, BIG_H), (255, 255, 255))  # white for diff
    d = ImageDraw.Draw(img)

    # ---- Color shorthand -------------------------------------------------
    ORANGE = 1
    DARK_O = 2
    LIGHT = 3
    DARK = 4
    BLACK = 5

    def cell_to_px(x: int, y: int) -> tuple[int, int]:
        return (x * SCALE, y * SCALE * 2)

    def px(x: int, y: int) -> tuple[int, int]:
        return (x * SCALE, y * SCALE * 2)

    # ---- Ears (triangles) ------------------------------------------------
    # Left outer ear: vertices approx at cells (3, 0), (10, 0), (6, 4)
    d.polygon(
        [px(3, 1), px(10, 1), px(7, 5)],
        fill=PAL_RGB[DARK_O],
    )
    d.polygon(
        [px(4, 2), px(9, 2), px(7, 4)],
        fill=PAL_RGB[ORANGE],
    )
    # Right outer ear (mirror)
    d.polygon(
        [px(22, 1), px(29, 1), px(25, 5)],
        fill=PAL_RGB[DARK_O],
    )
    d.polygon(
        [px(23, 2), px(28, 2), px(25, 4)],
        fill=PAL_RGB[ORANGE],
    )
    # Inner ears (lighter)
    d.polygon([px(5, 2.5), px(8, 2.5), px(7, 4.5)], fill=PAL_RGB[LIGHT])
    d.polygon([px(24, 2.5), px(27, 2.5), px(25, 4.5)], fill=PAL_RGB[LIGHT])

    # ---- Top tufts (5 little hairs at cells 11-20, row 0) ---------------
    tufts_x = [12, 14, 16, 18, 20]
    for tx in tufts_x:
        d.line([px(tx, 0.4), px(tx, 1.6)], fill=PAL_RGB[DARK], width=2)

    # ---- Face (orange filled rounded) -----------------------------------
    d.rounded_rectangle(
        [px(3, 4), px(29, 17)],
        radius=20,
        fill=PAL_RGB[ORANGE],
    )
    # Inner darker shading at the very bottom (chin line)
    d.rectangle(
        [px(5, 16), px(27, 17)],
        fill=PAL_RGB[DARK_O],
    )
    # Re-paint the ears on top of face fill
    d.polygon([px(3, 1), px(10, 1), px(7, 5)], fill=PAL_RGB[DARK_O])
    d.polygon([px(4, 2), px(9, 2), px(7, 4)], fill=PAL_RGB[ORANGE])
    d.polygon([px(22, 1), px(29, 1), px(25, 5)], fill=PAL_RGB[DARK_O])
    d.polygon([px(23, 2), px(28, 2), px(25, 4)], fill=PAL_RGB[ORANGE])
    d.polygon([px(5, 2.5), px(8, 2.5), px(7, 4.5)], fill=PAL_RGB[LIGHT])
    d.polygon([px(24, 2.5), px(27, 2.5), px(25, 4.5)], fill=PAL_RGB[LIGHT])
    # Re-paint tufts
    for tx in tufts_x:
        d.line([px(tx, 0.4), px(tx, 1.6)], fill=PAL_RGB[DARK], width=2)

    # ---- Eyes (big black circles around cells 9-10 and 22-23, row 7-9) --
    d.ellipse([px(8, 7), px(11.2, 10.3)], fill=PAL_RGB[BLACK])
    d.ellipse([px(20.8, 7), px(24, 10.3)], fill=PAL_RGB[BLACK])
    # Pupil highlights (small white dots) — we'll keep as black for half-block
    # simplicity (rendering treats BLACK as one color)

    # ---- Cheek highlights (small cream patches under eyes) --------------
    d.ellipse([px(7, 11), px(12, 13.5)], fill=PAL_RGB[LIGHT])
    d.ellipse([px(20, 11), px(25, 13.5)], fill=PAL_RGB[LIGHT])

    # ---- Nose (small triangle at center, cell 15.5 row 10) --------------
    d.polygon(
        [px(15, 10.0), px(17, 10.0), px(16, 11.2)],
        fill=PAL_RGB[DARK],
    )

    # ---- "w" mouth (zig-zag from nose down and out) ---------------------
    # Center bottom of nose ~ (16, 11.4); draw two soft curves.
    # Use polylines for crispness.
    d.line(
        [px(15.6, 11.4), px(14.4, 12.6), px(16, 12.1), px(17.6, 12.6), px(16.4, 11.4)],
        fill=PAL_RGB[DARK],
        width=3,
    )

    # ---- Whiskers (3 each side, radiating from cells (10, 11.5)/(22, 11.5))
    whisker_anchors = [11.0, 11.7, 12.4]
    for i, y in enumerate(whisker_anchors):
        slope = (i - 1) * 0.3  # -0.3, 0, +0.3
        # Left side
        d.line(
            [px(8, y), px(1.5, y + slope)],
            fill=PAL_RGB[DARK],
            width=2,
        )
        # Right side
        d.line(
            [px(24, y), px(30.5, y - slope)],
            fill=PAL_RGB[DARK],
            width=2,
        )

    # ---- Base line (horizontal black bar row 17 across the bottom) ------
    d.rectangle([px(0, 17), px(32, 18)], fill=PAL_RGB[BLACK])

    return img


def draw_small_base() -> Image.Image:
    """Draw small 16×9-cell orange cat (base/idle pose).

    Includes two paws (cells 1-3, 8 and 13-15, 8) and a tail curl to
    the right edge — these are needed by the wave/tail animations.
    """

    img = Image.new("RGB", (SMALL_W, SMALL_H), (255, 255, 255))
    d = ImageDraw.Draw(img)

    ORANGE = 1
    DARK_O = 2
    LIGHT = 3
    DARK = 4
    BLACK = 5

    def px(x: int, y: int) -> tuple[int, int]:
        return (x * SCALE, y * SCALE * 2)

    # ---- Tail curl (right side, drawn first so face fill covers it) ----
    # A small "?" curl sitting at the right cheek.
    d.arc(
        [px(13.5, 5.5), px(15.7, 7.5)],
        start=270, end=90,
        fill=PAL_RGB[DARK_O], width=4,
    )

    # ---- Ears (compact triangles) --------------------------------------
    d.polygon([px(1, 0.5), px(5, 0.5), px(3.5, 2.5)], fill=PAL_RGB[DARK_O])
    d.polygon([px(11, 0.5), px(15, 0.5), px(12.5, 2.5)], fill=PAL_RGB[DARK_O])
    d.polygon([px(2, 0.8), px(4, 0.8), px(3.5, 2.2)], fill=PAL_RGB[ORANGE])
    d.polygon([px(12, 0.8), px(14, 0.8), px(12.5, 2.2)], fill=PAL_RGB[ORANGE])
    d.polygon([px(2.4, 1.0), px(3.6, 1.0), px(3.5, 2.0)], fill=PAL_RGB[LIGHT])
    d.polygon([px(12.4, 1.0), px(13.6, 1.0), px(12.5, 2.0)], fill=PAL_RGB[LIGHT])

    # ---- Face (rounded rect) ---------------------------------------------
    d.rounded_rectangle([px(0.5, 2), px(15.5, 8.5)], radius=14, fill=PAL_RGB[ORANGE])
    # Re-paint ears on top so they stay visible
    d.polygon([px(1, 0.5), px(5, 0.5), px(3.5, 2.5)], fill=PAL_RGB[DARK_O])
    d.polygon([px(11, 0.5), px(15, 0.5), px(12.5, 2.5)], fill=PAL_RGB[DARK_O])
    d.polygon([px(2, 0.8), px(4, 0.8), px(3.5, 2.2)], fill=PAL_RGB[ORANGE])
    d.polygon([px(12, 0.8), px(14, 0.8), px(12.5, 2.2)], fill=PAL_RGB[ORANGE])
    d.polygon([px(2.4, 1.0), px(3.6, 1.0), px(3.5, 2.0)], fill=PAL_RGB[LIGHT])
    d.polygon([px(12.4, 1.0), px(13.6, 1.0), px(12.5, 2.0)], fill=PAL_RGB[LIGHT])

    # ---- Eyes ------------------------------------------------------------
    d.ellipse([px(3.5, 3.6), px(5.5, 5.4)], fill=PAL_RGB[BLACK])
    d.ellipse([px(10.5, 3.6), px(12.5, 5.4)], fill=PAL_RGB[BLACK])

    # ---- Cheek highlights ------------------------------------------------
    d.ellipse([px(3, 5.5), px(6, 6.8)], fill=PAL_RGB[LIGHT])
    d.ellipse([px(10, 5.5), px(13, 6.8)], fill=PAL_RGB[LIGHT])

    # ---- Nose ------------------------------------------------------------
    d.polygon([px(7.4, 5.2), px(8.6, 5.2), px(8, 5.9)], fill=PAL_RGB[DARK])

    # ---- w mouth ---------------------------------------------------------
    d.line(
        [px(7.8, 5.95), px(7.1, 6.5), px(8, 6.3), px(8.9, 6.5), px(8.2, 5.95)],
        fill=PAL_RGB[DARK],
        width=2,
    )

    # ---- Whiskers (2 each side) -----------------------------------------
    for y in (5.5, 6.3):
        d.line([px(3.5, y), px(0.3, y)], fill=PAL_RGB[DARK], width=1)
        d.line([px(12.5, y), px(14.0, y)], fill=PAL_RGB[DARK], width=1)

    # ---- Paws (left & right at bottom of face, used for wave) -----------
    # Left paw (cell range 1-3, row 7.6-8.4).
    d.rounded_rectangle(
        [px(0.5, 7.5), px(3.5, 8.5)],
        radius=8, fill=PAL_RGB[ORANGE],
    )
    # Right paw (cell range 12.5-15.5, row 7.6-8.4).
    d.rounded_rectangle(
        [px(12.5, 7.5), px(15.5, 8.5)],
        radius=8, fill=PAL_RGB[ORANGE],
    )

    # ---- Base line ------------------------------------------------------
    d.rectangle([px(0, 8.5), px(16, 9)], fill=PAL_RGB[BLACK])

    return img


# ---------------------------------------------------------------------------
# Animation overlays
# ---------------------------------------------------------------------------

def _wave(img: Image.Image, frame: int) -> Image.Image:
    """Right paw raises and waves. Frame 0 = base paw; frames 1-3 cycle
    the paw height: low → high → low to simulate waving.
    """
    img = img.copy()
    d = ImageDraw.Draw(img)

    def px(x: int, y: int) -> tuple[int, int]:
        return (x * SCALE, y * SCALE * 2)

    # Wipe the default right paw by repainting the area with face fill.
    d.rectangle(
        [px(12.4, 7.4), px(15.7, 8.6)],
        fill=PAL_RGB[1],
    )

    if frame == 0:
        # Re-draw the paw at the base position.
        d.rounded_rectangle(
            [px(12.5, 7.5), px(15.5, 8.5)],
            radius=8, fill=PAL_RGB[1],
        )
        return img

    # Frames 1, 2, 3: paw at heights 6.0, 3.5, 6.0 (clear up-down wave).
    heights = {1: 6.0, 2: 3.5, 3: 6.0}
    paw_y0 = heights[frame]
    # Make the raised paw slightly wider so it's clearly visible above head.
    paw_x0 = 13.5
    paw_x1 = 15.5
    d.rounded_rectangle(
        [px(paw_x0, paw_y0), px(paw_x1, paw_y0 + 1.0)],
        radius=8, fill=PAL_RGB[1],
    )
    # Outline darker so it stands out against orange face.
    d.rectangle(
        [px(paw_x0 - 0.1, paw_y0 + 0.05), px(paw_x1 + 0.1, paw_y0 + 1.0)],
        outline=PAL_RGB[2], width=1,
    )
    return img


def _ear(img: Image.Image, frame: int) -> Image.Image:
    """Ears tilt back then return. Frame 0/2 = upright; 1/3 = tilted."""
    img = img.copy()
    if frame in (0, 2):
        return img  # base pose already drawn

    d = ImageDraw.Draw(img)

    def px(x: int, y: int) -> tuple[int, int]:
        return (x * SCALE, y * SCALE * 2)

    # Reset ears to base (orange + dark_o triangles), then tilt.
    # Left ear base
    d.polygon([px(1, 0.5), px(5, 0.5), px(3.5, 2.5)], fill=PAL_RGB[2])
    d.polygon([px(2, 0.8), px(4, 0.8), px(3.5, 2.2)], fill=PAL_RGB[1])
    # Right ear base
    d.polygon([px(11, 0.5), px(15, 0.5), px(12.5, 2.5)], fill=PAL_RGB[2])
    d.polygon([px(12, 0.8), px(14, 0.8), px(12.5, 2.2)], fill=PAL_RGB[1])

    # Tilt both ears outward: left ear leans left, right ear leans right.
    # Use a strong shift so the tilt is clearly visible.
    tilt = 1.5 if frame == 1 else 1.8
    # Left ear tilted left
    d.polygon(
        [px(1 - tilt, 0.5), px(5 - tilt, 0.5), px(3.5, 2.5)],
        fill=PAL_RGB[2],
    )
    d.polygon(
        [px(2 - tilt, 0.8), px(4 - tilt, 0.8), px(3.5, 2.2)],
        fill=PAL_RGB[1],
    )
    d.polygon(
        [px(2.4 - tilt, 1.0), px(3.6 - tilt, 1.0), px(3.5, 2.0)],
        fill=PAL_RGB[3],
    )
    # Right ear tilted right
    d.polygon(
        [px(11 + tilt, 0.5), px(15 + tilt, 0.5), px(12.5, 2.5)],
        fill=PAL_RGB[2],
    )
    d.polygon(
        [px(12 + tilt, 0.8), px(14 + tilt, 0.8), px(12.5, 2.2)],
        fill=PAL_RGB[1],
    )
    d.polygon(
        [px(12.4 + tilt, 1.0), px(13.6 + tilt, 1.0), px(12.5, 2.0)],
        fill=PAL_RGB[3],
    )
    return img


def _tail(img: Image.Image, frame: int) -> Image.Image:
    """Tail curl swings. Frame 0 = base; 1/3 = swing left/right; 2 = base.

    The base tail is an arc on the right side of the face (cells 13.5-15.7,
    rows 5.5-7.5). We swing it by adjusting the arc's bounding box.
    """
    img = img.copy()
    d = ImageDraw.Draw(img)

    def px(x: int, y: int) -> tuple[int, int]:
        return (x * SCALE, y * SCALE * 2)

    # Wipe the existing tail arc area (rightmost columns, vertical band).
    d.rectangle(
        [px(13.3, 5.3), px(15.7, 7.6)],
        fill=PAL_RGB[1],
    )

    # Map frame index to a horizontal offset relative to base.
    offsets = [0, -0.6, 0, 0.6]  # frame 0/2 = centered
    dx = offsets[frame]

    # Draw new tail arc at shifted position.
    d.arc(
        [px(13.5 + dx, 5.5), px(15.7 + dx, 7.5)],
        start=270, end=90,
        fill=PAL_RGB[2], width=4,
    )
    return img


def _blink(img: Image.Image, frame: int) -> Image.Image:
    """Eyes close progressively. Frame 0 = open; 3 = fully open again.
    Frame 1 = half closed (line); Frame 2 = fully closed.
    """
    if frame == 0 or frame == 3:
        return img  # base eyes
    img = img.copy()
    d = ImageDraw.Draw(img)

    def px(x: int, y: int) -> tuple[int, int]:
        return (x * SCALE, y * SCALE * 2)

    # Wipe the existing eyes with orange face fill
    d.ellipse([px(3.5, 3.6), px(5.5, 5.4)], fill=PAL_RGB[1])
    d.ellipse([px(10.5, 3.6), px(12.5, 5.4)], fill=PAL_RGB[1])

    if frame == 1:
        # Half closed: thin horizontal arcs
        d.line(
            [px(3.7, 4.7), px(5.3, 4.7)],
            fill=PAL_RGB[5], width=3,
        )
        d.line(
            [px(10.7, 4.7), px(12.3, 4.7)],
            fill=PAL_RGB[5], width=3,
        )
    elif frame == 2:
        # Closed: just a curved line
        d.arc(
            [px(3.5, 3.6), px(5.5, 5.4)],
            start=20, end=160,
            fill=PAL_RGB[5], width=3,
        )
        d.arc(
            [px(10.5, 3.6), px(12.5, 5.4)],
            start=20, end=160,
            fill=PAL_RGB[5], width=3,
        )
    return img


def _peek(img: Image.Image, frame: int) -> Image.Image:
    """Cat peeks up from below. We shift the cat upward by ``frame`` cells."""
    if frame == 0:
        return img
    img = img.copy()
    # Use PIL paste with a shifted area; alpha doesn't apply here so we
    # crop & paste on a fresh transparent canvas.
    shift_cells = frame
    bg = Image.new("RGB", (SMALL_W, SMALL_H), (255, 255, 255))
    shift_px = shift_cells * SCALE * 2
    bg.paste(img, (0, -shift_px))
    return bg


ANIMS = {
    "wave": _wave,
    "ear": _ear,
    "tail": _tail,
    "blink": _blink,
    "peek": _peek,
}


# ---------------------------------------------------------------------------
# Quantization: PIL image → cell grid (palette indices)
# ---------------------------------------------------------------------------

def _cell_idx(rgb: tuple[int, int, int]) -> int:
    """Return palette index of the closest match to ``rgb``."""
    best = -1
    best_d = 1 << 30
    for idx, prgb in PAL_RGB.items():
        d = (rgb[0] - prgb[0]) ** 2 + (rgb[1] - prgb[1]) ** 2 + (rgb[2] - prgb[2]) ** 2
        if d < best_d:
            best_d = d
            best = idx
    return best


def quantize(img: Image.Image, cells_w: int, cells_h: int) -> list[list[int]]:
    """Quantize a PIL RGB image into a ``cells_h × cells_w`` palette-index grid.

    Each cell maps to a 2-row strip of pixels in the source image (since
    half-block rendering combines two rows into one cell). For pixels that
    are pure white (the canvas background), we emit index 0 (transparent).
    """

    cell_w = img.width // cells_w
    cell_h = img.height // cells_h

    grid: list[list[int]] = []
    src = img.load()
    for cy in range(cells_h):
        row: list[int] = []
        for cx in range(cells_w):
            # Sample four corners of the cell. If they're all white, transparent.
            samples: list[tuple[int, int, int]] = []
            for dy in (0, cell_h - 1):
                for dx in (0, cell_w - 1):
                    px_x = min(cx * cell_w + dx, img.width - 1)
                    px_y = min(cy * cell_h + dy, img.height - 1)
                    samples.append(src[px_x, px_y])
            # If majority white, treat as transparent.
            white_count = sum(1 for s in samples if s == (255, 255, 255))
            if white_count >= 3:
                row.append(0)
                continue
            # Otherwise pick the most-common non-white color, fall back to
            # nearest in palette on first hit.
            non_white = [s for s in samples if s != (255, 255, 255)]
            color = non_white[0] if non_white else (255, 255, 255)
            row.append(_cell_idx(color))
        grid.append(row)
    return grid


def grid_to_pixels(grid: list[list[int]], cells_h: int, cells_w: int) -> list[list[int]]:
    """Expand a half-block-friendly grid (one entry per cell-row pair) into
    full pixel rows (height = 2 × cells_h, each cell maps to two stacked
    pixels). The renderer reads ``grid[2*y]`` and ``grid[2*y+1]`` to colour
    the upper and lower half-block characters.
    """

    full_h = cells_h * 2
    rows: list[list[int]] = []
    for cell_y in range(cells_h):
        # Each cell_row holds one palette index per cell.
        top = grid[cell_y * 2]
        bot = grid[cell_y * 2 + 1]
        # The render output is cells_w wide.
        rows.extend([top, bot])
    return rows


# ---------------------------------------------------------------------------
# Output writers
# ---------------------------------------------------------------------------

def _py_literal(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)


def write_assets_py(big_grid: list[list[int]], small_frames: dict[str, list[list[int]]]) -> None:
    ASSETS_PY.parent.mkdir(parents=True, exist_ok=True)
    pal_lines = ",\n    ".join(repr(p) for p in PALETTE)
    big_lines = (
        "[\n"
        + "\n".join(f"        {row}," for row in big_grid)
        + "\n    ]"
    )
    sm_lines: list[str] = []
    names = list(small_frames.keys())
    for idx, name in enumerate(names):
        frames = small_frames[name]
        frame_blocks: list[str] = []
        for frame in frames:
            block = "[\n" + "\n".join(f"            {row}," for row in frame) + "\n        ]"
            frame_blocks.append(block)
        joined = ",\n        ".join(frame_blocks)
        comma = "," if idx < len(names) - 1 else ""
        sm_lines.append(f'    "{name}": [\n        {joined},\n    ]{comma}')

    body = (
        '"""Auto-generated by tools/build_logos.py — do not edit by hand."""\n'
        "from __future__ import annotations\n\n"
        "PALETTE: tuple[str | None, ...] = (\n"
        f"    {pal_lines},\n"
        ")\n\n"
        "BIG_HEAD_CELLS_W: int = 32\n"
        "BIG_HEAD_CELLS_H: int = 18\n"
        "SMALL_CELLS_W: int = 16\n"
        "SMALL_CELLS_H: int = 9\n"
        "BIG_HEAD: tuple[tuple[int, ...], ...] = (\n"
        f"    {big_lines}\n"
        ")\n"
        "SMALL_FRAMES: dict[str, tuple[tuple[tuple[int, ...], ...], ...]] = {\n"
        + "\n".join(sm_lines)
        + "\n}\n"
    )
    ASSETS_PY.write_text(body, encoding="utf-8")


def write_preview_pngs(big_img: Image.Image, small_frames_imgs: dict[str, list[Image.Image]]) -> None:
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    big_img.save(PREVIEW_DIR / "big.png")
    for name, frames in small_frames_imgs.items():
        for i, frame in enumerate(frames):
            frame.save(PREVIEW_DIR / f"small_{name}_{i}.png")


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def build(preview_only: bool = False) -> None:
    big_img = draw_big()
    small_base = draw_small_base()

    small_frames_imgs: dict[str, list[Image.Image]] = {}
    small_frames_grids: dict[str, list[list[list[int]]]] = {}
    for name, fn in ANIMS.items():
        frames = [fn(small_base, i) for i in range(4)]
        small_frames_imgs[name] = frames
        if not preview_only:
            small_frames_grids[name] = [
                quantize(f, SMALL_CELLS_W, SMALL_CELLS_H * 2) for f in frames
            ]

    big_grid = quantize(big_img, BIG_CELLS_W, BIG_CELLS_H * 2)

    if not preview_only:
        write_assets_py(big_grid, small_frames_grids)
    write_preview_pngs(big_img, small_frames_imgs)
    total_pngs = 1 + sum(len(frames) for frames in small_frames_imgs.values())
    print(f"Wrote {total_pngs} PNG previews to {PREVIEW_DIR}")
    if not preview_only:
        print(f"Wrote asset module to {ASSETS_PY}")


if __name__ == "__main__":
    preview_only = "--preview" in sys.argv
    build(preview_only=preview_only)
