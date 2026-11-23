# assistant-skills

Skills for coding assistants, installable across Claude Code, Codex, pi and Cursor.
Each skill is a folder under `skills/` with a `SKILL.md` (agent-skills format).

| Skill | What it does | Always on |
|---|---|---|
| `clear-response` | Plain-language gist first, severity-coded must-know items, ASCII diagrams, jargon explained inline, pathways/risks/divergence for plans | yes |
| `orient` | One-page map of an unfamiliar area before changing it: gist, diagram with file paths, glossary, landmines, where the change goes | no (on request / unfamiliar area) |
| `handoff` | Write, update, or resume from `~/workspace/handoff/<project>/handoff.md` with a fixed structure and verified facts | no (on request / session start) |

## Install

```bash
./install.sh                          # Claude Code, Codex, pi (skips hosts not installed)
./install.sh --cursor ~/code/myapp    # also add Cursor rules to one project
./install.sh --uninstall [--cursor ~/code/myapp]
```

What it does per host:

| Host | Skill files | Always-on |
|---|---|---|
| Claude Code | symlink in `~/.claude/skills/` | `@…/SKILL.md` import line in `~/.claude/CLAUDE.md` |
| Codex | symlink in `~/.codex/skills/` | marked block in `~/.codex/AGENTS.md` |
| pi | symlink in `~/.pi/agent/skills/` | marked block in `~/.pi/agent/AGENTS.md` |
| Cursor | — | `.cursor/rules/<skill>.mdc` with `alwaysApply: true`, per project (Cursor's global rules are UI-only) |

Your existing content in those files is preserved; install is safe to re-run.

**After editing a skill, re-run `./install.sh`.** Claude Code reads the symlinked file
directly, but Codex/pi/Cursor get an inlined copy.

Which skills are always-on is set by `ALWAYS_ON` at the top of `install.sh`.

## Tuning clear-response

List your areas of expertise under **Strong areas** in
`skills/clear-response/SKILL.md`. Jargon explanations are skipped there; the gist and
must-know sections stay on everywhere.

## Tests

```bash
tests/test_install.sh   # runs the installer against a sandbox $HOME
```
