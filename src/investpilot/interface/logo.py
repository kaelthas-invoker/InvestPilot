from __future__ import annotations

MAIN = "#35C4E8"
LIGHT = "#A9E5F5"
DARK = "#0C3C5A"

FRAME_COUNT = 3
FRAME_WIDTH = 16
MAX_OFFSET = 20

HEAD_ART: list[str] = [
    "     ██          ██     ",
    "    ████        ████    ",
    "   █████▄▄▄▄▄▄▄▄█████   ",
    "   ██████████████████   ",
    "  ██▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀██  ",
    "  ██   ▓▓      ▓▓   ██  ",
    "  ██   ▓▓      ▓▓   ██  ",
    "  ██░░░░░░░▄▄░░░░░░░██  ",
    "  ██░░░░░░░▓▓░░░░░░░██  ",
    "   ██░░░░░▓▓▓▓░░░░░██   ",
    "   ██░░░░░▀  ▀░░░░░██   ",
    "    ▀██████████████▀    ",
    "      ▀▀▀▀▀▀▀▀▀▀▀▀      ",
]

RUN_FRAMES: list[list[str]] = [
    [
        " ██         ███ ",
        " ████▄▄▄▄▄▄▄  █ ",
        " █▓██████████▄  ",
        "████ ███████    ",
        "  █  █  █  █    ",
    ],
    [
        " ██         ███ ",
        " ████▄▄▄▄▄▄▄  █ ",
        " █▓██████████▄  ",
        "████ ▀█████▀    ",
        "  █     █       ",
    ],
    [
        " ██         ███ ",
        " ████▄▄▄▄▄▄▄  █ ",
        " █▓██████████▄  ",
        "██▀█ ███▀███    ",
        "     █     █    ",
    ],
]


def _colorize(line: str) -> str:
    """按字符染色：░浅蓝脸颊、▓深蓝眼鼻、其余主色。"""
    out: list[str] = []
    for ch in line:
        if ch == " ":
            out.append(" ")
        elif ch == "░":
            out.append(f"[{LIGHT}]█[/]")
        elif ch == "▓":
            out.append(f"[{DARK}]█[/]")
        else:
            out.append(f"[{MAIN}]{ch}[/]")
    return "".join(out)


def render_head_markup() -> str:
    """狗头多行 markup，可直接给 Static(markup=True)。"""
    return "\n".join(_colorize(line) for line in HEAD_ART)


def run_frame_text(frame_index: int, offset: int) -> str:
    """取一帧，左侧加 offset 空格；offset 超出 MAX_OFFSET 取模回绕。"""
    frame = RUN_FRAMES[frame_index % FRAME_COUNT]
    pad = " " * (offset % (MAX_OFFSET + 1))
    return "\n".join(pad + line for line in frame)
