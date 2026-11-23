# clear-response Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the `clear-response` skill plus a cross-host installer that makes it always-on in Claude Code, Codex, pi and Cursor.

**Architecture:** Skill rules live in `skills/clear-response/SKILL.md` (agent-skills format). `install.sh` symlinks every skill under `skills/` into each host's skills dir, and for skills listed in `ALWAYS_ON` adds an always-on hook: an `@` import in Claude Code's `CLAUDE.md`, an inlined marked block in Codex/pi global `AGENTS.md`, or a Cursor `.mdc` rule in a given project.

**Tech Stack:** Markdown, POSIX-ish bash (bash 4+), no dependencies.

**Spec:** `docs/superpowers/specs/2026-11-22-clear-response-design.md`

## Global Constraints

- No raw ANSI escape codes in skill output rules.
- Severity palette exactly: 🔴 CRITICAL, 🟠 HIGH, 🟡 MEDIUM, 🟢 OK, 🔵 INFO (meanings as in spec).
- Layout order exactly: GIST, MUST-KNOW, PICTURE, DETAIL, PATHS; empty sections omitted; gist + must-know never omitted when they have content.
- 🔴/🟠 items in full plain sentences, stating consequence to the user.
- Must coexist with caveman (caveman = wording, clear-response = structure) and work without it.
- `SKILL.md` body ≤ 80 lines (it is inlined into AGENTS.md and loaded every session).
- Installer idempotent, preserves all existing user content in files it touches, supports `--uninstall`.
- Host paths (verified on this machine 2026-11-22): Claude `~/.claude/skills`, `~/.claude/CLAUDE.md`; Codex `~/.codex/skills`, `~/.codex/AGENTS.md`; pi `~/.pi/agent/skills`, `~/.pi/agent/AGENTS.md`; Cursor `<project>/.cursor/rules/<skill>.mdc`.

## Review Focus

1. Existing `CLAUDE.md` / `AGENTS.md` with user content — install and uninstall must leave every other line byte-identical.
2. Running install twice — exactly one import line / one marked block, not two.
3. Host dir absent (e.g. no `~/.pi`) — skip that host with a message, do not create it, do not fail.
4. Target skill path already exists as a real directory (not our symlink) — leave it, warn, continue.
5. `$HOME` containing a space — all paths quoted.

Tests for all five are in Task 3.

---

### Task 1: Repo init

**Files:**
- Create: `.gitignore` (empty is fine)

- [ ] **Step 1:** `git init -b main` in `/home/sajjad/workspace/assistant-skills`.
- [ ] **Step 2: Commit** the spec and this plan.

```bash
git add docs .gitignore
git commit -m "docs: clear-response design and plan"
```

### Task 2: The skill

**Files:**
- Create: `skills/clear-response/SKILL.md`
- Create: `skills/clear-response/examples.md`

**Interfaces:**
- Produces: `SKILL.md` with YAML frontmatter `name: clear-response` and a `description` that triggers on any debugging, development, planning or explanation response. Body is self-contained (Task 3 inlines it into AGENTS.md with frontmatter stripped, so the body must not reference `examples.md` as required reading — "see examples.md for samples" is fine).

- [ ] **Step 1: Write `SKILL.md`.** Sections, in order: purpose (one paragraph: user may be outside their expertise; never let them miss the gist or a critical item); layout (the five sections, with the spec's layout block); severity palette (spec block verbatim); jargon rule (plain meaning in parentheses on first use; skip only for areas listed under "Strong areas"); diagram rules (ASCII/box-drawing in fenced blocks, ≤ 60 columns wide so it fits IDE panels, only when it shows structure/flow — no decorative diagrams); planning rules (PATHS shows branches, each branch's risk with severity marker, and divergence points: "if X later, this path forks to…"); extra color sources (`diff` blocks, `> [!WARNING]` callouts); caveman coexistence (spec section); a "Strong areas" stub section with a commented example line, empty by default.
- [ ] **Step 2: Write `examples.md`.** Three short before/after pairs: a debug answer, a dev answer, a planning answer (the planning one includes a PATHS tree with a divergence point). Each "after" must follow every rule in `SKILL.md`.
- [ ] **Step 3: Verify size.** Run: `awk '/^---$/{n++; next} n>=2' skills/clear-response/SKILL.md | wc -l` — Expected: ≤ 80.
- [ ] **Step 4: Behavioral check.** Run: `claude -p --append-system-prompt "$(cat skills/clear-response/SKILL.md)" "Plan migrating a small app's sessions from cookies to JWT"` — Expected: output starts with a plain gist, has a 🔴/🟠 must-know block with user-facing consequences, at least one diagram, a PATHS section with a divergence point, no ANSI codes. Repeat with a debug prompt ("my node server's memory grows until it crashes"). Adjust wording and re-run until both pass.
- [ ] **Step 5: Commit**

