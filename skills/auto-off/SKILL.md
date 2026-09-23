---
name: auto-off
description: "Disable automatic plan review for this session, or persist it in an explicitly selected project/user scope."
disable-model-invocation: true
argument-hint: "[session|project|user]"
---

# auto-off

Set automatic plan review mode to `off`. Follow [the shared toggle procedure](../setup/references/auto-review.md). Invocation arguments select scope only; this command does not reverse its mode based on contradictory arguments. Clarify a conflicting request instead of guessing. Never reset a logical plan's review count.
