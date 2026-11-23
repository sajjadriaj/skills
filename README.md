# skills

Skills for coding assistants that make their answers easy to follow, even in areas you don't know well. Works with Claude Code, Codex, pi and Cursor.

Each skill is a folder in `skills/` with a `SKILL.md` (agent-skills format).

## Skills

| Skill | What it does | Loads |
|---|---|---|
| `clear-response` | Plain-language gist first, severity-coded must-know items (🔴🟠🟡🟢🔵), ASCII diagrams, jargon explained inline, paths and risks for plans | always |
| `prove-it` | No "done", "fixed" or "works" without the command and its output | always |
| `orient` | One-page map of an unfamiliar area: gist, diagram with file paths, terms, landmines, where the change goes | on request |
| `debug-flow` | Reproduce, hypothesis tree, confirmed root cause with `file:line`, fix proven by a test that failed first | on bugs |
| `pr-review` | Plain brief, findings with failure scenarios, ship-risk checklist, verdict | on request |
| `pr-write` | PR title and body: why, what changed, ship risks, how tested, rollback | on request |
| `handoff` | Write, resume or audit a session handoff doc; `audit.py` catches stale refs, secrets, invented SHAs | on request / session start |
| `learn` | Per-domain notes of terms, traps and what you already know, so explanations skip it | on request |
| `product-test` | User story or codebase to step-by-step YAML product test specs, with edge cases | on request |
| `diagram` | Polished SVG diagrams with a fixed design system, light/dark, embedded fonts, layout lint | on request |

## Install

**Claude Code** (plugin: skills plus hooks for always-on skills and handoff reminders):

```
/plugin marketplace add sajjadriaj/skills
/plugin install assistant-skills@assistant-skills
```

**Codex, pi, Cursor** (clone, then run the installer):

```bash
git clone https://github.com/sajjadriaj/skills.git && cd skills
./install.sh --skip claude              # Codex + pi (skips hosts not installed)
./install.sh --skip claude --cursor ~/code/app   # also Cursor rules for one project
./install.sh --uninstall                # remove everything it added
```

| Host | Skills | Always-on skills |
|---|---|---|
| Claude Code (no plugin) | symlinks in `~/.claude/skills/` | `@import` in `~/.claude/CLAUDE.md` |
| Codex | symlinks in `~/.codex/skills/` | marked block in `~/.codex/AGENTS.md` |
| pi | symlinks in `~/.pi/agent/skills/` | marked block in `~/.pi/agent/AGENTS.md` |
| Cursor | `.cursor/rules/<skill>.mdc` per project | same, with `alwaysApply: true` |

Existing content in those files is kept, and re-running is safe. Codex, pi and Cursor get an inlined copy, so re-run `./install.sh` after editing a skill.

## Configure

- **Your strong areas:** list them under `Strong areas` in `skills/clear-response/SKILL.md` to skip jargon explanations there.
- **Always-on set:** `ALWAYS_ON` at the top of `install.sh`.
- **Folders:** handoffs go in `~/workspace/handoff/<project>/`, notes in `~/workspace/learn/` (change the first line of each skill; hooks read `ASSISTANT_SKILLS_HANDOFF_ROOT`).

## Test

```bash
tests/test_install.sh          # installer, in a sandbox $HOME
tests/test_handoff_audit.sh    # audit.py
tests/test_hooks.sh            # plugin hooks
evals/run.py [--host claude,codex,pi] [--case pr-review]   # every skill, pass/fail grid
```

Evals run each skill on a small fixture repo with planted bugs and check the reply and the files. Replies land in `evals/out/`. Set `PI_MODEL=provider/model` to choose pi's model.

## License

Fonts in `skills/diagram/fonts/` (Inter, JetBrains Mono) are under the SIL Open Font License.
