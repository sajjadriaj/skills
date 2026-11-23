#!/usr/bin/env python3
"""Render an SVG diagram to PNG (light + dark) so the author can look at it.

Usage: render.py diagram.svg [out_dir]
Writes <name>.light.png and <name>.dark.png (dark only with Playwright).
Tries Playwright (Chromium, honors the dark-mode media query), then cairosvg (light only).
Exit 2 if no renderer is available; the SVG is still valid, just unchecked.
"""
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    svg = Path(sys.argv[1]).resolve()
    out = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else svg.parent
    out.mkdir(parents=True, exist_ok=True)
    root = ET.parse(svg).getroot()  # fails loudly on malformed XML
    w = int(float(root.get("width", 800)))
    h = int(float(root.get("height", 600)))
    stem = out / svg.stem

    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch()
            for scheme in ("light", "dark"):
                page = browser.new_page(viewport={"width": w, "height": h},
                                        device_scale_factor=2, color_scheme=scheme)
                page.goto(svg.as_uri())
                page.screenshot(path=f"{stem}.{scheme}.png")
                page.close()
            browser.close()
        print(f"{stem}.light.png\n{stem}.dark.png")
        return 0
    except Exception as e:  # missing module or missing browser binary
        err = e

    try:
        import cairosvg
        cairosvg.svg2png(url=str(svg), write_to=f"{stem}.light.png", scale=2)
        print(f"{stem}.light.png  (cairosvg: light only; playwright failed: {err})")
        return 0
    except ImportError:
        pass

    print(f"no renderer (pip install playwright && playwright install chromium); last error: {err}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