```bash
git add skills/clear-response
git commit -m "feat: add clear-response skill"
```

### Task 3: Installer

**Files:**
- Create: `install.sh` (executable)
- Create: `tests/test_install.sh` (executable)

**Interfaces:**
- Consumes: every `skills/<name>/SKILL.md`.
- Produces: `install.sh [--uninstall] [--cursor <project-dir>]`. Top of file: `ALWAYS_ON="clear-response"`. Marker strings: `<!-- assistant-skills:<name>:start -->` / `<!-- assistant-skills:<name>:end -->`. Claude import line: `@<repo-abs-path>/skills/<name>/SKILL.md`.

Behavior per host (skip host with `skip: <host> (not installed)` if its root dir — `~/.claude`, `~/.codex`, `~/.pi/agent` — is absent):
- Skills: symlink `skills/<name>` into host skills dir (create skills dir if host root exists). Existing real dir at target: print `warn:` and leave it.
- Claude always-on: append import line to `~/.claude/CLAUDE.md` if not already present (create file if missing).
- Codex / pi always-on: replace-or-append marked block containing `SKILL.md` body without frontmatter.
- `--cursor <dir>`: write `<dir>/.cursor/rules/<name>.mdc` with frontmatter `description: <skill description>`, `alwaysApply: true`, then the body.
- `--uninstall`: remove our symlinks (only if they point into this repo), the import line, the marked blocks, and (with `--cursor`) the `.mdc` files.

- [ ] **Step 1: Write the failing test.** `tests/test_install.sh` creates a sandbox `HOME="$(mktemp -d)/home with space"`, makes `.claude`, `.codex`, but NOT `.pi`, seeds `CLAUDE.md` and `.codex/AGENTS.md` with `# mine\nkeep this line`, pre-creates a real dir `.codex/skills/clear-response-other`. Runs `HOME=$sandbox ./install.sh` twice, then asserts:
  - `~/.claude/skills/clear-response` is a symlink to the repo skill dir
  - `grep -c '^@.*clear-response/SKILL.md$' ~/.claude/CLAUDE.md` == 1
  - `grep -c 'assistant-skills:clear-response:start' ~/.codex/AGENTS.md` == 1
  - `keep this line` still present in both files
  - `~/.pi` does not exist; installer output contains `skip: pi`
  - `HOME=$sandbox ./install.sh --cursor "$sandbox/proj"` creates `proj/.cursor/rules/clear-response.mdc` containing `alwaysApply: true`
  - after `--uninstall` (with `--cursor "$sandbox/proj"`): both files are byte-identical to their seeded content (`cmp`), symlinks gone, `.mdc` gone
  - Also a case where `~/.claude/skills/clear-response` is a pre-existing real dir: install prints `warn:` and the dir is untouched.
  Prints `PASS` at the end; exits non-zero on first failure.
- [ ] **Step 2: Run** `tests/test_install.sh` — Expected: FAIL (`install.sh` missing).
- [ ] **Step 3: Implement `install.sh`.** Block replace via `awk` skipping lines between markers; import-line removal via `grep -vxF`. Write edits to a temp file then `mv` (no partial writes). Repo path from `$(cd "$(dirname "$0")" && pwd)`.
- [ ] **Step 4: Run** `tests/test_install.sh` — Expected: `PASS`.
- [ ] **Step 5: Commit**

```bash
git add install.sh tests
git commit -m "feat: cross-host installer with always-on activation"
```

### Task 4: README + real install

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write `README.md`:** what the repo is, skill table (name, one line, always-on yes/no), install/uninstall commands, Cursor per-project note, "re-run install after editing a skill — Codex/pi copies are inlined, not linked", how to fill "Strong areas".
- [ ] **Step 2: Ask the user before running** `./install.sh` against the real `$HOME` (it edits `~/.claude/CLAUDE.md`). After approval, run it and confirm `~/.claude/CLAUDE.md` gained exactly one import line.
- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: README"
```
