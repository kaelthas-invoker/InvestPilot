from __future__ import annotations

import pytest

from investpilot.interface import logo

# ---------------------------------------------------------------------------
# Shape & palette
# ---------------------------------------------------------------------------


def test_palette_length() -> None:
    assert len(logo.PALETTE) == 6


def test_animations_constant() -> None:
    """v0.2.3 collapses the 5 animations into a single ``blink_ear``."""
    assert logo.ANIMATIONS == ("blink_ear",)
    assert logo.FRAMES_PER_ANIM == 4


def test_big_head_cell_geometry() -> None:
    """Boot head: 16×9 cells, 2 pixel rows per cell."""
    from investpilot.interface import _logo_assets

    grid = _logo_assets.HEAD
    assert len(grid) == logo.HEAD_CELLS_H * 2 == 18
    for row in grid:
        assert len(row) == logo.HEAD_CELLS_W == 16


def test_small_frames_shape() -> None:
    """Mascot frames: ``SMALL_CELLS_W × SMALL_CELLS_H`` cells, 4 frames."""
    from investpilot.interface import _logo_assets

    assert set(_logo_assets.SMALL_FRAMES) == set(logo.ANIMATIONS)
    for name in logo.ANIMATIONS:
        frames = _logo_assets.SMALL_FRAMES[name]
        assert len(frames) == logo.FRAMES_PER_ANIM
        for frame in frames:
            assert len(frame) == logo.SMALL_CELLS_H * 2
            for row in frame:
                assert len(row) == logo.SMALL_CELLS_W


def test_grids_only_use_palette_indices() -> None:
    from investpilot.interface import _logo_assets

    palette_size = len(logo.PALETTE)
    for row in _logo_assets.HEAD:
        for v in row:
            assert 0 <= v < palette_size

    for frames in _logo_assets.SMALL_FRAMES.values():
        for frame in frames:
            for row in frame:
                for v in row:
                    assert 0 <= v < palette_size


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def test_render_head_uses_halfblock() -> None:
    text = logo.render_head()
    assert any(ch in text for ch in ("▀", "▄", "█"))


def test_render_head_includes_palette_colors() -> None:
    text = logo.render_head().lower()
    palette_hexes = {c.lower() for c in logo.PALETTE if c is not None}
    assert any(hex_code in text for hex_code in palette_hexes)


def test_render_head_visual_rows_count() -> None:
    text = logo.render_head()
    lines = text.split("\n")
    assert len(lines) == logo.HEAD_CELLS_H == 9


def test_render_small_frame_known_animation() -> None:
    text = logo.render_small_frame("blink_ear", 0)
    assert text.count("\n") == logo.SMALL_CELLS_H - 1


def test_render_small_frame_unknown_animation_raises() -> None:
    with pytest.raises(ValueError):
        logo.render_small_frame("nope", 0)


def test_blink_ear_frames_differ() -> None:
    """Blink + ear animation: frames 0/2 differ (open vs closed eyes);
    frames 1/3 should be the same intermediate state."""
    from investpilot.interface import _logo_assets

    base = _logo_assets.SMALL_FRAMES["blink_ear"][0]
    closed = _logo_assets.SMALL_FRAMES["blink_ear"][2]
    assert base != closed  # eyes change between open and closed

    # Cross-check: peak (closed eyes + tilted ears) versus base (open
    # eyes + upright ears) must differ in multiple cells.
    diffs = sum(
        1 for r_a, r_b in zip(base, closed) for a, b in zip(r_a, r_b) if a != b
    )
    assert diffs >= 4  # at minimum: 2 eyes + 2 ears


# ---------------------------------------------------------------------------
# State + advance
# ---------------------------------------------------------------------------


def test_advance_walks_through_frames_in_one_animation() -> None:
    logo.set_state("blink_ear", 0)
    seen: set[tuple[str, int]] = set()
    for _ in range(4):  # one loop = 4 frames in a single animation
        name, idx = logo.get_state()
        seen.add((name, idx))
        logo.advance_state()
    assert seen == {("blink_ear", i) for i in range(4)}


def test_advance_cycles_after_one_full_loop() -> None:
    logo.set_state("blink_ear", 0)
    for _ in range(4):
        logo.advance_state()
    name, idx = logo.get_state()
    assert name == "blink_ear"
    assert idx == 0


def test_render_small_static_matches_set_state() -> None:
    logo.set_state("blink_ear", 2)
    text = logo.render_small_static()
    expected = logo.render_small_frame("blink_ear", 2)
    assert text == expected


def test_set_state_rejects_unknown_animation() -> None:
    with pytest.raises(ValueError):
        logo.set_state("nonexistent", 0)
