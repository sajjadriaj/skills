---
name: learn
description: Build the user's personal knowledge as they work - after work in an area they don't know well, capture 3-5 new terms, lessons and traps into a per-domain notes file, and read those notes so later explanations skip what they already know. Use at the end of work in an unfamiliar area, or when the user says "what did I learn", "add to my notes", "teach me", "explain like I'm new to this".
---

# learn

Notes root: `~/workspace/learn/` (one file per domain: `<root>/<domain>.md`, e.g. `postgres.md`, `aws-api-gateway.md`, `stripe.md`). Change this line to relocate.

## Capture (end of work in an unfamiliar area)

1. Pick at most 5 things from this session worth keeping, in priority order: traps that would bite again, concepts that unlocked understanding, terms that kept coming up.
2. Write them generic and plain, so they help on any project: "API Gateway REST APIs base64-encode binary bodies unless the content type is listed in `binaryMediaTypes`", not "fixed uraan previews".
3. Show them and ask: "Add these to learn/<domain>.md?" Write only on yes.
4. Append under the right heading, skip anything already there (search first), keep the file sorted by heading.

## File format

```markdown
# <domain>

## Terms
- **<term>**: plain meaning in one line. (YYYY-MM-DD, where it came up)

## How it works
- one-line mental model or rule of thumb

## Traps
- 🔴/🟠 what bites, the consequence, how to avoid it

## Know well
- terms/topics the user has mastered: stop explaining these
```

## Use (any time)

- Before explaining something in a domain, read `<root>/<domain>.md` if it exists. Don't re-explain its Terms or Know well items at length; a short reminder is fine. Lean on its Traps when reviewing or planning.
- When the user shows they know something (explains it, corrects you), offer to move it to Know well.

## Teach mode ("teach me X", "explain like I'm new")

Build up in layers, each 2-4 lines: what it is and why it exists, a concrete everyday analogy, a small diagram, a minimal real example, the one trap everyone hits. Then ask one check question so the user can test themselves. Offer to capture it.

## Rules

- Never store secrets, credentials, customer data, or private project details: lessons only.
- Plain words; a term's meaning must make sense without the session's context.
- Small and curated beats complete: prune entries the user now knows into Know well.
