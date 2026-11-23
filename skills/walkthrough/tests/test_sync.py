"""The synchronisation contract: picture length must equal narration length.

Every bug this tool has had was a silent desync, so these tests cover the
timeline arithmetic rather than the rendering. They need no model, no agg and
no ffmpeg.
"""

from __future__ import annotations

import json
import wave
from pathlib import Path

import pytest

from walkthrough import config
from walkthrough.assemble import build_audio
from walkthrough.terminal import CastWriter, render_cast
from walkthrough.tts import SAMPLE_RATE, Clip


def _silent_wav(path: Path, seconds: float) -> Clip:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(SAMPLE_RATE)
        handle.writeframes(b"\x00\x00" * int(seconds * SAMPLE_RATE))
    return Clip(path=path, seconds=seconds, text="test")


def _plan(**overrides: object) -> config.Walkthrough:
    defaults: dict[str, object] = {
        "kind": "terminal",
        "title": "Test",
        "scenes": [config.Scene(say="one", run="printf hello")],
        "rows": 10,
        "cols": 40,
    }
    defaults.update(overrides)
    return config.Walkthrough(**defaults)  # type: ignore[arg-type]


def test_audio_is_padded_so_every_clip_starts_where_its_scene_starts(tmp_path: Path) -> None:
    clips = [
        _silent_wav(tmp_path / "a.wav", 1.0),
        _silent_wav(tmp_path / "b.wav", 2.0),
    ]
    lengths = [4.0, 3.0]

    total = build_audio(clips, lengths, tmp_path / "out.wav")

    assert total == pytest.approx(7.0)
    with wave.open(str(tmp_path / "out.wav"), "rb") as handle:
        rendered = handle.getnframes() / handle.getframerate()
    # The second clip must begin at 4.0s, which only holds if the first was
    # padded rather than butted up against it.
    assert rendered == pytest.approx(7.0, abs=0.01)


def test_a_scene_never_ends_before_its_narration(tmp_path: Path) -> None:
    plan = _plan(
        scenes=[
            config.Scene(say="a long line", run="printf hi", hold=0.0),
            config.Scene(say="another", hold=0.0),
        ]
    )
    durations = [6.0, 4.0]

    lengths, trailing = render_cast(plan, durations, tmp_path / "t.cast")

    assert len(lengths) == 2
    assert lengths[0] >= 6.0
    assert lengths[1] == pytest.approx(4.0, abs=0.01)
    assert trailing > 0.0


def test_the_cast_records_a_command_and_its_real_output(tmp_path: Path) -> None:
    cast = tmp_path / "t.cast"
    render_cast(_plan(scenes=[config.Scene(say="hi", run="printf marker-42")]), [1.0], cast)

    lines = cast.read_text(encoding="utf-8").splitlines()
    # Typing is one event per character, so the stream has to be rejoined.
    stream = "".join(json.loads(line)[2] for line in lines[1:])
    assert "printf marker-42" in stream  # the command was typed
    assert stream.rstrip().endswith("marker-42")  # and really ran


def test_trailing_hold_covers_the_gap_after_the_last_visible_output() -> None:
    writer = CastWriter(40, 10, "t")
    writer.write("visible", advance=1.0)
    writer.hold(9.0)

    # The renderer stops at the last visible change, so the 9s tail has to be
    # reported separately or narration-only scenes vanish from the video.
    assert writer.clock == pytest.approx(10.0)
    assert writer.last_output_at == pytest.approx(0.0)
    assert writer.clock - writer.last_output_at == pytest.approx(10.0)


def test_a_scene_without_narration_is_rejected() -> None:
    with pytest.raises(ValueError):
        config.Scene(say="   ")


def test_a_web_walkthrough_requires_a_starting_url() -> None:
    with pytest.raises(ValueError):
        config.Walkthrough(kind="web", title="t", scenes=[config.Scene(say="x")])


def test_an_answer_to_a_line_editor_is_not_typed_twice(tmp_path: Path) -> None:
    editor = (
        "python3 -c \"import sys,termios,tty; tty.setcbreak(0); print('ready', flush=True); "
        "line = sys.stdin.readline(); print('echo:' + line.strip(), flush=True)\""
    )
    cast = tmp_path / "t.cast"
    plan = _plan(scenes=[config.Scene(say="a", run=editor), config.Scene(say="b", send="zebra")])

    render_cast(plan, [0.5, 0.5], cast)

    lines = cast.read_text(encoding="utf-8").splitlines()
    stream = "".join(json.loads(line)[2] for line in lines[1:])
    assert stream.count("zebra") == 1
    assert "echo:zebra" in stream


def test_a_secret_answer_is_masked_in_the_cast(tmp_path: Path) -> None:
    program = "python3 -c \"print('pw?', flush=True); print('got:' + input()[::-1], flush=True)\""
    cast = tmp_path / "t.cast"
    plan = _plan(
        scenes=[
            config.Scene(say="a", run=program),
            config.Scene(say="b", send="hunter2", secret=True),
        ]
    )

    render_cast(plan, [0.5, 0.5], cast)

    lines = cast.read_text(encoding="utf-8").splitlines()
    stream = "".join(json.loads(line)[2] for line in lines[1:])
    assert "hunter2" not in stream
    assert "•••••••" in stream
    assert "got:2retnuh" in stream
