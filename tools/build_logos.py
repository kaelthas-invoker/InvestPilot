#!/usr/bin/env python3
"""Build orange-cat half-block logo assets for InvestPilot v0.2.3.

User feedback after v0.2.2 review:
- Big logo uses the same 16×9 cells as the small one
- Small face has 1 px padding on each axis (more breathing room)
- The 5 separate animations collapse into a single 4-frame
  ``blink_ear`` (eyes close in sync with ears tilting outward)

Outputs two artifacts:

1. ``src/investpilot/interface/_logo_assets.py`` — Python constants
   ``PALETTE`` (hex strings + ``None``), ``HEAD`` (16 cols × 18 rows of
   palette indices), and ``SMALL_FRAMES["blink_ear"]`` (4 frames, each
   16 cols × 18 rows).

2. ``docs/iterations/v0.2.3/preview/*.png`` — human-review PNGs.

Run with ``uv run python tools/build_logos.py``. Idempotent.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
ASSETS_PY = ROOT / "src" / "investpilot" / "interface" / "_logo_assets.py"
PREVIEW_DIR = ROOT / "docs" / "iterations" / "v0.2.3" / "preview"

# ---------------------------------------------------------------------------
# Palette + grid geometry
# ---------------------------------------------------------------------------

PALETTE: tuple[str | None, ...] = (
    None,           # 0 transparent
    "#F2B675",      # 1 orange (body/face)
    "#E89B4A",      # 2 darker orange (ear edges, base shading)
    "#FCE3C8",      # 3 light cream (inner ears, cheek highlights)
    "#3B2A20",      # 4 dark brown (mouth, whiskers, outlines)
    "#221814",      # 5 near-black (eyes, pupils)
)

PAL_HEX = {idx: c for idx, c in enumerate(PALETTE) if c is not None}


def _hex(rgb: str) -> tuple[int, int, int]:
    rgb = rgb.lstrip("#")
    return (int(rgb[0:2], 16), int(rgb[2:4], 16), int(rgb[4:6], 16))


PAL_RGB = {idx: _hex(c) for idx, c in PAL_HEX.items()}

# Big and small both use the same 16×9 cell grid (per user feedback on
# v0.2.2 — big should match small to avoid duplicate art).
CELLS_W, CELLS_H = 16, 9

# Source pixel scale per cell for PIL drawing (lets anti-aliasing look nice).
SCALE = 8
W = CELLS_W * SCALE
H = CELLS_H * SCALE * 2  # 2 rows of pixels per cell


# ---------------------------------------------------------------------------
# Cat drawing
# ---------------------------------------------------------------------------

def draw_head() -> Image.Image:
    """Draw the orange-cat head as a 16×9 cell image.

    Both the boot big logo and the small-mascot base share this artwork.
    The face area has 1-cell padding on every axis (per user feedback).
    """

    img = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(img)

    ORANGE = 1
    DARK_O = 2
    LIGHT = 3
    DARK = 4
    BLACK = 5

    def px(x: int, y: int) -> tuple[int, int]:
        return (x * SCALE, y * SCALE * 2)

    # ---- Ears (compact triangles at the top corners) -------------------
    d.polygon([px(1, 0.4), px(5, 0.4), px(3.5, 2.4)], fill=PAL_RGB[DARK_O])
    d.polygon([px(11, 0.4), px(15, 0.4), px(12.5, 2.4)], fill=PAL_RGB[DARK_O])
    d.polygon([px(2, 0.7), px(4, 0.7), px(3.5, 2.0)], fill=PAL_RGB[ORANGE])
    d.polygon([px(12, 0.7), px(14, 0.7), px(12.5, 2.0)], fill=PAL_RGB[ORANGE])
    # Inner ears (cream) — accent for contrast
    d.polygon([px(2.4, 0.95), px(3.6, 0.95), px(3.5, 1.8)], fill=PAL_RGB[LIGHT])
    d.polygon([px(12.4, 0.95), px(13.6, 0.95), px(12.5, 1.8)], fill=PAL_RGB[LIGHT])

    # ---- Face (rounded rect with 1-cell padding on each axis) -----------
    # Original: [px(0.5, 2), px(15.5, 8.5)]
    # v0.2.3:    [px(1.5, 2.5), px(14.5, 8.0)]  — 1-cell breathing room
    d.rounded_rectangle(
        [px(1.5, 2.5), px(14.5, 8.0)],
        radius=18,
        fill=PAL_RGB[ORANGE],
    )
    # Re-paint ears on top of face fill so they stay visible.
    d.polygon([px(1, 0.4), px(5, 0.4), px(3.5, 2.4)], fill=PAL_RGB[DARK_O])
    d.polygon([px(11, 0.4), px(15, 0.4), px(12.5, 2.4)], fill=PAL_RGB[DARK_O])
    d.polygon([px(2, 0.7), px(4, 0.7), px(3.5, 2.0)], fill=PAL_RGB[ORANGE])
    d.polygon([px(12, 0.7), px(14, 0.7), px(12.5, 2.0)], fill=PAL_RGB[ORANGE])
    d.polygon([px(2.4, 0.95), px(3.6, 0.95), px(3.5, 1.8)], fill=PAL_RGB[LIGHT])
    d.polygon([px(12.4, 0.95), px(13.6, 0.95), px(12.5, 1.8)], fill=PAL_RGB[LIGHT])

    # ---- Forehead micro-arc (between the ears, only here) -------------
    # Per v0.2.4-mini user feedback: keep v0.2.3 design (flat face) but
    # add **a bit** of arc in the area between the two ear bases.  The
    # arc is a small top-half chord that occupies cells 4-12 horizontally
    # and rows 1.5-3 vertically — well inside the ear-free space.
    d.chord([px(4, 1.5), px(12, 4.0)], 180, 360, fill=PAL_RGB[ORANGE])
    # Re-paint ears again so the new forehead arc doesn't cover them.
    d.polygon([px(1, 0.4), px(5, 0.4), px(3.5, 2.4)], fill=PAL_RGB[DARK_O])
    d.polygon([px(11, 0.4), px(15, 0.4), px(12.5, 2.4)], fill=PAL_RGB[DARK_O])
    d.polygon([px(2, 0.7), px(4, 0.7), px(3.5, 2.0)], fill=PAL_RGB[ORANGE])
    d.polygon([px(12, 0.7), px(14, 0.7), px(12.5, 2.0)], fill=PAL_RGB[ORANGE])
    d.polygon([px(2.4, 0.95), px(3.6, 0.95), px(3.5, 1.8)], fill=PAL_RGB[LIGHT])
    d.polygon([px(12.4, 0.95), px(13.6, 0.95), px(12.5, 1.8)], fill=PAL_RGB[LIGHT])

    # ---- Eyes (round black dots) ----------------------------------------
    d.ellipse([px(4, 3.6), px(6, 5.6)], fill=PAL_RGB[BLACK])
    d.ellipse([px(10, 3.6), px(12, 5.6)], fill=PAL_RGB[BLACK])

    # ---- Cheek highlights (cream patches under eyes) -------------------
    d.ellipse([px(3.2, 5.6), px(6.4, 7.0)], fill=PAL_RGB[LIGHT])
    d.ellipse([px(9.6, 5.6), px(12.8, 7.0)], fill=PAL_RGB[LIGHT])

    # ---- Nose ----------------------------------------------------------
    d.polygon([px(7.6, 5.2), px(8.4, 5.2), px(8, 5.9)], fill=PAL_RGB[DARK])

    # ---- w mouth -------------------------------------------------------
    d.line(
        [px(7.85, 5.95), px(7.2, 6.5), px(8, 6.3), px(8.8, 6.5), px(8.15, 5.95)],
        fill=PAL_RGB[DARK],
        width=2,
    )

    # ---- Whiskers (2 each side) ----------------------------------------
    for y in (5.6, 6.3):
        d.line([px(3.2, y), px(0.5, y)], fill=PAL_RGB[DARK], width=1)
        d.line([px(12.8, y), px(15.5, y)], fill=PAL_RGB[DARK], width=1)

    # ---- Base line (very bottom) ---------------------------------------
    d.rectangle([px(0, 8.4), px(16, 9)], fill=PAL_RGB[BLACK])

    return img


# ---------------------------------------------------------------------------
# Combined blink + ear animation
# ---------------------------------------------------------------------------

def _blink_ear(img: Image.Image, frame: int) -> Image.Image:
    """Returns ``img`` with eyes closing in sync with ears tilting outward.

    Frame schedule:
      0 — eyes open, ears upright (base pose)
      1 — eyes half-closed, ears slightly tilted
      2 — eyes closed, ears fully tilted outward (peak)
      3 — eyes half-closed, ears slightly tilted (decay)

    One loop = 4 frames at 0.10s ≈ 0.4s.
    """

    img = img.copy()
    d = ImageDraw.Draw(img)

    ORANGE = 1
    DARK_O = 2
    LIGHT = 3
    DARK = 4
    BLACK = 5

    def px(x: int, y: int) -> tuple[int, int]:
        return (x * SCALE, y * SCALE * 2)

    # Per-frame parameters
    eye_states = {
        0: "open",
        1: "half",
        2: "closed",
        3: "half",
    }
    tilt = {0: 0.0, 1: 0.7, 2: 1.5, 3: 0.7}[frame]

    # ---- Redraw the eyes ------------------------------------------------
    # Wipe the existing eye area with face fill, then re-draw according
    # to the eye state for this frame.
    d.ellipse([px(4, 3.6), px(6, 5.6)], fill=PAL_RGB[ORANGE])
    d.ellipse([px(10, 3.6), px(12, 5.6)], fill=PAL_RGB[ORANGE])

    state = eye_states[frame]
    if state == "open":
        # Round black eyes (same as base pose).
        d.ellipse([px(4, 3.6), px(6, 5.6)], fill=PAL_RGB[BLACK])
        d.ellipse([px(10, 3.6), px(12, 5.6)], fill=PAL_RGB[BLACK])
    elif state == "half":
        # Thin black arc at the centre of each eye.
        d.arc(
            [px(4, 3.6), px(6, 5.6)],
            start=180, end=360,
            fill=PAL_RGB[BLACK], width=2,
        )
        d.arc(
            [px(10, 3.6), px(12, 5.6)],
            start=180, end=360,
            fill=PAL_RGB[BLACK], width=2,
        )
    elif state == "closed":
        # Single dark horizontal line per eye.
        d.line(
            [px(4.05, 4.7), px(5.95, 4.7)],
            fill=PAL_RGB[BLACK], width=2,
        )
        d.line(
            [px(10.05, 4.7), px(11.95, 4.7)],
            fill=PAL_RGB[BLACK], width=2,
        )

    # ---- Redraw ears with tilt ------------------------------------------
    # Wipe the ear region with face fill.
    d.rectangle([px(0, 0), px(16, 2.6)], fill=PAL_RGB[ORANGE])

    if tilt > 0:
        # Left ear tilted outward (left), right ear tilted outward (right).
        # Outer triangle (dark orange) + inner orange + cream accent + dark outline.
        left_outer = [px(1 - tilt, 0.4), px(5 - tilt, 0.4), px(3.5, 2.4)]
        d.polygon(left_outer, fill=PAL_RGB[DARK_O])
        d.polygon(
            [px(2 - tilt, 0.7), px(4 - tilt, 0.7), px(3.5, 2.0)],
            fill=PAL_RGB[ORANGE],
        )
        d.polygon(
            [px(2.4 - tilt, 0.95), px(3.6 - tilt, 0.95), px(3.5, 1.8)],
            fill=PAL_RGB[LIGHT],
        )
        d.line(left_outer + [left_outer[0]], fill=PAL_RGB[DARK], width=2)

        right_outer = [px(11 + tilt, 0.4), px(15 + tilt, 0.4), px(12.5, 2.4)]
        d.polygon(right_outer, fill=PAL_RGB[DARK_O])
        d.polygon(
            [px(12 + tilt, 0.7), px(14 + tilt, 0.7), px(12.5, 2.0)],
            fill=PAL_RGB[ORANGE],
        )
        d.polygon(
            [px(12.4 + tilt, 0.95), px(13.6 + tilt, 0.95), px(12.5, 1.8)],
            fill=PAL_RGB[LIGHT],
        )
        d.line(right_outer + [right_outer[0]], fill=PAL_RGB[DARK], width=2)
    else:
        # Frame 0: redraw the original (upright) ears over the wipe.
        d.polygon([px(1, 0.4), px(5, 0.4), px(3.5, 2.4)], fill=PAL_RGB[DARK_O])
        d.polygon([px(11, 0.4), px(15, 0.4), px(12.5, 2.4)], fill=PAL_RGB[DARK_O])
        d.polygon([px(2, 0.7), px(4, 0.7), px(3.5, 2.0)], fill=PAL_RGB[ORANGE])
        d.polygon([px(12, 0.7), px(14, 0.7), px(12.5, 2.0)], fill=PAL_RGB[ORANGE])
        d.polygon([px(2.4, 0.95), px(3.6, 0.95), px(3.5, 1.8)], fill=PAL_RGB[LIGHT])
        d.polygon([px(12.4, 0.95), px(13.6, 0.95), px(12.5, 1.8)], fill=PAL_RGB[LIGHT])

    return img


ANIMS = {
    "blink_ear": _blink_ear,
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
            # Sample four corners of the cell.
            samples: list[tuple[int, int, int]] = []
            for dy in (0, cell_h - 1):
                for dx in (0, cell_w - 1):
                    px_x = min(cx * cell_w + dx, img.width - 1)
                    px_y = min(cy * cell_h + dy, img.height - 1)
                    samples.append(src[px_x, px_y])
            white_count = sum(1 for s in samples if s == (255, 255, 255))
            if white_count >= 3:
                row.append(0)
                continue
            non_white = [s for s in samples if s != (255, 255, 255)]
            color = non_white[0] if non_white else (255, 255, 255)
            row.append(_cell_idx(color))
        grid.append(row)
    return grid


# ---------------------------------------------------------------------------
# Output writers
# ---------------------------------------------------------------------------

def write_assets_py(head_grid: list[list[int]], frames_grids: dict[str, list[list[list[int]]]]) -> None:
    ASSETS_PY.parent.mkdir(parents=True, exist_ok=True)
    pal_lines = ",\n    ".join(repr(p) for p in PALETTE)
    head_lines = (
        "[\n"
        + "\n".join(f"        {row}," for row in head_grid)
        + "\n    ]"
    )
    sm_lines: list[str] = []
    names = list(frames_grids.keys())
    for idx, name in enumerate(names):
        frames = frames_grids[name]
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
        "HEAD_CELLS_W: int = 16\n"
        "HEAD_CELLS_H: int = 9\n"
        "HEAD: tuple[tuple[int, ...], ...] = (\n"
        f"    {head_lines}\n"
        ")\n"
        "SMALL_FRAMES: dict[str, tuple[tuple[tuple[int, ...], ...], ...]] = {\n"
        + "\n".join(sm_lines)
        + "\n}\n"
    )
    ASSETS_PY.write_text(body, encoding="utf-8")


def write_preview_pngs(head_img: Image.Image, small_imgs: dict[str, list[Image.Image]]) -> None:
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    head_img.save(PREVIEW_DIR / "head.png")
    for name, frames in small_imgs.items():
        for i, frame in enumerate(frames):
            frame.save(PREVIEW_DIR / f"{name}_{i}.png")


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def build(preview_only: bool = False) -> None:
    head_img = draw_head()

    small_frames_imgs: dict[str, list[Image.Image]] = {}
    small_frames_grids: dict[str, list[list[list[int]]]] = {}
    for name, fn in ANIMS.items():
        frames = [fn(head_img, i) for i in range(4)]
        small_frames_imgs[name] = frames
        if not preview_only:
            small_frames_grids[name] = [
                quantize(f, CELLS_W, CELLS_H * 2) for f in frames
            ]

    head_grid = quantize(head_img, CELLS_W, CELLS_H * 2)

    if not preview_only:
        write_assets_py(head_grid, small_frames_grids)
    write_preview_pngs(head_img, small_frames_imgs)
    total_pngs = 1 + sum(len(frames) for frames in small_frames_imgs.values())
    print(f"Wrote {total_pngs} PNG previews to {PREVIEW_DIR}")
    if not preview_only:
        print(f"Wrote asset module to {ASSETS_PY}")


if __name__ == "__main__":
    preview_only = "--preview" in sys.argv
    build(preview_only=preview_only)
