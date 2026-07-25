#!/usr/bin/env python3
"""Capture TUI screenshots for each small-logo size variant.

This is a **review-only** harness used while the user picks which
small-logo size to adopt.  It boots the InvestPilot TUI, swaps in the
chosen variant into the ``#mascot`` slot for each size, captures an
SVG, and converts to PNG via ``rsvg-convert``.
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
VERIFY_DIR = ROOT / "docs" / "iterations" / "v0.2.3" / "verify-variants"


class _NoopSession:
    """Minimal ChatSession stub: never invoked."""

    async def send(self, user_text: str):
        yield StreamChunk("text", "verify-variants")
        yield StreamChunk("done")


def _save_svg(app: InvestPilotApp, name: str) -> Path:
    """Save the current TUI screenshot as SVG."""
    out = VERIFY_DIR / f"{name}.svg"
    out.parent.mkdir(parents=True, exist_ok=True)
    svg = app.export_screenshot()
    out.write_text(svg, encoding="utf-8")
    return out


def _svg_to_png(svg_path: Path) -> Path:
    png_path = svg_path.with_suffix(".png")
    subprocess.run(
        ["rsvg-convert", "-o", str(png_path), str(svg_path)],
        check=True, timeout=30,
    )
    return png_path


async def main() -> int:
    if shutil.which("rsvg-convert") is None:
        print("rsvg-convert not found; cannot convert SVG → PNG", file=sys.stderr)
        return 1

    sizes = list(logo.VARIANT_SIZES.keys())  # 12x7, 10x6, 8x5

    app = InvestPilotApp(_NoopSession(), title_suffix="variant-review")
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        # Quick boot screenshot with the default 16×9 mascot for reference.
        _save_svg(app, "00_default_16x9")

        mascot_widget = app.query_one("#mascot", Static)
        for size_label in sizes:
            # Replace the mascot content with the variant render.
            mascot_widget.update(logo.render_variant(size_label))
            await pilot.pause()
            _save_svg(app, f"variant_{size_label}")
            print(f"  saved variant_{size_label}")

    svgs = sorted(VERIFY_DIR.glob("*.svg"))
    for svg in svgs:
        _svg_to_png(svg)
    print(f"Converted {len(svgs)} SVGs to PNGs under {VERIFY_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
