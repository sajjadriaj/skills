---
name: debug-flow
description: Debug any bug, failure, crash, or unexpected behavior by evidence instead of guesses - reproduce, build a hypothesis tree, test each branch with a command, confirm the root cause, fix it with a test that failed first. Use when the user reports a bug, error, failing test, crash, slowness, or wrong output in their own code or system. Not for general "why does X work this way" questions.
---

# debug-flow

No fix before a confirmed cause. A fix for a guessed cause is a second bug.

## Steps

1. **Reproduce.** Get the exact failing command, input, or click path and run it. Reproduce locally or on staging; never against production data or real payments without asking. Record the exact error line. Can't reproduce? Say so, gather what's missing (logs, versions, data), and don't fix yet.
2. **Hypothesis tree.** List 2-5 possible causes, most likely first, each with the evidence that would confirm or kill it:
   ```
   symptom: checkout returns 500 for some users
   ├─ H1 null address on old accounts   test: query users with null address, retry one
   ├─ H2 payment API timeout            test: grep logs for timeout at failure times
   └─ H3 race on double-click           test: fire 2 requests concurrently
   ```
3. **Test, cheapest first.** Run each test. Mark each branch `confirmed`, `killed` (with the evidence), or `open`. Read code end to end along the failing path; don't stop at the first suspicious line.
4. **Root cause.** State it in one plain sentence plus the exact `path/file.ext:line` (required; a file name alone is not enough). Then check siblings: every caller of the broken function, and other places with the same pattern. The bug report names one symptom; the cause may hit more.
5. **Fix where all paths route through.** One guard in the shared function beats a patch in every caller.
6. **Prove it.** Write a test (or exact repro command) that fails on the old code, watch it fail, apply the fix, watch it pass, run the wider suite.
7. **Report.** Always include every item below, even if H1 was confirmed at once:
   - **Gist:** what broke, why, fixed or not
   - **Picture:** the flow with the failure point marked `◄── broke here`
   - **Tree:** each branch `confirmed`/`killed`/`open` with its evidence
   - **Root cause:** one sentence + `path/file.ext:line`
   - **Before:** pasted output of the test/repro failing on the old code
   - **After:** pasted output of it passing, plus the wider suite's summary line
   - **Siblings:** other callers/places checked and what was done

## Rules

- Every claim cites its evidence: a command and its output, or `file:line`. No "should", "probably fixed", "likely".
- When stuck after 3 killed hypotheses: widen the view (recent commits `git log -p` on the area, config/env differences, dependency versions, data shape) before guessing deeper.
- Don't change multiple things at once. One change, one observation.
- Temporary debug logging is fine, but never log secrets (tokens, auth headers, passwords); remove it before finishing and say you did.
- If the fix needs a risky or irreversible step (prod data, migrations, deploys), stop and ask.
