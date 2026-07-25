"""Half-block orange-cat logo renderer (InvestPilot v0.2.3).

v0.2.3 user feedback resolved:
- Big boot logo uses the same 16×9 cells as the mascot (no more 32×18
  duplicate artwork).
- Small face has 1-cell padding on every axis.
- The 5 separate animations collapse into a single ``blink_ear`` 4-frame
  loop that combines eyes-closing with ears tilting outward.

Public API:
- :data:`PALETTE` — palette colors re-exported for tests.
- :data:`ANIMATIONS` — animation names (``("blink_ear",)``).
- :data:`FRAMES_PER_ANIM` — frames per animation (currently 4).
- :func:`render_head` — static 16×9 cat (used for the boot big logo).
- :func:`render_small_frame` — single small-logo animation frame.
- :func:`render_small_static` — current frame per module-level state.
- :func:`set_small_state` — set state for the static renderer.
- :func:`advance_state` — bump to the next frame.
"""

from __future__ import annotations

from investpilot.interface import _logo_assets

PALETTE: tuple[str | None, ...] = _logo_assets.PALETTE
PAL_HEX_LOWER = {idx: c.lower() for idx, c in enumerate(PALETTE) if c is not None}

HEAD_CELLS_W: int = _logo_assets.HEAD_CELLS_W
HEAD_CELLS_H: int = _logo_assets.HEAD_CELLS_H

# v0.2.8: the runtime small mascot has been promoted to 8×5 cells
# (round-ellipse face).  The boot head stays at 16×9.
SMALL_CELLS_W: int = _logo_assets.SMALL_CELLS_W
SMALL_CELLS_H: int = _logo_assets.SMALL_CELLS_H

ANIMATIONS: tuple[str, ...] = ("blink_ear",)
FRAMES_PER_ANIM: int = 4


def _cell_to_markup(up_idx: int, down_idx: int) -> str:
    """Render a single cell (two pixel rows) to Rich markup.

    - Both transparent → ``" "``.
    - Only top colored → ``▀`` with fg = top.
    - Only bottom colored → ``▄`` with fg = bottom.
    - Both same color → full-block ``█``.
    - Different colors → ``▀`` with ``[fg on bg]`` markup.
    """
    if up_idx == 0 and down_idx == 0:
        return " "
    if up_idx == 0:
        assert PALETTE[down_idx] is not None
        return f"[{PAL_HEX_LOWER[down_idx]}]▄[/]"
    if down_idx == 0:
        assert PALETTE[up_idx] is not None
        return f"[{PAL_HEX_LOWER[up_idx]}]▀[/]"
    upper = PAL_HEX_LOWER[up_idx]
    lower = PAL_HEX_LOWER[down_idx]
    if upper == lower:
        return f"[{upper}]█[/]"
    return f"[{upper} on {lower}]▀[/]"


def _render_grid(rows: tuple[tuple[int, ...], ...], cells_w: int, cells_h: int) -> str:
    """Convert a (cells_h×2 pixel rows) × cells_w grid to markup text."""
    out_lines: list[str] = []
    for cell_y in range(cells_h):
        top = rows[cell_y * 2]
        bot = rows[cell_y * 2 + 1]
        line_parts = [_cell_to_markup(top[col], bot[col]) for col in range(cells_w)]
        out_lines.append("".join(line_parts))
    return "\n".join(out_lines)


def render_head() -> str:
    """Render the static orange-cat head (16 cells × 9 cell-rows visual = 18 lines)."""
    return _render_grid(_logo_assets.HEAD, HEAD_CELLS_W, HEAD_CELLS_H)


# Backwards-compat alias — `render_big_head` was the v0.2.2 name.
render_big_head = render_head


def _validate_anim_frame(name: str, frame_index: int) -> tuple[int, ...]:
    if name not in _logo_assets.SMALL_FRAMES:
        raise ValueError(
            f"unknown animation {name!r}; expected one of {ANIMATIONS}"
        )
    frames = _logo_assets.SMALL_FRAMES[name]
    idx = frame_index % len(frames)
    return frames[idx]


def render_small_frame(name: str, frame_index: int) -> str:
    """Render the small orange-cat mascot for one animation frame."""
    rows = _validate_anim_frame(name, frame_index)
    return _render_grid(rows, SMALL_CELLS_W, SMALL_CELLS_H)


# v0.2.6 size variants — see _logo_assets.SMALL_VARIANT_BASE for grids.
VARIANT_SIZES: dict[str, tuple[int, int]] = dict(_logo_assets.VARIANT_SIZES)


def render_variant(size_label: str) -> str:
    """Render a size-variant small logo (e.g. ``"12x7"``).

    These variants are matched in style to the v0.2.5-mini big logo but
    drawn at smaller cell grids for review.
    """
    if size_label not in _logo_assets.SMALL_VARIANT_BASE:
        raise ValueError(
            f"unknown variant size {size_label!r}; "
            f"expected one of {list(_logo_assets.SMALL_VARIANT_BASE)}"
        )
    cw, ch = VARIANT_SIZES[size_label]
    rows = _logo_assets.SMALL_VARIANT_BASE[size_label]
    return _render_grid(rows, cw, ch)


# ---------------------------------------------------------------------------
# Module-level state used by the TUI tick loop.
# ---------------------------------------------------------------------------

_state: dict[str, int] = {"anim_idx": 0, "frame_idx": 0}


def get_state() -> tuple[str, int]:
    return ANIMATIONS[_state["anim_idx"] % len(ANIMATIONS)], _state["frame_idx"] % FRAMES_PER_ANIM


def set_small_state(name: str, frame_index: int) -> None:
    """Override the static-renderer state. Mainly for tests."""
    if name not in ANIMATIONS:
        raise ValueError(f"unknown animation {name!r}")
    _state["anim_idx"] = ANIMATIONS.index(name)
    _state["frame_idx"] = frame_index


# Backwards-compat alias (kept for the test suite naming convenience).
set_state = set_small_state


def advance_state() -> tuple[str, int]:
    """Advance to the next frame; roll over to next animation at end.

    With only one animation it simply walks 0 → 1 → 2 → 3 → 0.
    """
    _state["frame_idx"] += 1
    if _state["frame_idx"] >= FRAMES_PER_ANIM:
        _state["frame_idx"] = 0
        _state["anim_idx"] = (_state["anim_idx"] + 1) % len(ANIMATIONS)
    return get_state()


def render_small_static() -> str:
    """Render the small mascot using the current module state."""
    name, idx = get_state()
    return render_small_frame(name, idx)
