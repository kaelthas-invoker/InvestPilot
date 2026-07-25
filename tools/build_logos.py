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
    # v0.2.5-mini: each eye shrunk from 2×2 cells to 2×1 cells (1 cell
    # removed vertically — keeping the same 2-cell width).
    d.ellipse([px(4, 4.0), px(6, 5.0)], fill=PAL_RGB[BLACK])
    d.ellipse([px(10, 4.0), px(12, 5.0)], fill=PAL_RGB[BLACK])

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
# Small-logo size variants (v0.2.6 user feedback)
#
# The big boot logo (draw_head()) is **pin-locked** at v0.2.5-mini: arched
# forehead + 2×1 round eyes + full set of features.  The small mascot
# logo is being designed to match the big logo's visual style at smaller
# cell grids.  Each size drops features in proportion to its grid size.
#
#   16×9 → full detail (matches big logo, w/ forehead arc + cheek + 2×1 eyes)
#   12×7 → no forehead arc, smaller cheeks, 1×1 eyes
#   10×6 → drops cheeks, simpler mouth, 1 whisker/side
#   8×5  → minimal icon (ears, 1×1 eyes, smile, base)
# ---------------------------------------------------------------------------


def _make_small_variant(cells_w: int, cells_h: int, *, features: dict) -> Image.Image:
    """Draw a small cat at ``(cells_w, cells_h)`` choosing features.

    ``features`` keys:
        forehead_arc: bool  — top-half chord between ears
        eye_w: float         — eye width in cells (≥ 1)
        eye_h: float         — eye height in cells (≥ 0.5)
        cheeks: bool         — cream cheek patches
        nose: bool           — triangular nose
        whiskers: int        — number of whiskers per side (0/1/2)
        base_line: bool      — full-width black bar at the bottom
        mouth: str           — "w" for w-mouth, "smile" for simple smile,
                               "dot" for two tiny dots
    """
    SCALE = 8
    W = cells_w * SCALE
    H = cells_h * SCALE * 2
    img = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(img)

    ORANGE = 1
    DARK_O = 2
    LIGHT = 3
    DARK = 4
    BLACK = 5

    def px(x: float, y: float) -> tuple[int, int]:
        return (int(x * SCALE), int(y * SCALE * 2))

    # ---- Ears (always present, scaled) ---------------------------------
    # Left ear outer triangle: vertices (ear_left_x0, 0.3), (ear_left_x1, 0.3),
    # (ear_left_tip_x, ear_tip_y)
    ear_left_x0 = max(0.3, cells_w * 0.05)
    ear_left_x1 = max(ear_left_x0 + 2, cells_w * 0.35)
    ear_left_tip_x = (ear_left_x0 + ear_left_x1) / 2
    ear_right_x1 = min(cells_w - 0.3, cells_w * 0.95)
    ear_right_x0 = min(ear_right_x1 - 2, cells_w * 0.65)
    ear_right_tip_x = (ear_right_x0 + ear_right_x1) / 2
    ear_tip_y = cells_h * 0.27   # ~2 cells

    d.polygon([px(ear_left_x0, 0.3), px(ear_left_x1, 0.3),
               px(ear_left_tip_x, ear_tip_y)], fill=PAL_RGB[DARK_O])
    d.polygon([px(ear_right_x0, 0.3), px(ear_right_x1, 0.3),
               px(ear_right_tip_x, ear_tip_y)], fill=PAL_RGB[DARK_O])
    d.polygon([px(ear_left_x0 + 0.6, 0.55), px(ear_left_x1 - 0.6, 0.55),
               px(ear_left_tip_x, ear_tip_y * 0.7)],
              fill=PAL_RGB[ORANGE])
    d.polygon([px(ear_right_x0 + 0.6, 0.55), px(ear_right_x1 - 0.6, 0.55),
               px(ear_right_tip_x, ear_tip_y * 0.7)],
              fill=PAL_RGB[ORANGE])
    # Light inner-ear only on bigger sizes (skip for 8×5)
    if cells_w >= 10:
        d.polygon([px(ear_left_x0 + 1.0, 0.75), px(ear_left_x1 - 1.0, 0.75),
                   px(ear_left_tip_x, ear_tip_y * 0.55)],
                  fill=PAL_RGB[LIGHT])
        d.polygon([px(ear_right_x0 + 1.0, 0.75), px(ear_right_x1 - 1.0, 0.75),
                   px(ear_right_tip_x, ear_tip_y * 0.55)],
                  fill=PAL_RGB[LIGHT])

    # ---- Face (always present, with horizontal padding) ----------------
    pad_x = 0.5 if cells_w >= 10 else 0.4
    pad_top = 1.5 if cells_h >= 7 else 1.0
    pad_bottom = 1.0 if cells_h >= 5 else 0.5
    face_x0 = pad_x
    face_x1 = cells_w - pad_x
    face_y0 = pad_top
    face_y1 = cells_h - pad_bottom

    face_shape = features.get("face_shape", "rect")
    if face_shape == "ellipse":
        # True ellipse — fully rounded head (used by 8×5 for "圆润" look).
        d.ellipse(
            [px(face_x0, face_y0), px(face_x1, face_y1)],
            fill=PAL_RGB[ORANGE],
        )
    else:
        radius = min(face_x1 - face_x0, face_y1 - face_y0) * features.get(
            "face_corner_radius", 0.28
        )
        d.rounded_rectangle(
            [px(face_x0, face_y0), px(face_x1, face_y1)],
            radius=radius,
            fill=PAL_RGB[ORANGE],
        )

    # Re-paint ears on top of face fill.
    d.polygon([px(ear_left_x0, 0.3), px(ear_left_x1, 0.3),
               px(ear_left_tip_x, ear_tip_y)], fill=PAL_RGB[DARK_O])
    d.polygon([px(ear_right_x0, 0.3), px(ear_right_x1, 0.3),
               px(ear_right_tip_x, ear_tip_y)], fill=PAL_RGB[DARK_O])
    d.polygon([px(ear_left_x0 + 0.6, 0.55), px(ear_left_x1 - 0.6, 0.55),
               px(ear_left_tip_x, ear_tip_y * 0.7)],
              fill=PAL_RGB[ORANGE])
    d.polygon([px(ear_right_x0 + 0.6, 0.55), px(ear_right_x1 - 0.6, 0.55),
               px(ear_right_tip_x, ear_tip_y * 0.7)],
              fill=PAL_RGB[ORANGE])
    if cells_w >= 10:
        d.polygon([px(ear_left_x0 + 1.0, 0.75), px(ear_left_x1 - 1.0, 0.75),
                   px(ear_left_tip_x, ear_tip_y * 0.55)],
                  fill=PAL_RGB[LIGHT])
        d.polygon([px(ear_right_x0 + 1.0, 0.75), px(ear_right_x1 - 1.0, 0.75),
                   px(ear_right_tip_x, ear_tip_y * 0.55)],
                  fill=PAL_RGB[LIGHT])

    # ---- Forehead micro-arc (only 16×9 has it) --------------------------
    if features["forehead_arc"]:
        arc_pad = 2.0 if cells_w >= 12 else 1.5
        d.chord(
            [px(cells_w / 2 - cells_w * 0.4 + arc_pad * 0, 0.4),
             px(cells_w - arc_pad, face_y0 + 1.0)],
            180, 360, fill=PAL_RGB[ORANGE],
        )
        # Re-paint ears on top of the chord.
        d.polygon([px(ear_left_x0, 0.3), px(ear_left_x1, 0.3),
                   px(ear_left_tip_x, ear_tip_y)], fill=PAL_RGB[DARK_O])
        d.polygon([px(ear_right_x0, 0.3), px(ear_right_x1, 0.3),
                   px(ear_right_tip_x, ear_tip_y)], fill=PAL_RGB[DARK_O])
        d.polygon([px(ear_left_x0 + 0.6, 0.55), px(ear_left_x1 - 0.6, 0.55),
                   px(ear_left_tip_x, ear_tip_y * 0.7)],
                  fill=PAL_RGB[ORANGE])
        d.polygon([px(ear_right_x0 + 0.6, 0.55), px(ear_right_x1 - 0.6, 0.55),
                   px(ear_right_tip_x, ear_tip_y * 0.7)],
                  fill=PAL_RGB[ORANGE])
        if cells_w >= 12:
            d.polygon([px(ear_left_x0 + 1.0, 0.75), px(ear_left_x1 - 1.0, 0.75),
                       px(ear_left_tip_x, ear_tip_y * 0.55)],
                      fill=PAL_RGB[LIGHT])
            d.polygon([px(ear_right_x0 + 1.0, 0.75), px(ear_right_x1 - 1.0, 0.75),
                       px(ear_right_tip_x, ear_tip_y * 0.55)],
                      fill=PAL_RGB[LIGHT])

    # ---- Eyes ----------------------------------------------------------
    eye_w = features["eye_w"]
    eye_h = features["eye_h"]
    eye_y = face_y0 + (face_y1 - face_y0) * 0.42
    # Distance between the two eyes scales with grid width.
    eye_spacing_x = cells_w * 0.34
    center_x = cells_w / 2
    eye_left_x = center_x - eye_spacing_x / 2 - eye_w / 2
    eye_right_x = center_x + eye_spacing_x / 2 - eye_w / 2
    d.ellipse([px(eye_left_x, eye_y), px(eye_left_x + eye_w, eye_y + eye_h)],
              fill=PAL_RGB[BLACK])
    d.ellipse([px(eye_right_x, eye_y), px(eye_right_x + eye_w, eye_y + eye_h)],
              fill=PAL_RGB[BLACK])

    # ---- Cheek highlights (when enabled) -------------------------------
    if features["cheeks"]:
        cheek_y = eye_y + eye_h + 0.3
        d.ellipse([px(face_x0 + 0.5, cheek_y),
                   px(face_x0 + 0.5 + cells_w * 0.25, cheek_y + cells_h * 0.18)],
                  fill=PAL_RGB[LIGHT])
        d.ellipse([px(face_x1 - 0.5 - cells_w * 0.25, cheek_y),
                   px(face_x1 - 0.5, cheek_y + cells_h * 0.18)],
                  fill=PAL_RGB[LIGHT])

    # ---- Nose (when enabled) -------------------------------------------
    if features["nose"]:
        nose_y = eye_y + eye_h + 0.05
        nose_w = 0.8
        d.polygon(
            [px(center_x - nose_w / 2, nose_y), px(center_x + nose_w / 2, nose_y),
             px(center_x, nose_y + 0.6)],
            fill=PAL_RGB[DARK],
        )

    # ---- Mouth ---------------------------------------------------------
    mouth_kind = features["mouth"]
    if mouth_kind == "w":
        mouth_y = eye_y + eye_h + 0.7
        # w-shape: two soft zigzag (left → down → up → down → up → right)
        d.line(
            [px(center_x - 0.85, mouth_y), px(center_x - 0.55, mouth_y + 0.5),
             px(center_x, mouth_y + 0.3), px(center_x + 0.55, mouth_y + 0.5),
             px(center_x + 0.85, mouth_y)],
            fill=PAL_RGB[DARK], width=2,
        )
    elif mouth_kind == "smile":
        mouth_y = eye_y + eye_h + 0.9
        d.arc(
            [px(center_x - 0.8, mouth_y - 0.2), px(center_x + 0.8, mouth_y + 0.4)],
            start=20, end=160, fill=PAL_RGB[DARK], width=2,
        )
    elif mouth_kind == "dot":
        d.ellipse([px(center_x - 0.3, eye_y + eye_h + 0.6),
                   px(center_x + 0.3, eye_y + eye_h + 0.9)],
                  fill=PAL_RGB[DARK])

    # ---- Whiskers (0/1/2 per side) -------------------------------------
    n_whiskers = features["whiskers"]
    if n_whiskers >= 1:
        for wy_rel in (0.65, 0.85)[:n_whiskers]:
            wy = eye_y + eye_h + wy_rel
            d.line([px(face_x0 + 0.6, wy), px(0.5, wy)], fill=PAL_RGB[DARK], width=1)
            d.line([px(face_x1 - 0.6, wy), px(cells_w - 0.5, wy)],
                   fill=PAL_RGB[DARK], width=1)

    # ---- Base line -----------------------------------------------------
    if features["base_line"]:
        d.rectangle([px(0, cells_h - 0.6), px(cells_w, cells_h)],
                    fill=PAL_RGB[BLACK])

    return img


