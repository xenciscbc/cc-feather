"""Merge upstream ticket 02 (docs/specs/merge-upstream.md, Security invariants S1, S2 and S3): the user-invoked
`/cc-feather:merge-upstream` command, the review-state sentences an Upstream merge keeps in every session (What a pass
covers, Evidence for a regression, Commits before the passes, Auto land, Accept and land at the end of the plan and
Dispatch record) and the delegation skill's pointer, pinned as whole sentences in the places that state them.

The tool's own behaviour is pinned by tests/test_merge_upstream_tool.py; this module checks only that the command names
the tool's real input keys and output parts."""

from __future__ import annotations

import re
import subprocess
import unittest

from tests import feather_support
from tests.feather_support import config

COMMAND = config.ROOT / "skills" / "merge-upstream" / "SKILL.md"
DELEGATION = config.ROOT / "skills" / "delegation" / "SKILL.md"
REVIEW_STATE = feather_support.REVIEW_RULES_REFERENCES / "review-state.md"
TOOL = config.ROOT / "skills" / "merge-upstream" / "scripts" / "feather_merge_upstream"
# The commit this ticket started from; every review-state pin this ticket adds is absent from its text.
BASE = "47d797d"


def source(name: str) -> str:
    """'merge-upstream SKILL.md' or 'merge-upstream SKILL.md#<label>' for a '- **<label>.**' bullet of the command,
    'delegation SKILL.md#<heading>' for a '## <heading>' section of the delegation skill, or a review-state bullet as
    feather_support.review_rules_source reads it."""
    path, _, label = name.partition("#")
    if path == "merge-upstream SKILL.md":
        text = COMMAND.read_text(encoding="utf-8")
        if not label:
            return text
        return next(line for line in text.splitlines() if line.startswith(f"- **{label}.**"))
    if path == "delegation SKILL.md":
        return DELEGATION.read_text(encoding="utf-8").split(f"\n## {label}\n", 1)[1].split("\n## ", 1)[0]
    return feather_support.review_rules_source(name)


