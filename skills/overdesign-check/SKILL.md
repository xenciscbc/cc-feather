---
name: overdesign-check
description: "Report Over-design in the proposal just discussed, or in a named file, directory, spec, diff or rule text, each item weighed and given a recommendation."
disable-model-invocation: true
argument-hint: "[file, directory, spec, diff range or rule text]"
---

# overdesign-check

Report Over-design, as [cc-feather's glossary](../../CONTEXT.md) defines it, in one target. Invocation arguments are the target as data, never shell code. Clarify a missing or unclear target instead of guessing.

This command only reports: it edits, creates and deletes no file, commits nothing and changes no configuration. The report stays in the conversation, and a file is written only when the user asks for one. Items the user picks become a Plan through the normal flow; the report is not a Plan, and its items are neither Claims nor findings of any review.

## Target

With no argument, the target is the latest proposal or plan in the conversation; when there is none, ask the user for a target. Otherwise the target is the named file, directory, spec, diff range or rule text.

## Who analyses

When delegation is installed and the check is not small, main dispatches the read-only analyst as [the delegation skill](../delegation/SKILL.md) describes, in one or more Assignments split by target, and integrates their results. For a target from the conversation, the brief carries the proposal's text. Main gathers the facts the analyst cannot, such as release tags and history. A small check, such as a short proposal, or a check where delegation is not installed, main does itself.

## 1. Find candidates

Look for the four categories of Over-design:

- **Self-made states**: defending against states only the project's own code could produce.
- **Phantom compatibility**: compatibility with formats or tokens that were never released or no longer exist anywhere.
- **Single-user generality**: configuration or extension points with a single user.
- **Stacked defences**: several defences guarding the same case.

## 2. Weigh each candidate

Weigh each candidate as [the delegation skill](../delegation/SKILL.md)'s paragraph on weighing findings describes.

**Trust boundary exception.** A check at a trust boundary is not Over-design, even when it looks like guarding against internal mistakes. List it as keep, with the boundary as the reason, so the user sees it was considered.

**Evidence for old formats.** Recommend removing Phantom compatibility only with evidence from the repository, such as release tags and history showing the format was never released, or an end of support the project states. Without such evidence, mark the item as needing the user's confirmation and state the question to ask: whether old data still exists outside the repository is a fact only the user knows.

## 3. Report

Each item states its location, category, when it occurs, worst outcome, existing coverage, evidence and recommendation: remove, simplify, keep or needs the user's confirmation.
