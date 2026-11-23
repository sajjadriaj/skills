# assistant-skills

Skills for coding assistants, installable across Claude Code, Codex, pi and Cursor.
Each skill is a folder under `skills/` with a `SKILL.md` (agent-skills format).

| Skill | What it does | Always on |
|---|---|---|
| `clear-response` | Plain-language gist first, severity-coded must-know items, ASCII diagrams, jargon explained inline, pathways/risks/divergence for plans | yes |
| `orient` | One-page map of an unfamiliar area before changing it: gist, diagram with file paths, glossary, landmines, where the change goes | no (on request / unfamiliar area) |
| `diagram` | Clean SVG diagrams (architecture, flow, sequence, state, decision paths, timeline) with a fixed design system, light/dark, fonts embedded + layout lint via `build.py` | no (on request) |
| `pr-review` | Review any PR/branch/diff: plain-language brief, verified findings with failure scenarios, ship-risk checklist, verdict | no (on request) |
| `pr-write` | PR title + description: why, behavior changes, ship risks, honest test notes, rollback | no (on request) |
| `handoff` | Write, update, audit, or resume from `~/workspace/handoff/<project>/handoff.md`; `audit.py` checks staleness, secrets, broken refs | no (on request / session start) |
| `prove-it` | No "done/fixed/works" without the command and its output in the same message | yes |
| `debug-flow` | Reproduce, hypothesis tree, test each branch, confirmed root cause, fix with a test that failed first | no (on bugs) |
| `learn` | Per-domain notes (`~/workspace/learn/<domain>.md`): terms, traps, what you know; teach mode | no (end of unfamiliar work / on request) |
| `product-test` | User story or codebase into step-by-step YAML product test specs (steps, expectations, edge cases); optional browser run | no (on request) |

## Install

**Claude Code (plugin, recommended):** skills + hooks (always-on skills at session start, handoff resume prompt, end-of-day handoff reminder).

```
/plugin marketplace add /path/to/assistant-skills
/plugin install assistant-skills@assistant-skills
```

Then run `./install.sh --skip claude` for the other hosts, so Claude Code doesn't load the skills twice.

**Everything via script:**

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
tests/test_install.sh         # installer against a sandbox $HOME
tests/test_handoff_audit.sh   # handoff audit.py against a seeded doc
evals/run.py                  # every skill on claude, codex, pi: pass/fail grid
evals/run.py --host codex --case pr-review
PI_MODEL=provider/model evals/run.py --host pi
```

Evals run each case's prompt with the skill loaded, in a temp dir seeded with a small fixture
(`evals/fixtures/shop`: a repo with planted bugs on `feature/coupons`), then check the reply and the
files. Replies land in `evals/out/`. Re-run after editing any skill.

Fonts in `skills/diagram/fonts/` (Inter, JetBrains Mono) are under the SIL Open Font License; see the OFL files there.
