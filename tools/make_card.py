#!/usr/bin/env python3
"""Render a launch card from an HTML file to PNG at 2x.

    python tools/make_card.py docs/method-card.html docs/method-card.png

The cards are made by a script, not by hand, so the next one looks like the
last one and every number on them comes from the same place.
"""
import asyncio
import sys
from pathlib import Path

from playwright.async_api import async_playwright


async def main(src: Path, out: Path, width: int) -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": width, "height": 900},
                                      device_scale_factor=2)
        await page.goto(src.resolve().as_uri(), wait_until="networkidle")
        await page.wait_for_timeout(400)
        el = await page.query_selector("#card")
        await (el or page).screenshot(path=str(out))
        await browser.close()
    print(f"{out} written")


if __name__ == "__main__":
    src = Path(sys.argv[1])
    out = Path(sys.argv[2])
    width = int(sys.argv[3]) if len(sys.argv) > 3 else 1200
    asyncio.run(main(src, out, width))
