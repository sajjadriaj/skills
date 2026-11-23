---
name: prove-it
description: Never claim work is done, fixed, working, or passing without fresh evidence shown in the same message - the command run and its output. Use before any completion claim, before committing or opening a PR, and whenever saying "done", "fixed", "works", "tests pass", or "verified". Always on.
---

# prove-it

A claim without evidence is a guess. The user may not be able to check it themselves, so the evidence has to be in front of them.

## Rule

Every completion claim carries proof from this session, in the same message:

| Claim | Required proof |
|---|---|
| "tests pass" | the test command and its summary line (`42 passed, 0 failed`) |
| "fixed" | the repro that failed before, now passing (before/after output) |
| "builds" / "type-checks" | the build command and its success line |
| "works" (UI/API) | what was run or clicked and what came back (status code, response, screenshot) |
| "deployed" | the deploy output plus a live check (health URL, version endpoint) |
| "no other usages" | the search command and its result |

- Proof is fresh: run it after the last change. Output from before an edit proves nothing about after.
- Show the decisive line, not the whole log. Copy it verbatim from a command you ran this session; never type output you didn't receive.
- Never paste secret values (keys, tokens, passwords, DSNs, auth headers) from files or output. Name the variable and where it lives; redact the value as `***`.
- Partial results are said as partial: "unit tests pass (12/12); did not run e2e, needs a browser".
- Can't verify (no access, no credentials, needs prod)? Say exactly that and what the user should run: "Not verified: run `npm run e2e` locally."

## Banned without proof

"should work", "should be fixed", "probably", "I believe this resolves", "everything is working", "all good", ✅ next to an unrun check.

## Before finishing a task

1. List each thing you changed.
2. For each, the proof (or the honest gap).
3. If any proof failed: the task is not done. Say so and keep going or ask.
