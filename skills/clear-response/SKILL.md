---
name: clear-response
description: Structure every debugging, development, planning or explanation response so a non-expert gets the gist and never misses critical information - plain-language gist first, severity-coded must-know items, ASCII diagrams, jargon explained inline, and pathways/risks/divergence for plans. Always on.
---

# clear-response

The user may be outside their expertise. Your job: they always get the gist and never miss a critical item, even if they read only the top of your reply.

## Layout (in this order; omit empty sections; a one-line answer stays one line)

```
GIST       1-2 plain sentences, no jargon. Readable alone.
MUST-KNOW  🔴/🟠 items: plain words + consequence to the user
PICTURE    ascii diagram, only when structure/flow is easier seen
DETAIL     technical content, terms explained on first use
PATHS      planning only: branches, risks, divergence points
```

- Gist and must-know are never skipped when they have content.
- A 🔴/🟠 item never appears only in DETAIL. Surface it in MUST-KNOW too.
- Use short bold labels (`**Gist:**`, `**Must know:**`) rather than big headers.

## Severity

```
🔴 CRITICAL  data loss / security / prod down / irreversible
🟠 HIGH      breaks a feature, fix before ship
🟡 MEDIUM    risk, watch it
🟢 OK        verified / safe path
🔵 INFO      context worth knowing
```

- Markers carry meaning; never use them as decoration.
- 🔴/🟠 items: full plain sentences, no fragments. State what happens to the user or their product ("users get logged out mid-checkout"), then the technical cause.
- No raw ANSI color codes. Extra color where hosts render it: ```` ```diff ```` blocks (`+` green, `-` red) for before/after; `> [!WARNING]` callouts for a single critical note.

## Jargon

- First use of a term gets a plain meaning in parentheses: "idempotent (safe to run twice)". After that, the bare term is fine.
- Acronyms: expand once: "CORS (browser rule blocking cross-site calls)".
- Skip meanings only for areas listed under Strong areas below.

## Diagrams

- ASCII / box-drawing in fenced code blocks, ≤ 60 columns wide (fits IDE panels).
- Draw when it shows structure, flow, sequence, or where something breaks. Mark the failure point: `◄── fails here`.
- Keep to what matters; 3-8 boxes. No decorative diagrams.

## Planning (PATHS)

Show the routes, not just the recommendation:

```
 now ─┬─► A: quick fix ──► debt grows ─► ◆ traffic 10x? ─► rewrite
      │   🟡 1 day                         (divergence)
      └─► B: proper fix ─► stable ─────► ◆ traffic 10x? ─► holds
          🟢 1 week
```

- `◆` marks a divergence point. Keep emoji off aligned diagram lines when possible (they are double-width and skew columns).

- Each branch: what it costs, its biggest risk with a severity marker.
- Divergence points: "if X happens later, this path forks to Y". Name the trigger.
- End with your pick and one-line why.

## Debugging

- Gist = what is broken and the likely cause, in plain words.
- Picture = the flow with the failure point marked.
- Separate confirmed (🟢 verified) from guessed (🟡 suspected).

## Working with terse styles (e.g. caveman)

Terse style owns wording; this skill owns structure and required content. Keep the layout, markers and inline meanings (compressed: "idempotent (safe re-run)"). 🔴/🟠 items stay full sentences.

## Strong areas

Areas listed here are user expertise: skip inline term meanings there (gist and must-know stay).
<!-- e.g. - React, TypeScript, Python -->

See examples.md (same folder) for before/after samples.
