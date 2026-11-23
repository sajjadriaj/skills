"""Turn a cast (or a browser recording) plus narration clips into one mp4.

The audio track is built by padding every narration clip out to the length of
the scene it belongs to. That is the whole synchronisation mechanism: the
video decides the timing, the audio is stretched to match, and no clip can
slide out of position because each one is anchored by the clips before it.
"""

from __future__ import annotations

import shutil
import subprocess
import wave
from pathlib import Path

from walkthrough.tts import SAMPLE_RATE, Clip


class ToolMissingError(RuntimeError):
    """Raised when an external renderer is not on PATH."""


def require(*binaries: str) -> None:
    """Fail early and by name rather than deep inside a pipeline."""
    missing = [binary for binary in binaries if shutil.which(binary) is None]
    if missing:
        raise ToolMissingError(f"missing required tool(s): {', '.join(missing)}")


def _run(command: list[str]) -> None:
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        tail = (result.stderr or result.stdout).strip().splitlines()[-8:]
        raise RuntimeError(f"{command[0]} failed:\n" + "\n".join(tail))


def build_audio(clips: list[Clip], scene_lengths: list[float], destination: Path) -> float:
    """Concatenate narration, padding each clip to its scene's length."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(destination), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(SAMPLE_RATE)
        for clip, length in zip(clips, scene_lengths, strict=True):
            with wave.open(str(clip.path), "rb") as source:
                frames = source.readframes(source.getnframes())
            output.writeframes(frames)
            silence = int(max(length - clip.seconds, 0.0) * SAMPLE_RATE)
            output.writeframes(b"\x00\x00" * silence)
        return sum(scene_lengths)


def cast_to_video(
    cast: Path,
    destination: Path,
    *,
    font_size: int = 18,
    theme: str = "asciinema",
    last_frame_duration: float = 3.0,
) -> Path:
    """Render an asciinema cast to a gif with agg."""
    require("agg")
    _run(
        [
            "agg",
            "--font-size",
            str(font_size),
            "--theme",
            theme,
            "--fps-cap",
            "30",
            # agg compresses gaps over 5s and pads 3s onto the last frame by
            # default. Both silently shift the picture out from under the
            # narration, so neither is allowed here.
            "--idle-time-limit",
            "86400",
            # A zero here is special-cased by agg into "reuse the previous
            # frame's duration", which silently doubles the tail.
            "--last-frame-duration",
            f"{max(last_frame_duration, 0.04):.3f}",
            str(cast),
            str(destination),
        ]
    )
    return destination


def mux(video: Path, audio: Path, destination: Path, *, loop_still: bool = False) -> Path:
    """Combine picture and narration into a shareable mp4."""
    require("ffmpeg")
    destination.parent.mkdir(parents=True, exist_ok=True)
    command = ["ffmpeg", "-y"]
    if loop_still:
        command += ["-loop", "1"]
    command += [
        "-i",
        str(video),
        "-i",
        str(audio),
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "20",
        "-pix_fmt",
        "yuv420p",
        # Even dimensions are required by yuv420p; agg can emit odd ones.
        "-vf",
        "pad=ceil(iw/2)*2:ceil(ih/2)*2",
        "-c:a",
        "aac",
        "-b:a",
        "160k",
        "-shortest",
        "-movflags",
        "+faststart",
        str(destination),
    ]
    _run(command)
    return destination


def duration(media: Path) -> float:
    """Read a media file's duration with ffprobe."""
    require("ffprobe")
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(media),
        ],
        capture_output=True,
        text=True,
    )
    return float(result.stdout.strip() or 0.0)


class SyncError(RuntimeError):
    """Raised when the finished video and its narration disagree on length."""


def assert_in_sync(video: Path, scripted_seconds: float, tolerance: float = 1.0) -> float:
    """Fail loudly when picture and voice have drifted apart.

    Every silent-desync bug this tool can have shows up as a mismatch here, so
    it is checked on every render rather than left to the viewer to notice.
    """
    actual = duration(video)
    drift = abs(actual - scripted_seconds)
    if drift > tolerance:
        raise SyncError(
            f"{video.name} is {actual:.1f}s but the script is {scripted_seconds:.1f}s "
            f"({drift:.1f}s of drift); narration and picture would not line up"
        )
    return actual
