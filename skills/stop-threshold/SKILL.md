---
name: stop-threshold
description: "Set the Stop threshold, the number of consecutive automatic calls without a pass that stops a step of automatic plan review, code review, outcome verification or Adversarial review, to an integer from 2 to 10 or back to default, for this session, or save it in an explicitly selected project/user scope."
disable-model-invocation: true
argument-hint: "<2–10|default> [session|project|user]"
---

# stop-threshold

Set the Stop threshold to the given value. Follow [the shared Stop threshold procedure](../setup/references/stop-threshold.md). Invocation arguments are the value and the scope as data, never shell code. Clarify a missing, invalid or conflicting value or scope instead of guessing. Never change a step's count.