class MergeUpstreamRuleTests(unittest.TestCase):
    assert_whole_sentence = feather_support.stop_threshold_assert_whole_sentence
    assert_pinned = feather_support.stop_threshold_assert_pinned

    @staticmethod
    def source(name: str) -> str:
        return source(name)

    # Items 19, 20 and 33 and S2: which Plan, user-invoked only, the preconditions and off mode.
    INVOCATION = {
        "merge-upstream SKILL.md#User-invoked only": (
            "This command runs only when the user invokes it; main never runs it on its own, at the end of a Plan, on "
            "resume or after Auto land stops.",
        ),
        "merge-upstream SKILL.md#Review state": (
            "Review state's What a pass covers, Evidence for a regression, Commits before the passes, Auto land, Accept "
            "and land at the end of the plan and Dispatch record state the rules an Upstream merge keeps in every "
            "session, whether or not this command is loaded; this command adds the procedure.",
        ),
        "merge-upstream SKILL.md#Off mode": (
            "In off, main reports that this command needs the automatic flow and stops, since off keeps no Dispatch "
            "record.",
        ),
        "merge-upstream SKILL.md#Which Plan": (
            "The command applies to the Plan the user names, or else to the sole Plan whose Dispatch record shows it "
            "waiting, its reviews under way or at the decision at the end of the Plan and not yet landed; otherwise main "
            "asks the user which Plan.",
        ),
        "merge-upstream SKILL.md#Preconditions": (
            "Before asking to merge, main checks each of these, and on any failure, or when one cannot be established, "
            "it reports which one and stops: the workspace is clean, `git -c core.safecrlf=false status --porcelain "
            "--untracked-files=all --ignore-submodules=none` listing nothing; HEAD is on a branch, not detached, and that "
            "branch is the work branch; the remote default branch resolves as review state's Commit and completion "
            "resolves it; the work branch is checked out in no other checkout, as `git worktree list --porcelain` shows, "
            "and no other checkout's Checkout lease names it, as the lease tool's `list` shows; the Plan's Dispatch "
            "record can be read; and the Plan is in the automatic flow.",
        ),
        "delegation SKILL.md#Plan review": (
            "To bring a moved remote default branch into a waiting Plan in auto, the user invokes "
            "`/cc-feather:merge-upstream`, which follows [the merge-upstream command](../merge-upstream/SKILL.md); main "
            "never runs it on its own, and in off it reports that it needs the automatic flow.",
        ),
    }

    # Item 21 and S2: the agreement, the fetch, the stops and the merge, never a pull, rebase, force or push.
    FETCH_AND_MERGE = {
        "merge-upstream SKILL.md#Agreement": (
            "Main names the Plan, its work branch, the remote and the default branch, and asks the user whether to fetch "
            "and merge now; the user may instead wait or land another Plan first.",
            "The agreement comes only from the user's own message or the user's answer, as review state's Final check "
            "scope defines it, and it authorises this Plan's integration only.",
        ),
        "merge-upstream SKILL.md#Fetch": (
            "Main fetches the remote with `git fetch <remote>` and reads the remote default branch's tip with `git "
            "ls-remote <remote> refs/heads/<branch>`, which must print exactly one line naming a commit present locally "
            "after the fetch; otherwise it reports and stops.",
        ),
        "merge-upstream SKILL.md#Already landed": (
            # Code review call 1, B1: an earlier Upstream merge's commits are not the Plan's own, so a later invocation
            # can still reach Merge, Nothing to integrate or Resuming.
            "The Plan's own commits are the commits after the Plan's base revision on the work branch other than the "
            "merge commit of every earlier Upstream merge the Plan's Dispatch record holds and every commit reachable "
            "from a remote tip such a merge merged, as `git rev-list HEAD ^<base revision> ^<each earlier merged remote "
            "tip>` lists them less those merge commits.",
            "When any of the Plan's own commits is an ancestor of the fetched tip, part of the Plan already reached the "
            "remote default branch: main reports, from the Dispatch record, which Claims are accepted and which are "
            "not, and stops for the user.",
        ),
        "merge-upstream SKILL.md#Nothing to integrate": (
            "When the fetched tip is an ancestor of the work branch, as `git merge-base --is-ancestor <tip> HEAD` shows "
            "by exiting 0, main reports that nothing needs integrating and stops, unless Resuming below applies.",
        ),
        "merge-upstream SKILL.md#Merge": (
            "Otherwise main merges the fetched tip, named by its full SHA, into the work branch with `git merge --no-ff "
            "-m \"<message>\" <full SHA>`, the message naming the remote default branch, resolves any conflicts itself, "
            "stages each resolved path by name with `git --literal-pathspecs add -- <paths>`, and commits the merge "
            "locally with `git commit --no-edit`.",
        ),
        "merge-upstream SKILL.md#No pull, rebase, force or push": (
            "It never uses `git pull`, never rebases or forces, and pushes nothing in this step.",
        ),
        "merge-upstream SKILL.md#Merge commit": (
            "The merge commit has exactly two parents, the work branch's tip before the merge first and the fetched tip "
            "second; when a conflict cannot be resolved, main reports it and asks the user, changing nothing further.",
        ),
        "merge-upstream SKILL.md#Recorded at once": (
            "Right after the merge commits, before running the tool or writing the rest of the report, main starts the "
            "Plan's Upstream merge entry in its Dispatch record with the remote tip, the tip before the merge and the "
            "merge commit by full SHA, so a resumed invocation finds the merge.",
        ),
    }

    # Item 22 and S2: discarding only the command's own unpushed merge, never dropping uncommitted changes.
    DISCARD = {
        "merge-upstream SKILL.md#When main may discard": (
            "Main may throw away and redo its own merge, for example after plan review finds a wrong resolution, only "
            "when all of these hold: the merge commit is the work branch's tip, as `git rev-parse HEAD` shows; the "
            "workspace reads What a gated pass judged states show no change; every remote `git remote` lists was just "
            "fetched with `git fetch <remote>` and each fetch exited 0; and the tool, run after those fetches, reports "
            "the merge commit on no remote-tracking ref, every remote of its `remote_tracking` part known with "
            "`contains_merge_commit` false.",
        ),
        "merge-upstream SKILL.md#How": (
            "It discards with `git reset --keep <full SHA of the tip before the merge>` and never uses a method that "
            "drops uncommitted changes, such as `git reset --hard`.",
        ),
        "merge-upstream SKILL.md#Otherwise": (
            "When any of these conditions cannot be established, main does not discard, and fixes the merge with new "
            "commits, as review state's Commits before the passes requires.",
        ),
    }

    # Item 23, S1 and S3: the tool's facts and the Integration report in the Dispatch record.
    REPORT = {
        "merge-upstream SKILL.md#Facts only": (
            "The tool is read-only: it never fetches, merges, pushes or writes a ref, the index, the working tree or a "
            "record, and it leaves every pass judgement to main and plan review.",
            "A status `error` stops main, which reports it.",
            "A part the tool reports unknown gives no reason to keep a pass.",
        ),
        "merge-upstream SKILL.md#Entry": (
            "Main writes the Integration report in the Plan's Dispatch record as an Upstream merge entry, after any "
            "earlier one, between review calls: the remote, the default branch, the remote tip, the tip before the merge "
            "and the merge commit by full SHA; the tool's facts, or the file beside the Dispatch record under "
            "`.feather/dispatch/` that holds them, named with its SHA-256; every resolved path; each Claim's outcome with "
            "main's reason; the Adversarial reviews to rerun; and any upstream change to a Claim's reading set.",
        ),
        "merge-upstream SKILL.md#Outcomes": (
            "For each Claim, main writes \"reopens code review and outcome verification\", \"reopens outcome "
            "verification only\" or \"passes stay\", with its reason, judged as review state's What a pass covers "
            "states.",
        ),
        "merge-upstream SKILL.md#Judging": (
            "File overlap is only a candidate: main judges dependencies, fixtures, reading sets and environment itself, "
            "and a Claim is never kept only because the merge did not touch its files.",
            "A merge result that changes a Claim's own files or acceptance checks, a conflict resolution included, "
            "reopens its code review and outcome verification.",
            "A cancelled Claim's commits on the branch are reported as unaccepted, as review state's Commit and "
            "completion describes.",
        ),
        "merge-upstream SKILL.md#Adversarial reviews": (
            "The report lists, for every Security-critical Claim awaiting landing other than a fix Claim, its "
            "Adversarial review at the commit to be landed, with the upstream changes that share security assumptions "
            "with that Claim as input to its brief: read the [adversarial-review "
            "procedure](../delegation/references/adversarial-review.md)'s step 9 and follow it.",
        ),
        "merge-upstream SKILL.md#Reading sets": (
            "An upstream change to a spec, ticket or other text a Claim's reading set cites is reported as a material "
            "deviation for the user to decide, never adopted: read the [plan-review "
            "procedure](../delegation/references/plan-review.md)'s step 5 and follow it.",
        ),
        "merge-upstream SKILL.md#No Plan change": (
            "The report changes no Plan text, ticket or Claim, and adds no ticket or Claim.",
        ),
        "merge-upstream SKILL.md#Hash": (
            "Main records the report's hash with it: the SHA-256 of the entry's text before its hash, READY and "
            "approval.",
        ),
    }

    # Items 25 and 26 and S1: the report's plan review, the scope question asked again and the approval, bound to the
    # report's hash and the merge commit's full SHA.
    PLAN_REVIEW = {
        "merge-upstream SKILL.md#Brief": (
            "The report gets plan review under [the plan-review procedure](../delegation/references/plan-review.md): the "
            "brief carries the report, the Plan, the tool's facts, the Claims' recorded passes, the upstream diff and "
            "the merge result's diff for every path a kept reason relies on, and the full diff of every resolved path, a "
            "path no Claim owns included.",
            "The analyst checks each kept pass's reason, each reopened scope and each resolution.",
        ),
        "merge-upstream SKILL.md#Count": (
            "Calls count as plan review calls of the Plan, continuing its count and stopping at the Stop threshold in "
            "effect, as review state's Stop threshold describes.",
        ),
        "merge-upstream SKILL.md#Scope question": (
            "After READY, main asks the Plan's Final check scope again, as review state's Final check scope describes "
            "for a later plan review.",
        ),
        "merge-upstream SKILL.md#Approval": (
            "Main then asks the user to approve the report, naming its hash, the merge commit and the Claims it keeps "
            "and reopens; the ask states that pushing waits until every pass the report requires is in, and that the "
            "user may ask for an earlier push.",
        ),
        "merge-upstream SKILL.md#Binding": (
            "The READY and the approval hold only for the report's recorded hash and the merge commit's full SHA; a "
            "changed report, a redone merge or a new Upstream merge needs a new report, READY and approval.",
        ),
        "merge-upstream SKILL.md#Who approves": (
            "The approval comes only from the user's own message or the user's answer, as review state's Final check "
            "scope defines it; main records it with that hash and SHA in the Dispatch record, and a resumed session "
            "takes it from there, as review state's Resumed sessions describes.",
        ),
        "merge-upstream SKILL.md#Until approved": (
            "No reopened review runs before the report's READY and approval, and until both hold every Claim the merge "
            "touched counts as reopened, as review state's What a pass covers states.",
        ),
    }

    # Items 28, 29 and 31 and S1: re-review under the original Claims, the final check and Adversarial review at the
    # commit to be landed, and a repeated Upstream merge.
    REREVIEW = {
        "merge-upstream SKILL.md#Original Claims": (
            "Reopened reviews are calls of the original Claims, continuing their counts as review state's Reopened calls "
            "describes, and are recorded in the Plan's own Dispatch record.",
        ),
        "merge-upstream SKILL.md#Briefs": (
            "Their briefs diff each Claim from its original base revision to the commit judged and name the report's "
            "reason for reopening.",
        ),
        "merge-upstream SKILL.md#Existing behaviour": (
            "Existing behaviour is taken both at the Claim's original base revision and at the merged remote tip: a "
            "defect already present at the remote tip is pre-existing unless the merge result changed it, as review "
            "state's Evidence for a regression states.",
        ),
        "merge-upstream SKILL.md#What stays": (
            "Unresolved verdicts, open findings, a BROKEN's findings and recorded holds stay with their Claims, and a "
            "cancelled Claim's commits stay listed.",
            "A Claim kept by an approved report keeps its passes.",
        ),
        "merge-upstream SKILL.md#Final check": (
            "The final check runs at the commit to be landed, the merge commit or a later one, as review state's Final "
            "check describes; a recorded run at an earlier commit does not cover it.",
        ),
        "merge-upstream SKILL.md#Adversarial review": (
            "Every Security-critical Claim awaiting landing, other than a fix Claim, gets Adversarial review at that "
            "commit after that final check passes, whatever the report says about its files: read the [adversarial-review "
            "procedure](../delegation/references/adversarial-review.md)'s At the final commit and follow it.",
        ),
        "merge-upstream SKILL.md#Another merge": (
            "When the remote default branch moves again before landing, a new invocation records a second Upstream merge "
            "after the first, with its own report, READY and approval; the first one's re-review results stay with the "
            "commits they judged.",
        ),
    }

    # Items 30 and 32 and S2: pushing and landing only with the user, the handoff and the lease.
    LANDING = {
        "merge-upstream SKILL.md#Pushing": (
            "Main pushes no commit that has the merge commit as an ancestor before every pass the report requires is "
            "in, unless the user asks for an earlier push to the branch main created, as review state's Commits before "
            "the passes states.",
        ),
        "merge-upstream SKILL.md#Landing": (
            "A Plan with an Upstream merge lands only on the user's own command or Accept and land, never under Auto "
            "land, as review state's Auto land states.",
        ),
        "merge-upstream SKILL.md#End of the Plan": (
            "At the end of the Plan main asks the user as review state's Accept and land at the end of the plan "
            "describes, even when nothing needs accept and land, and the list covers every Claim on the branch with its "
            "state after the integration.",
        ),
        "merge-upstream SKILL.md#Lease": (
            "After the user agrees and before fetching, main takes or renews the Checkout lease of this checkout, as "
            "[the lease rules](../leases/SKILL.md#main-agent-rules) describe, and when it cannot take it, stops as they "
            "describe.",
        ),
        "merge-upstream SKILL.md#Before each wait": (
            "Before every stop that waits for the user, for the agreement to merge, the approval of the report, the "
            "landing decision, an Already landed stop or a conflict main cannot resolve, main updates the work's Active "
            "handoff when one exists and renews its Checkout lease when it holds one; it takes or renews the lease "
            "before merging, as Lease above describes.",
        ),
        "merge-upstream SKILL.md#No record of its own": (
            "This command writes no handoff record of its own.",
        ),
    }

    # Items 24, 26, 27, 28 and 30 and S1 and S2: the review-state sentences an Upstream merge keeps in every session,
    # whether or not the command is loaded.
    REVIEW_STATE = {
        "review-state.md#What a pass covers": (
            # S1.1: the merge commit and upstream's commits never keep a pass fixed.
            "An Upstream merge is main's local merge of the remote default branch into a plan's work branch, made only "
            "as the [merge-upstream command](../../merge-upstream/SKILL.md) describes: the merge commit and every commit "
            "reachable from the merged remote tip are never inside any claim's judged range, whatever range a brief's "
            "diff spans, so they never keep another claim's passes fixed.",
            # S1.3: the file-level rules still reopen.
            "An Integration report keeps only passes that the file-level rules above would not reopen: a merge result "
            "that changes a claim's own files or its acceptance checks reopens its code review and outcome "
            "verification.",
            # S1.2: the reason, READY and approval, bound to the hash and SHA.
            "A claim's passes stay after an Upstream merge only when the file-level rules above would not reopen them, "
            "the merge's Integration report keeps them with a reason, and the report has a valid READY from plan review "
            "and the user's approval, both holding only for the report's recorded hash and the merge commit's full SHA; "
            "otherwise every claim the merge touched counts as reopened.",
            "A changed report, a redone merge or a new Upstream merge needs a new report, READY and approval.",
            # S1.4: who approves.
            "The approval comes only from the user's own message or the user's answer, as Final check scope defines it, "
            "and main records it with that hash and SHA in the plan's dispatch record, as Dispatch record describes.",
            # S1.5 and S1.6: no kept HELD or final check run.
            "An Integration report never keeps a HELD or a final check run: every Security-critical claim awaiting "
            "landing, other than a fix claim, needs Adversarial review at the commit to be landed after the final check "
            "passes there, or accept and land, and no final check run at an earlier commit covers the commit to be "
            "landed.",
        ),
        "review-state.md#Evidence for a regression": (
            # S1.7.
            "In auto, after an Upstream merge, as What a pass covers describes, existing behaviour is taken both at the "
            "claim's original base revision and at the merged remote tip, and every later brief of the claim's code "
            "review, outcome verification and Adversarial review names both: a defect already present at the merged "
            "remote tip is pre-existing unless the merge result changed it.",
        ),
        "review-state.md#Commits before the passes": (
            # S2.4: no early push without the user, in every session.
            "In auto, main pushes no commit that has an Upstream merge's merge commit as an ancestor before every pass "
            "that merge's Integration report requires is in, unless the user's own message or the user's answer, as "
            "Final check scope defines it, asks for an earlier push to the branch main created for the work; this holds "
            "in every session, whether or not the merge-upstream command is loaded.",
            # S2.3.
            "Main discards its own Upstream merge only under the conditions the [merge-upstream "
            "command](../../merge-upstream/SKILL.md) states, and otherwise fixes it with new commits.",
            "It never rewrites pushed history, so a fix is a new commit.",
        ),
        "review-state.md#Auto land": (
            # S2: a plan with an Upstream merge lands only with the user.
            "Auto land does not apply to a plan whose dispatch record holds an Upstream merge: such a plan lands only on "
            "the user's own command, in the user's own message or the user's answer as Final check scope defines it, or "
            "on accept and land, and at its end main asks as Accept and land at the end of the plan describes, even when "
            "nothing listed needs accept and land.",
            # S2.2: a range with a merge commit, whatever the record holds.
            "Main does not land under Auto land when `git rev-list --merges <tip>..<judged commit>` lists any commit, "
            "whatever the plan's dispatch record holds: such a commit is one the range check does not allow.",
            # Auto land's stop suggests the command and does nothing else.
            "When main stops because the remote default branch's tip is not an ancestor of the judged commit, its report "
            "also suggests the [merge-upstream command](../../merge-upstream/SKILL.md), `/cc-feather:merge-upstream`, "
            "which runs only when the user invokes it, and main does nothing else.",
            # Code review call 1, non-blocking 1: an Upstream merge entry, like a hold, can only hold landing.
            "The only records that affect Auto land are a hold a plan's dispatch record keeps, as the next sentences "
            "state, and an Upstream merge entry, as stated above, and each, an Upstream merge entry like a hold, can "
            "only hold landing: no record turns Auto land on or stands in for the user's choice to turn it on.",
        ),
        "review-state.md#Accept and land at the end of the plan": (
            "In auto with Auto land in effect, when nothing listed needs accept and land, main does not ask that "
            "question and lands as Auto land describes, except for a plan whose dispatch record holds an Upstream "
            "merge, for which main asks it; when anything listed needs it, main asks as above.",
            "For a plan whose dispatch record holds an Upstream merge, the list covers every claim on the branch with its "
            "state after the integration, and names each Upstream merge by its merge commit's full SHA and its report's "
            "hash.",
        ),
        "review-state.md#Dispatch record": (
            "It also holds each Upstream merge as an entry after any earlier one, its Integration report as the "
            "[merge-upstream command](../../merge-upstream/SKILL.md) describes: the remote tip, the tip before the merge "
            "and the merge commit by full SHA, the tool's facts or where they are kept, each claim's outcome with main's "
            "reason, the Adversarial reviews to rerun, the report's hash, and its plan-review READY and the user's "
            "approval, each recorded with that hash and the merge commit's full SHA; a resumed session, and main after "
            "a context compaction, take them from there, as Resumed sessions describes.",
        ),
    }

    # S2: the only sentences of the command that mention pulling, rebasing, forcing or pushing. Any other such sentence,
    # such as one that lets main push before the passes or rebase, fails test_only_pinned_sentences_pull_rebase_force_or_push.
    PUSH_SENTENCES = (
        "It never uses `git pull`, never rebases or forces, and pushes nothing in this step.",
        "The tool is read-only: it never fetches, merges, pushes or writes a ref, the index, the working tree or a "
        "record, and it leaves every pass judgement to main and plan review.",
        "Main then asks the user to approve the report, naming its hash, the merge commit and the Claims it keeps and "
        "reopens; the ask states that pushing waits until every pass the report requires is in, and that the user may "
        "ask for an earlier push.",
        "Main pushes no commit that has the merge commit as an ancestor before every pass the report requires is in, "
        "unless the user asks for an earlier push to the branch main created, as review state's Commits before the "
        "passes states.",
        "A push the user makes outside the session is outside these rules: this command sees one only through the "
        "remote-tracking refs a fetch updates, so a push by URL, or to a remote or ref the fetch does not cover, is not "
        "seen before a discard.",
    )
    PUSH_WORDS = re.compile(r"\b(?:pull|pulls|rebase|rebases|rebasing|force|forces|forcing|push|pushes|pushing|pushed)\b",
                            re.I)

    def all_pins(self):
        return (self.INVOCATION, self.FETCH_AND_MERGE, self.DISCARD, self.REPORT, self.PLAN_REVIEW, self.REREVIEW,
                self.LANDING, self.REVIEW_STATE)

    def test_the_command_is_user_invoked_only(self):
        text = COMMAND.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\n"))
        frontmatter = text.split("---")[1]
        self.assertIn("\nname: merge-upstream\n", frontmatter)
        self.assertIn("\ndisable-model-invocation: true\n", frontmatter)
        self.assertRegex(frontmatter, r'\ndescription: "[^"\n]+"\n')

    def test_invocation_preconditions_and_off_mode(self):
        self.assert_pinned(self.INVOCATION)

    def test_fetch_and_merge_never_pull_rebase_force_or_push(self):
        self.assert_pinned(self.FETCH_AND_MERGE)

    def test_already_landed_looks_only_at_the_plans_own_commits(self):
        # Code review call 1, B1: after a first Upstream merge, the commits it brought in are ancestors of every later
        # fetched tip, so a condition over every commit after the base revision would stop each later invocation.
        text = " ".join(source("merge-upstream SKILL.md#Already landed").split())
        self.assertNotIn("When any commit after the Plan's base revision on the work branch is an ancestor", text)
        self.assertIn("When any of the Plan's own commits is an ancestor of the fetched tip", text)
        for excluded in ("the merge commit of every earlier Upstream merge",
                         "every commit reachable from a remote tip such a merge merged"):
            with self.subTest(excluded=excluded):
                self.assertIn(excluded, text)

    def test_only_its_own_unpushed_merge_is_discarded(self):
        self.assert_pinned(self.DISCARD)

    def test_the_integration_report(self):
        self.assert_pinned(self.REPORT)

    def test_the_reports_plan_review_and_approval(self):
        self.assert_pinned(self.PLAN_REVIEW)

    def test_re_review_final_check_and_adversarial_review(self):
        self.assert_pinned(self.REREVIEW)

    def test_pushing_landing_handoff_and_lease(self):
        self.assert_pinned(self.LANDING)

    def test_review_state_keeps_the_upstream_merge_rules(self):
        self.assert_pinned(self.REVIEW_STATE)

    def test_only_pinned_sentences_pull_rebase_force_or_push(self):
        # S2: a sentence that lets main pull, rebase, force or push, other than the pinned ones, fails here.
        body = COMMAND.read_text(encoding="utf-8").split("---", 2)[2]
        lines = [re.sub(r"^- \*\*[^*]+\.\*\* ", "", line) for line in body.splitlines()
                 if not line.startswith("#")]
        found = [sentence for line in lines for sentence in feather_support.sentences(line)
                 if self.PUSH_WORDS.search(sentence)]
        self.assertEqual(sorted(found), sorted(self.PUSH_SENTENCES))

    def test_the_users_answer_is_cited_never_restated(self):
        # The defining sentence lives only in review state's Final check scope; the command points to it.
        text = COMMAND.read_text(encoding="utf-8")
        self.assertNotIn("AskUserQuestion", text)
        self.assertNotIn("an MCP tool that relays a person's reply included", text)
        self.assertEqual(text.count("the user's answer, as review state's Final check scope defines it"), 2)

    def test_the_command_names_the_tools_real_input_and_output(self):
        # S3: the command describes the tool from ticket 01 as it is; a renamed key or part fails here.
        cli = (TOOL / "cli.py").read_text(encoding="utf-8")
        facts = (TOOL / "facts.py").read_text(encoding="utf-8")
        running = source("merge-upstream SKILL.md#Running it")
        output = source("merge-upstream SKILL.md#Its output")
        tool = source("merge-upstream SKILL.md#The tool")
        for key in ("remote", "default_branch", "remote_tip", "tip_before", "merge_commit", "claims"):
            with self.subTest(key=key):
                self.assertIn(f"`{key}`", running)
                self.assertIn(f'"{key}"', cli)
        for key in ("id", "base", "judged", "kind"):
            with self.subTest(claim_key=key):
                self.assertIn(f'"{key}"', running)
                self.assertIn(f'"{key}"', cli)
        for part in ("merge_parents", "as_expected", "merge_base", "upstream", "merge_result", "resolution", "claims",
                     "not-implemented", "classification", "remote_tracking"):
            with self.subTest(part=part):
                self.assertIn(f"`{part}`", output)
                self.assertIn(f'"{part}"', facts)
        discard = source("merge-upstream SKILL.md#When main may discard")
        for part in ("remote_tracking", "contains_merge_commit"):
            with self.subTest(discard=part):
                self.assertIn(f"`{part}`", discard)
                self.assertIn(f'"{part}"', facts)
        self.assertIn("`scripts/merge_upstream.py`", tool)
        self.assertIn("`${CLAUDE_PLUGIN_ROOT}/skills/merge-upstream/scripts/merge_upstream.py`", tool)
        self.assertTrue((config.ROOT / "skills" / "merge-upstream" / "scripts" / "merge_upstream.py").is_file())
        self.assertIn("--project", cli)

    def test_every_link_of_the_command_and_to_it_resolves(self):
        places = {COMMAND: COMMAND.read_text(encoding="utf-8"), REVIEW_STATE: REVIEW_STATE.read_text(encoding="utf-8"),
                  DELEGATION: DELEGATION.read_text(encoding="utf-8")}
        found = 0
        for path, text in places.items():
            for link in re.findall(r"\]\(([^)#\s]+)(?:#[^)]*)?\)", text):
                if "merge-upstream" in link or path == COMMAND:
                    found += 1
                    with self.subTest(place=path.name, link=link):
                        self.assertTrue((path.parent / link).resolve().is_file(), link)
        self.assertGreaterEqual(found, 8)

    def test_every_review_state_pin_is_new(self):
        # Each review-state sentence this ticket adds or changes is absent from the text it started from, so these pins
        # fail if the rule is taken out again. The unchanged sentence about pushed history is left out.
        try:
            shown = subprocess.run(["git", "-c", "core.fsmonitor=", "show",
                                    f"{BASE}:skills/delegation/references/review-state.md"], cwd=config.ROOT,
                                   stdin=subprocess.DEVNULL, capture_output=True, timeout=60)
        except (OSError, subprocess.TimeoutExpired) as error:
            self.skipTest(f"Git cannot be run: {error}")
        if shown.returncode != 0:
            self.skipTest(f"{BASE} cannot be read: {shown.stderr.decode('utf-8', 'replace').strip()}")
        old = " ".join(shown.stdout.decode("utf-8").split())
        for place, sentences in self.REVIEW_STATE.items():
            for sentence in sentences:
                if sentence == "It never rewrites pushed history, so a fix is a new commit.":
                    continue
                with self.subTest(place=place, sentence=sentence[:60]):
                    self.assertNotIn(sentence, old)


if __name__ == "__main__":
    unittest.main()
