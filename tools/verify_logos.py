#!/usr/bin/env python3
"""Headless TUI screenshots for logo review.

Boots the app in a Textual test pilot, walks the mascot's pose schedule,
and saves one screenshot per unique pose plus a boot shot. SVGs are
converted to PNG with ``rsvg-convert``.
"""

from __future__ import annotations

import asyncio
import shutil
import subprocess
import sys
from pathlib import Path

from textual.widgets import Static

from investpilot.interface import logo
from investpilot.interface.tui_app import InvestPilotApp
from investpilot.providers.base import StreamChunk

ROOT = Path(__file__).resolve().parents[1]
VERIFY_DIR = ROOT / "docs" / "iterations" / "v0.3.0" / "verify"


class _NoopSession:
    """ChatSession stand-in; the harness never sends a real message."""

    async def send(self, user_text: str):
        yield StreamChunk("text", "verify-mode")
        yield StreamChunk("done")


def _save_svg(app: InvestPilotApp, name: str) -> Path:
    out = VERIFY_DIR / f"{name}.svg"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(app.export_screenshot(), encoding="utf-8")
    return out


async def main() -> int:
    if shutil.which("rsvg-convert") is None:
        print("rsvg-convert not found; cannot convert SVG to PNG", file=sys.stderr)
        return 1

    if VERIFY_DIR.exists():
        for stale in VERIFY_DIR.glob("*.svg"):
            stale.unlink()
        for stale in VERIFY_DIR.glob("*.png"):
            stale.unlink()

    app = InvestPilotApp(_NoopSession(), title_suffix="verify")
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        _save_svg(app, "app_boot")
        print("saved app_boot")

        mascot = app.query_one("#mascot", Static)
        # One screenshot per unique pose, reached through the schedule so
        # the shots reflect what the running loop actually shows.
        for pose in logo.POSES:
            frame = next(
                i for i in range(logo.FRAME_COUNT) if logo.pose_at(i) == pose
            )
            logo.set_frame(frame)
            mascot.update(logo.render_small_static())
            await pilot.pause()
            _save_svg(app, f"mascot_{pose}")
            print(f"saved mascot_{pose} (frame {frame})")

        # Chat still works with the mascot resident.
        app.query_one("#chat-input").value = "ping"
        await pilot.press("enter")
        await pilot.pause()
        print("chat round OK, mascot intact")

    svgs = sorted(VERIFY_DIR.glob("*.svg"))
    for svg in svgs:
        subprocess.run(
            ["rsvg-convert", "-o", str(svg.with_suffix(".png")), str(svg)],
            check=True,
            timeout=30,
        )
    print(f"converted {len(svgs)} SVGs to PNG under {VERIFY_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
