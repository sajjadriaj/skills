"""Record a narrated terminal session as an asciinema cast.

Commands run in a real pty, so programs see a terminal and emit their true
colours, box drawing and progress output. The cast clock is ours, not the
wall clock, which is what keeps narration and picture locked together: each
scene occupies max(typing + runtime, narration) seconds, and the audio track
is padded to exactly that. Nothing drifts, however long a command takes.
"""

from __future__ import annotations

import fcntl
import json
import os
import pty
import select
import signal
import struct
import subprocess
import termios
import time
from dataclasses import dataclass
from pathlib import Path

from walkthrough.config import Scene, Walkthrough

IDLE_SECONDS = 0.4
FIRST_OUTPUT_SECONDS = 20.0
READ_CHUNK = 65_536


@dataclass
class _Event:
    at: float
    data: str


class CastWriter:
    """Accumulate asciinema v2 events against a clock we control."""

    def __init__(self, width: int, height: int, title: str) -> None:
        self._header = {
            "version": 2,
            "width": width,
            "height": height,
            "timestamp": int(time.time()),
            "title": title,
            "env": {"SHELL": "/bin/bash", "TERM": "xterm-256color"},
        }
        self._events: list[_Event] = []
        self.clock = 0.0
        self.last_output_at = 0.0

    def write(self, data: str, advance: float = 0.0) -> None:
        """Append output at the current clock, then optionally advance it."""
        if data:
            self._events.append(_Event(round(self.clock, 4), data))
            self.last_output_at = self.clock
        self.clock += advance

    def hold(self, seconds: float) -> None:
        """Leave the frame on screen."""
        self.clock += max(seconds, 0.0)

    def save(self, path: Path) -> float:
        """Write the cast file and return its total duration."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            handle.write(json.dumps(self._header) + "\n")
            for event in self._events:
                handle.write(json.dumps([event.at, "o", event.data]) + "\n")
        return self.clock


class PtySession:
    """A single long-lived pty that scenes type into, one command at a time."""

    def __init__(self, walkthrough: Walkthrough) -> None:
        self._walkthrough = walkthrough
        self._process: subprocess.Popen[bytes] | None = None
        self._master: int | None = None

    def start(self, command: str) -> None:
        """Launch a command attached to a correctly sized pty."""
        self.close()
        master, slave = pty.openpty()
        fcntl.ioctl(
            slave,
            termios.TIOCSWINSZ,
            struct.pack("HHHH", self._walkthrough.rows, self._walkthrough.cols, 0, 0),
        )
        # The recorder animates typing itself, so the tty must not also echo
        # what we send - otherwise every answer appears twice.
        attributes = termios.tcgetattr(slave)
        attributes[3] &= ~termios.ECHO
        termios.tcsetattr(slave, termios.TCSANOW, attributes)
        environment = {
            **os.environ,
            "TERM": "xterm-256color",
            "COLUMNS": str(self._walkthrough.cols),
            "LINES": str(self._walkthrough.rows),
            "FORCE_COLOR": "1",
            "PYTHONUNBUFFERED": "1",
            **self._walkthrough.env,
        }
        self._process = subprocess.Popen(  # noqa: S602 - the script author owns the command
            command,
            shell=True,
            stdin=slave,
            stdout=slave,
            stderr=slave,
            cwd=self._walkthrough.cwd,
            env=environment,
            start_new_session=True,
            close_fds=True,
        )
        os.close(slave)
        self._master = master

    def send(self, line: str) -> None:
        """Answer a prompt in the running program."""
        if self._master is None:
            raise RuntimeError("no running command to send input to")
        os.write(self._master, (line + "\n").encode())

    def echoes_itself(self) -> bool:
        """Whether the program has taken the tty out of line mode.

        Readline, prompt_toolkit and similar line editors switch canonical mode
        off and draw typed characters themselves. Typing into the cast as well
        would show every answer twice.
        """
        if self._master is None:
            return False
        try:
            return not termios.tcgetattr(self._master)[3] & termios.ICANON
        except termios.error:
            return False

    def drain(self, timeout: float = 120.0) -> tuple[str, float]:
        """Read until the program exits or stops producing output.

        Returns the captured bytes and how long the program actually took, so
        the caller can decide how much of the scene budget that consumed.
        """
        if self._master is None:
            return "", 0.0
        started = time.monotonic()
        chunks: list[str] = []
        last_output = time.monotonic()
        while True:
            if time.monotonic() - started > timeout:
                break
            # A slow-starting program (interpreter start-up, imports) has not
            # gone idle - it has not spoken yet. Treating that as "waiting for
            # input" types the next answer before the prompt is even drawn.
            grace = FIRST_OUTPUT_SECONDS if not chunks else IDLE_SECONDS
            ready, _, _ = select.select([self._master], [], [], 0.1)
            if ready:
                try:
                    data = os.read(self._master, READ_CHUNK)
                except OSError:
                    break
                if not data:
                    break
                chunks.append(data.decode("utf-8", errors="replace"))
                last_output = time.monotonic()
                continue
            finished = self._process is not None and self._process.poll() is not None
            if finished:
                # Collect anything still buffered in the pty after exit.
                try:
                    while data := os.read(self._master, READ_CHUNK):
                        chunks.append(data.decode("utf-8", errors="replace"))
                except OSError:
                    pass
                break
            if time.monotonic() - last_output > grace:
                break  # the program is waiting for input
        return "".join(chunks), time.monotonic() - started

    def running(self) -> bool:
        """Whether a program is still attached and alive."""
        return self._process is not None and self._process.poll() is None

    def close(self) -> None:
        """Terminate any running program and release the pty."""
        if self._process is not None and self._process.poll() is None:
            with_group = os.getpgid(self._process.pid)
            os.killpg(with_group, signal.SIGTERM)
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:  # pragma: no cover - stubborn child
                os.killpg(with_group, signal.SIGKILL)
        if self._master is not None:
            os.close(self._master)
        self._process = None
        self._master = None


def render_cast(
    walkthrough: Walkthrough, durations: list[float], cast_path: Path
) -> tuple[list[float], float]:
    """Play the whole script into a cast.

    `durations` is the narration length per scene. Returns each scene's video
    length - what the audio track must be padded to - and how long the final
    frame must be held. That trailing figure has to be passed to the renderer
    explicitly: a cast ends at its last *visible* change, so scenes that only
    narrate would otherwise be dropped from the finished video.
    """
    writer = CastWriter(walkthrough.cols, walkthrough.rows, walkthrough.title)
    session = PtySession(walkthrough)
    lengths: list[float] = []
    prompt = f"\r\n\x1b[1;33m{walkthrough.shell_prompt}\x1b[0m"
    try:
        for scene, narration in zip(walkthrough.scenes, durations, strict=True):
            start = writer.clock
            if scene.clear:
                writer.write("\x1b[2J\x1b[H", advance=0.2)
            _play_scene(
                writer,
                session,
                scene,
                prompt,
                walkthrough.typing_speed,
                walkthrough.max_typing_seconds,
            )
            spoken_end = start + narration
            # The scene lasts as long as the slower of picture and voice.
            writer.hold(max(spoken_end - writer.clock, 0.0) + scene.hold)
            lengths.append(writer.clock - start)
    finally:
        session.close()
    total = writer.save(cast_path)
    return lengths, total - writer.last_output_at


def _play_scene(
    writer: CastWriter,
    session: PtySession,
    scene: Scene,
    prompt: str,
    typing_speed: float,
    typing_budget: float,
) -> None:
    """Type and run one scene's action into the cast."""
    if scene.run is not None:
        writer.write(prompt, advance=0.25)
        _type(writer, scene.run, typing_speed, typing_budget)
        writer.write("\r\n", advance=0.1)
        session.start(scene.run)
        output, elapsed = session.drain()
        writer.write(output, advance=min(elapsed, 8.0))
    elif scene.send is not None:
        if not session.echoes_itself():
            shown = "•" * len(scene.send) if scene.secret else scene.send
            _type(writer, shown, typing_speed, typing_budget)
            # The pty's echo is off so typing can be animated, which also means
            # nothing echoes the Return. Without this the whole interview renders
            # as one run-on line.
            writer.write("\r\n", advance=0.1)
        session.send(scene.send)
        output, elapsed = session.drain()
        writer.write(output, advance=min(elapsed, 8.0))


def _type(writer: CastWriter, text: str, speed: float, budget: float) -> None:
    """Emit text a character at a time, fast enough to stay inside the budget.

    A long command typed at a human rate would eat the whole scene, leaving no
    time on screen for the output it produces.
    """
    if text and len(text) * speed > budget:
        speed = budget / len(text)
    for character in text:
        writer.write(character, advance=speed)
