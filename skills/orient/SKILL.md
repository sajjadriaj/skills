---
name: orient
description: Before changing code in an area the user doesn't know well (or when they ask to "orient", "map this", "explain this codebase/area", "what am I looking at"), produce a one-page map - plain-language gist, ASCII diagram of the parts with file paths, glossary, landmines, and where the change goes - so the user can steer instead of trusting blindly.
---

# orient

Goal: in one page, give the user enough of a mental model to judge and steer the work. Not a tour of everything: only what matters for the task at hand.

## Process

1. Pin the scope: the task, or the area the user named. If neither is clear, ask one question.
2. If the user keeps learning notes (learn skill, `~/workspace/learn/<domain>.md`), read the relevant ones first: skip terms they already know, lean on their recorded traps.
3. Read before claiming. Trace the real flow end to end: entry point, the code it calls, where data is stored, what runs on deploy. Use file search and reading, not guesses from names.
4. Hunt landmines on purpose: prod credentials or prod DB in local env, migrations, money/payment paths, auth, cron/queue jobs, generated code, shared config, anything with no tests.
5. Write the map (below). Stop at about one screen; offer depth instead of dumping it.

## Output

```
**Gist:**        2 plain sentences: what this area does, for whom
**Must know:**   🔴/🟠 landmines, plain consequence first
**Map:**         ascii diagram, boxes labeled with file paths
**Terms:**       5-10 domain + code terms, plain meaning each
**Change goes:** files to touch for the task, and what else they affect
**Unverified:**  what you inferred but did not confirm
```

- Map: ≤ 60 columns, 3-10 boxes, arrows show data/control flow, mark external systems (DB, queue, third-party API) distinctly, e.g. `[(postgres)]`, `{stripe}`.
- Cite `path:line` for every claim the user might act on.
- Terms: include the project's own vocabulary (model names, internal service names), not only general tech words.
- Change goes: list the blast radius (other callers, jobs, tests touching the same code). If the change looks risky, say which landmine it touches.
- Tag inferences: anything not read in code or run goes under Unverified.

## Example map

```
 browser ─► app/api/checkout/route.ts
                 │
                 ▼
          lib/billing/charge.ts ──► {stripe}
                 │                     │ webhook
                 ▼                     ▼
          [(orders table)] ◄── api/webhooks/stripe.ts
```

## After

Offer: "Want this saved?" If yes, save to `docs/orient/<area>.md` in the repo, or into the project's handoff if one exists. If clear-response is active, its severity palette and jargon rules apply here too. Offer to capture new terms and traps with the learn skill.
