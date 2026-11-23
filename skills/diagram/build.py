#!/usr/bin/env python3
"""Finish an SVG diagram: embed fonts (subset to the glyphs used), then render PNG previews.

Usage: build.py diagram.svg [out_dir]

1. Embeds Inter (400/600) and JetBrains Mono (400) as base64 woff2 @font-face rules,
   subset to only the characters in the diagram (a few KB). Re-running replaces the
   previous embed. Needs fontTools + brotli (pip install fonttools brotli); without
   them the SVG keeps system-font fallbacks and a warning is printed.
2. Renders <name>.light.png and <name>.dark.png at 2x with Playwright (Chromium,
   honors the dark-mode media query), else light only with cairosvg.
Exit 2 if no renderer is available: the SVG is still valid, just unchecked.
"""
import base64
import io
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

FONTS = Path(__file__).resolve().parent / "fonts"
FACES = [  # (css family, weight, file)
    ("DgSans", 400, "inter-latin-400-normal.woff2"),
    ("DgSans", 600, "inter-latin-600-normal.woff2"),
    ("DgMono", 400, "jetbrains-mono-latin-400-normal.woff2"),
]
START, END = "/* dg-fonts:start */", "/* dg-fonts:end */"

# Measures real rendered text: text must sit inside its node with >= 12px side padding,
# texts must not overlap each other, edges must not pass through a node they don't start/end at.
LINT_JS = """() => {
  const out = [], pad = 12;
  const nodes = [...document.querySelectorAll('rect.node')].filter(r => r.getBBox().width > 24).map(r => r.getBBox());
  const texts = [...document.querySelectorAll('text')];
  const inside = (p, b) => p.x >= b.x && p.x <= b.x + b.width && p.y >= b.y && p.y <= b.y + b.height;
  const boxes = texts.map(t => [t, t.getBBox()]);
  for (const [t, b] of boxes) {
    const n = nodes.find(n => inside({x: b.x + 1, y: b.y + b.height / 2}, n));
    if (n && (b.x < n.x + pad - 0.5 || b.x + b.width > n.x + n.width - pad + 0.5))
      out.push(`"${t.textContent}" overflows its node (needs ${Math.ceil(b.x + b.width + pad - n.x - n.width)}px more width)`);
  }
  for (let i = 0; i < boxes.length; i++) for (let j = i + 1; j < boxes.length; j++) {
    const [a, A] = boxes[i], [c, C] = boxes[j];
    if (A.x < C.x + C.width && C.x < A.x + A.width && A.y < C.y + C.height && C.y < A.y + A.height)
      out.push(`"${a.textContent}" overlaps "${c.textContent}"`);
  }
  for (const e of document.querySelectorAll('path.edge')) {
    const L = e.getTotalLength(), s = e.getPointAtLength(0), f = e.getPointAtLength(L);
    for (const n of nodes) {
      if (inside(s, {x: n.x - 2, y: n.y - 2, width: n.width + 4, height: n.height + 4}) ||
          inside(f, {x: n.x - 10, y: n.y - 10, width: n.width + 20, height: n.height + 20})) continue;
      for (let d = 0; d <= L; d += 4)
        if (inside(e.getPointAtLength(d), n)) { out.push(`edge "${e.getAttribute('d')}" crosses a node at (${n.x},${n.y})`); break; }
    }
  }
  return out;
}"""


def used_chars(svg_text: str) -> str:
    root = ET.fromstring(svg_text)
    chars = set()
    for el in root.iter():
        if el.tag.split("}")[-1] in ("text", "tspan", "textPath"):
            chars.update("".join(el.itertext()))
    return "".join(sorted(chars)) or " "


def subset_woff2(path: Path, text: str) -> str:
    from fontTools import subset
    from fontTools.ttLib import TTFont
    font = TTFont(str(path))
    opts = subset.Options()
    opts.flavor = "woff2"
    opts.layout_features = ["kern", "liga", "calt", "tnum"]
    sub = subset.Subsetter(opts)
    sub.populate(text=text)
    sub.subset(font)
    buf = io.BytesIO()
    font.flavor = "woff2"
    font.save(buf)
    return base64.b64encode(buf.getvalue()).decode()


def embed_fonts(svg: Path) -> None:
    s = svg.read_text()
    s = re.sub(re.escape(START) + r".*?" + re.escape(END) + r"\n?", "", s, flags=re.S)
    try:
        text = used_chars(s)
        rules = "".join(
            f"@font-face{{font-family:{fam};font-weight:{w};"
            f"src:url(data:font/woff2;base64,{subset_woff2(FONTS / f, text)}) format('woff2')}}\n"
            for fam, w, f in FACES)
    except ImportError as e:
        print(f"warn: fonts not embedded ({e}); pip install fonttools brotli")
        svg.write_text(s)
        return
    if "<style>" not in s:
        raise SystemExit("error: SVG has no <style> block; copy it from template.svg")
    s = s.replace("<style>", f"<style>\n{START}\n{rules}{END}", 1)
    svg.write_text(s)


def render(svg: Path, out: Path) -> int:
    root = ET.parse(svg).getroot()  # fails loudly on malformed XML
    w, h = int(float(root.get("width", 800))), int(float(root.get("height", 600)))
    stem = out / svg.stem
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch()
            for scheme in ("light", "dark"):
                page = browser.new_page(viewport={"width": w, "height": h},
                                        device_scale_factor=2, color_scheme=scheme)
                page.goto(svg.as_uri())
                page.wait_for_timeout(100)  # let embedded fonts decode
                if scheme == "light":
                    for problem in page.evaluate(LINT_JS):
                        print(f"lint: {problem}")
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
        print("UNCHECKED: layout lint needs Chromium (Playwright). Tell the user overlaps/overflow were not checked,"
              " or ask them to run build.py outside the sandbox.")
        return 0
    except ImportError:
        print(f"no renderer (pip install playwright && playwright install chromium); last error: {err}")
        return 2


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    svg = Path(sys.argv[1]).resolve()
    out = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else svg.parent
    out.mkdir(parents=True, exist_ok=True)
    embed_fonts(svg)
    print(f"{svg}  ({svg.stat().st_size // 1024} KB)")
    return render(svg, out)


if __name__ == "__main__":
    sys.exit(main())
