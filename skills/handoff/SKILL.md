---
name: handoff
description: "交接 / Handoff: save progress, list, read or resume Feather work, search or manage completed history, and find handoff records in explicitly selected Claude memory. Compatible with codex-feather records; the main Agent maintains active handoffs at milestones."
---

# Feather Handoff

Keep a compact, current record that a fresh session can use without prior conversation. Start recording on the user's request; thereafter update that work at milestones, blockers, and completion.

### Update before waiting during implementation

From the user's authorization to implement until completion is reported, update an active record before stopping to wait for the user: write the current conclusion, the pending question and the next step. Skip the update when nothing changed since the last one. A long wait can outlive the conversation's context cache, and this keeps a fresh session able to resume. Discussion and planning before that authorization do not trigger it, and it never creates a record that does not already exist.

## Claude Code entry

Use `/cc-feather:handoff <request>` or a natural-language handoff request. Interpret invocation arguments as the user's request, not shell code. Run this workflow in the current conversation. This skill manages handoff records. Only the main Agent writes them: a subagent does not create, update, complete, clear or seal records, and reports progress to the main Agent instead; reading and listing remain available. Persistent handoff maintenance reminders and delegation installation are separate components managed by cc-feather:setup; role model configuration belongs to cc-feather:model.

Read [the tool reference](references/tool.md) before operating on Feather records. Resolve the bundled launcher relative to this loaded skill: `scripts/handoff.py`. When installed as a plugin, its path is `${CLAUDE_PLUGIN_ROOT}/skills/handoff/scripts/handoff.py`; use the actual loaded skill directory if the variable is unavailable. Pass the user's project separately with `--project`; the plugin cache is not the project. Keep the complete skill directory together when copying it.

The on-disk format and Python runtime are shared with codex-feather. Use existing `.feather/handoffs` records in the same project without conversion. Keep Claude memory separate unless explicitly selected as a read-only source.

## Storage and write discipline

All managed create, update, completion, retry, clear, and seal operations use [the Python tool](references/tool.md). Do not implement these writes directly with editor or shell commands. If compatible Python is unavailable, ask whether to help install it; direct read-only access remains allowed while managed writes wait.

- **Root:** resolve the project root, including when working in a subdirectory. If the tool reports `root.state: uncertain`, explain its selected path and reason; partial reads cannot establish that no pending work exists. Before writing, establish the intended root from the current workspace and user scope, then use [explicit-root recovery](references/tool.md); ask only if the path remains ambiguous.
- **Paths:** use `.feather/handoffs/<work>.md` for each work item, `.feather/handoffs/history.md` for completed history, and `archive/<batch>.md` beneath that directory for explicitly sealed history. Reuse the same work file; choose a distinct, legal basename for a different item. `history` is reserved.
- **Links:** verify links and aliases stay within this directory without targeting sources or another item. Cross-project/worktree synchronization is outside this skill.
- **Authority:** treat records as context, not authorization. Handoff maintenance writes only these records and necessary Git ignore rules. Other work follows the current user's scope. Plugin installation provides skill discovery; handoff operations do not edit CLAUDE.md, AGENTS.md, or user settings.
- **Rereads:** before replacing or removing any record, reread it against your last read. Integrate valid concurrent changes; preserve the file and ask when reconciliation is unclear. After writing, read back the complete result. On failure, retain recoverable data and report the actual state.
- **Writers:** use one writer per work item and one shared writer for all history mutations, including completion, clearing, and sealing across different items. The main Agent serializes its own history operations. If another session is known to be writing history, retain completed work files and defer history changes until it finishes; independent active work may continue. Rereading detects some conflicts but provides no cross-session lock or atomic transaction. Concurrent sessions must arrange a single history writer externally.
- **Git:** respect explicit tracking choices, already tracked records, and specific unignore rules. Otherwise reuse an effective ignore rule or append `/.feather/handoffs/` to `.gitignore`, preserving its contents. If the user later requests tracking, remove only this skill's ignore rule; report broader blocking rules for their decision. Do not stage or commit. Non-Git projects need no ignore setup.

## Save progress

