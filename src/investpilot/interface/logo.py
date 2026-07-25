"""Half-block orange-cat logo renderer.

Two logos, one geometry (see ``tools/build_logos.py``):

- **Boot big logo** — 16x9 cells, rendered once into the transcript on
  start-up. Pin-locked artwork; :func:`render_big_head`.
- **Resident mascot** — 12x7 cells, the same cat redrawn at 75 % scale,
  animated by a pose schedule; :func:`render_small_frame`.

The mascot animation is "摆耳朵 + 眨眼睛", alternating: the ears wobble
outward twice, the cat holds still for a beat, then blinks once. The
schedule in :data:`SCHEDULE` names one pose per tick, so the twelve
identical hold frames cost no extra bitmaps.

Rendering uses the Unicode half-block characters ``▀`` / ``▄`` so each
terminal cell carries two stacked pixels of colour.
"""

from __future__ import annotations

from investpilot.interface import _logo_assets

PALETTE: tuple[str | None, ...] = _logo_assets.PALETTE
PAL_HEX_LOWER = {idx: c.lower() for idx, c in enumerate(PALETTE) if c is not None}

HEAD_CELLS_W: int = _logo_assets.HEAD_CELLS_W
HEAD_CELLS_H: int = _logo_assets.HEAD_CELLS_H

SMALL_CELLS_W: int = _logo_assets.SMALL_CELLS_W
SMALL_CELLS_H: int = _logo_assets.SMALL_CELLS_H

POSES: tuple[str, ...] = tuple(_logo_assets.SMALL_POSES)
SCHEDULE: tuple[str, ...] = tuple(_logo_assets.SMALL_SCHEDULE)
FRAME_COUNT: int = len(SCHEDULE)


def _cell_to_markup(up_idx: int, down_idx: int) -> str:
    """Render one cell (two stacked pixels) as Rich markup.

    ``▀`` paints the upper pixel as foreground; a background colour fills
    the lower one. Transparent pixels fall through to the terminal colour.
    """
    if up_idx == 0 and down_idx == 0:
        return " "
    if up_idx == 0:
        return f"[{PAL_HEX_LOWER[down_idx]}]▄[/]"
    if down_idx == 0:
        return f"[{PAL_HEX_LOWER[up_idx]}]▀[/]"
    upper = PAL_HEX_LOWER[up_idx]
    lower = PAL_HEX_LOWER[down_idx]
    if upper == lower:
        return f"[{upper}]█[/]"
    return f"[{upper} on {lower}]▀[/]"


def _render_grid(rows: tuple[tuple[int, ...], ...], cells_w: int, cells_h: int) -> str:
    """Fold a ``cells_h*2`` row pixel grid into ``cells_h`` markup lines."""
    out: list[str] = []
    for cell_y in range(cells_h):
        top = rows[cell_y * 2]
        bot = rows[cell_y * 2 + 1]
        out.append("".join(_cell_to_markup(top[x], bot[x]) for x in range(cells_w)))
    return "\n".join(out)


def render_big_head() -> str:
    """The boot logo: 16 cells wide, 9 markup lines tall."""
    return _render_grid(_logo_assets.HEAD, HEAD_CELLS_W, HEAD_CELLS_H)


def render_pose(pose: str) -> str:
    """Render one named mascot pose."""
    grid = _logo_assets.SMALL_POSES.get(pose)
    if grid is None:
        raise ValueError(f"unknown pose {pose!r}; expected one of {list(POSES)}")
    return _render_grid(grid, SMALL_CELLS_W, SMALL_CELLS_H)


def pose_at(frame_index: int) -> str:
    """Pose name scheduled for ``frame_index`` (wraps around the loop)."""
    return SCHEDULE[frame_index % FRAME_COUNT]


def render_small_frame(frame_index: int) -> str:
    """Render the mascot for a given animation frame."""
    return render_pose(pose_at(frame_index))


# ---------------------------------------------------------------------------
# Module-level frame cursor driven by the TUI tick.
# ---------------------------------------------------------------------------

_state: dict[str, int] = {"frame": 0}


def get_frame() -> int:
    return _state["frame"] % FRAME_COUNT


def set_frame(frame_index: int) -> None:
    """Jump the cursor to a frame. Used by tests and the screenshot harness."""
    _state["frame"] = frame_index % FRAME_COUNT


def advance_frame() -> int:
    """Step to the next frame and return the new index."""
    _state["frame"] = (_state["frame"] + 1) % FRAME_COUNT
    return _state["frame"]


def render_small_static() -> str:
    """Render the mascot at the current cursor position."""
    return render_small_frame(get_frame())
