"""Record a narrated browser walkthrough with Playwright.

Same contract as the terminal recorder: every scene lasts at least as long as
its narration, and the per-scene lengths come back so the audio track can be
padded to match.
"""

from __future__ import annotations

import time
from pathlib import Path

from walkthrough.config import Scene, Walkthrough

CURSOR_SCRIPT = """
(() => {
  const dot = document.createElement('div');
  dot.id = '__wt_cursor';
  dot.style.cssText = `position:fixed;z-index:2147483647;width:18px;height:18px;
    margin:-9px 0 0 -9px;border-radius:50%;background:rgba(201,138,43,.85);
    box-shadow:0 0 0 4px rgba(201,138,43,.25);pointer-events:none;
    transition:left .45s ease,top .45s ease;left:-50px;top:-50px`;
  document.body.appendChild(dot);
  window.__wtMove = (x, y) => { dot.style.left = x + 'px'; dot.style.top = y + 'px'; };
})();
"""

HIGHLIGHT_STYLE = (
    "outline:3px solid rgba(201,138,43,.9);outline-offset:3px;transition:outline-color .3s ease"
)


def record(
    walkthrough: Walkthrough, durations: list[float], video_dir: Path
) -> tuple[Path, list[float]]:
    """Drive the browser through the script; return the raw video and lengths."""
    from playwright.sync_api import sync_playwright

    video_dir.mkdir(parents=True, exist_ok=True)
    width, height = walkthrough.viewport
    lengths: list[float] = []
    with sync_playwright() as playwright:
        browser = _launch(playwright, walkthrough)
        context = browser.new_context(
            viewport={"width": width, "height": height},
            # Rendered at the scale factor, recorded back down to the viewport:
            # the downsample is what makes webfont text look like the app rather
            # than like a screenshot of the app.
            device_scale_factor=walkthrough.device_scale_factor,
            record_video_dir=str(video_dir),
            record_video_size={"width": width, "height": height},
            **({"permissions": list(walkthrough.permissions)} if walkthrough.permissions else {}),
        )
        page = context.new_page()
        # Playwright starts recording the moment the page exists, so the first
        # navigation and the cursor injection are already in the video. Charge
        # that prelude to scene one, or the picture is longer than the sum of
        # the scenes and every line lands early.
        opened = time.monotonic()
        page.goto(walkthrough.url or "about:blank", wait_until="domcontentloaded")
        page.add_init_script(CURSOR_SCRIPT)
        page.evaluate(CURSOR_SCRIPT)
        for index, (scene, narration) in enumerate(zip(walkthrough.scenes, durations, strict=True)):
            started = opened if index == 0 else time.monotonic()
            _play(page, scene, walkthrough.typing_speed)
            spent = time.monotonic() - started
            remaining = max(narration - spent, 0.0) + scene.hold
            page.wait_for_timeout(int(remaining * 1000))
            lengths.append(spent + remaining)
        video = page.video
        path = Path(video.path()) if video is not None else Path()
        context.close()
        browser.close()
    return path, lengths


def _launch(playwright: object, walkthrough: Walkthrough) -> object:
    """Start Chromium, turning a missing browser into a one-line fix."""
    from playwright.sync_api import Error, Playwright

    assert isinstance(playwright, Playwright)
    try:
        return playwright.chromium.launch(args=list(walkthrough.browser_args))
    except Error as error:
        if "Executable doesn't exist" not in str(error):
            raise
        raise RuntimeError(
            "Chromium is not installed; run: "
            '"$(uv tool dir)/walkthrough-generator/bin/playwright" install chromium'
        ) from None