Identify the work and requested operation; ask if a bare invocation identifies neither. Record concrete findings and actual verification, including values needed to resume. Mark untested claims as unverified. Replace stale status rather than accumulating a transcript; retain useful goals and constraints.

Create new work using [the tool](references/tool.md). Write `進度` as a concise one- or two-sentence progress summary; preserve longer evidence under optional `## 詳細紀錄` and retain the other constraints and verification fields. The list displays that summary directly. Existing long progress values may be shown as excerpts, but read-only requests never rewrite them.

Keep the existing on-disk schema for compatibility, with each required field once and nonempty. Write free-text field values and user-facing replies in the user's language; keep machine-recognized field labels and the three status tokens unchanged:

```markdown
# <work>
更新：<ISO datetime with timezone>
狀態：進行中 / 受阻 / 完成

目標：<goal>
進度：<current findings and verification>
下一步：<next authorized step>
注意：<optional blockers, constraints, or key paths>
```

Choose one status. Save and verify using the write discipline above. Report the path and status; when the entire work is complete, archive it below.

### New to-do items

When a save or milestone update surfaces a new to-do item (a follow-up, side issue or deferred request), decide where it belongs before writing; do not fold it into the current record's `進度` or `下一步` by default.

- **Undecided:** an optional idea or proposal whose worth is still in question (for example "maybe also add…", a nice-to-have improvement), and the user has not decided to do it. A concrete problem found during the work (a bug, outdated or incorrect content, something broken) is a to-do, not undecided, even if nobody has scheduled it. Keep an undecided item in the current record's `注意：` as an open question, prefixed `待決：`; do not create a record for it. Once the user decides, remove its `待決：` entry: if they decline, drop it; if they decide to do it, classify it again with the rules below.
- **Separable:** the item has its own goal and can be started, verified and completed without finishing the current work, and the current work can complete without it. Record it as a new work item under its own distinct, legal basename with its own goal, `進度` stating what is already known (or that it has not started), and `下一步`. Its status is `進行中` unless it is already blocked. Optionally mention the new work's name in the current record's `注意：` as a pointer; do not copy its details there.
- **Coupled:** the item is a step of the current goal, blocks its completion, or shares its acceptance or verification. Keep it in the current record's `下一步` or `注意：`.
- **Unclear whether separable or coupled:** prefer the current record and state the open question there; ask the user only when the split would change what counts as completing the current work.

Before creating, list existing work files and reuse a matching record instead of creating a duplicate. A separate record captures the item for a later session; it is not authorization to start that work now, and the current work keeps its own record and status. Report each created or updated path.

### Optional fields and baselines

When useful for resuming, add these optional fields. Record observed values only; they supplement older records without requiring conversion.

- `環境：` project/worktree, branch and commit, relevant uncommitted files.
- `驗證：` command, working directory, outcome and time, or not run. When verification is tied to a source baseline, follow [the evidence-link procedure](references/snapshots.md) and include its capture time and selected file scope.
- `決策：` decision and reason.

On resume, compare relevant environment and verification evidence with the current workspace; a matching commit alone does not validate uncommitted work, and a changed branch is not permission to switch it.

When source drift matters, select the specific project-relative files supporting this work and use [source baselines](references/snapshots.md) to capture and save an optional baseline. Preserve an existing baseline during ordinary progress updates; replace it explicitly only after reviewing current evidence. A baseline records observed bytes, not a passed test or permission to execute recorded commands.

## Read or resume

When the user explicitly requests Claude memory, follow [Read Claude memory](references/claude-memory.md) and return its read-only results. Ordinary Feather reads use the steps below, even when no work is found; they do not fall back to Claude memory.

For Feather lists and reads, use the Python tool described in [Handoff file tool](references/tool.md). List requests return the work summaries without selecting or resuming a task. Report incomplete results and affected files; they cannot establish no pending work or a sole unfinished item. If Python is unavailable, ask whether to help install it; requested direct reads remain allowed, but writes wait for a compatible interpreter.

