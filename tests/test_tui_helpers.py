from __future__ import annotations

from investpilot.interface.tui_app import (
    format_assistant_prefix,
    format_user_line,
    is_quit_command,
)


def test_quit_commands() -> None:
    assert is_quit_command("/quit")
    assert is_quit_command("/exit")
    assert is_quit_command("  /QUIT  ")
    assert not is_quit_command("hello")
    assert not is_quit_command("/help")


def test_format_lines() -> None:
    assert "你" in format_user_line("hi")
    assert "hi" in format_user_line("hi")
    assert format_assistant_prefix()
