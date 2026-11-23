"""`walkthrough render script.yaml` - narrate, record, and mux in one pass."""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
from pathlib import Path

from walkthrough import assemble, config
from walkthrough.tts import Clip, NarrationError, Narrator, wav_seconds


def _narrate(plan: config.Walkthrough, work: Path) -> list[Clip]:
    """Render every narration line first; durations drive everything downstream.

    Clips are cached by line, voice and speed, so editing or inserting a scene
    re-synthesises only the lines that changed. A clip is renamed into the
    cache only once complete, so an interrupted run never leaves a short one.
    `audio/NNN.wav` is a per-scene copy, kept so scene timings can be rebuilt
    from the files later.
    """
    narrator: Narrator | None = None
    clips: list[Clip] = []
    cache = work / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    for index, scene in enumerate(plan.scenes):
        key = hashlib.sha256(f"{plan.voice}|{plan.speed}|{scene.say}".encode()).hexdigest()[:16]
        cached = cache / f"{key}.wav"
        if not cached.exists():
            if narrator is None:
                narrator = Narrator(voice=plan.voice, speed=plan.speed)
            print(f"  narrating {index + 1}/{len(plan.scenes)}", file=sys.stderr)
            partial = cached.with_suffix(".part")
            narrator.say(scene.say, partial)
            partial.replace(cached)
        destination = work / "audio" / f"{index:03d}.wav"
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(cached, destination)
        clips.append(Clip(destination, wav_seconds(destination), scene.say))
    return clips


def render(script: Path, output: Path) -> Path:
    """Build one walkthrough video from a script file."""
    plan = config.load(script)
    work = output / "work"
    work.mkdir(parents=True, exist_ok=True)

    print(f"narration: {len(plan.scenes)} scenes", file=sys.stderr)
    clips = _narrate(plan, work)
    durations = [clip.seconds for clip in clips]

    if plan.kind == "terminal":
        from walkthrough import terminal

        print("recording terminal session", file=sys.stderr)
        cast = output / f"{_slug(plan.title)}.cast"
        lengths, trailing = terminal.render_cast(plan, durations, cast)
        print("rendering cast to video", file=sys.stderr)
        picture = assemble.cast_to_video(
            cast,
            work / "video.gif",
            font_size=plan.font_size,
            theme=plan.theme,
            last_frame_duration=trailing,
        )
    else:
        from walkthrough import web

        print("recording browser session", file=sys.stderr)
        picture, lengths = web.record(plan, durations, work / "video")

    print("building audio track", file=sys.stderr)
    audio = assemble.build_audio(clips, lengths, work / "narration.wav")
    final = output / f"{_slug(plan.title)}.mp4"
    print("muxing", file=sys.stderr)
    assemble.mux(picture, work / "narration.wav", final)

    actual = assemble.assert_in_sync(final, audio)
    print(f"\n{final}  ({actual:.1f}s, in sync)", file=sys.stderr)
    return final


def _slug(title: str) -> str:
    keep = [character.lower() if character.isalnum() else "-" for character in title]
    return "".join(keep).strip("-").replace("--", "-") or "walkthrough"


def main(argv: list[str] | None = None) -> int:
    """Entry point for the `walkthrough` command."""
    parser = argparse.ArgumentParser(
        prog="walkthrough", description="Generate a narrated walkthrough video."
    )
    parser.add_argument("script", nargs="?", help="YAML or JSON walkthrough script")
    parser.add_argument("-o", "--output", default="./out", help="output directory")
    parser.add_argument(
        "--rehearse",
        action="store_true",
        help="web only: play every scene in a browser, no audio or video, report failures",
    )
    parser.add_argument(
        "--from", dest="start", type=int, default=0, help="with --rehearse: first scene index"
    )
    parser.add_argument(
        "--voices", action="store_true", help="list available Kokoro voices and exit"
    )
    arguments = parser.parse_args(argv)

    if arguments.voices:
        print("\n".join(Narrator().voices()))
        return 0
    if arguments.script is None:
        parser.error("a script is required")
    try:
        if arguments.rehearse:
            from walkthrough import web

            return web.rehearse(config.load(arguments.script), arguments.start)
        render(Path(arguments.script), Path(arguments.output))
    except (
        NarrationError,
        assemble.SyncError,
        assemble.ToolMissingError,
        RuntimeError,
        ValueError,
    ) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
