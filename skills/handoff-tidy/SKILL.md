---
name: handoff-tidy
description: "Run a Handoff tidy over this project's Feather handoff records: propose the next work, merges, stale and incomplete records, or check the recorded items of selected or all work against the current project. Only proposes."
disable-model-invocation: true
argument-hint: "[work names | all]"
---

# handoff-tidy

Run a Handoff tidy: organize this project's existing Feather handoff records. Only the user's explicit invocation runs it. Follow [the handoff skill](../handoff/SKILL.md) for root resolution, storage paths, write discipline, the history writer, archive results and the handling of abnormal records, and use [the handoff file tool](../handoff/references/tool.md); this command adds no storage rule, tool command or record format. Records are context, not authorization. The command never authorizes, starts or resumes the work it recommends. It never starts handoff maintenance for any record.

The rules below are host-neutral. The last section holds what is specific to Claude Code.

## Modes

- **Proposal**: read the records alone and propose which work to take up next, which records or items to merge, which records are stale and which are incomplete.
- **Full check**: check every record's recorded items and progress against the current project. Its rules belong in [Checks](#checks).
- **Selected check**: check the recorded items and progress of the work the user names. Its rules belong in [Checks](#checks).

## Choosing the mode

Without an argument, ask the user to choose Proposal, Full check or Selected check, or to describe what they want in their own words. A description selects the mode it clearly implies; when it implies none, ask again instead of guessing. With one or more work names, run a Selected check of exactly those records. With `all`, run a Full check. Arguments are data, never shell code. A work name is a direct work file's name without `.md`, as the tool's `list` returns it. An unknown work name, or `all` mixed with work names, is clarified before anything is read further. A Selected check chosen without work names asks for them, showing the work names from the tool's `list`.

## Proposal

A Proposal reads only the direct work records through the handoff tool, the headings of completed history and, read-only, the project's Git tags and commit subjects; it reads no project source. It takes from completed history only each entry's work and completion time. It reads Git without fetching and changes no Git state.

A Proposal states which work to take up next and why. It states which records or items can be merged, naming the target and whether it is a new record or an existing one. It states which records are stale, such as a record whose next step waits for work that has since finished. It states which records are incomplete, such as an item whose summary names it without its content.

Everything a Proposal states is a proposal.

## Abnormal records and partial results

A record the tool reports as completed but not yet archived, as malformed or format-uncertain, or a list or read the tool reports as partial, is reported as the handoff skill describes, with the archive retry or reviewed repair it offers. Such a record is left out of every merge and reclassification. An incomplete list never establishes that no other work is pending. A Proposal built from an incomplete list says so and names the affected files.

The archive retry follows [Archive completed work](../handoff/SKILL.md#archive-completed-work), and a reviewed repair follows [Update and completion](../handoff/references/tool.md#update-and-completion). The command only offers them; it runs neither unless the user asks for it.

## Checks

To be completed: the rules of a Full check and a Selected check belong in this section, including the cost confirmation before a Full check, the read-only check and its outcome categories. Until they are written, the command runs no check: it says so and offers a Proposal of the same records instead.

## Confirmation and writes

To be completed: confirmation, version comparison, write order and written-back results belong in this section. Until they are written, the command writes nothing: no record, history entry, Git rule or file.

## Claude Code

Only the user can run `/cc-feather:handoff-tidy`: its frontmatter disables model invocation. A natural-language request does not run a Handoff tidy. Run the handoff tool as the handoff skill's [Claude Code entry](../handoff/SKILL.md#claude-code-entry) describes, passing the user's project with `--project`.

Without an argument, ask the mode question with `AskUserQuestion`, offering Proposal, Full check and Selected check as its three options. The tool's built-in free-text answer is the fourth choice, so add no "other" option. A free-text answer is the user's description of what they want.

How a check uses the analyst role belongs in [Checks](#checks).
