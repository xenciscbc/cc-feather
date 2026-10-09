---
name: auto-on
description: "Enable automatic plan review, code review, outcome verification and, for Security-critical claims, Adversarial review of plan-driven work, which lets main commit, push to branches it created and open pull requests before acceptance without asking, while landing, release and completion still wait for both passes, plus HELD for a Security-critical claim, or the user's explicit accept-and-land decision, for this session, or persist it in an explicitly selected project/user scope."
disable-model-invocation: true
argument-hint: "[session|project|user]"
---

# auto-on

Set automatic review mode to `auto`. Follow [the shared toggle procedure](../setup/references/auto-review.md). Invocation arguments select scope only; this command does not reverse its mode based on contradictory arguments. Clarify a conflicting request instead of guessing. Never reset a logical plan's review count.
