from __future__ import annotations

import hashlib
import json

import pytest

from investpilot.interface import _logo_assets, logo

# The boot big logo is pin-locked: the user signed off on this exact artwork.
# Any geometry edit that changes it must update this digest deliberately.
BIG_LOGO_SHA256 = "f8367d21be1d5dcbc7ccb490e2ef031ab4abaf44c1cdddb8bc045ebeeb216dac"


def _grid_digest(grid: object) -> str:
    return hashlib.sha256(json.dumps(grid, sort_keys=True).encode()).hexdigest()


def _cell_delta(a: tuple[tuple[int, ...], ...], b: tuple[tuple[int, ...], ...]) -> int:
    """Count cells that differ between two same-shaped grids."""
    return sum(1 for ra, rb in zip(a, b) for x, y in zip(ra, rb) if x != y)


# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------


def test_palette_length() -> None:
    assert len(logo.PALETTE) == 6


def test_palette_index_zero_is_transparent() -> None:
    assert logo.PALETTE[0] is None
    assert all(c is not None for c in logo.PALETTE[1:])


# ---------------------------------------------------------------------------
# Big boot logo — pin-locked
# ---------------------------------------------------------------------------


def test_big_logo_geometry_unchanged() -> None:
    """Guards the signed-off boot artwork against accidental drift."""
    assert _grid_digest(_logo_assets.HEAD) == BIG_LOGO_SHA256


def test_big_logo_cell_geometry() -> None:
    grid = _logo_assets.HEAD
    assert len(grid) == logo.HEAD_CELLS_H * 2 == 18
    assert all(len(row) == logo.HEAD_CELLS_W == 16 for row in grid)


# ---------------------------------------------------------------------------
# Mascot poses
# ---------------------------------------------------------------------------


def test_mascot_longest_side_within_cap() -> None:
    """User constraint: the small logo may shrink below the old 12-cell cap."""
    assert max(logo.SMALL_CELLS_W, logo.SMALL_CELLS_H) <= 9
    assert logo.SMALL_CELLS_H == 5


def test_pose_grid_shapes() -> None:
    assert set(logo.POSES) == set(_logo_assets.SMALL_POSES)
    for name, grid in _logo_assets.SMALL_POSES.items():
        assert len(grid) == logo.SMALL_CELLS_H * 2, name
        assert all(len(row) == logo.SMALL_CELLS_W for row in grid), name


def test_grids_only_use_palette_indices() -> None:
    size = len(logo.PALETTE)
    grids = [_logo_assets.HEAD, *_logo_assets.SMALL_POSES.values()]
    for grid in grids:
        for row in grid:
            assert all(0 <= v < size for v in row)


def test_every_pose_is_distinct() -> None:
    """Five poses, five different bitmaps — no accidental duplicates."""
    seen = {name: _grid_digest(grid) for name, grid in _logo_assets.SMALL_POSES.items()}
    assert len(set(seen.values())) == len(seen), f"duplicate poses: {seen}"


def test_mascot_cheek_highlights_are_refined() -> None:
    """The small logo keeps cheek highlights compact, not face-dominant."""
    for name, grid in _logo_assets.SMALL_POSES.items():
        lower_face_light = sum(v == 3 for row in grid[7:11] for v in row)
        assert lower_face_light <= 4, name


def test_mascot_face_is_symmetric_on_idle_and_blink() -> None:
    """Odd-width mascot face rows must not drift left or right."""
    for name in ("idle", "blink1", "blink2"):
        grid = _logo_assets.SMALL_POSES[name]
        for row_idx, row in enumerate(grid):
            assert row == list(reversed(row)), f"{name} row {row_idx}: {row}"


def test_mascot_face_footprint_stays_small() -> None:
    """The shrunken mascot face keeps visible side and lower breathing room."""
    idle = _logo_assets.SMALL_POSES["idle"]
    assert idle[8] == [0, 0, 0, 1, 1, 1, 0, 0, 0]
    for row_idx in (3, 8):
        row = idle[row_idx]
        assert row[0] == row[-1] == 0, row_idx


def test_mascot_open_eyes_are_single_cell() -> None:
    """Open eyes should be crisp one-cell dots at the smaller size."""
    idle = _logo_assets.SMALL_POSES["idle"]
    assert [(row_idx, col_idx) for row_idx, row in enumerate(idle) for col_idx, v in enumerate(row) if v == 5] == [
        (5, 2),
        (5, 6),
        *[(9, col_idx) for col_idx in range(logo.SMALL_CELLS_W)],
    ]


def test_mascot_blink_uses_vertical_two_cell_eyes() -> None:
    """The final blink is a vertical two-cell mark per eye."""
    blink = _logo_assets.SMALL_POSES["blink2"]
    eye_cells = [
        (row_idx, col_idx)
        for row_idx, row in enumerate(blink)
        for col_idx, value in enumerate(row)
        if value == 5 and row_idx != 9
    ]
    assert eye_cells == [(6, 2), (6, 6), (7, 2), (7, 6)]


