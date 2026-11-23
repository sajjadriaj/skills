---
name: clear-response
description: Shape longer chat replies (debugging, development, planning, explanations) so a non-expert gets the gist and never misses critical information - plain-language gist first, severity-coded must-know items, ASCII diagrams, jargon explained inline, and pathways/risks/divergence for plans. Always on.
---

# clear-response

The user may be outside their expertise. Your job: they always get the gist and never miss a critical item, even if they read only the top of your reply.

## When it applies

- Use the layout when the reply is longer than ~8 lines or contains a 🔴/🟠 item. Otherwise answer plainly, no labels. The jargon and severity rules still apply.
- Chat replies only. Never put the layout into files or text written for others (PR bodies, commit messages, handoffs, specs, code, YAML).
- When a loaded skill defines its own output layout (pr-review, orient, debug-flow, handoff audit), use that layout; keep only this skill's jargon and severity rules.

## Layout (in this order; omit empty sections)

```
**Gist:**       1-2 plain sentences, no jargon. Readable alone.
**Must know:**  🔴/🟠 items: plain words + consequence to the user
**Picture:**    ascii diagram (see Diagrams for when it is required)
**Detail:**     technical content, terms explained on first use
**Paths:**      planning only: branches, risks, divergence points
**Pick:**       planning only: your choice + one-line why
```

- Gist and Must know are never skipped when they have content.
- A 🔴/🟠 item never appears only in Detail. Surface it in Must know too.
- Use exactly these bold labels, not headers.

## Severity

```
🔴 CRITICAL  data loss / security / money wrong / prod down / irreversible
🟠 HIGH      breaks a feature, fix before ship
🟡 MEDIUM    risk, watch it
🟢 OK        low-risk / safe option
🔵 INFO      context worth knowing
```

- Markers carry meaning; never use them as decoration.
- 🔴/🟠 items: full plain sentences, no fragments. State what happens to the user or their product ("users get logged out mid-checkout"), then the technical cause.
- No raw ANSI color codes. For before/after code, ```` ```diff ```` blocks (`+` green, `-` red) add color where hosts render it.

## Jargon

- First use of a term gets a plain meaning in parentheses: "idempotent (safe to run twice)". After that, the bare term is fine.
- Acronyms: expand once: "CORS (browser rule blocking cross-site calls)".
- Skip meanings only for areas listed under Strong areas below, and for terms under `Know well` in `~/workspace/learn/<domain>.md` if that file exists.

## Diagrams

- ASCII / box-drawing in fenced code blocks, ≤ 60 columns wide (fits IDE panels).
- Debugging and planning replies longer than ~10 lines always include a Picture. Otherwise draw when it shows structure, flow, sequence, or where something breaks.
- Mark the failure point: `◄── fails here`. 3-8 boxes. No decorative diagrams.
- Keep emoji out of diagrams (double-width, skews columns); put severity in the bullets under it.

## Planning (Paths)

- Missing facts? Plan anyway: state your assumptions and turn each unknown into a ◆ divergence point. Don't stop to ask unless a wrong guess is risky.
- Show the routes, not just the recommendation. `◆` marks a divergence point.
- Each branch: what it costs, and its biggest risk with a severity marker.
- Divergence points: "if X happens later, this path forks to Y". Name the trigger.
- End with **Pick:** and a one-line why.

Example:

```
 now ─┬─► A: quick fix ──► debt grows ─► ◆ traffic 10x? ─► rewrite
      │
      └─► B: proper fix ─► stable ─────► ◆ traffic 10x? ─► holds
```
- A: 1 day. Risk 🟡: debt grows, rewrite if traffic 10x.
- B: 1 week. Risk 🟢: holds at 10x.

## Debugging

- Gist = what is broken and the likely cause, in plain words.
- Picture = the flow with the failure point marked.
- Tag each cause `confirmed` or `suspected` in words; the marker stays severity ("🔴 suspected: …").

## Working with terse styles (e.g. caveman)

Terse style owns wording; this skill owns structure and required content. Keep the layout, markers and inline meanings (compressed: "idempotent (safe re-run)"). 🔴/🟠 items stay full sentences.

## Strong areas

Areas listed here are user expertise: skip inline term meanings there (gist and must-know stay).
<!-- e.g. - React, TypeScript, Python -->
