---
name: stop-threshold
description: "Set the Stop threshold, the number of consecutive automatic calls without a pass that stops a step of automatic plan review, code review, outcome verification or Adversarial review, to an integer from 2 to 10 or back to default, for this session, or save it in an explicitly selected project/user scope."
disable-model-invocation: true
argument-hint: "<2–10|default> [session|project|user]"
---

# stop-threshold

Set the Stop threshold to the given value. Follow [the shared Stop threshold procedure](../setup/references/stop-threshold.md). Invocation arguments are the value and the scope as data, never shell code. Clarify a missing, invalid or conflicting value or scope instead of guessing. Never change a step's count. Before applying the value or resolving the Stop threshold in effect, in off and in auto, main reads [review state](../delegation/references/review-state.md) in full, every line, and when one read returns only part of the file it reads the rest before acting; a full read whose text is still in main's context serves here until main reads review state again, which it does after any context compaction, at the start of a new or resumed session and whenever it cannot quote the owner's sentence it is about to apply.
