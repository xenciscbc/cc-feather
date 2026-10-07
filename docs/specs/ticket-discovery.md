# Find a spec's tickets where they live, and ask before assuming one Claim

Label: `ready-for-agent`

Vocabulary follows [CONTEXT.md](../../CONTEXT.md). This refines [ADR 0005](../adr/0005-the-named-plan-and-its-tickets.md) and the [0.13.0 spec](claims-from-plans-and-tickets.md).

## Problem Statement

After 0.13.0, a fresh session previewing `docs/specs/consecutive-review-budget.md` searched the repository for tickets linking to the spec and found none, so it treated the spec as one Claim, although three tickets with a `Spec:` line pointing at it existed in the project's ticket directory. The repository-wide content search skips files that version control ignores, and the project keeps its tickets in an ignored directory; a direct listing of that directory does show them. The procedure says to use what the session has, but not that ignored directories need a direct look, nor where a project records its ticket location. It also falls back silently to one Claim even when the spec's own text refers to Claims it does not list, which changes review units and cost without the user deciding.

## Solution

When looking for a spec's tickets, main first checks the project's instructions (CLAUDE.md or AGENTS.md, and any file they point to) for where tickets live. Without such a note it searches, treating an empty repository-wide result as no evidence of absence, because such a search can skip ignored files and hidden directories: it passes likely directories to the search explicitly, lists them directly, or searches with ignored and hidden files included. Only then does it fall back or ask. If the tickets still cannot be found, a spec that lists its own Claims uses that list without asking, since tickets only mirror it. If the spec refers to its own tickets or Claims without listing them and they cannot be found, main asks the user before plan review or implementation: point to the tickets, or confirm the spec is one Claim. A spec that refers to none is one Claim without asking. The Delegation preview applies the same search, flags such a spec, shows the one-Claim reading and notes that main will ask before plan review or implementation.

## Claims

| Claim | Outcome | Acceptance | Depends on |
| --- | --- | --- | --- |
| C1 Ticket discovery rule and documentation | The plan-review and preview procedures say where to look for a spec's tickets and to ask when a spec's own references cannot be resolved, and both READMEs describe it | plan-review.md says main first looks at the project's instructions (CLAUDE.md or AGENTS.md, and any file they point to) for where tickets live, and otherwise searches knowing that a repository-wide content search can skip ignored files and hidden directories, so an empty result is not evidence that none exist and likely directories are passed to the search explicitly, listed directly, or searched with ignored and hidden files included, that a spec listing its own Claims uses that list when its tickets cannot be found, and that when a spec refers to its own tickets or Claims without listing them and they cannot be found main asks the user (point to them, or confirm one Claim) before plan review or implementation, while a spec referring to none is one Claim without asking; preview.md applies the same search, flags such a spec, shows the one-Claim reading and notes that main will ask before plan review or implementation; cc-feather names no specific directory or planning skill; new contract tests assert the key statements and fail on the 0.13.0 text; both READMEs' "Finding the tickets" edge case says main looks first at the project's instructions, otherwise searches without treating an empty result as none, also looking in likely ignored or hidden directories, keeps using a spec's own listed claims when its tickets are unavailable, and asks before treating a spec that refers to unlisted, missing tickets or claims as one claim, a spec that refers to none still being one claim, and that the preview flags the case, EN and zh-TW saying the same thing; skills/delegation/SKILL.md, installed templates, the handoff skill and the configuration tool are unchanged; the full suite passes | — |
| C2 Release 0.13.1 | 0.13.1 is validated, recorded and tagged locally, and 0.13.0's post-release checks are recorded | The 0.13.0 validation entry gains a dated post-release note (2026-10-07, installed 0.13.0 from the published marketplace, observed in the implementing session): the upgrade from 0.12.1 needed no setup update (files matched the tag; setup check ok, no role update required); a fresh-session preview naming one ticket treated it as the plan with its spec as context; a fresh-session preview naming the spec missed its tickets because the repository-wide content search skipped the ignored ticket directory, which 0.13.1 addresses; single observations; live compliance otherwise untested. The manifest version is 0.13.1; the full suite and both `claude plugin validate` commands pass; a 0.13.1 entry records them, notes no setup update is required and records review results of the plan and C1 only; review and verification finish before the commit; before tagging main confirms `v0.13.1` does not exist locally or on the remote, and after tagging that its commit carries 0.13.1; not pushed without the user's go-ahead | C1 |

