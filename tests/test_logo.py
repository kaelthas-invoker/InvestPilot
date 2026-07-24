from investpilot.interface import logo


def test_head_art_shape() -> None:
    assert len(logo.HEAD_ART) == 13
    assert all(len(line) == 24 for line in logo.HEAD_ART)


def test_run_frames_shape() -> None:
    assert len(logo.RUN_FRAMES) == 3
    for frame in logo.RUN_FRAMES:
        assert len(frame) == 5
        assert all(len(line) == 16 for line in frame)


def test_render_head_markup_contains_color() -> None:
    text = logo.render_head_markup()
    assert "#35c4e8" in text.lower()
    assert "█" in text


def test_run_frame_text_offset_moves_content() -> None:
    a = logo.run_frame_text(0, 0)
    b = logo.run_frame_text(0, 5)
    assert a != b
    # 所有行等宽（左 padding 后总宽 = FRAME_WIDTH + offset）
    lines = b.splitlines()
    assert all(len(line) == 16 + 5 for line in lines)


def test_run_frame_text_wraps_offset() -> None:
    w0 = logo.run_frame_text(0, 0)
    wrapped = logo.run_frame_text(0, logo.MAX_OFFSET + 1)
    assert wrapped.splitlines() == w0.splitlines()
    assert wrapped == w0