# ---- Public dispatch for small variants -----------------------------------

SMALL_VARIANT_SIZES: tuple[tuple[int, int], ...] = (
    (16, 9),
    (12, 7),
    (10, 6),
    (8, 5),
)


def draw_small_variant(size_label: str) -> Image.Image:
    """Generate a small cat head at the requested size.

    ``size_label`` is a key like ``"16x9"``, ``"12x7"``, ``"10x6"``, ``"8x5"``.
    Each size follows the big-logo visual style with features scaled to
    the grid size.
    """
    table = {
        "16x9": dict(
            cells_w=16, cells_h=9,
            forehead_arc=True, eye_w=2.0, eye_h=1.0, cheeks=True,
            nose=True, whiskers=2, base_line=True, mouth="w",
        ),
        "12x7": dict(
            cells_w=12, cells_h=7,
            forehead_arc=False, eye_w=1.6, eye_h=1.0, cheeks=True,
            nose=True, whiskers=1, base_line=True, mouth="w",
        ),
        "10x6": dict(
            cells_w=10, cells_h=6,
            forehead_arc=False, eye_w=1.4, eye_h=0.9, cheeks=False,
            nose=True, whiskers=1, base_line=True, mouth="smile",
        ),
        "8x5": dict(
            cells_w=8, cells_h=5,
            forehead_arc=False, eye_w=1.0, eye_h=0.9, cheeks=False,
            nose=False, whiskers=0, base_line=True, mouth="smile",
            face_shape="ellipse",  # v0.2.7: rounder face
        ),
    }
    if size_label not in table:
        raise ValueError(f"unknown small variant size: {size_label!r}")
    spec = table[size_label]
    return _make_small_variant(
        spec["cells_w"], spec["cells_h"],
        features={
            "forehead_arc": spec["forehead_arc"],
            "eye_w": spec["eye_w"], "eye_h": spec["eye_h"],
            "cheeks": spec["cheeks"], "nose": spec["nose"],
            "whiskers": spec["whiskers"], "base_line": spec["base_line"],
            "mouth": spec["mouth"],
        },
    )