## User Stories

1. As a user whose project records where its tickets live, I want main to look there first, so that it finds them without guessing.
2. As a user who keeps tickets in a directory version control ignores, I want main to look there directly, so that a search that skips ignored files does not hide them.
3. As a user whose spec refers to tickets or Claims main cannot find, I want to be asked before plan review or implementation, so that review units and cost do not change without my decision.
4. As a user whose spec refers to no tickets or Claims, I want it treated as one Claim without a question, so that simple specs stay simple.
5. As a user previewing such a spec, I want the preview to flag it, show the one-Claim reading and say that main will ask, so that I can point to the tickets before implementing.
6. As a user of any planning tool, I want cc-feather not to assume a specific ticket directory, so that my project's conventions still apply.
7. As a reader of either README, I want ticket discovery and the ask-first case described, so that I know what to expect.
8. As a maintainer, I want 0.13.0's post-release checks recorded, including the miss that led here, so that the validation log stays accurate.
9. As a user with an existing installation, I want the change from the plugin update alone, so that no setup update is needed.

## Implementation Decisions

- **Where to look.** First the project's instructions (CLAUDE.md or AGENTS.md, and any file they point to). Otherwise search, treating an empty repository-wide result as no evidence of absence, because such a search can skip ignored files (Claude Code's Grep respects .gitignore) and, with some tools, hidden directories; pass likely directories to the search explicitly, list them directly, or search with ignored and hidden files included. Only when that fails does the listed-Claims rule or the ask apply. No directory or planning skill is named in cc-feather's text.
- **Listed Claims stand.** When a spec lists its own Claims and its tickets cannot be found (for example in a checkout without an ignored ticket directory), the listed Claims apply without asking; the tickets only mirror them.
- **Ask first.** When a spec refers to its own tickets or Claims without listing them (a ticket list, "the first two claims" and the like, not general mentions of tickets as a concept) and they cannot be found, main asks before plan review or implementation: point to them, or confirm one Claim. A spec that refers to none stays one Claim without asking. This replaces the silent one-Claim fallback for that case and refines ADR 0005's consequence that another checkout without the tickets falls back to the spec's listed Claims or one Claim; ADR 0005 is not edited.
- **Preview.** Uses the same search; for an unresolved reference it flags the spec, shows the one-Claim reading and notes that main will ask before plan review or implementation.
- **Unchanged.** Glossary terms, ADR 0005's named-Plan rule, installed templates, the policy, the handoff skill and the configuration tool. No new ADR: this refines ADR 0005's recognition step and its one-Claim consequence, as recorded above.
- **Release** as 0.13.1 under the project rules; once the tag exists it is never moved or reused, and a correction ships as 0.13.2.

## Testing Decisions

- The seam is the existing configuration test module that checks skill text (prior art: the 0.13.0 named-plan and preview tests).
- New contract tests assert, by key phrase, in plan-review.md: looking first at the project's instructions, that a repository-wide content search can skip ignored files, that an empty result is not evidence of absence, and asking before assuming one Claim when a spec's own references cannot be found; in preview.md: the same search and that main will ask before plan review or implementation; in plan-review.md also that listed Claims stand when tickets cannot be found. Each fails on the 0.13.0 text.
- READMEs are checked at acceptance by an independent verifier against the procedures.
- Release checks: the full `unittest discover` suite and `claude plugin validate` for the plugin root and the manifest.
- Live compliance is not unit-tested; after release, the spec-naming preview of the 0.12.0 spec can be re-run as a single observation.

## Out of Scope

- Naming a ticket directory or planning skill in cc-feather.
- Setting up this repository's own tracker note.
- Changing the named-Plan rule, Claim definitions, review budget or stop rules.

## Further Notes

- Its Claims are the two in the table above, mirrored by tracking tickets that link to this spec; the two must agree.