def test_mascot_blink_lids_do_not_touch_nose() -> None:
    """Blink eyes stay on their own row, separated from the centre nose."""
    for name in ("blink1", "blink2"):
        grid = _logo_assets.SMALL_POSES[name]
        nose_cells = [
            (row_idx, col_idx)
            for row_idx, row in enumerate(grid)
            for col_idx, value in enumerate(row)
            if value == 4
        ]
        assert nose_cells == [(7, 4)], name
        assert grid[6][4] != 5, name
        assert grid[7][4] != 5, name


# ---------------------------------------------------------------------------
# Animation visibility — the reason this iteration exists
# ---------------------------------------------------------------------------


def test_ear_wobble_is_visible() -> None:
    """Ear tilt must change enough cells to read at the smaller mascot size."""
    idle = _logo_assets.SMALL_POSES["idle"]
    assert _cell_delta(idle, _logo_assets.SMALL_POSES["ear1"]) >= 6
    assert _cell_delta(idle, _logo_assets.SMALL_POSES["ear2"]) >= 8


def test_blink_is_visible() -> None:
    """Closed eyes must change enough cells to read at the smaller mascot size.

    Earlier revisions used a lid the same width as the open eye, which
    flipped too few cells and was invisible in the terminal.
    """
    blink = _logo_assets.SMALL_POSES["blink2"]
    assert blink[6][2] == blink[7][2] == 5
    assert blink[6][6] == blink[7][6] == 5


def test_ear_wobble_keeps_eyes_open() -> None:
    """The two motions are alternating, not simultaneous."""
    for pose in ("ear1", "ear2"):
        spec_eyes = _cell_delta(
            _logo_assets.SMALL_POSES[pose], _logo_assets.SMALL_POSES["blink2"]
        )
        assert spec_eyes > 0, pose


# ---------------------------------------------------------------------------
# Schedule
# ---------------------------------------------------------------------------


def test_schedule_names_are_all_known_poses() -> None:
    assert set(logo.SCHEDULE) <= set(logo.POSES)


def test_schedule_covers_both_motions() -> None:
    assert {"ear1", "ear2"} <= set(logo.SCHEDULE), "ear wobble missing"
    assert {"blink1", "blink2"} <= set(logo.SCHEDULE), "blink missing"


def test_blink_is_occasional_not_constant() -> None:
    """User picked 偶尔眨（自然）: most of the loop holds eyes open."""
    closed = sum(1 for p in logo.SCHEDULE if p in ("blink1", "blink2"))
    assert closed / logo.FRAME_COUNT <= 0.2, "blinking too often"


def test_loop_is_long_enough_to_feel_natural() -> None:
    """At 0.10 s/frame the loop should run at least ~2 s."""
    from investpilot.interface.tui_app import InvestPilotApp

    loop_seconds = logo.FRAME_COUNT * InvestPilotApp.MASCOT_INTERVAL_SECONDS
    assert loop_seconds >= 2.0


def test_pose_at_wraps_around_the_loop() -> None:
    assert logo.pose_at(0) == logo.pose_at(logo.FRAME_COUNT)
    assert logo.pose_at(3) == logo.pose_at(logo.FRAME_COUNT + 3)


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def test_render_big_head_uses_halfblock_and_palette() -> None:
    text = logo.render_big_head()
    assert any(ch in text for ch in ("▀", "▄", "█"))
    lowered = text.lower()
    assert any(c.lower() in lowered for c in logo.PALETTE if c is not None)


def test_render_big_head_line_count() -> None:
    assert len(logo.render_big_head().split("\n")) == logo.HEAD_CELLS_H == 9


def test_render_small_frame_line_count() -> None:
    text = logo.render_small_frame(0)
    assert len(text.split("\n")) == logo.SMALL_CELLS_H


def test_render_pose_rejects_unknown_name() -> None:
    with pytest.raises(ValueError):
        logo.render_pose("nope")


def test_rendered_frames_change_across_the_loop() -> None:
    """Walking the schedule must yield more than one distinct rendering."""
    rendered = {logo.render_small_frame(i) for i in range(logo.FRAME_COUNT)}
    assert len(rendered) == len(set(logo.SCHEDULE))


# ---------------------------------------------------------------------------
# Frame cursor
# ---------------------------------------------------------------------------


def test_advance_frame_walks_the_whole_loop_then_repeats() -> None:
    logo.set_frame(0)
    walked = []
    for _ in range(logo.FRAME_COUNT):
        walked.append(logo.get_frame())
        logo.advance_frame()
    assert walked == list(range(logo.FRAME_COUNT))
    assert logo.get_frame() == 0, "cursor should wrap back to the start"


def test_render_small_static_follows_the_cursor() -> None:
    logo.set_frame(21)  # a blink frame
    assert logo.pose_at(21) == "blink2"
    assert logo.render_small_static() == logo.render_pose("blink2")


def test_set_frame_wraps_out_of_range_input() -> None:
    logo.set_frame(logo.FRAME_COUNT + 5)
    assert logo.get_frame() == 5
