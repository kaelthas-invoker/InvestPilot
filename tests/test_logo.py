from __future__ import annotations

import pytest

from investpilot.interface import logo

# ---------------------------------------------------------------------------
# Shape & palette
# ---------------------------------------------------------------------------


def test_palette_length() -> None:
    assert len(logo.PALETTE) == 6


def test_animations_constant() -> None:
    assert logo.ANIMATIONS == ("wave", "ear", "tail", "blink", "peek")
    assert logo.FRAMES_PER_ANIM == 4


def test_big_head_cell_geometry() -> None:
    """Grid stores 2 pixel rows per cell, so cols == 32 and rows == 18 * 2."""
    from investpilot.interface import _logo_assets

    grid = _logo_assets.BIG_HEAD
    assert len(grid) == logo.BIG_HEAD_CELLS_H * 2 == 36
    for row in grid:
        assert len(row) == logo.BIG_HEAD_CELLS_W == 32


def test_small_frames_shape() -> None:
    """5 animations × 4 frames, each 18 pixel-rows × 16 columns."""
    from investpilot.interface import _logo_assets

    assert set(_logo_assets.SMALL_FRAMES) == set(logo.ANIMATIONS)
    for name in logo.ANIMATIONS:
        frames = _logo_assets.SMALL_FRAMES[name]
        assert len(frames) == logo.FRAMES_PER_ANIM
        for frame in frames:
            assert len(frame) == logo.SMALL_CELLS_H * 2 == 18
            for row in frame:
                assert len(row) == logo.SMALL_CELLS_W == 16


def test_grids_only_use_palette_indices() -> None:
    """All grid cells must index into the 6-color palette (0..5)."""
    from investpilot.interface import _logo_assets

    palette_size = len(logo.PALETTE)
    for row in _logo_assets.BIG_HEAD:
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


def test_render_big_head_uses_halfblock() -> None:
    text = logo.render_big_head()
    # Contains at least one half-block char
    assert any(ch in text for ch in ("▀", "▄", "█"))


def test_render_big_head_includes_palette_colors() -> None:
    text = logo.render_big_head().lower()
    palette_hexes = {c.lower() for c in logo.PALETTE if c is not None}
    assert any(hex_code in text for hex_code in palette_hexes)


def test_render_big_head_visual_rows_count() -> None:
    text = logo.render_big_head()
    lines = text.split("\n")
    # 18 visual rows (each row = two stacked pixel rows in the grid)
    assert len(lines) == logo.BIG_HEAD_CELLS_H == 18
    for line in lines:
        # Each visual row contains BIG_HEAD_CELLS_W terminal cols
        # Even after Rich strips tags, terminal cell width remains the
        # number of half-block characters. We just verify non-empty.
        assert line


def test_render_small_frame_known_animation() -> None:
    text = logo.render_small_frame("wave", 0)
    assert text.count("\n") == logo.SMALL_CELLS_H - 1 == 8


def test_render_small_frame_unknown_animation_raises() -> None:
    with pytest.raises(ValueError):
        logo.render_small_frame("nope", 0)


def test_animation_frames_differ_from_each_other() -> None:
    """Within an animation, frames 0/2 (base) may match; frames 1/3 should
    differ; and cross-animation frames must differ somewhere."""
    from investpilot.interface import _logo_assets

    # Tail frame 1 and frame 3 should differ from base since they swing
    # the tail arc.
    base = _logo_assets.SMALL_FRAMES["tail"][0]
    swung_left = _logo_assets.SMALL_FRAMES["tail"][1]
    swung_right = _logo_assets.SMALL_FRAMES["tail"][3]
    assert base != swung_left
    assert base != swung_right

    # Peek frame 3 (deepest peek) should differ from frame 0 (base).
    base = _logo_assets.SMALL_FRAMES["peek"][0]
    up = _logo_assets.SMALL_FRAMES["peek"][3]
    assert base != up

    # Cross-animation: blink frame 2 should differ from peek frame 0.
    blink_closed = _logo_assets.SMALL_FRAMES["blink"][2]
    peek_base = _logo_assets.SMALL_FRAMES["peek"][0]
    assert blink_closed != peek_base


# ---------------------------------------------------------------------------
# State + advance
# ---------------------------------------------------------------------------


def test_advance_state_progresses_through_animations() -> None:
    logo.set_state("wave", 0)
    seen: set[tuple[str, int]] = set()
    for _ in range(20):  # 5 anims × 4 frames
        name, idx = logo.get_state()
        seen.add((name, idx))
        logo.advance_state()
    # All 5×4 = 20 distinct (anim, frame) pairs should have been seen.
    assert seen == {
        (a, i)
        for a in logo.ANIMATIONS
        for i in range(logo.FRAMES_PER_ANIM)
    }


def test_render_small_static_matches_set_state() -> None:
    logo.set_state("ear", 2)
    text = logo.render_small_static()
    expected = logo.render_small_frame("ear", 2)
    assert text == expected


def test_set_state_rejects_unknown_animation() -> None:
    with pytest.raises(ValueError):
        logo.set_state("nonexistent", 0)
