---
name: product-test
description: Turn a user story or flow into a step-by-step product test spec (YAML) - preconditions, actions, expected results, edge cases, side effects - for a human tester or a browser agent to walk through the real product. Can also derive the user stories from a codebase first. Not unit/e2e test code. Use when the user says "test plan", "QA this flow", "what should I test", "write test spec", "user story to test", or points at a repo and asks for product tests.
---

# product-test

Specs describe what a real user does and sees, in product words ("press Apply", "total shows $18.00"), never selectors or code. Anyone, human or agent, should be able to walk one with no other context.

## Mode A: from a story or flow

1. Restate the story in one line: `As a <role>, I want <goal>, so that <value>`. If the role, goal, or success isn't clear, state your assumption in one line and proceed. Ask first only if a wrong guess is risky or would waste a lot of work.
2. Write the happy path as numbered steps: one user action per step, each with observable expectations.
3. Add edge cases with the checklist below. Keep the ones that matter for this flow; say which you skipped and why in `not_covered`.

## Mode B: from a codebase ("build the stories from this repo")

1. Find the user-facing entry points: pages/routes, navigation, forms, API endpoints a UI calls, emails/notifications sent, background jobs a user would notice.
2. Group them into journeys and write each as a user story. Rank by value × risk (money, auth, data loss, first-run experience first).
3. Show the list (story, entry files, risk) and ask which to spec. Default to the top 3 if told "just do it".
4. Spec each chosen story as in Mode A. Every expectation inferred from code gets `from: file:line` so the user can check it against intent; expectations from the story get no tag. Code says what it does, not what it should do: flag any place where code behavior looks wrong for the user (`suspect:`).

## Edge-case checklist

Input: empty, too long, invalid format, boundary values (0, 1, max), special characters/unicode · Flow: back button, refresh mid-flow, double-click/double-submit, two tabs, abandon and resume · Access: logged out, wrong role, another user's data via URL · Network: slow, offline, timeout from a third party · Money/time: rounding, currency, timezone, date boundaries · Device: phone width, keyboard-only, screen reader labels · Side effects: emails, notifications, records created, analytics events, what the admin sees.

## Spec format (`product-tests/<flow-slug>.yaml`)

```yaml
flow: Apply a coupon at checkout
story: As a shopper, I want to apply a coupon code, so that I pay less.
source: story            # or: code (src/server.js, src/cart.js)
env:
  url: http://localhost:3000        # where to test
  needs: [test account, coupon SAVE10 = 10% off, coupon FIXED50 = $50 off]
preconditions:
  - Logged in as a shopper
  - Cart has 1 item at $20.00
steps:
  - id: S1
    do: Open the cart page
    expect:
      - Cart shows 1 item
      - Subtotal $20.00
  - id: S2
    do: Enter SAVE10 in the coupon field and press Apply
    expect:
      - Total shows $18.00
      - Coupon SAVE10 shown as applied
  - id: S3
    do: Press Pay and complete payment with the test card
    expect:
      - Confirmation page shows $18.00
after:                               # side effects to verify outside the UI
  - Order in admin shows coupon SAVE10, amount $18.00
  - Confirmation email total is $18.00
edge_cases:
  - id: E1
    severity: critical               # critical | high | medium
    why: Coupon worth more than the cart
    setup: Cart $20.00, coupon FIXED50
    do: Apply FIXED50
    expect:
      - Total is $0.00 or the coupon is rejected with a message; never negative
    from: src/cart.js:10             # only when inferred from code
    suspect: Code subtracts amountOff with no floor; total can go negative
not_covered:
  - Currency other than USD (single-currency app)
```

## Rules

- One action per step; every step has at least one expectation a person can see or check.
- Exact values (amounts, messages, counts) whenever known; `???` with a question when not, never a guess dressed as fact.
- Severity on edge cases uses the clear-response meaning (critical = money, security, data loss).
- Use block lists (`- item`), not `[a, b]`: values like `$1,000.00` or `Note: x` break flow-style YAML.
- Keep a spec to one flow; 3-10 steps, 3-8 edge cases.

## Run mode (only when asked to "run" / "walk" a spec)

If a browser tool is available, walk the steps against `env.url`, and for every expectation record `pass`, `fail` (what was seen instead, screenshot), or `blocked`. Write results next to the spec as `<flow-slug>.results.yaml` with the date, URL and build/commit, then summarize: failures first, with severity. Never run against production or with real payment methods unless the user explicitly says so.
