---
name: pr-review
description: Review any pull request, branch, or local diff in three parts - a plain-language brief of what it does, verified findings with concrete failure scenarios, and ship risks (migrations, config/secrets, dependencies, contracts, irreversible ops, rollback) - ending in a verdict. Use when the user asks to review a PR, branch, diff, or "what does this PR do".
---

# pr-review

The reader may not know this area. They must leave knowing what the change does, what's wrong with it, and what could bite at merge or deploy.

## 1. Get the change

- PR number/URL: `gh pr view <n> --json title,body,baseRefName,headRefName,files` and `gh pr diff <n>`.
- Branch: `git diff $(git merge-base <base> <branch>)..<branch>` (base = repo default branch unless told).
- Nothing given: the working tree (`git diff HEAD`, plus untracked files).
- Read beyond the diff: callers of every changed function, the tests that cover it, config it reads. A diff hides what it breaks elsewhere.

## 2. Output

```
**Gist:**        what the change does and why, 2 plain sentences
**Verdict:**     approve | approve with fixes | block, plus the one reason
**Must fix:**    🔴/🟠 findings
**Picture:**     ascii flow of the affected path, change marked (◄── new / changed)
**Findings:**    all findings, most severe first
**Ship risks:**  checklist below; "none found" stated explicitly per item
**Test by hand:** 2-5 concrete things to click/run that the tests don't cover
**Ask author:**  open questions only the author can answer
```

## 3. Findings

Each finding: `severity · file:line · problem · failure scenario · fix`.

- Failure scenario = concrete input or state, then the wrong result ("empty cart + coupon: total goes negative, charge fails"). No scenario, no finding.
- Verify by reading the code path end to end. If you can't confirm, keep it only as `suspected` with what would confirm it.
- Look for: wrong logic and edge cases (empty, null, zero, duplicate, concurrent, retry, timezone, unicode, large input); error handling that loses data or hides failure; security (authz on every new endpoint, injection, secrets in code/logs, unsafe deserialization); data (migrations vs. existing rows, nullability, indexes on new queries); contract breaks for existing callers; missing or meaningless tests for the new logic.
- Skip style and naming unless it changes meaning. No praise padding.
- Severity: 🔴 data loss, security hole, prod outage, money wrong · 🟠 feature broken for some users, fix before merge · 🟡 risk or debt worth a follow-up.

## 4. Ship risks (check each, report each)

| Risk | Look for |
|---|---|
| Schema / data migration | migration dirs, `*.sql`, ORM schema files; irreversible changes (drop, rename, type change); backfills; lock time on big tables |
| Config & secrets | new env vars / config keys / feature flags (grep `env`, `getenv`, `process.env`, `os.environ`, settings files); must they exist before deploy? |
| Dependencies | manifest + lockfile changes; major bumps; new packages (maintained? license?) |
| Contracts | API routes, request/response shapes, events, public exports, CLI flags: does any existing caller break? |
| Infra / CI | workflows, Dockerfiles, IaC, build config, bundle size |
| Irreversible side effects | emails, payments, deletes, external writes, cache/key changes |
| Deploy order | does service A need to ship before B, or migration before code? |
| Rollback | can it be reverted by redeploying the old version? If not (migration, data change), what's the way back? |

## 5. After

- Offer to fix the 🔴/🟠 findings or to draw the flow with the diagram skill.
- Never post to GitHub unless asked. When asked: one review comment via `gh pr review <n> --comment --body-file <file>`, or inline comments only if requested.
