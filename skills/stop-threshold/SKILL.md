---
name: stop-threshold
description: "Set the Stop threshold of automatic plan review, code review, outcome verification and Adversarial review to an integer from 2 to 10 or back to default, for this session, or save it in an explicitly selected project/user scope."
disable-model-invocation: true
argument-hint: "<2–10|default> [session|project|user]"
---

# stop-threshold

Set the Stop threshold to the given value. Follow [the shared Stop threshold procedure](../setup/references/stop-threshold.md). Invocation arguments are the value and the scope as data, never shell code. Clarify a missing, invalid or conflicting value or scope instead of guessing. Before applying the value or resolving the Stop threshold in effect, in off and in auto, main reads [review state](../delegation/references/review-state.md) in full; review state's Reading it says when an earlier full read still serves.