SMALL_VARIANT_PREVIEW_NAMES = tuple(f"small_variant_{w}x{h}" for w, h in SMALL_VARIANT_SIZES)


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

def write_assets_py(
    head_grid: list[list[int]],
    frames_grids: dict[str, list[list[list[int]]]],
    variant_grids: dict[str, list[list[int]]] | None = None,
    variant_sizes: dict[str, tuple[int, int]] | None = None,
) -> None:
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

    variant_block = ""
    if variant_grids and variant_sizes:
        size_lines = ",\n".join(
            f'    "{k}": {v}' for k, v in variant_sizes.items()
        )
        grid_lines = []
        for name, grid in variant_grids.items():
            block = "[" + "\n".join(f"            {row}," for row in grid) + "\n        ]"
            grid_lines.append(f'    "{name}": {block}')
        variant_block = (
            "VARIANT_SIZES: dict[str, tuple[int, int]] = {\n"
            f"{size_lines},\n"
            "}\n"
            "SMALL_VARIANT_BASE: dict[str, tuple[tuple[int, ...], ...]] = {\n"
            + ",\n".join(grid_lines)
            + ",\n}\n"
        )

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
        + variant_block
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

def build(preview_only: bool = False, include_size_variants: bool = True) -> None:
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

    # v0.2.6 user feedback: render small-logo size variants and embed
    # their grids into the asset module so the TUI can render them at
    # runtime via ``render_variant``.
    variant_grids: dict[str, list[list[int]]] = {}
    variant_sizes: dict[str, tuple[int, int]] = {}
    variant_pngs: list[tuple[str, Path]] = []
    if include_size_variants:
        PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
        for w, h in SMALL_VARIANT_SIZES:
            size_label = f"{w}x{h}"
            img = draw_small_variant(size_label)
            out = PREVIEW_DIR / f"small_variant_{size_label}.png"
            img.save(out)
            variant_pngs.append((size_label, out))
            # Only embed in the asset module the sizes that **differ**
            # from the default 16×9 (which already lives in ``HEAD`` /
            # ``SMALL_FRAMES``).
            if not preview_only and (w, h) != (16, 9):
                variant_grids[size_label] = quantize(img, w, h * 2)
                variant_sizes[size_label] = (w, h)

    if not preview_only:
        write_assets_py(
            head_grid, small_frames_grids,
            variant_grids=variant_grids or None,
            variant_sizes=variant_sizes or None,
        )
    write_preview_pngs(head_img, small_frames_imgs)

    total_pngs = 1 + sum(len(frames) for frames in small_frames_imgs.values())
    total_pngs += len(variant_pngs)
    print(f"Wrote {total_pngs} PNG previews to {PREVIEW_DIR}")
    if not preview_only:
        print(f"Wrote asset module to {ASSETS_PY}")


if __name__ == "__main__":
    preview_only = "--preview" in sys.argv
    build(preview_only=preview_only)
