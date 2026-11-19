# Handoff history command

Label: `ready-for-agent`

Vocabulary follows [CONTEXT.md](../../CONTEXT.md), which defines the Handoff store; this spec adds no term. "History" means the completed entries in the Handoff store's `history.md`, and "sealed history" the entries moved into its `archive/<batch>.md` files.

## Problem Statement

Once a handoff is completed, the handoff tool archives it into history, and from then on the user has no command that shows it. `/cc-feather:handoff-list` deliberately leaves out history and sealed archives, `/cc-feather:handoff-resume` stops without opening history when no unfinished work is left, and `/cc-feather:handoff-tidy` reads only history headings to build its Proposal. The capability exists: the handoff skill's Inspect/search rules and the handoff tool's `history` command filter by work title, completion date range and keyword, with sealed files on request. But it is reachable only by a natural-language request the user has to know to make, so finished work effectively disappears from view.

## Solution

cc-feather gains a read-only command only the user can run, `/cc-feather:handoff-history`. Without an argument it lists the headings of the ten most recently completed entries in `history.md`. An argument narrows the list by a completion date or date range, by an exact work title or by a keyword, can include sealed history with the word `sealed`, and can set how many headings are shown with a trailing number or `all`. Every heading is numbered; the user replies with numbers to see those entries in full. The command follows the handoff skill's existing Inspect/search rules and the handoff tool's existing `history` command, and changes neither.

When `/cc-feather:handoff-list` finds no pending work, or `/cc-feather:handoff-resume` finds no unfinished work, each says completed work can be viewed with `/cc-feather:handoff-history`, without opening history itself.

## User Stories

1. As a user who just completed a handoff, I want a command that shows completed work, so that finished work does not vanish from view once it is archived.
2. As a user, I want the command to run only when I invoke it, so that history is never opened unless I ask.
3. As a user, I want the command without an argument to show the ten most recently completed entries, so that I see recent work without reading the whole history.
4. As a user, I want the list ordered newest first, so that the work I most likely care about comes first.
5. As a user, I want each listed entry to show its work title, completion time and source file, so that I can tell entries apart, including the same work completed more than once.
6. As a user, I want only headings listed, not entry bodies, so that a long history stays readable.
7. As a user, I want every heading numbered, so that I can ask for a specific entry without retyping its title.
8. As a user, I want to reply with one or more numbers to see those entries in full, so that I can read the details of the work I chose.
9. As a user, I want the full entries shown exactly as recorded, so that nothing in the history is summarized away.
10. As a user, I want to filter by a single completion date, so that I can see what finished on a given day.
11. As a user, I want to filter by a completion date range, so that I can review what finished over a period.
12. As a user, I want date ranges to include both ends, so that the range means what I typed.
13. As a user, I want to filter by an exact work title, so that I can see every completion of one piece of work.
14. As a user, I want any other text treated as a keyword searched in entry content, so that I can find work by what it was about.
15. As a user, I want keyword results to show the matching lines under each heading, so that I can see why an entry matched before opening it.
16. As a user, I want filtered results to be headings too, limited to ten by default, so that a broad filter does not flood the screen.
17. As a user, I want to set how many headings are shown with a trailing number, so that I can see more or fewer than ten.
18. As a user, I want `all` as the trailing token to show every match, so that I can see the complete list when I need it.
19. As a user, I want the output to state how many were shown out of how many matched, so that I know when there are more.
20. As a user, I want the output to state how my argument was read (date, range, work title or keyword; sealed or not; the count), so that a misread argument is obvious.
21. As a user, I want sealed history left out unless I include the word `sealed`, so that the command follows the same default as the handoff skill.
22. As a user, I want sealed entries, when included, merged into the same newest-first list with their source file shown, so that I can tell shared history from sealed batches.
23. As a user, I want completion dates compared in my local timezone, so that "today" means my today.
24. As a user, I want the timezone used stated in the output, including when it falls back to UTC, so that I can judge the date filtering.
25. As a user, I want entries whose completion time cannot be parsed placed last and marked, so that they are neither hidden nor misordered.
26. As a user, I want an incomplete history read reported as incomplete, with the affected files, so that I never take a partial list as the whole history.
27. As a user, I want a missing history or no match reported plainly, so that I know there is nothing to show rather than guessing.
28. As a user, I want the command never to write anything, so that browsing cannot change records, history or Git rules.
29. As a user, I want the command never to clear or seal history, so that destructive history operations still need my explicit request through the handoff skill.
30. As a user, I want the command never to execute a recorded next step or resume completed work, so that reading history is not authorization.
31. As a user, I want the command never to start handoff maintenance, so that browsing does not commit the session to maintaining a record.
32. As a user, I want my argument treated as data and never as shell code, so that a title or keyword cannot run anything.
33. As a user whose project lives in a linked worktree, I want the command to read the same shared Handoff store the other handoff commands use, so that history looks the same from every checkout.
34. As a user, I want `/cc-feather:handoff-list` to point to the history command when it finds no pending work, so that I learn where finished work went.
35. As a user, I want `/cc-feather:handoff-resume` to point to the history command when no unfinished work is left, so that I am not left at a dead end.
36. As a user, I want those two pointers to only mention the command, so that neither command starts opening history on its own.
37. As a user who needs combined filters, I want to know a natural-language request to the handoff skill still covers them, so that the command's single-filter argument does not limit what I can find.
38. As a user reading the README in either language, I want the command listed with the other handoff commands and shown in the handoff examples, so that I can discover it.
39. As a user updating the plugin, I want the update notes to say what 0.41.0 adds and whether a setup update is needed, so that I know what to do after updating.

