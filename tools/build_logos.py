#!/usr/bin/env python3
"""Build orange-cat half-block logo assets for InvestPilot.

The cat is authored ONCE as a coordinate list on a 16x9 reference grid
(:func:`draw_cat`).  The boot big logo renders it at 16x9; the resident
mascot re-renders the same geometry at 12x7, scaled — a real redraw, not a
bitmap resample.  Mascot poses vary two parameters: ear tilt and eye state.

Outputs two artifacts:

1. ``src/investpilot/interface/_logo_assets.py`` — ``PALETTE``, ``HEAD``
   (the 16x9 boot logo), ``SMALL_POSES`` (unique mascot bitmaps) and
   ``SMALL_SCHEDULE`` (one pose name per animation frame).

2. ``docs/iterations/v0.3.0/preview/*.png`` — human-review PNGs.

Run with ``uv run python tools/build_logos.py``. Idempotent.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
ASSETS_PY = ROOT / "src" / "investpilot" / "interface" / "_logo_assets.py"
PREVIEW_DIR = ROOT / "docs" / "iterations" / "v0.3.0" / "preview"

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

# Pixels drawn per cell. A cell is SCALE wide and SCALE*2 tall, because
# half-block rendering stacks two pixel rows into one terminal character.
SCALE = 8


# ---------------------------------------------------------------------------
# Cat drawing — ONE parametrised geometry
#
# v0.3.0 (user feedback: "以大logo为锚点，缩小重绘小logo"):
# The cat is authored ONCE as a coordinate list on a 16x9 reference grid.
# Rendering at any other cell grid multiplies every coordinate by
# ``sx = cells_w / 16`` and ``sy = cells_h / 9`` and re-draws with PIL.
# That is a genuine scale-down *redraw* — crisp vector shapes rasterised at
# the target size — NOT a LANCZOS resample of the big bitmap (which is what
# v0.2.10/v0.2.11 did, and which produced the mushy small logo).
#
# ``draw_cat(16, 9)`` reproduces the pin-locked big logo pixel-for-pixel;
# tests/test_logo.py::test_big_logo_geometry_unchanged enforces that.
# ---------------------------------------------------------------------------

# Reference grid the geometry below is authored against.
REF_W, REF_H = 16, 9

# Palette shorthand (indices into PALETTE).
_ORANGE = 1
_DARK_O = 2
_LIGHT = 3
_DARK = 4
_BLACK = 5

EYE_STATES = ("open", "half", "closed")


def draw_cat(
    cells_w: int = REF_W,
    cells_h: int = REF_H,
    *,
    ear_tilt: float = 0.0,
    eye_state: str = "open",
    whiskers: bool = True,
    forehead_arc: bool = True,
    cheek_scale: float = 1.0,
    cheek_centers: tuple[float, float] = (4.8, 11.2),
    eye_centers: tuple[float, float] = (5.0, 11.0),
    lid_centers: tuple[float, float] | None = None,
    nose_scale: float = 1.0,
    nose_y_offset: float = 0.0,
    face_bounds: tuple[float, float, float, float] = (1.5, 2.5, 14.5, 8.0),
    ear_style: str = "cat",
) -> Image.Image:
    """Draw the orange cat head at ``cells_w x cells_h`` cells.

    Parameters
    ----------
    cells_w, cells_h:
        Target cell grid. Geometry scales from the 16x9 reference.
    ear_tilt:
        Outward ear lean, in *reference* cells. ``0.0`` = upright.
    eye_state:
        ``"open"`` round dots / ``"half"`` lower-lid slit / ``"closed"`` line.
    whiskers:
        Draw two whiskers per side. Dropped on the small mascot — at 12x7
        they quantise down to stray one-pixel specks.
    forehead_arc:
        Draw the micro-arc between the two ear bases.
    cheek_scale:
        Scale the cheek highlights around their centres. The boot logo keeps
        the signed-off 1.0 geometry; the small mascot uses a tighter value.
    cheek_centers:
        Reference-grid x positions for cheek centres. The mascot overrides
        this to quantize symmetrically on its odd-width grid.
    eye_centers:
        Reference-grid x positions for eye centres. The mascot overrides this
        for the same odd-width symmetry reason.
    lid_centers:
        Optional reference-grid x positions for closed blink lids. Mascot
        closed lids need a slight inward offset so they do not touch the nose.
    nose_scale, nose_y_offset:
        Small-mascot nose tuning. The boot logo keeps the signed-off defaults.
    face_bounds:
        Reference-grid face rectangle. The mascot overrides this to keep the
        face smaller and balanced after quantization.
    ear_style:
        ``"cat"`` keeps the signed-off boot ears. ``"dog"`` uses shorter,
        blunter ears for the small mascot.
    """
    if eye_state not in EYE_STATES:
        raise ValueError(f"eye_state must be one of {EYE_STATES}, got {eye_state!r}")

    sx = cells_w / REF_W
    sy = cells_h / REF_H
    img = Image.new("RGB", (cells_w * SCALE, cells_h * SCALE * 2), (255, 255, 255))
    d = ImageDraw.Draw(img)

    def px(x: float, y: float) -> tuple[float, float]:
        """Reference-grid cell coords -> canvas pixel coords."""
        return (x * sx * SCALE, y * sy * SCALE * 2)

    def stroke(width: int) -> int:
        """Scale a stroke width, never thinner than 1 px."""
        return max(1, round(width * min(sx, sy)))

    t = ear_tilt

    def draw_ears() -> None:
        """Ears sit on top of everything drawn before them, so this runs
        again after each layer that would otherwise cover them."""
        if ear_style == "dog":
            # Short blunt ears read less cat-like at 9x6 than tall triangles.
            d.rounded_rectangle(
                [px(1.7 - t, 0.7), px(4.2 - t, 2.4)],
                radius=6 * min(sx, sy),
                fill=PAL_RGB[_DARK_O],
            )
            d.rounded_rectangle(
                [px(11.8 + t, 0.7), px(14.3 + t, 2.4)],
                radius=6 * min(sx, sy),
                fill=PAL_RGB[_DARK_O],
            )
            d.polygon([px(2.1 - t, 1.0), px(3.9 - t, 1.0), px(3.5 - t, 2.1)], fill=PAL_RGB[_ORANGE])
            d.polygon([px(12.1 + t, 1.0), px(13.9 + t, 1.0), px(12.5 + t, 2.1)], fill=PAL_RGB[_ORANGE])
        else:
            # Outer shells (darker orange)
            d.polygon([px(1 - t, 0.4), px(5 - t, 0.4), px(3.5, 2.4)], fill=PAL_RGB[_DARK_O])
            d.polygon([px(11 + t, 0.4), px(15 + t, 0.4), px(12.5, 2.4)], fill=PAL_RGB[_DARK_O])
            # Inner shells (main orange)
            d.polygon([px(2 - t, 0.7), px(4 - t, 0.7), px(3.5, 2.0)], fill=PAL_RGB[_ORANGE])
            d.polygon([px(12 + t, 0.7), px(14 + t, 0.7), px(12.5, 2.0)], fill=PAL_RGB[_ORANGE])
            # Inner-ear accent (cream)
            d.polygon(
                [px(2.4 - t, 0.95), px(3.6 - t, 0.95), px(3.5, 1.8)], fill=PAL_RGB[_LIGHT]
            )
            d.polygon(
                [px(12.4 + t, 0.95), px(13.6 + t, 0.95), px(12.5, 1.8)], fill=PAL_RGB[_LIGHT]
            )

    # ---- Ears (first pass) ----------------------------------------------
    draw_ears()

    # ---- Face ------------------------------------------------------------
    d.rounded_rectangle(
        [px(face_bounds[0], face_bounds[1]), px(face_bounds[2], face_bounds[3])],
        radius=18 * min(sx, sy),
        fill=PAL_RGB[_ORANGE],
    )
    draw_ears()

    # ---- Forehead micro-arc between the ear bases ------------------------
    if forehead_arc:
        d.chord([px(4, 1.5), px(12, 4.0)], 180, 360, fill=PAL_RGB[_ORANGE])
        draw_ears()

    # ---- Eyes ------------------------------------------------------------
    # Drawn fresh onto the orange face, so the half / closed poses need no
    # wipe pass. Eye centres sit at reference columns 5 and 11.
    #
    # The closed lid is deliberately WIDER and LOWER than the open eye: at
    # 12x7 the eye is only ~1.5 cells across, so a same-width lid changed
    # just 2 of 168 cells and the blink was invisible. The wide lid flips
    # ~10 cells — the same order as the ear wobble. Geometry was tuned by
    # measuring post-quantisation cell deltas, not by eye.
    closed_lids = lid_centers if lid_centers is not None else eye_centers
    for cx, closed_lid_cx in zip(eye_centers, closed_lids, strict=True):
        if eye_state == "open":
            d.ellipse([px(cx - 1.0, 4.0), px(cx + 1.0, 5.0)], fill=PAL_RGB[_BLACK])
        elif eye_state == "half":
            # Lid part-way down. Keep it compact so it does not touch the nose
            # after the mascot is quantized onto a small odd-width grid.
            d.rectangle(
                [px(cx - 1.1, 4.25), px(cx + 1.1, 5.75)], fill=PAL_RGB[_BLACK]
            )
        else:  # closed — flat lash line, roughly the open eye's width
            d.rectangle(
                [px(closed_lid_cx - 1.55, 5.15), px(closed_lid_cx + 1.55, 5.95)],
                fill=PAL_RGB[_BLACK],
            )

    # ---- Cheek highlights ------------------------------------------------
    if cheek_scale == 1.0:
        d.ellipse([px(3.2, 5.6), px(6.4, 7.0)], fill=PAL_RGB[_LIGHT])
        d.ellipse([px(9.6, 5.6), px(12.8, 7.0)], fill=PAL_RGB[_LIGHT])
    else:
        cheek_w = 3.2 * cheek_scale
        cheek_h = 1.4 * cheek_scale
        for cx in cheek_centers:
            d.ellipse(
                [
                    px(cx - cheek_w / 2, 6.3 - cheek_h / 2),
                    px(cx + cheek_w / 2, 6.3 + cheek_h / 2),
                ],
                fill=PAL_RGB[_LIGHT],
            )

    # ---- Nose ------------------------------------------------------------
    if nose_scale == 1.0 and nose_y_offset == 0.0:
        d.polygon([px(7.6, 5.2), px(8.4, 5.2), px(8, 5.9)], fill=PAL_RGB[_DARK])
    else:
        d.rectangle([px(7.2, 6.0 + nose_y_offset), px(8.8, 6.7 + nose_y_offset)], fill=PAL_RGB[_DARK])

    # ---- w mouth ---------------------------------------------------------
    d.line(
        [px(7.85, 5.95), px(7.2, 6.5), px(8, 6.3), px(8.8, 6.5), px(8.15, 5.95)],
        fill=PAL_RGB[_DARK],
        width=stroke(2),
    )

    # ---- Whiskers --------------------------------------------------------
    if whiskers:
        for y in (5.6, 6.3):
            d.line([px(3.2, y), px(0.5, y)], fill=PAL_RGB[_DARK], width=stroke(1))
            d.line([px(12.8, y), px(15.5, y)], fill=PAL_RGB[_DARK], width=stroke(1))

    # ---- Base line -------------------------------------------------------
    d.rectangle([px(0, 8.4), px(16, 9)], fill=PAL_RGB[_BLACK])

    return img


def draw_head() -> Image.Image:
    """The boot big logo — 16x9 cells, pin-locked at v0.2.5-mini."""
    return draw_cat(REF_W, REF_H, whiskers=True, forehead_arc=True)


# ---------------------------------------------------------------------------
# Small mascot: 9x5 cells, redrawn from the same geometry
#
# Size: longest side 9. The odd width keeps the face centred around one middle
# column and makes the left/right cheeks quantize symmetrically.
# Whiskers dropped per user feedback ("去掉胡须").
# Forehead arc dropped for the small mascot so it can lose one vertical row.
# ---------------------------------------------------------------------------

MASCOT_CELLS_W, MASCOT_CELLS_H = 9, 5
MASCOT_WHISKERS = False
MASCOT_FOREHEAD_ARC = False

# Unique poses. The animation is "摆耳朵 + 眨眼睛", alternating: the ears
# wobble outward twice, the cat holds still, then it blinks once.
MASCOT_POSES: dict[str, dict[str, object]] = {
    "idle": {"ear_tilt": 0.0, "eye_state": "open"},
    "ear1": {"ear_tilt": 0.7, "eye_state": "open"},
    "ear2": {"ear_tilt": 1.4, "eye_state": "open"},
    "blink1": {"ear_tilt": 0.0, "eye_state": "half"},
    "blink2": {"ear_tilt": 0.0, "eye_state": "closed"},
}

# 24 frames at 0.10 s = 2.4 s per loop:
#   frames  0-7   ears wobble outward twice   (0.8 s)
#   frames  8-19  hold still, eyes open       (1.2 s)
#   frames 20-23  one blink                   (0.4 s)
# The long hold is what makes the blink read as occasional rather than a
# nervous twitch (user picked "偶尔眨（自然）").
MASCOT_SCHEDULE: tuple[str, ...] = (
    "idle", "ear1", "ear2", "ear1",
    "idle", "ear1", "ear2", "ear1",
    *(("idle",) * 12),
    "blink1", "blink2", "blink1", "idle",
)


def draw_mascot_pose(pose: str) -> Image.Image:
    """Render one named mascot pose at the mascot cell grid."""
    if pose not in MASCOT_POSES:
        raise ValueError(f"unknown pose {pose!r}; expected one of {list(MASCOT_POSES)}")
    spec = MASCOT_POSES[pose]
    return draw_cat(
        MASCOT_CELLS_W,
        MASCOT_CELLS_H,
        ear_tilt=float(spec["ear_tilt"]),
        eye_state=str(spec["eye_state"]),
        whiskers=MASCOT_WHISKERS,
        forehead_arc=MASCOT_FOREHEAD_ARC,
        cheek_scale=0.6,
        cheek_centers=(4.5, 10.5),
        eye_centers=(4.0, 11.5),
        lid_centers=(3.5, 11.0),
        nose_scale=1.35,
        nose_y_offset=0.0,
        face_bounds=(3.0, 2.9, 13.0, 7.4),
        ear_style="dog",
    )


# ---------------------------------------------------------------------------
# Review-only size variants (preview PNGs, not shipped in the asset module)
# ---------------------------------------------------------------------------

SMALL_VARIANT_SIZES: tuple[tuple[int, int], ...] = (
    (12, 7),
    (10, 6),
    (8, 5),
)

SMALL_VARIANT_PREVIEW_NAMES = tuple(f"small_variant_{w}x{h}" for w, h in SMALL_VARIANT_SIZES)


def draw_small_variant(size_label: str) -> Image.Image:
    """Redraw the cat at one of the review sizes (no whiskers)."""
    table = {f"{w}x{h}": (w, h) for w, h in SMALL_VARIANT_SIZES}
    if size_label not in table:
        raise ValueError(f"unknown small variant size: {size_label!r}")
    cells_w, cells_h = table[size_label]
    return draw_cat(cells_w, cells_h, whiskers=False, forehead_arc=True)



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


def symmetrize_odd_width_grid(grid: list[list[int]]) -> list[list[int]]:
    """Mirror the left half onto the right half for odd-width mascot grids."""
    if not grid or len(grid[0]) % 2 == 0:
        return grid
    width = len(grid[0])
    mid = width // 2
    out: list[list[int]] = []
    for row in grid:
        mirrored = list(row)
        for x in range(mid):
            mirrored[width - 1 - x] = mirrored[x]
        out.append(mirrored)
    return out


def refine_mascot_grid(pose: str, grid: list[list[int]]) -> list[list[int]]:
    """Final low-res mascot polish after quantization."""
    refined = symmetrize_odd_width_grid(grid)
    if len(refined) == 10 and len(refined[0]) == 9:
        # At 9x5, force the facial pixels onto clean symmetric cells. Open
        # eyes are one cell each; the final blink is a two-cell vertical mark.
        refined[5] = [0, 1, 5, 1, 1, 1, 5, 1, 0]
        refined[6] = [0, 1, 1, 1, 1, 1, 1, 1, 0]
        if pose == "blink1":
            refined[5] = [0, 1, 1, 1, 1, 1, 1, 1, 0]
            refined[6] = [0, 1, 5, 1, 1, 1, 5, 1, 0]
        elif pose == "blink2":
            refined[5] = [0, 1, 1, 1, 1, 1, 1, 1, 0]
            refined[6] = [0, 1, 5, 1, 1, 1, 5, 1, 0]
        refined[7] = [0, 1, 3, 1, 4, 1, 3, 1, 0]
        if pose == "blink2":
            refined[7] = [0, 1, 5, 1, 4, 1, 5, 1, 0]
    return refined


# ---------------------------------------------------------------------------
# Output writers
# ---------------------------------------------------------------------------

def write_assets_py(
    head_grid: list[list[int]],
    pose_grids: dict[str, list[list[int]]],
    schedule: tuple[str, ...],
    *,
    mascot_cells_w: int,
    mascot_cells_h: int,
) -> None:
    """Emit the generated asset module.

    v0.3.0 data model: the mascot ships as a small set of unique *poses*
    plus a *schedule* naming one pose per animation frame.  The 24-frame
    loop only needs 5 bitmaps, so the twelve identical hold frames cost
    nothing.
    """
    ASSETS_PY.parent.mkdir(parents=True, exist_ok=True)

    def grid_literal(grid: list[list[int]], indent: str) -> str:
        rows = "\n".join(f"{indent}    {row}," for row in grid)
        return f"(\n{rows}\n{indent})"

    pal_lines = ",\n    ".join(repr(p) for p in PALETTE)
    pose_lines = ",\n".join(
        f'    "{name}": {grid_literal(grid, "    ")}'
        for name, grid in pose_grids.items()
    )
    schedule_lines = ",\n".join(f'    "{name}"' for name in schedule)

    body = (
        '"""Auto-generated by tools/build_logos.py — do not edit by hand."""\n'
        "from __future__ import annotations\n"
        "\n"
        "PALETTE: tuple[str | None, ...] = (\n"
        f"    {pal_lines},\n"
        ")\n"
        "\n"
        "# ---- Boot big logo (16x9 cells, pin-locked) -------------------------\n"
        f"HEAD_CELLS_W: int = {REF_W}\n"
        f"HEAD_CELLS_H: int = {REF_H}\n"
        f"HEAD: tuple[tuple[int, ...], ...] = {grid_literal(head_grid, '')}\n"
        "\n"
        "# ---- Resident mascot (redrawn from the same geometry) ---------------\n"
        f"SMALL_CELLS_W: int = {mascot_cells_w}\n"
        f"SMALL_CELLS_H: int = {mascot_cells_h}\n"
        "\n"
        "# Unique poses: ears wobble outward, then the cat blinks.\n"
        "SMALL_POSES: dict[str, tuple[tuple[int, ...], ...]] = {\n"
        f"{pose_lines},\n"
        "}\n"
        "\n"
        "# One pose name per animation frame; index advances every tick.\n"
        "SMALL_SCHEDULE: tuple[str, ...] = (\n"
        f"{schedule_lines},\n"
        ")\n"
    )
    ASSETS_PY.write_text(body, encoding="utf-8")


def write_preview_pngs(
    head_img: Image.Image,
    pose_imgs: dict[str, Image.Image],
    variant_imgs: dict[str, Image.Image],
) -> int:
    """Write human-review PNGs; returns the file count."""
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    head_img.save(PREVIEW_DIR / "big.png")
    count = 1
    for name, img in pose_imgs.items():
        img.save(PREVIEW_DIR / f"mascot_{name}.png")
        count += 1
    for label, img in variant_imgs.items():
        img.save(PREVIEW_DIR / f"small_variant_{label}.png")
        count += 1
    return count


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def build(preview_only: bool = False) -> None:
    head_img = draw_head()
    pose_imgs = {name: draw_mascot_pose(name) for name in MASCOT_POSES}
    variant_imgs = {
        f"{w}x{h}": draw_small_variant(f"{w}x{h}") for w, h in SMALL_VARIANT_SIZES
    }

    if not preview_only:
        write_assets_py(
            head_grid=quantize(head_img, REF_W, REF_H * 2),
            pose_grids={
                name: refine_mascot_grid(name, quantize(img, MASCOT_CELLS_W, MASCOT_CELLS_H * 2))
                for name, img in pose_imgs.items()
            },
            schedule=MASCOT_SCHEDULE,
            mascot_cells_w=MASCOT_CELLS_W,
            mascot_cells_h=MASCOT_CELLS_H,
        )

    n = write_preview_pngs(head_img, pose_imgs, variant_imgs)
    print(f"Wrote {n} PNG previews to {PREVIEW_DIR}")
    if not preview_only:
        print(f"Wrote asset module to {ASSETS_PY}")
        print(
            f"  mascot {MASCOT_CELLS_W}x{MASCOT_CELLS_H} cells, "
            f"{len(MASCOT_POSES)} poses, {len(MASCOT_SCHEDULE)}-frame loop"
        )


if __name__ == "__main__":
    build(preview_only="--preview" in sys.argv)