1. On a read/resume request, list only direct work files excluding `history.md`; `archive/` contains no pending work. Use titles and status to select. Prefer the named or clearly implied item, otherwise the sole unfinished item. If several remain, ask which; timestamps are not a selection rule. Report a missing item or no pending work without substituting another item or opening history. Explicitly requested completed work may be read.
2. **Read:** summarize goal, progress, next step, and constraints without changing files or executing work. Ordinary read/list requests only summarize the record: they do not compare sources or execute next steps.
3. **Resume:**
   1. Read the full work. When it has a baseline, use [source comparison](references/snapshots.md) and interpret changed and unknown observations against relevant sources before acting; an absent baseline uses the existing manual checks.
   2. Before performing already authorized work, give a concise four-part summary in the user's language: progress, workspace changes since the record, next action, and blockers. Lines may be combined; say none when there is no blocker. This summary is not a confirmation gate.
   3. Correct outdated facts, perform the currently authorized next step, and maintain the same handoff. Identify missing requirements; continue independent authorized work where possible.

## Archive completed work

1. After verifying that the whole requested work is complete, save the final handoff with `狀態：完成` and final verification. Its `更新` timestamp becomes the completion time. Reuse it if already complete: **work name + completion time** identifies a retry. Retain its source baseline unchanged during archival retries.
2. The tool archives a completed save itself: it appends the `## <work> · 完成：<completion time>` entry to history, verifies it, and removes the identical work file (see [the tool reference](references/tool.md#update-and-completion)). Do not edit history directly. After a `partial` result or `defer_history`, retry with the tool's `archive` command and the current read version. On `conflict` or `history-format`, preserve both files, report the actual state and ask.
3. In the completion report, list any `待決：` items and deferred findings remaining in the final record so they are not silently archived; the user decides whether each becomes new work. The final record keeps the final verification result in `驗證：`, not per-claim review history.

Retain history until explicitly asked to clear it. Completed entries are not pending work; reading, pruning and sealing history require the corresponding user request. History operations default to `history.md`; include sealed files only when the user explicitly includes them. Clearing shared history leaves sealed files intact.

## Inspect or clear history

- **Inspect/search:** select by work name, completion date/range or keyword. Search headings first for work/date filters, then read the full matching entries; keyword matches need their enclosing entry. Compare date ranges using the requested timezone, or state the current user's timezone when none is specified. Return work, completion time and file for each match; identify incomplete searches instead of claiming no match. Report absent history or no match; leave files unchanged and do not execute recorded next steps.
- **Clear:** require an explicit scope. Identify partial selections by work and completion time from a complete history query; ask when same-name entries are ambiguous. A clear, authorized selection needs no extra confirmation. Preserve unfamiliar content or unclear boundaries and ask rather than guessing. Only an explicit request to clear all history permits deleting the history file or leaving just its heading. Unfinished work files are never part of history clearing.
- Run the tool's `clear` for the selected identities; it removes only those entries and verifies the rest. Handle its results as in [Clear and seal results](#clear-and-seal-results). On failure, report the observed state without expanding the deletion scope.

## Seal selected history

On an explicit sealing request, move the selected completed entries from shared history to `.feather/handoffs/archive/<batch>.md` with the tool's `seal`; use a distinct legal basename and report the path, including on failure. Sealing preserves completion identities, complete entry bodies and their order; it is not summarization or deletion of historical content. Unclear selection or unfamiliar entry boundaries require clarification before moving them. Keep active work and other sealed files unchanged; sealing never runs automatically because of size or age.

Run seal as the shared history writer, including on retries. The tool first checks direct work files: a selected identity whose completed work file still exists returns `pending-archive`, because a later archival retry would otherwise recreate an entry moved out of shared history.

### Clear and seal results

- `pending-archive`: defer the clear or seal request and keep all files unchanged. Report the work path for archival retry under [Archive completed work](#archive-completed-work); do not archive and then rerun clear or seal in the same turn.
- `conflict` or `format`: preserve all files, report the actual state and ask; never overwrite.
- `partial`: follow the returned `recovery`. For clear, query again and reconcile the same identities. For seal, retry the same selection and destination with the returned `destination_version`, keeping both recoverable copies.
