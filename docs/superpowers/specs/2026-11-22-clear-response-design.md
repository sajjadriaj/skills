# clear-response skill — design

## Intent

When working in areas outside the user's expertise, coding assistants get too technical.
The user loses the gist or misses critical information buried in the detail.
`clear-response` makes every response (debugging, development, planning) readable at a
glance: plain-language gist first, critical items impossible to miss, diagrams for
concepts, and — for planning — the pathways, risks and future divergence points.

First skill in `assistant-skills`, a repo of skills installable across Claude Code,
Codex, Cursor, pi, and similar assistants.

## Goals

- Gist readable by a non-expert in 1-2 sentences, every response.
- Critical information (severity-coded) always surfaced at the top, never only in detail.
- Jargon explained inline on first use.
- Simple ASCII diagrams where a concept, flow or structure is easier seen than read.
- Planning responses show pathways, risks, and where paths diverge later.
- Renders correctly in terminal and IDE chat panels.
- Coexists with caveman (terse wording) — and works without it.

## Non-goals

- Raw ANSI color codes (not rendered reliably by any host's chat output).
- Per-tool output styles or features that only exist in one host.
- The other planned skills (debug-flow, plan-map, design-review, handoff) — later.

## Anti-goals

- Wordier responses that bury the signal in explanation (the cure becoming the disease).
- Decoration: emoji/diagrams/tables that carry no meaning.
- A critical item that appears only in the detail section.

## Response layout

```
GIST       1-2 plain sentences, no jargon
MUST-KNOW  🔴/🟠 items, plain words + consequence to the user ("users get logged out")
PICTURE    ascii diagram, when it helps
DETAIL     technical content; terms explained on first use: "idempotent (safe re-run)"
PATHS      planning only: branches, risks, divergence points
```

Sections are omitted when empty (a one-line answer stays one line). The gist and
must-know rules are never omitted when they have content.

### Severity palette

```
🔴 CRITICAL  data loss / security / prod down / irreversible
🟠 HIGH      breaks a feature, fix before ship
🟡 MEDIUM    risk, watch it
🟢 OK        verified / safe path
🔵 INFO      context worth knowing
```

Extra color sources used where they render: ```` ```diff ```` blocks (`+` green, `-` red)
and `> [!WARNING]`-style callouts (degrade to plain quotes elsewhere).

## Expertise handling

Default: always plain (gist + must-know + inline term meanings everywhere).
Optional: a short "strong areas" list in the skill config; inline term meanings are
dropped only for those areas. Gist and must-know stay on regardless.

## Caveman coexistence

- Caveman owns wording; clear-response owns structure and required content.
- Severity markers are functional, not decorative — allowed under caveman.
- Inline term meanings stay, compressed ("idempotent (safe re-run)").
- 🔴/🟠 items are written in full plain sentences (extends caveman's own auto-clarity rule).

## Approaches considered

1. **SKILL.md + always-on activation per host** — chosen. Rules live in one file;
   each host gets a small always-on hook. Portable and never skipped.
2. SKILL.md only — loads only when the model judges it relevant; misses cases, which is
   exactly the failure the user wants to avoid.
3. Claude Code output style — native and always on, but Claude Code only.

## Install / activation (per host)

| Host | Skill file | Always-on mechanism |
|---|---|---|
| Claude Code | `~/.claude/skills/clear-response/` | `@` import line in `~/.claude/CLAUDE.md` (same as RTK.md); simpler than a hook |
| Codex | Codex skills dir | marked block inlined into global `AGENTS.md` |
| pi | pi skills dir | marked block inlined into global `AGENTS.md` |
| Cursor | — | `.cursor/rules/clear-response.mdc` with `alwaysApply: true` (per project; Cursor global rules are UI-only) |

Installer: one shell script, idempotent, removes/replaces its own marked block, supports
`--uninstall`. Symlinks where possible so edits to the repo propagate.

## Repo layout

```
skills/clear-response/SKILL.md      rules (compact enough to inline into AGENTS.md)
skills/clear-response/examples.md   before/after samples: debug, dev, planning
install.sh
README.md
```

## Left to the builder

- Verify exact current skills/AGENTS.md paths for Codex and pi before writing the installer.
- Exact wording of SKILL.md; keep it short (it is loaded every session — token cost).
