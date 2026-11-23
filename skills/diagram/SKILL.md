---
name: diagram
description: Draw clean, beautiful, self-contained SVG diagrams (architecture, flow, sequence, state, decision paths, timelines) with a fixed design system, light/dark aware, plus an ASCII preview in chat. Use when the user asks for a diagram, chart of a system, flow, map, or "draw/visualize this", or when a visual would explain a design better than text.
---

# diagram

One visual language for every diagram: quiet, precise, meaningful color only. The bar is "would look at home in a top-tier engineering blog".

## Workflow

1. Decide the one thing the diagram must make obvious (the request path, the failure point, the decision). Everything else is secondary and visually quieter.
2. Pick a type (below) and sketch it in ASCII in chat first. That's the user's instant preview.
3. Write the SVG by copying the `<style>` and `<defs>` from `template.svg` (same folder) verbatim. Do not invent new colors, fonts, stroke widths or markers.
4. Lay out on the grid (below). Compute every coordinate; never eyeball.
5. Build and look: `python3 <skill-dir>/build.py file.svg <out-dir>` embeds the fonts (subset, a few KB), prints `lint:` lines for text overflowing its node, overlapping text and edges crossing nodes, and writes `.light.png` + `.dark.png`. Fix every `lint:` line, open both images and fix anything else off (uneven gaps, cramped labels). Repeat until zero lint lines and clean images. If it exits 2 (no renderer), say the diagram is unchecked. Always run it: without it the fonts are not embedded.
6. Save to `docs/diagrams/<slug>.svg` in a repo (else the current dir). Give the path and the markdown embed `![<title>](docs/diagrams/<slug>.svg)`. Offer PNG for tools that don't take SVG (slides, Google Docs).

## Grid and geometry

- 8px grid. Canvas padding 40. Title baseline y=52, subtitle y=74, content starts y=120.
- Nodes: height 60 (label + sub) or 44 (label only), `rx=10`, uniform width per column.
- Width: label (Inter 14px/600) ≈ 8.4px/char, sub (JetBrains Mono 11px) = 6.6px/char exactly, kind tag needs ~60px on the right; plus 20px padding each side; round up to 8. Use the widest node in the column. The lint check is the final word.
- Gaps: 72 between columns, 64 between rows; more when an edge carries a label.
- Text in node: label at (x+20, y+27), sub at (x+20, y+45), kind tag right-aligned at (x+w-16, y+18).
- Every node gets a `shadow` rect at y+2 drawn just before it.
- ≤ 12 nodes. More? Split into two diagrams or group into a region.

## Edges

- Orthogonal only (H/V segments). Bends: `Q` corner with 8px radius. Never diagonal, never crossing a node.
- Draw edges before nodes. Start exactly on the source border; end exactly 6px before the target border (the arrowhead covers the last 3px and stops 3px short: an even gap everywhere). Never put `marker-end` on a path that doesn't reach a node.
- `edge` = normal, `edge hot` + `#arrow-hot` = THE path the diagram is about (one per diagram), `edge async` = queues, webhooks, events.
- Forks: branches share one trunk from the source, then split at a bend; draw the `hot` branch last so it sits on top at the shared segment.
- Labels: 11px, one or two words, beside vertical edges (x+10), above horizontal edges; on short gaps put an `elabel-bg` rect behind the text.

## Meaning, not decoration

- `node hot`: on the main path. `node ext`: third-party or outside our control (dashed). `node crit`/`high`/`ok`: severity, same meaning as clear-response 🔴🟠🟢. Plus a `dot` in the kind-tag spot.
- Kind tags (CLIENT, API, SVC, DB, QUEUE, EXT, JOB) say what a box is so its shape doesn't have to.
- Sub-lines: the real file path, table, or endpoint, so the diagram doubles as a map.
- Legend: only for styles actually used, under a `rule` line, one row. Put a crit/high explanation in plain words there.

## Types

- **Architecture / flow**: left-to-right main path on row 1, side effects below. See `template.svg`.
- **Sequence**: actors as nodes in one row; dashed vertical lifelines (`edge async`); numbered messages as horizontal edges going down, labels above ("1 POST /checkout").
- **State**: nodes = states (44 high), edges = events as labels; start state `hot`, terminal states `ok`/`crit`.
- **Decision paths** (see `example-paths.svg`): start node left, branches fan right on separate rows; a divergence point is a 12px diamond on the edge (fill = background, stroke = the edge's own color, 1.5px) with the trigger as its label above; each branch ends in a node marked `ok`/`high`/`crit` for its risk.
- **Timeline**: one horizontal `rule` axis, 8px circles on it, label above, date below (mono); highlight "now" with `hot`.

## Rules that keep it extraordinary

- One accent (the hot path). Severity colors only on what is actually at risk.
- Align everything: shared tops, shared centers, equal gaps. Asymmetry only when it carries meaning.
- Sentence case labels, no trailing periods, no emoji, no icons, no gradients, no drop shadows beyond the `shadow` rect.
- Title says what the diagram shows; subtitle says how to read it ("Highlighted path = the user's request").
- Keep `<title>`/`<desc>` filled (accessibility, and how it reads in a screen reader or search).
- Self-contained: no external font links, images or scripts (GitHub and docs strip them). Fonts are embedded by build.py; never hand-edit the `dg-fonts` block.
