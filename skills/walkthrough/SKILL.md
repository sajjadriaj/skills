---
name: walkthrough
description: Make a narrated walkthrough video (mp4) of a CLI or web app from a YAML script - Kokoro speaks each line, a real pty or a real Chromium performs the action, ffmpeg assembles, and the render refuses to emit a file where voice and picture drift. Use when the user asks for a demo video, walkthrough, narrated tour, screencast, product video or "record a demo" of a terminal tool or a website. Not for slides or static screenshots.
---

# walkthrough

A script is a list of scenes. Each scene has one narration line (`say`) and at most one action. All narration is synthesised first, so every line's length is known. Then the recorder gives each scene `max(action time, narration time) + hold`, and the audio is padded to match. Sync is structural: nobody tunes sleeps.

`<skill-dir>` = the folder containing this SKILL.md.

## Setup (once per machine)

```bash
uv tool install --reinstall '<skill-dir>[web]'           # puts `walkthrough` on PATH
"$(uv tool dir)/walkthrough-generator/bin/playwright" install chromium   # web only
```

Re-run the install after the skills update: the command runs a copy, not this folder. Also needed on PATH: `ffmpeg` and `ffprobe` (package manager), and `agg` for terminal videos (`cargo install --git https://github.com/asciinema/agg`). The Kokoro model (~340 MB) downloads on first render into `~/.cache/kokoro-onnx` (`KOKORO_HOME` overrides). `walkthrough --voices` lists voices. Check each tool exists before you write a long script; a missing one fails by name.

## Workflow

1. **Agree the story.** Who watches, what they must believe at the end, how long. Write the outline as parts of 3 to 10 scenes each and show it before you write scenes. Ask only if the audience or the goal is unclear and a wrong guess wastes a take.
2. **Use the real app first.** Terminal: run every command yourself and read the real output, so the narration describes what will actually print. Web: open each page, find stable selectors, and note which actions are slow (an agent run, a job, a cold start).
3. **Write the script** next to the project, as `walkthrough/<slug>.yaml` unless the user says otherwise. Copy the shape of `<skill-dir>/examples/terminal.yaml` or `<skill-dir>/examples/web.yaml`.
4. **Reset state** the take depends on (seed data, a fresh demo account, today's date in fixtures). A take that starts from yesterday's state records yesterday's mess.
5. **Rehearse.** Web: `walkthrough script.yaml --rehearse` plays every scene with no audio or video and lists each failing scene; `--from N` restarts at scene N. Fix every failure. Terminal: step 2 is the rehearsal.
6. **Render.** `walkthrough script.yaml -o ./out`. Narration is cached by text, voice and speed in `out/work/cache/`, so a re-render only synthesises lines you changed.
7. **Check the video, not only the exit code.** The last line must read `<file>.mp4  (<seconds>s, in sync)`. Then pull a frame from the start, the middle and the end, and look at each one:
   `ffmpeg -v error -ss <seconds> -i out/<slug>.mp4 -frames:v 1 /tmp/frame-<seconds>.png`
   Check the frame shows what that scene's line says. Report the path, the duration and what you looked at.

## Script reference

Top level: `kind` (`terminal` | `web`, required), `title` (required, names the file), `scenes` (required), `voice` (`af_heart`), `speed` (1.0), `cwd` (relative to the script), `env`, `typing_speed` (0.035 s/char), `max_typing_seconds` (2.5).
Terminal only: `cols` (100), `rows` (32), `font_size` (18), `theme` (`asciinema`), `shell_prompt` (`"$ "`).
Web only: `url` (required), `viewport` ([1280, 800]), `device_scale_factor` (use 2 with `browser_args: ["--font-render-hinting=none"]` for crisp webfonts), `browser_args`, `permissions` (e.g. `camera`).

Scene keys: `say` (required), `hold` (0.8 s after the narration ends), `clear` (terminal: wipe the screen first; web: empty the field before `fill`).
- Terminal: `run` (types and runs a command; ends the previous program), `send` (types an answer into the running program), `secret: true` (the video shows `•` for each character of `send`; the program gets the real text).
- Web, in the order they run: `goto`, `wait_for`, `highlight`, `fill` + `value`, `select` + `option` (visible label), `click`, `press` (a key such as `Enter`).

Placeholders, filled at load time inside quoted string values: `{{env:NAME}}` from the environment (unset is an error), `{{dir}}` the script's folder (for `"file://{{dir}}/cards.html"`). Quote them: unquoted `{{` is YAML syntax. Unknown keys are an error that names the scene.

## Narration rules

- Write for the ear. Spell out numbers and codes: "zero point eight", "D forty two". Kokoro reads digits literally and often wrong.
- One idea per scene. The scene is the unit of sync; a second idea in the same `say` cannot get its own frame.
- Say only what the frame shows. Never claim a number the app did not print.
- A scene that only talks holds the frame. Use it to explain output that is already on screen.
- Over a title card, say what the card does not; the viewer reads the card.

## Web selector rules

- `wait_for` runs before the scene's action. To wait for the page a click opens, put the `wait_for` on the next scene.
- Qualify selectors with `:visible`. Responsive layouts often render a hidden twin first in the DOM, and an unqualified selector waits on it forever.
- Never `wait_for` or `highlight` text a model or a random source generates. Wait on the stable UI around it and give the scene a fixed `hold`.
- Navigate with `goto` where you can. A click that hits the wrong element loses the whole take; a URL cannot.
- Slow backends: the scenes after a slow action must cover its run time, or the camera arrives before the result. `wait_for` allows up to five minutes.
- Record a production build. A dev server shows overlays and compiles routes on first visit, which leaves the narration over a blank page.
- The app cannot show a spreadsheet, a slide or a diagram. Put those in a local HTML file and `goto: file://{{dir}}/page.html`.

## Terminal notes

- Pick `rows` tall enough that the output you talk over fits on one screen.
- A program that waits for input is detected after 0.4 s of silence (20 s before its first output). A prompt that prints, pauses, then prints more can get an early answer; add a scene that only talks between them.
- `run` starts a new program and ends the one before. Use `send` for every answer to an interactive program.
- Line editors (readline, prompt_toolkit, the Python REPL) draw their own input, so a `send` to one appears at once rather than typed out.

## Safety

- Never record against production, real customer data or real accounts unless the user says so. Use a demo tenant and fabricated data.
- Secrets go in `{{env:NAME}}`, never in the script. Do not commit a script with a secret in it.
- A secret typed in a terminal scene needs `secret: true`, or it is spelled out in the video. A line editor that draws its own input shows it anyway; check the frame. In a web scene, type secrets only into `type=password` fields.
- A demo account created for a take is a real credential. Tell the user to delete it when the video is done.
- Never replace failed narration with silence. If synthesis fails, the render fails; fix the cause.