def _play(page: object, scene: Scene, typing_speed: float) -> None:
    """Perform one scene's browser action."""
    from playwright.sync_api import Page

    assert isinstance(page, Page)
    if scene.goto:
        page.goto(scene.goto, wait_until="domcontentloaded")
        page.evaluate(CURSOR_SCRIPT)
    if scene.wait_for:
        # A live agent run can take minutes to reach the state a scene is
        # waiting on. A wait that is already satisfied costs nothing, so the
        # ceiling is generous rather than tight — five minutes, because a cold
        # provider connection on a just-restarted app answered a first turn in
        # over two, and a take that dies there has already spent ten minutes.
        page.wait_for_selector(scene.wait_for, timeout=300_000)
    if scene.highlight:
        _point_at(page, scene.highlight)
        page.eval_on_selector(
            scene.highlight, f"element => element.style.cssText += ';{HIGHLIGHT_STYLE}'"
        )
        page.eval_on_selector(
            scene.highlight, "element => element.scrollIntoView({block:'center'})"
        )
    if scene.fill and scene.value is not None:
        _point_at(page, scene.fill)
        page.click(scene.fill)
        # `clear` empties the field first, so a scene can retype a value the
        # page already carries — a rename types over the old name instead of
        # appending to it.
        if scene.clear:
            page.fill(scene.fill, "")
        page.type(scene.fill, scene.value, delay=typing_speed * 1000)
    if scene.select and scene.option is not None:
        _point_at(page, scene.select)
        page.select_option(scene.select, label=scene.option)
    if scene.click:
        _point_at(page, scene.click)
        page.click(scene.click)
    if scene.press:
        page.keyboard.press(scene.press)


def _point_at(page: object, selector: str) -> None:
    """Move the synthetic cursor so the viewer's eye follows the action."""
    from playwright.sync_api import Page

    assert isinstance(page, Page)
    box = page.locator(selector).first.bounding_box()
    if box is None:
        return
    x = box["x"] + box["width"] / 2
    y = box["y"] + box["height"] / 2
    page.evaluate("([x, y]) => window.__wtMove && window.__wtMove(x, y)", [x, y])
    page.wait_for_timeout(500)


WORDS_PER_SECOND = 2.6


def rehearse(walkthrough: Walkthrough, start: int = 0) -> int:
    """Play every scene in a headless browser with no audio or video.

    Each scene waits roughly as long as its narration will take (estimated from
    the word count), so a scene that waits on a slow backend gets the time it
    will get in the real take. Returns 1 if any scene failed.
    """
    from playwright.sync_api import sync_playwright

    if walkthrough.kind != "web":
        raise ValueError("--rehearse is for web walkthroughs")
    width, height = walkthrough.viewport
    failures: list[tuple[int, str]] = []
    with sync_playwright() as playwright:
        browser = _launch(playwright, walkthrough)
        context = browser.new_context(
            viewport={"width": width, "height": height},
            **({"permissions": list(walkthrough.permissions)} if walkthrough.permissions else {}),
        )
        page = context.new_page()
        page.goto(walkthrough.url or "about:blank", wait_until="domcontentloaded")
        page.add_init_script(CURSOR_SCRIPT)
        page.evaluate(CURSOR_SCRIPT)
        for index, scene in enumerate(walkthrough.scenes):
            if index < start:
                continue
            began = time.monotonic()
            try:
                _play(page, scene, walkthrough.typing_speed)
                status = "ok  "
            except Exception as error:  # every failure is reported, then the run goes on
                message = str(error).splitlines()[0][:120]
                failures.append((index, message))
                status = "FAIL"
            spent = time.monotonic() - began
            print(f"{index:3d} {status} {spent:5.1f}s  {scene.say[:60]}", flush=True)
            narration = len(scene.say.split()) / WORDS_PER_SECOND
            page.wait_for_timeout(int((max(narration - spent, 0.0) + scene.hold) * 1000))
        page.screenshot(path="rehearse-last.png")
        context.close()
        browser.close()
    print(f"\n{len(failures)} failure(s); last frame in rehearse-last.png")
    for index, message in failures:
        print(f"  scene {index}: {message}")
    return 1 if failures else 0
