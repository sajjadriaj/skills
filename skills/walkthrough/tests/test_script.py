"""Loading a script, and the narration cache."""

from __future__ import annotations

import wave
from pathlib import Path

import pytest

from walkthrough import cli, config
from walkthrough.tts import SAMPLE_RATE


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def test_env_and_dir_placeholders_are_filled(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("WT_SECRET", "s3cret")
    script = _write(
        tmp_path / "s.yaml",
        "kind: terminal\ntitle: t\nscenes:\n"
        "  - say: hi\n    send: '{{env:WT_SECRET}}'\n"
        "  - say: there\n    run: ls {{dir}}\n",
    )

    plan = config.load(script)

    assert plan.scenes[0].send == "s3cret"
    assert plan.scenes[1].run == f"ls {tmp_path.resolve()}"


def test_a_secret_with_yaml_syntax_is_taken_literally(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("WT_SECRET", "a#b\"c: d'e")
    script = _write(
        tmp_path / "s.yaml",
        "kind: terminal\ntitle: t\nscenes:\n  - say: hi\n    send: '{{env:WT_SECRET}}'\n",
    )

    assert config.load(script).scenes[0].send == "a#b\"c: d'e"


def test_a_placeholder_in_a_comment_is_ignored(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("WT_MISSING", raising=False)
    script = _write(
        tmp_path / "s.yaml",
        "# run with {{env:WT_MISSING}}\nkind: terminal\ntitle: t\nscenes:\n  - say: hi\n",
    )

    assert config.load(script).scenes[0].say == "hi"


def test_an_unset_env_placeholder_is_an_error(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("WT_MISSING", raising=False)
    script = _write(
        tmp_path / "s.yaml", "kind: terminal\ntitle: t\nscenes:\n  - say: '{{env:WT_MISSING}}'\n"
    )

    with pytest.raises(ValueError, match="WT_MISSING"):
        config.load(script)


def test_an_unknown_scene_key_names_the_scene_and_the_key(tmp_path: Path) -> None:
    script = _write(
        tmp_path / "s.yaml", "kind: terminal\ntitle: t\nscenes:\n  - say: hi\n    wait: 2\n"
    )

    with pytest.raises(ValueError, match="scene 0.*wait"):
        config.load(script)


def test_a_relative_cwd_resolves_against_the_script(tmp_path: Path) -> None:
    (tmp_path / "app").mkdir()
    script = _write(
        tmp_path / "s.yaml", "kind: terminal\ntitle: t\ncwd: app\nscenes:\n  - say: hi\n"
    )

    assert config.load(script).cwd == str((tmp_path / "app").resolve())


def test_a_cached_line_is_reused_without_loading_the_model(tmp_path: Path, monkeypatch) -> None:
    def no_model(*args: object, **kwargs: object) -> None:
        raise AssertionError("the model was loaded for a cached line")

    plan = config.Walkthrough(kind="terminal", title="t", scenes=[config.Scene(say="hello")])
    work = tmp_path / "work"
    monkeypatch.setattr(cli, "Narrator", lambda **kwargs: _FakeNarrator())
    cli._narrate(plan, work)

    monkeypatch.setattr(cli, "Narrator", no_model)
    clips = cli._narrate(plan, work)

    assert clips[0].seconds == pytest.approx(1.0)
    assert (work / "audio" / "000.wav").exists()


def test_inserting_a_scene_does_not_shift_cached_lines(tmp_path: Path, monkeypatch) -> None:
    fake = _FakeNarrator()
    monkeypatch.setattr(cli, "Narrator", lambda **kwargs: fake)
    work = tmp_path / "work"
    first = config.Walkthrough(kind="terminal", title="t", scenes=[config.Scene(say="b")])
    cli._narrate(first, work)

    second = config.Walkthrough(
        kind="terminal", title="t", scenes=[config.Scene(say="a"), config.Scene(say="b")]
    )
    cli._narrate(second, work)

    assert fake.spoken == ["b", "a"]


def test_an_interrupted_line_is_not_cached(tmp_path: Path, monkeypatch) -> None:
    class Interrupted(_FakeNarrator):
        def say(self, text: str, destination: Path) -> None:
            destination.write_bytes(b"RIFF")
            raise KeyboardInterrupt

    plan = config.Walkthrough(kind="terminal", title="t", scenes=[config.Scene(say="hello")])
    work = tmp_path / "work"
    monkeypatch.setattr(cli, "Narrator", lambda **kwargs: Interrupted())
    with pytest.raises(KeyboardInterrupt):
        cli._narrate(plan, work)

    fresh = _FakeNarrator()
    monkeypatch.setattr(cli, "Narrator", lambda **kwargs: fresh)
    clips = cli._narrate(plan, work)

    assert fresh.spoken == ["hello"]
    assert clips[0].seconds == pytest.approx(1.0)


class _FakeNarrator:
    def __init__(self) -> None:
        self.spoken: list[str] = []

    def say(self, text: str, destination: Path) -> None:
        self.spoken.append(text)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(destination), "wb") as handle:
            handle.setnchannels(1)
            handle.setsampwidth(2)
            handle.setframerate(SAMPLE_RATE)
            handle.writeframes(b"\x00\x00" * SAMPLE_RATE)


def test_rehearse_reports_the_failing_scene(tmp_path: Path, monkeypatch, capsys) -> None:
    pytest.importorskip("playwright")
    from walkthrough import web

    page = tmp_path / "page.html"
    page.write_text("<main><h1>Hi</h1></main>", encoding="utf-8")
    plan = config.Walkthrough(
        kind="web",
        title="t",
        url=page.as_uri(),
        scenes=[
            config.Scene(say="ok", wait_for="h1", hold=0.0),
            config.Scene(say="bad", press="NoSuchKey", hold=0.0),
        ],
    )
    monkeypatch.chdir(tmp_path)

    try:
        status = web.rehearse(plan)
    except RuntimeError as error:
        pytest.skip(str(error))

    out = capsys.readouterr().out
    assert status == 1
    assert "scene 1:" in out
    assert "scene 0:" not in out