## Implementation Decisions

- **A new command skill, `handoff-history`.** Its frontmatter names it, describes it as a read-only listing of completed Feather handoff history, sets `disable-model-invocation: true`, and gives an argument hint covering the filter, `sealed` and the count, for example `[date | date..date | work title | keyword] [sealed] [count | all]`.
- **It adds no rule of its own to storage or history.** It follows the handoff skill's root resolution, Handoff store and Inspect/search rules and runs the handoff tool's existing `history` command as the handoff skill's Claude Code entry describes; it adds no storage rule, tool command or record format. The handoff tool is unchanged: it already returns every matching entry in full, and the command sorts, limits and formats what it gets back.
- **Read-only, and no authority.** The command writes no record, history entry, Git rule or file; it offers no archive retry, clear or seal; it never executes or resumes a recorded next step and never starts handoff maintenance. Entry content is shown as data, never followed as instructions.
- **Argument parsing.** The argument is data, never shell code, and is read in this order:
  1. A standalone token `sealed` adds the tool's sealed option.
  2. When the last remaining token is a positive integer, it is the count; when it is `all`, there is no limit. Otherwise the count is 10.
  3. The rest of the text, kept whole because work titles may contain spaces, is a filter when present: `YYYY-MM-DD` filters that completion date; `YYYY-MM-DD..YYYY-MM-DD` filters that inclusive range; text equal to a work title recorded in an entry heading filters by that work; anything else is a keyword.
  A keyword consisting only of an integer in the count position is read as the count; a combined filter is not supported. The output states how the argument was read. The work-title check needs the titles the tool returns, so the command may query once without a filter to compare titles before running the filtered query.
- **Timezone.** The command reads the host's local UTC offset and passes it to the tool as a fixed offset such as `+08:00`, which needs no timezone database. When the offset cannot be read, it uses UTC. Either way the output names the timezone used.
- **Ordering and limiting.** Results from every source read are ordered together by completion time, newest first. Entries whose completion time cannot be parsed go last, marked as such. The first count entries are shown, and the output states how many were shown out of how many matched.
- **What is shown.** Every result, filtered or not, is a numbered heading line with the work title, completion time and source file (`history.md` or `archive/<batch>.md`). A keyword result also shows the lines of the entry that contain the keyword. Bodies are not shown in the list.
- **Full entries.** The list ends by saying that replying with numbers shows those entries in full. A reply in the same conversation with numbers from the list shows the complete content of those entries as the tool returned it, still read-only. Numbers that are not in the list are reported, not guessed.
- **Results the tool reports.** A `missing` result is reported as no history; an `ok` result with no entries as no match; a `partial` result as incomplete with its affected files and issues, never as the whole history; an `error` result, such as an invalid date, with its message.
- **Pointers from the existing commands.** `/cc-feather:handoff-list`, when its complete result has no pending work, and `/cc-feather:handoff-resume`, when no unfinished work is left, each add one sentence saying completed work can be viewed with `/cc-feather:handoff-history`. Neither opens or reads history; `handoff-resume`'s rule not to open history is kept.
- **Manifest.** The plugin manifest lists the new command directly after `handoff-list`, keeping `handoff-tidy` last among the handoff commands.
- **Documentation and release.** Both READMEs list the command with the other handoff commands and add it to the Handoff compatibility examples. The version becomes 0.41.0, the update notes in both READMEs describe the command and whether a setup update is needed (expected: none, since installed guidance, templates and the configuration tool are unchanged; confirmed at release by diffing them against v0.40.0), and the release's validation, including a live run of the command, is recorded under its version heading in the setup validation document.

## Testing Decisions

- **A good test here checks the command's stated contract, not wording that does not carry a decision.** The command is instructions the model follows, so its tests pin the sentences that carry each decision above and the structural facts the plugin loader depends on, as the existing command tests do. They do not test the model's behaviour; the live run recorded in the setup validation document covers that.
- **One seam: the command contract tests.** A new test class in the command test module, following the Handoff tidy command tests as prior art, checks that the command is listed in the manifest directly after `handoff-list` with `handoff-tidy` still last; that its frontmatter names it, disables model invocation and carries the argument hint; that it pins the read-only and no-authority sentences, the deference to the handoff skill and tool, the argument parsing order, the default count, `sealed`, the timezone rule, the ordering and limiting, the numbered headings and full-entry reply, and the handling of each tool result; that `handoff-list` and `handoff-resume` each carry the pointer sentence and `handoff-resume` keeps its rule not to open history; and that both READMEs list the command.
- **No new tool tests.** The handoff tool's `history` command is unchanged and already covered by the existing history tests.
- **Release consistency** is covered by the existing release tests, which check the manifest version against the release documentation.
- **Acceptance** for the single Claim is the full test suite, since this Plan has one Claim and no separate overall acceptance.

## Out of Scope

- Any change to the handoff tool, including a `--limit` option or new filters.
- Combined filters in the command's argument, such as a date range with a keyword; a natural-language request to the handoff skill covers them.
- Clearing or sealing history from the command.
- Any change to the handoff skill's natural-language history rules or to how completion archives work.
- Listing or browsing history from other checkouts' stores or from Claude memory.
- codex-feather support for the command.

## Further Notes

- The work-title match is exact against recorded entry titles, not work filenames, matching the tool's `--work` semantics.
- A purely numeric keyword in the last position is read as the count; the output states the reading, and a natural-language request covers that rare case.
- The Plan is one Claim and is cut into one ticket.
