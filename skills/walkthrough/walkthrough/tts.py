"""Narration via Kokoro, rendered to a wav per scene.

The whole design hangs on one fact: audio is synthesised *before* anything is
recorded, so the recorder knows exactly how long each scene must last. Never
substitute silence for a failed synthesis - a walkthrough with silent gaps is
worse than one that refuses to build.
"""

from __future__ import annotations

import os
import wave
from dataclasses import dataclass
from pathlib import Path
from urllib.request import urlopen

MODEL_RELEASE = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0"
MODEL_FILES = {
    "kokoro-v1.0.onnx": f"{MODEL_RELEASE}/kokoro-v1.0.onnx",
    "voices-v1.0.bin": f"{MODEL_RELEASE}/voices-v1.0.bin",
}
SAMPLE_RATE = 24_000


class NarrationError(RuntimeError):
    """Raised when narration cannot be produced; never swallowed into silence."""


def cache_dir() -> Path:
    """Where the Kokoro model files live."""
    return Path(os.environ.get("KOKORO_HOME", Path.home() / ".cache" / "kokoro-onnx"))


def ensure_models(download: bool = True) -> tuple[Path, Path]:
    """Return the model and voice paths, fetching them once if allowed."""
    directory = cache_dir()
    directory.mkdir(parents=True, exist_ok=True)
    for name, url in MODEL_FILES.items():
        target = directory / name
        if target.exists() and target.stat().st_size > 0:
            continue
        if not download:
            raise NarrationError(f"missing {target}; download it from {url}")
        with urlopen(url) as response, target.open("wb") as handle:  # noqa: S310
            while chunk := response.read(1 << 20):
                handle.write(chunk)
    return directory / "kokoro-v1.0.onnx", directory / "voices-v1.0.bin"


@dataclass(frozen=True)
class Clip:
    """One narration line rendered to disk."""

    path: Path
    seconds: float
    text: str


class Narrator:
    """Kokoro wrapper that renders one wav per line and reports its duration."""

    def __init__(self, voice: str = "af_heart", speed: float = 1.0) -> None:
        try:
            from kokoro_onnx import Kokoro
        except ImportError as error:  # pragma: no cover - environment problem
            raise NarrationError(
                "kokoro-onnx is not installed; run: pip install kokoro-onnx"
            ) from error
        model, voices = ensure_models()
        self._kokoro = Kokoro(str(model), str(voices))
        self._voice = voice
        self._speed = speed

    def voices(self) -> list[str]:
        """List every voice the loaded pack provides."""
        return sorted(self._kokoro.get_voices())

    def say(self, text: str, destination: Path) -> Clip:
        """Render one line to a 24 kHz mono wav and measure it."""
        samples, sample_rate = self._kokoro.create(
            text, voice=self._voice, speed=self._speed, lang="en-us"
        )
        if samples is None or len(samples) == 0:
            raise NarrationError(f"kokoro produced no audio for: {text!r}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        _write_wav(destination, samples, sample_rate)
        return Clip(path=destination, seconds=len(samples) / sample_rate, text=text)


def _write_wav(path: Path, samples: object, sample_rate: int) -> None:
    """Write float samples as 16-bit PCM without pulling in a heavy dependency."""
    import numpy as np

    array = np.asarray(samples, dtype="float32")
    peak = float(np.max(np.abs(array))) or 1.0
    pcm = (array / max(peak, 1.0) * 32767.0).astype("<i2")
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(pcm.tobytes())


def wav_seconds(path: Path) -> float:
    """Duration of a wav file, used when clips are reused from a cache."""
    with wave.open(str(path), "rb") as handle:
        return handle.getnframes() / float(handle.getframerate())
