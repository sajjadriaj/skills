---
name: pr-write
description: Write a pull request title and description for the current branch - why, what changed, ship risks, how it was tested, rollback - readable by a reviewer outside the area. Use when the user asks to write/draft/open a PR, or a PR description.
---

# pr-write

The description is for a reviewer who doesn't know this area and for whoever deploys it. They should be able to review and ship without asking you anything.

## 1. Gather facts

- Base = repo default branch unless told. `git log --oneline <base>..HEAD`, `git diff --stat <base>...HEAD`, `git diff <base>...HEAD`.
- Read the linked issue/ticket if one is named. Read the code paths the diff touches enough to describe behavior, not just files.
- Find what was actually tested: commands run this session and their results. Never claim a test you didn't see pass.

## 2. Title

Imperative, ≤ 70 chars, says the behavior change: `Stop double-charging on webhook retries`, not `Update webhook.ts`.

## 3. Body

```markdown
## Why
1-3 sentences: the problem or goal, in plain words. Link the issue.

## What changed
- Behavior-level bullets ("Retries with the same event id are ignored"), not a file list.
- Note anything deliberately left out of scope.

## Ship risks
- Migrations: none | <what, reversible?>
- Config / secrets / flags: none | <name, must exist before deploy?>
- Dependencies: none | <added/bumped>
- Contract changes: none | <API/event/export that changes, who's affected>
- Deploy order: none | <what ships first>

## How tested
- `<command>`: <result>
- Manual: <what was clicked/run and seen>
- Not tested: <honest gaps>

## Rollback
Revert + redeploy | <steps if a migration or data change makes revert unsafe>
```

- Every Ship risks line is filled; "none" is a checked answer, not a skipped one.
- Plain language; explain any domain term a reviewer outside the area wouldn't know.
- Screenshots or a short before/after for UI changes (ask the user to attach if you can't).
- No filler ("This PR aims to..."), no restating the diff line by line.

## 4. After

Show the title and body. Create the PR only when asked: `gh pr create --base <base> --title "<title>" --body-file <file>`. Ask before pushing the branch. If `gh` is unavailable, give the user the title and body to paste.
