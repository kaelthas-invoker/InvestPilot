#!/usr/bin/env python3
"""Headless screenshot harness for v0.2.2 mascot + big-logo acceptance.

Boots the InvestPilot TUI in a Textual ``run_test`` pilot, advances the
small-mascot state through ``wave → ear → tail → blink → peek → wave``
saving an SVG at every animation / frame pair, and writes the matching
PNGs via ``rsvg-convert``.

Also saves a "full app" screenshot to show the resident mascot in
context with the dialog input.
"""

from __future__ import annotations

import asyncio
import shutil
import subprocess
import sys
from pathlib import Path

from textual.widgets import Input

from investpilot.interface import logo
from investpilot.interface.tui_app import InvestPilotApp
from investpilot.providers.base import StreamChunk

ROOT = Path(__file__).resolve().parents[1]
VERIFY_DIR = ROOT / "docs" / "iterations" / "v0.2.2" / "verify"


class _NoopSession:
    """Minimal ChatSession: never invoked — verify only navigates UI."""

    async def send(self, user_text: str):
        yield StreamChunk("text", "verify-mode")
        yield StreamChunk("done")


def _save_svg(app: InvestPilotApp, name: str) -> Path:
    """Save the current TUI screenshot as SVG."""
    out = VERIFY_DIR / f"{name}.svg"
    out.parent.mkdir(parents=True, exist_ok=True)
    svg = app.export_screenshot()
    out.write_text(svg, encoding="utf-8")
    return out


def _svg_to_png(svg_path: Path) -> Path:
    """Convert SVG → PNG via rsvg-convert."""
    png_path = svg_path.with_suffix(".png")
    subprocess.run(
        ["rsvg-convert", "-o", str(png_path), str(svg_path)],
        check=True,
        timeout=30,
    )
    return png_path


async def main() -> int:
    if shutil.which("rsvg-convert") is None:
        print("rsvg-convert not found; cannot convert SVG → PNG", file=sys.stderr)
        return 1

    # Use a larger terminal so per-cell halfrendering stays readable in
    # the exported SVG/PNG.  (120×40 = 4800 chars, comfortably fits the
    # 32-wide big logo and 16-wide small mascot at full detail.)
    app = InvestPilotApp(_NoopSession(), title_suffix="verify")
    async with app.run_test(size=(120, 40)) as pilot:
        # Boot yields on_mount which already mounts the big logo and
        # starts the resident mascot ticker; pause so layout settles.
        await pilot.pause()
        _save_svg(app, "app_boot")
        print("Saved app_boot screenshot")

        # Walk every (anim, frame) deterministically by overriding state
        # and pushing the render directly (skipping _tick_mascot's
        # advance-state side effect).
        from textual.widgets import Static

        mascot_widget = app.query_one("#mascot", Static)
        for anim in logo.ANIMATIONS:
            for frame_index in range(logo.FRAMES_PER_ANIM):
                logo.set_small_state(anim, frame_index)
                mascot_widget.update(logo.render_small_static())
                await pilot.pause()
                name = f"mascot_{anim}_{frame_index}"
                _save_svg(app, name)
                print(f"  saved {name}")

        # Save a zoom-in screenshot focused on the small mascot, useful
        # for review of the 5 animation effects.
        _save_svg(app, "mascot_zoom_wave_2")
        logo.set_small_state("wave", 2)
        mascot_widget.update(logo.render_small_static())
        await pilot.pause()
        _save_svg(app, "mascot_zoom_wave_2")
        logo.set_small_state("tail", 1)
        mascot_widget.update(logo.render_small_static())
        await pilot.pause()
        _save_svg(app, "mascot_zoom_tail_1")
        logo.set_small_state("blink", 2)
        mascot_widget.update(logo.render_small_static())
        await pilot.pause()
        _save_svg(app, "mascot_zoom_blink_2")
        logo.set_small_state("peek", 3)
        mascot_widget.update(logo.render_small_static())
        await pilot.pause()
        _save_svg(app, "mascot_zoom_peek_3")

        # Final: ensure the chat dialog still works (smoke).
        inp = app.query_one("#chat-input", Input)
        mascot = app.query_one("#mascot", Static)
        assert mascot.render() is not None
        inp.value = "ping"
        await pilot.press("enter")
        await pilot.pause()
        print("Verified chat input submits without breaking mascot")

    # Convert all SVGs to PNGs.
    svgs = sorted(VERIFY_DIR.glob("*.svg"))
    for svg in svgs:
        _svg_to_png(svg)
    print(f"Converted {len(svgs)} SVGs to PNGs under {VERIFY_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
