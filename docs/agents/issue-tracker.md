# Issue tracker: Local Markdown

Specs and tickets for this repo are markdown files; GitHub Issues are not used.

## Conventions

- Specs live in `docs/specs/<feature-slug>.md` and are committed.
- Tickets live one file per ticket at `.scratch/<feature-slug>/issues/<NN>-<slug>.md`, numbered from `01` — never a single combined tickets file. `.scratch/` is gitignored, so tickets exist only in the working copy where they were written.
- Each ticket starts with a `Spec: docs/specs/<feature-slug>.md` line linking it to its spec. A spec may also list its claims in a Claims table; its tickets then mirror that table.
- Triage state is a `Status:` line near the top of each ticket (see `triage-labels.md`). Completion values: `resolved` means the ticket was implemented and accepted (both passes, plus HELD for a Security-critical claim, or the user's accept-and-land decision) and committed, with a `## Comments` note naming the version or commit and, for accept and land, the decision and its remaining risk; `wontfix` means it will not be done, is set only on the user's recorded cancellation and never counts as acceptance. Any other status, such as `ready-for-agent`, means the ticket is unfinished.
- Comments and conversation history append to the bottom of the file under a `## Comments` heading.

## When a skill says "publish to the issue tracker"

- A spec: write `docs/specs/<feature-slug>.md`.
- Tickets: create files under `.scratch/<feature-slug>/issues/`, each with its `Spec:` line.

## When a skill says "fetch the relevant ticket"

Read the file at the referenced path. To find a spec's tickets, list `.scratch/*/issues/` directly or search it with ignored and hidden files included: a repository-wide search that respects `.gitignore` skips `.scratch/`.

## Wayfinding operations

Used by `/wayfinder`: the map is `.scratch/<effort>/map.md` with one child file per ticket under `.scratch/<effort>/issues/`, following the same `Blocked by:` and `Status:` conventions.
