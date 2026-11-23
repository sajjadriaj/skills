"""The scene script: one narration line plus the action that plays under it.

A walkthrough is a list of scenes. Every scene owns exactly one narration
line, and the recorder guarantees the scene lasts at least as long as that
line takes to speak. Sync is therefore structural, not something the author
has to hand-tune with sleeps.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any, Literal

import yaml

Kind = Literal["terminal", "web"]


@dataclass(frozen=True)
class Scene:
    """One narrated beat of the walkthrough."""

    say: str
    run: str | None = None
    send: str | None = None
    goto: str | None = None
    click: str | None = None
    fill: str | None = None
    select: str | None = None
    option: str | None = None
    press: str | None = None
    value: str | None = None
    highlight: str | None = None
    wait_for: str | None = None
    clear: bool = False
    #: Terminal only: the video shows `•` for each character of `send`.
    secret: bool = False
    hold: float = 0.8
    expect_seconds: float | None = None

    def __post_init__(self) -> None:
        if not self.say.strip():
            raise ValueError("every scene needs a narration line")
        if self.fill is not None and self.value is None:
            raise ValueError("a 'fill' scene needs a 'value'")
        if self.select is not None and self.option is None:
            raise ValueError("a 'select' scene needs an 'option'")


@dataclass(frozen=True)
class Walkthrough:
    """A complete script: what kind of app, how it looks, and the scenes."""

    kind: Kind
    title: str
    scenes: list[Scene]
    voice: str = "af_heart"
    speed: float = 1.0
    cwd: str | None = None
    env: dict[str, str] = field(default_factory=dict)
    shell_prompt: str = "$ "
    cols: int = 100
    rows: int = 32
    font_size: int = 18
    theme: str = "asciinema"
    typing_speed: float = 0.035
    max_typing_seconds: float = 2.5
    url: str | None = None
    viewport: tuple[int, int] = (1280, 800)
    #: Render the page at this multiple of the viewport, then record down to the
    #: viewport size. Headless Chromium rasterises text at 1x with full hinting,
    #: which squashes and roughens a webfont badly enough that viewers notice the
    #: type is wrong before they notice anything else. Rendering at 2 and letting
    #: the recorder downsample restores the glyph shapes the app actually ships,
    #: at the cost of a larger file. Pair it with `--font-render-hinting=none`.
    device_scale_factor: float = 1.0
    #: Extra Chromium switches. A walkthrough of a flow that reads the camera
    #: needs a fake capture device, and there is no other way to hand one to the
    #: browser the recorder launches.
    browser_args: list[str] = field(default_factory=list)
    #: Permissions granted up front, so a scene never waits on a prompt the
    #: recorder cannot answer — "camera", "geolocation", and the rest.
    permissions: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.kind not in ("terminal", "web"):
            raise ValueError(f"kind must be 'terminal' or 'web', not {self.kind!r}")
        if not self.scenes:
            raise ValueError("a walkthrough needs at least one scene")
        if self.kind == "web" and not self.url:
            raise ValueError("a web walkthrough needs a starting 'url'")


PLACEHOLDER = re.compile(r"\{\{\s*(env:([A-Za-z_][A-Za-z0-9_]*)|dir)\s*\}\}")


def _substitute(value: Any, script_dir: Path, missing: list[str]) -> Any:
    """Fill `{{env:NAME}}` from the environment and `{{dir}}` with the script's folder.

    Runs on parsed values, so a secret with YAML syntax in it (`#`, `"`) is
    taken literally. Secrets such as a demo account password stay out of the
    script file.
    """
    if isinstance(value, dict):
        return {key: _substitute(item, script_dir, missing) for key, item in value.items()}
    if isinstance(value, list):
        return [_substitute(item, script_dir, missing) for item in value]
    if not isinstance(value, str):
        return value

    def fill(match: re.Match[str]) -> str:
        if match.group(1) == "dir":
            return str(script_dir)
        name = match.group(2)
        if name not in os.environ:
            missing.append(name)
            return ""
        return os.environ[name]

    return PLACEHOLDER.sub(fill, value)


def _check_keys(data: dict[str, Any], allowed: type, where: str) -> None:
    unknown = set(data) - {item.name for item in fields(allowed)}
    if unknown:
        known = ", ".join(sorted(item.name for item in fields(allowed)))
        raise ValueError(f"unknown {where} key(s): {', '.join(sorted(unknown))}; known: {known}")


def load(path: str | Path) -> Walkthrough:
    """Read a YAML or JSON walkthrough script.

    A relative `cwd` resolves against the script's folder, so a script can
    live next to the project it drives.
    """
    source = Path(path).resolve()
    raw = source.read_text(encoding="utf-8")
    parsed = json.loads(raw) if source.suffix == ".json" else yaml.safe_load(raw)
    missing: list[str] = []
    data: dict[str, Any] = _substitute(parsed, source.parent, missing)
    if missing:
        # A take that types an empty password fails minutes in, far from the cause.
        raise ValueError(f"unset environment variable(s): {', '.join(sorted(set(missing)))}")
    scenes = []
    for index, scene in enumerate(data.pop("scenes", None) or []):
        _check_keys(scene, Scene, f"scene {index}")
        scenes.append(Scene(**scene))
    _check_keys(data, Walkthrough, "top-level")
    viewport = data.pop("viewport", None)
    if viewport is not None:
        data["viewport"] = (int(viewport[0]), int(viewport[1]))
    if data.get("cwd"):
        data["cwd"] = str((source.parent / data["cwd"]).resolve())
    return Walkthrough(scenes=scenes, **data)
