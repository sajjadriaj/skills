---
name: handoff
description: Write, update, or resume from a session handoff doc so the next session (or another assistant) starts in seconds. Use when the user says "handoff", "write a handoff", "update the handoff", "wrap up", "where were we", or at session start on a project that has a handoff.
---

# handoff

Handoff root: `~/workspace/handoff/` (one folder per project: `<root>/<project>/handoff.md`). Change this line to relocate.

## Resume (session start / "where were we")

1. Read `<root>/<project>/handoff.md` if it exists.
2. Re-check anything that goes stale before acting on it: branch heads, open PRs, deploy state, running jobs. Use commands (`git log`, `gh pr list`, etc.), not the doc's word.
3. Tell the user in ≤ 5 lines: where things stand, what's in flight, the next step, and any 🔴 item. Flag anything that no longer matches the doc.

## Write / update

1. Gather facts with commands, not memory: `git status`, `git log`, branch heads, PR numbers, deploy/job status. Convert relative dates to absolute (YYYY-MM-DD).
2. Update the file in place. If rewriting most of it, first keep the old one as `handoff.<YYYY-MM-DD>.md`.
3. Copy any script the work relies on into `<root>/<project>/scripts/`. Never leave it only in a temp or session folder.
4. Never write secrets. Write where they live (`AURORA_RO_DSN in ~/project/.env`).

## Structure

```
# <project> — session handoff
Last updated YYYY-MM-DD. What changed this session: 3-6 bullets.

## 1. Where things are     repos, checkouts, servers, envs, URLs (table)
## 2. Current state        branches + heads, what is deployed where
## 3. In flight            unfinished work: branch, status, what's left
## 4. Next steps           ordered; first one doable immediately
## 5. Traps                🔴/🟠 things that bit or will bite; plain consequence
## 6. Decisions            what was decided, why, who said so
## 7. Scripts              each file in scripts/: what it does, how to run
```

- Omit empty sections; keep numbering stable so people can say "see section 5".
- Exact identifiers everywhere: commit SHAs, PR numbers, paths, hostnames, resource IDs.
- Decisions the user stated go in as theirs ("user said: keep the flag on permanently"); your own calls are marked as yours.
- Write it for someone with zero context: no "the bug we discussed"; name it.
- Prune: when something is done and merged, shrink it to one line in "What changed" or drop it.
