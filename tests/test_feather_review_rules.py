"""Review-rule tests: review state and the plan review, code review and outcome verification procedures, including
the review of a fix and the Stop threshold, as the procedures, READMEs and decision records state them."""

from __future__ import annotations

import re
import unittest

from tests import feather_support
from tests.feather_support import config


class ReviewRulesFollowUpTests(unittest.TestCase):
    """0.17.0 review-rule follow-ups (docs/specs/review-followups-0-16-0.md): whole sentences, absences and scenarios."""

    REFERENCES = feather_support.REVIEW_RULES_REFERENCES

    source = staticmethod(feather_support.review_rules_source)

    # C1: the repository authority auto grants, disclosed where auto is turned on and always loaded.
    REPOSITORY_AUTHORITY = {
        "review-state.md#Commits before the passes": (
            "Before its passes, main may commit a claim of plan-driven work in the automatic flow on any branch, push it to a branch main created for the current work and open a pull request whose description lists the claims still unaccepted, without the user's permission, and keeps that list current as claims pass or are accepted.",
            "Before pushing to a remote branch that already existed and that main did not create, it asks the user; in a resumed session main treats a branch as its own only when an active handoff records that main created it for this work, and otherwise asks.",
            "For a claim the gate covers only because an active handoff records it, main may make the local commit a gated call needs without asking, while pushes and pull requests follow off-mode behaviour, so main asks.",
            "Before dispatching a gated code review, outcome verification or Adversarial review, main ensures the claim's content is committed and the precondition of What a gated pass judged holds; when a commit is needed, the authority above permits it without asking, and an already suitable commit needs no new one.",
        ),
        "review-state.md#Repository authority": (
            "The authority under Commits before the passes covers committing, pushing and opening pull requests only.",
            "Opening a pull request is not permission to merge it, and a pass is a condition for landing or release, not a request to perform either: landing, merging, releasing and tagging need the user's authority for that operation.",
            "An explicit user instruction not to commit or not to push overrides this authority within its scope; when it leaves a gated call without the commit it needs, main reports the claim blocked rather than reviewing an uncommitted workspace.",
        ),
        "review-auto.md": (
            "In auto, before the passes of a claim of plan-driven work main may, without asking, commit it, push it to a branch main created for the current work and open a pull request listing the unaccepted claims; it asks before pushing to a branch it did not create, an explicit instruction not to commit or push wins, and a pull request is not permission to merge.",
            "Landing on the default branch, release, reporting complete and ticket completion still wait for both passes, plus a valid HELD for a Security-critical claim, or the user's explicit accept-and-land decision, as cc-feather:delegation's review state describes.",
        ),
        "auto-review.md#Meaning": (
            "`auto` also lets main, before the passes of a claim of plan-driven work and without asking, commit it, push it to a branch main created for the current work and open a pull request listing the unaccepted claims, as [review state](../../delegation/references/review-state.md) describes; main asks before pushing to a branch it did not create, an explicit instruction not to commit or push wins, and landing on the default branch, release, reporting complete and ticket completion still wait for both passes, plus a valid HELD for a Security-critical claim, or the user's explicit accept-and-land decision.",
            "Beyond that repository authority, turning a mode on or off grants no authority to implement, merge or release,",
        ),
        "auto-on": (
            "which lets main commit, push to branches it created and open pull requests before acceptance without asking, while landing, release and completion still wait for both passes, plus HELD for a Security-critical claim, or the user's explicit accept-and-land decision",
        ),
        "README.md#Commit": (
            "in auto, main may commit a claim of plan-driven work before its passes, push it to a branch it created for the work and open a pull request that lists the claims still unaccepted, without asking.",
            "It asks before pushing to a branch that already existed and that it did not create; in a resumed session a branch counts as its own only when an active handoff records that it created it for this work.",
            "Opening a pull request is not permission to merge it, a pass is not a request to land or release, and your explicit instruction not to commit or not to push wins; a claim whose review or verification then lacks its commit is reported blocked.",
            "For a claim gated only because an active handoff records it as unreviewed, unverified or pending acceptance, main may make the local commit a review or verification needs without asking, and asks before pushes and pull requests, as in `off`.",
        ),
        "README.zh-TW.md#Commit 條件": (
            "在 auto 下，主 Agent 可以不經詢問，在依計畫施工的 claim 通過前先 commit，推到它為這項工作建立的 branch，並開 PR 列出尚未驗收的 claim。",
            "要推到原本就存在、不是它建立的 branch 前，會先問你；恢復的 session 裡，只有進行中的交接記錄了它為這項工作建立該 branch，才算它自己的 branch。",
            "開 PR 不等於可以 merge，通過也不代表要 land 或 release；你明確說不要 commit 或不要 push 時，以你的指示為準，因此審查或驗證缺少所需 commit 時，該 claim 會回報為受阻。",
            "只因進行中的交接記錄為未審查、未驗證或待驗收而受把關的 claim，主 Agent 可以不經詢問做審查或驗證所需的本機 commit，但 push 與開 PR 會先問你，和 `off` 相同。",
        ),
        "README.md": (
            "enabled mode `auto` reviews plan-driven work and lets main, without asking, commit its claims before their passes, push them to branches it created for the work and open pull requests that list the unaccepted claims; landing on the default branch, release, reporting complete and ticket completion still wait for both passes, plus HELD for a Security-critical claim, or your explicit accept-and-land decision (see Commit and Your decisions above).",
        ),
        "README.zh-TW.md": (
            "開啟後的 `auto` 審查依計畫施工的工作，並讓主 Agent 不經詢問，在 claim 通過前先 commit、推到它為這項工作建立的 branch，以及開 PR 列出尚未驗收的 claim；進入預設 branch、release、回報完成與把 ticket 設成完成，仍要等兩關都通過（安全關鍵 claim 還要加上 HELD），或你明確決定「接受並合併」（見上方 Commit 條件與你的決定）；",
        ),
        "CONTEXT.md#Acceptance gate": (
            "The rule that a gated Claim, one of Plan-driven work in the Automatic flow or one an active handoff records as unreviewed, unverified or pending acceptance, is landed, released or tagged, reported complete or has its ticket set to a done value only with a valid APPROVED and a valid CONFIRMED, and for a Security-critical claim a valid HELD as well, or with the user's Accept and land decision.",
            "Committing it, and in auto pushing it to a branch main created and opening a pull request, are not gated; review state's Commits before the passes and Repository authority limit when main may do them.",
        ),
        "CONTEXT.md#Landing": (
            "Putting a Claim on the remote default branch by pushing it there or merging it, directly or through a pull request.",
            "Opening a pull request is not landing, and permission to open one is not permission to merge it.",
        ),
    }

    # 0.16.0 wording that granted push and pull-request authority in either mode or to any non-default branch.
    REPOSITORY_AUTHORITY_REMOVED = {
        "review-state.md": ("push it to any branch other than a default branch",
                            "main may commit such a claim on any branch"),
        "README.md": ("in the automatic flow, and for any claim an active handoff records as unreviewed or unverified, main may commit",
                      "push it to any branch other than the default branch"),
        "README.zh-TW.md": ("以及進行中的交接記錄為未審查或未驗證的 claim，主 Agent 可以在通過前先 commit",
                            "並推到預設 branch 以外的 branch"),
        "auto-review.md": ("Turning a mode on/off does not grant implementation authority",),
    }

    def test_repository_authority_is_stated_whole(self):
        for place, sentences in self.REPOSITORY_AUTHORITY.items():
            text = self.source(place)
            for sentence in sentences:
                with self.subTest(place=place, sentence=sentence[:60]):
                    self.assertIn(sentence, text)

    def test_repository_authority_wording_from_0_16_0_is_gone(self):
        for place, phrases in self.REPOSITORY_AUTHORITY_REMOVED.items():
            text = self.source(place)
            for phrase in phrases:
                with self.subTest(place=place, phrase=phrase[:60]):
                    self.assertNotIn(phrase, text)

    def test_rendered_auto_guidance_discloses_the_repository_authority(self):
        disclosure = self.REPOSITORY_AUTHORITY["review-auto.md"]
        for scope in ("user", "project"):
            rendered = config._policy("auto", scope=scope)
            for sentence in disclosure:
                with self.subTest(scope=scope, sentence=sentence[:60]):
                    self.assertIn(sentence, rendered)
        self.assertNotIn(disclosure[0], config._policy("off", scope="project"))

    # C2: one explicit way past the gate without both passes; finished is not accepted; won't-do is not acceptance.
    ACCEPTANCE_AND_COMPLETION = {
        "review-state.md#Commit and completion": (
            "reports it complete or sets its ticket to a done value only with a valid APPROVED and a valid CONFIRMED, and for a Security-critical claim a valid HELD as well, or with the user's accept-and-land decision for it.",
            "It covers the completion value for done work; a value for work that will not be done is set only on the user's recorded cancellation and never counts as acceptance.",
            "A cancelled claim's commits that remain on a branch are listed as unaccepted, in the report and in any active handoff, until the user decides their disposition: reverted with a new commit, kept off the default branch, or accepted and landed; landing a branch that carries them waits for that decision.",
        ),
        "review-state.md#Ticket status": (
            "after an accept-and-land decision it does the same, and the note also names the decision and its remaining risk.",
            "Finished means not redone, not accepted: only a ticket set to a done value after valid passes or an accept-and-land decision counts as accepted for landing and release, and only while no relevant change has reopened its claim.",
            "A value for work that will not be done never counts as acceptance.",
        ),
        "review-state.md#User decisions": (
            "main records the decision as one of re-review, deferral, cancellation, changed acceptance, waiver or accept and land, with its scope.",
            "its commits left on a branch stay listed until the user decides their disposition, as under Commit and completion.",
            "A waiver accepts a named open finding or missing pass and names what it waives; a missing READY can be waived as Implemented before plan review describes.",
            "A waiver does not complete a claim the acceptance gate covers: such a claim is landed on the default branch, released or reported complete only after a later pass or an accept-and-land decision.",
            "Separately, a work-in-progress push the user allows may move a gated claim's commits to the default branch, labelled as under Commits before the passes; it satisfies neither release nor completion.",
            "Accept and land is the user's explicit acceptance of a named gated claim without one or both passes or, for a Security-critical claim, without a valid HELD.",
            "Main records its scope, the commit it accepts, the missing passes and the remaining risk; it stays visible in the report and in any active handoff, is never recorded as READY, APPROVED, CONFIRMED or HELD, and satisfies the acceptance gate for that claim as it stands.",
            "A later relevant change to the claim ends it, as for a pass.",
            "Unlike a pass, it is the user's decision, so one recorded in an active handoff still satisfies the gate in a resumed session while no relevant change has followed the commit it names.",
            "A user statement that work is done counts as acceptance only after main confirms it with the user and records it as accept and land; otherwise it means the work is not to be redone.",
        ),
        "review-state.md#Resumed sessions": (
            "Only a claim whose ticket was set to a done value after valid passes or an accept-and-land decision, with no relevant change since, is exempt and counts as accepted for landing and release, as is a claim whose pending-acceptance note records an accept-and-land decision that still holds; any other finished ticket is only not redone.",
        ),
        "review-state.md#Claim changes": ("such as setting a value for work that will not be done after a cancellation.",),
        "review-auto.md": ("still wait for both passes, plus a valid HELD for a Security-critical claim, or the user's explicit accept-and-land decision, as cc-feather:delegation's review state describes.",),
        "auto-review.md#Meaning": ("still wait for both passes, plus a valid HELD for a Security-critical claim, or the user's explicit accept-and-land decision.",),
        "README.md#Commit": (
            "main lands the claim on the remote default branch, releases it, reports it complete or marks its ticket done only with a valid APPROVED and CONFIRMED, plus a valid HELD for a Security-critical claim, or with your accept-and-land decision.",
            "A cancelled claim's commits left on a branch stay listed as unaccepted until you decide to revert them, keep them off the default branch or accept and land them; a branch carrying them is not landed before that.",
        ),
        "README.md#Your decisions": (
            "main records what you decide as one of re-review, deferral, cancellation, changed acceptance, waiver or accept and land, with its scope.",
            "A waiver names the finding or missing pass it waives, stays visible with its remaining risk and never counts as READY, APPROVED, CONFIRMED or HELD, so a waived claim the acceptance gate covers is landed on the default branch, released or reported complete only after a later pass or your accept-and-land decision.",
            "A work-in-progress push you allow can move its commits to the default branch, but it is neither a release nor completion.",
            "Accept and land is your explicit acceptance of a named claim without one or both passes, or of a Security-critical claim without its HELD: main records the commit it accepts, the missing passes and the remaining risk, and for a missing HELD the known vulnerabilities, keeps them visible in reports and any active handoff, and the acceptance gate then no longer holds back landing, release or completion of that claim; a later relevant change ends it, and one recorded in an active handoff still holds in a resumed session until such a change.",
            "Saying the work is done counts as acceptance only after main confirms it with you and records it as accept and land;",
        ),
        "README.md#Resumed session": (
            "unless its ticket was set to a done value after both passes (plus HELD for a Security-critical claim) or your accept-and-land decision and nothing relevant changed since.",
        ),
        "README.md#Ticket status": (
            "After an accept-and-land decision main does the same and notes the decision and its remaining risk.",
            "Finished only means it is not redone: a ticket counts as accepted only when it was set to a done value after both passes (plus HELD for a Security-critical claim) or your accept-and-land decision and nothing relevant changed since, and a value for work that will not be done, such as `wontfix`, is set only when you cancel and never counts as acceptance.",
        ),
        "README.zh-TW.md#Commit 條件": (
            "以上 claim 都只有在 APPROVED 與 CONFIRMED（安全關鍵 claim 還要加上 HELD）都仍有效，或你決定接受並合併時，才會讓 claim 進入遠端的預設 branch、release、回報完成或把 ticket 設成完成。",
            "取消的 claim 留在 branch 上的 commit 會一直列為未驗收，直到你決定用新 commit revert、不讓它進入預設 branch，或接受並合併；在那之前，帶著它們的 branch 不會被合併。",
        ),
        "README.zh-TW.md#你的決定": (
            "主 Agent 會把你的決定記為重審、延後、取消、修改驗收、豁免或接受並合併其中一種，並註明範圍。",
            "豁免會寫明它豁免的是哪個問題或缺少的哪一關，",
            "你允許的工作中途推送可以把它的 commit 推到預設 branch，但不算 release，也不算完成。",
            "接受並合併是你明確接受某個 claim，即使它缺少一關或兩關，或安全關鍵 claim 缺少 HELD：主 Agent 會記下所接受的 commit、缺少的關卡與剩餘風險，缺少 HELD 時還會記下已知漏洞，在回報與進行中的交接中持續列出，之後驗收把關就不再擋下該 claim 的合併、release 或完成；之後若有相關變更就失效，記在進行中交接的決定在恢復的 session 仍然有效，直到發生這種變更。",
            "你說工作已完成，要等主 Agent 向你確認並記為接受並合併，才算驗收；",
        ),
        "README.zh-TW.md#恢復的 session": (
            "之前 session 通過的 claim 要重新審查與驗證，安全關鍵 claim 也要重新做對抗式審查；只有 ticket 是在兩關通過（安全關鍵 claim 還要加上 HELD）或你決定接受並合併之後才設成表示已完成的完成值、且之後沒有相關變更的 claim 例外。",
        ),
        "README.zh-TW.md#Ticket 狀態": (
            "你決定接受並合併後，主 Agent 也會這樣做，並註明這個決定與剩餘風險。",
            "完成只代表不再重做：ticket 要在兩關通過（安全關鍵 claim 還要加上 HELD）或你決定接受並合併之後才設成表示已完成的完成值，且之後沒有相關變更，才算已驗收；表示不會做的值（例如 `wontfix`）只在你取消時設定，絕不算驗收。",
        ),
        "CONTEXT.md#Accept and land": (
            "The user's explicit, recorded acceptance of a named gated Claim without one or both passes, or of a Security-critical claim without its HELD, with the commit it accepts, the missing passes and the remaining risk, and for a missing HELD the known vulnerabilities.",
            "It satisfies the Acceptance gate for that Claim until a relevant change, is never READY, APPROVED, CONFIRMED or HELD, and a casual \"done\" becomes one only after main confirms and records it.",
        ),
        "README.md#Not passed": ("Your accept-and-land decision is the only exception (see Your decisions).",),
        "README.zh-TW.md#未通過": ("唯一例外是你決定接受並合併（見你的決定）。",),
        "CONTEXT.md#Unreviewed claim": ("The only exception is the user's Accept and land decision.",),
        "CONTEXT.md#Unverified claim": ("The only exception is the user's Accept and land decision.",),
        "review-state.md#Commits before the passes": ("It pushes such commits to the remote default branch only after both passes, plus a valid HELD for a Security-critical claim, or the user's accept-and-land decision for their claim, or as a work-in-progress push the user explicitly allows,",),
        "issue-tracker.md": (
            "`resolved` means the ticket was implemented and accepted (both passes, plus HELD for a Security-critical claim, or the user's accept-and-land decision) and committed, with a `## Comments` note naming the version or commit and, for accept and land, the decision and its remaining risk;",
            "`wontfix` means it will not be done, is set only on the user's recorded cancellation and never counts as acceptance.",
        ),
        "handoff SKILL.md#Archive completed work": (
            "A work is complete only after each gated claim it records is accepted (both passes, plus a valid HELD for a Security-critical claim, or the user's accept-and-land decision) or cancelled with its commits' disposition decided.",
            "A deferred gated claim keeps the work, its note and any unaccepted commits open, and closing tickets or ending a session does not make it complete.",
        ),
    }

    # 0.16.0 wording that treated any finished ticket as accepted or tied a waiver to a work-in-progress push.
    # Historical ADR and spec text is not rewritten, so only these places are checked.
    ACCEPTANCE_AND_COMPLETION_REMOVED = {
        "review-state.md#Resumed sessions": ("a claim whose ticket is finished is not redone and counts as accepted for landing and release",),
        "README.md#Resumed session": ("unless its ticket is finished",),
        "README.zh-TW.md#恢復的 session": ("除非它的 ticket 已完成",),
        "review-state.md#User decisions": ("or pushed to the default branch as a work-in-progress push the user allows with its commits labelled",
                                           "re-review, deferral, cancellation, changed acceptance or waiver,"),
        "README.md#Your decisions": ("or pushed to the default branch as a work-in-progress push you allow",),
        "README.zh-TW.md#你的決定": ("或在你允許下把工作中途的 commit 推到預設 branch",),
        "review-state.md#Commit and completion": ("sets its ticket to a completion value only with",),
        "review-state.md#Commits before the passes": ("only after both passes, or as a work-in-progress push",),
        "CONTEXT.md#Acceptance gate": ("set to a completion value only with",),
        "handoff SKILL.md#Archive completed work": ("or deferred into separate work",),
    }

    def test_acceptance_and_completion_are_stated_whole(self):
        for place, sentences in self.ACCEPTANCE_AND_COMPLETION.items():
            text = self.source(place)
            for sentence in sentences:
                with self.subTest(place=place, sentence=sentence[:60]):
                    self.assertIn(sentence, text)

    def test_acceptance_wording_from_0_16_0_is_gone(self):
        for place, phrases in self.ACCEPTANCE_AND_COMPLETION_REMOVED.items():
            text = self.source(place)
            for phrase in phrases:
                with self.subTest(place=place, phrase=phrase[:60]):
                    self.assertNotIn(phrase, text)

    # C3: a gated claim stays gated after either single pass until it is landed, released, reported complete or cancelled.
    GATE_LIFETIME = {
        "review-state.md#Pending acceptance": (
            "A gated claim stays gated after either single pass, and a Security-critical claim after both until it also has a valid HELD.",
            "When a pass resolves an active handoff's unreviewed or unverified note for a gated claim, main replaces it with a note that the claim is pending acceptance, naming what is still missing and that it must not be landed on the default branch, released or reported complete.",
            "An accept-and-land decision does not remove the note: main records the decision in it, turning an unreviewed or unverified note into a pending-acceptance note, and the note then counts as the record that keeps the claim under the gate until it is landed.",
            "Main removes the note only when the claim is landed, released or reported complete, or cancelled with its commits disposed of; a deferral keeps it and a waiver stays visible in it.",
            "When a relevant change ends an accept-and-land decision, the note returns to pending acceptance, naming what is missing.",
            "A resumed session that finds a pending-acceptance note keeps the claim under the gate and obtains passes from the current session, as passing verdicts do not cross sessions, unless the note records an accept-and-land decision that still holds or the claim's ticket is exempt as under Resumed sessions.",
        ),
        "review-state.md#Commit and completion": ("and for any claim an active handoff records as unreviewed, unverified or pending acceptance, main lands the claim",),
        "review-state.md#Existing handoff notes": ("An active handoff's record that a claim is unreviewed, unverified or pending acceptance restricts it under the acceptance gate whatever its wording,",),
        "review-state.md#Resumed sessions": ("as is a claim whose pending-acceptance note records an accept-and-land decision that still holds;",),
        "code-review.md": ("When a later call passes it, replace that note with a pending-acceptance note naming what is still missing; change or remove the note only as [review state](review-state.md)'s Pending acceptance describes, so a deferral keeps it and a waiver stays visible in it.",
                           "a claim an active handoff records as unreviewed, unverified or pending acceptance, and the handoff note changes after a pass as [review state](review-state.md)'s Pending acceptance describes in either mode;"),
        "outcome-verification.md": ("When a later call passes it, replace that note with a pending-acceptance note naming what is still missing; change or remove the note only as [review state](review-state.md)'s Pending acceptance describes, so a deferral keeps it and a waiver stays visible in it.",),
        "README.md#Not passed": (
            "After a pass, the note says the claim is pending acceptance and names what is still missing; it is removed only when the claim is landed, released or reported complete, or cancelled with its commits decided, so an approval alone, as from an explicit review in `off`, never lets the claim reach the default branch.",
            "A deferral keeps the note and a waiver stays recorded in it.",
        ),
        "README.zh-TW.md#未通過": (
            "通過其中一關後，記錄會改成這個 claim 待驗收，並寫明還缺什麼；只有在 claim 進入預設 branch、release、回報完成，或取消且其 commit 已有決定時才移除，所以單靠一次通過（例如 `off` 下明確要求的審查）絕不會讓 claim 進入預設 branch。",
        ),
        "README.md#Resumed session": (
            "A claim whose handoff note says it is pending acceptance stays gated and needs both passes, plus HELD for a Security-critical claim, in the new session, unless the note records your accept-and-land decision and nothing relevant changed since, or its ticket was set to a done value as above.",
        ),
        "README.zh-TW.md#恢復的 session": (
            "交接記錄為待驗收的 claim 仍受把關，在新的 session 要重新通過兩關（安全關鍵 claim 還要加上 HELD），除非記錄裡有你接受並合併的決定且之後沒有相關變更，或它的 ticket 已如上所述設成表示已完成的完成值。",
        ),
        "CONTEXT.md#Active handoff": (
            "An unfinished Feather handoff record for the work under the project's `.feather/handoffs/`.",
            "It is how unresolved verdicts and gate notes reach a resumed session.",
        ),
        "CONTEXT.md#Pending-acceptance claim": (
            "A gated Claim whose Active handoff note says it has passed one or more of the steps it needs (code review, outcome verification and, for a Security-critical claim, Adversarial review), or has an Accept and land decision, but is not yet landed, released or reported complete.",
            "It stays under the Acceptance gate until then, or until it is cancelled with its commits decided.",
        ),
    }

    # 0.16.0 wording that removed the handoff note once a single later call passed.
    GATE_LIFETIME_REMOVED = {
        "code-review.md": ("Once the claim is resolved, because a later call passes it or the user decides",),
        "outcome-verification.md": ("Once the claim is resolved, because a later call passes it or the user decides",),
        "README.md#Not passed": ("An active handoff records what remains unresolved until it is resolved;",),
        "README.zh-TW.md#未通過": ("會記下尚未解決的結論，解決後移除",),
    }

    def test_gate_lifetime_is_stated_whole(self):
        for place, sentences in self.GATE_LIFETIME.items():
            text = self.source(place)
            for sentence in sentences:
                with self.subTest(place=place, sentence=sentence[:60]):
                    self.assertIn(sentence, text)

    def test_gate_lifetime_wording_from_0_16_0_is_gone(self):
        for place, phrases in self.GATE_LIFETIME_REMOVED.items():
            text = self.source(place)
            for phrase in phrases:
                with self.subTest(place=place, phrase=phrase[:60]):
                    self.assertNotIn(phrase, text)

    # C4: review scope follows established coverage, not call count; budgets are unchanged.
    RETRY_COVERAGE = {
        "review-state.md#Completed calls and coverage": (
            "A completed call is one that returned a verdict for the content it judged; a call that failed, was interrupted, broke protocol or returned no verdict did not complete.",
            "Only a completed review establishes coverage.",
            "A second review, narrowed to the earlier findings and the fixes, and the range from the previously judged commit follow only when the previous call completed.",
            "After a call that did not complete, the next call reviews the claim's full scope from its base revision (for plan review, the whole plan), carrying any partial findings as evidence, not as coverage.",
            "Every attempted call still counts as under What counts as a call, and the budgets are unchanged.",
        ),
        "review-state.md#What a gated pass judged": (
            "and a second review after a completed review receives the range from the previously judged commit to the new one, as Completed calls and coverage describes.",
        ),
        "code-review.md": (
            "On a later call for the same claim, state whether the previous call completed with a verdict; the reviewer narrows its review only when the brief says it did, as [review state](review-state.md)'s Completed calls and coverage describes.",
            "the range from the previously judged commit to the new one; when the previous call did not complete, supply instead the full range from the claim's base revision with earlier and partial findings as evidence.",
        ),
        "plan-review.md": (
            "On a later call for the same plan, state whether the previous call completed with a verdict; analyst narrows its review only when the brief says it did, and otherwise reviews the whole plan, as [review state](review-state.md)'s Completed calls and coverage describes.",
        ),
        "reviewer.md": ('When the brief says the previous call for this claim completed with a verdict, check only whether the earlier findings are closed and whether the fixes introduced regressions; do not expand into unrelated work. When it does not, because that call failed, was interrupted, broke protocol or returned no verdict, review the full scope from the base revision and treat earlier and partial findings supplied as evidence only.',),
        "analyst.md": ('When the brief says the previous call for this plan completed with a verdict, verify resolved blockers and material regressions introduced by the revision without expanding into unrelated work; when it does not, because that call failed, was interrupted, broke protocol or returned no verdict, review the whole plan and treat earlier and partial findings supplied as evidence only.',),
        # Budgets stay as they were.
        "review-state.md#Stop": ("As many consecutive automatic calls without a pass as the Stop threshold in effect stop the step for that work; it waits for the user's explicit request.",),
        "review-state.md#What counts as a call": ("Every attempted call counts, including a generic retry after a temporary failure, and a stopped step is never dispatched again as a retry.",),
    }

    RETRY_COVERAGE_REMOVED = {
        "reviewer.md": ("On a second review, check only whether the earlier findings are closed", "an earlier review of this claim completed"),
        "analyst.md": ("On a second review, verify resolved blockers", "an earlier review of this plan completed"),
        "review-state.md#What a gated pass judged": ("The pass covers that commit, and a second review receives the range",),
    }

    def test_retry_coverage_is_stated_whole(self):
        for place, sentences in self.RETRY_COVERAGE.items():
            text = self.source(place)
            for sentence in sentences:
                with self.subTest(place=place, sentence=sentence[:60]):
                    self.assertIn(sentence, text)

    def test_retry_coverage_wording_from_0_16_0_is_gone(self):
        for place, phrases in self.RETRY_COVERAGE_REMOVED.items():
            text = self.source(place)
            for phrase in phrases:
                with self.subTest(place=place, phrase=phrase[:60]):
                    self.assertNotIn(phrase, text)

    def test_installed_reviewer_and_analyst_render_the_coverage_rule(self):
        choice = {"model": "sonnet", "effort": "high"}
        for role, sentence in (("reviewer", 'When the brief says the previous call for this claim completed with a verdict, check only whether the earlier findings are closed and whether the fixes introduced regressions; do not expand into unrelated work. When it does not, because that call failed, was interrupted, broke protocol or returned no verdict, review the full scope from the base revision and treat earlier and partial findings supplied as evidence only.'), ("analyst", 'When the brief says the previous call for this plan completed with a verdict, verify resolved blockers and material regressions introduced by the revision without expanding into unrelated work; when it does not, because that call failed, was interrupted, broke protocol or returned no verdict, review the whole plan and treat earlier and partial findings supplied as evidence only.')):
            for prefix in ("", "cc-"):
                with self.subTest(role=role, prefix=prefix):
                    self.assertIn(sentence, config._render(role, choice, prefix).decode("utf-8"))

    # C8: the 0.17.0 release records its decisions and requires setup update.
    RELEASE_0_17_0 = {
        "README.md": (
            "0.17.0 changes the reviewer and analyst role definitions and the automatic review guidance, so run setup update in every scope where delegation is installed, then start a fresh session; until then `check` reports the roles from an older template, and `model`, `review` and session export ask for setup update first, in `auto` and in `off`.",
        ),
        "README.zh-TW.md": (
            "0.17.0 改了 reviewer 與 analyst 的角色定義和自動審查指引，所以每個裝有分派元件的範圍都要跑 setup update，再開新 session；在那之前，`auto` 與 `off` 下 check 都會回報來自較舊範本的角色，`model`、`review` 與 session export 也會要求先做 setup update。",
        ),
    }

    def test_release_0_17_0_requires_setup_update(self):
        for place, sentences in self.RELEASE_0_17_0.items():
            text = self.source(place)
            for sentence in sentences:
                with self.subTest(place=place, sentence=sentence[:60]):
                    self.assertIn(sentence, text)
        entry = (config.ROOT / "docs" / "setup-validation.md").read_text(encoding="utf-8").split("## 0.17.0 ", 1)[1].split("\n## ", 1)[0]
        for sentence in ("**Setup update is required.** Unlike 0.14.0–0.16.0, this release changes the reviewer and analyst role definitions and the automatic review guidance: run setup update in every scope where delegation is installed, then start a fresh session.",
                         "`v0.16.0` tags da4948c, the clarification commit after the 0.16.0 release commit cd74ac4; this entry does not move it.",
                         "Live scenarios: none of C1–C4's new rules was exercised by a session running the 0.17.0 rules with installed roles."):
            with self.subTest(entry=sentence[:50]):
                self.assertIn(sentence, entry)
        self.assertNotIn("no setup update is required", entry)

    def test_adr_0008_records_the_decisions_and_amends_adr_0007(self):
        adr = config.ROOT / "docs" / "adr"
        decision = (adr / "0008-repository-authority-acceptance-and-gate-lifetime.md").read_text(encoding="utf-8")
        for phrase in ("**U1**: in auto, committing before the passes, pushing to working branches and opening pull requests stay on, and are disclosed",
                       "**U2**: main pushes freely only to a branch it created for the current work and asks before pushing to a pre-existing remote branch it did not create",
                       "**U3**: a sixth user decision, accept and land, is the only way past the acceptance gate without both passes",
                       "**U4**: in off mode, a Claim gated only by an active handoff record gets the local commit a gated call needs",
                       "**U5**: an accept-and-land decision recorded in an active handoff still holds in a resumed session",
                       "**U6**: when the handoff tool's first Git probe cannot run Git or times out",
                       "**U7**: the configuration tool reports an unedited managed role rendered from an older template as needing setup update",
                       "**Gate lifetime.** A gated Claim stays gated after either single pass.",
                       "**Retry coverage.** Only a completed call establishes coverage.",
                       "**Completion values.** The gate covers done values;",
                       "This amends ADR 0007's push rule, its handoff-note lifetime and its rule that a finished ticket counts as accepted: the gate covers done values, finished means not redone, and only a done value set after valid passes or accept and land, with no relevant change since, counts as accepted.",
                       "so every scope where delegation is installed needs setup update and a fresh session"):
            with self.subTest(phrase=phrase[:50]):
                self.assertIn(phrase, decision)
        note = '(Amended by ADR 0008: in auto, main pushes freely only to a branch it created for the current work and asks before pushing to a pre-existing one; in off, a Claim gated by a handoff record gets only the local commit a gated call needs; a pass turns the handoff note into a pending-acceptance note that stays until the Claim is landed, released or reported complete, or cancelled with its commits disposed of; the user may accept and land a Claim without both passes; the gate covers done values, and a finished ticket counts as accepted only when it was set to a done value after valid passes or accept and land, with no relevant change since.)'
        self.assertIn(note, (adr / "0007-commit-before-acceptance.md").read_text(encoding="utf-8").splitlines())
        self.assertIn("(Amended by ADR 0008: a finished ticket counts as accepted only when it was set to a done value after valid passes or an accept-and-land decision, with no relevant change since; a won't-do value never counts as acceptance.)",
                      (adr / "0006-review-state-validity-and-completion.md").read_text(encoding="utf-8").splitlines())

    # Each scenario names the outcome and the sentences that decide it; a sentence from 0.16.0 that would
    # decide it differently must be gone. Places are '<file>' or '<file>#<bullet label>'.
    TRANSITION_SCENARIOS = (
        ("a code review call fails before returning a verdict, then the next call",
         "the next call reviews the full scope from the base revision; the failed call still counts",
         (("review-state.md#Completed calls and coverage", "After a call that did not complete, the next call reviews the claim's full scope from its base revision (for plan review, the whole plan), carrying any partial findings as evidence, not as coverage."),
          ("reviewer.md", "When it does not, because that call failed, was interrupted, broke protocol or returned no verdict, review the full scope from the base revision and treat earlier and partial findings supplied as evidence only."),
          ("review-state.md#What counts as a call", "Every attempted call counts, including a generic retry after a temporary failure,")),
         (("reviewer.md", "On a second review, check only whether the earlier findings are closed"),)),
        ("a review is interrupted after reporting partial findings",
         "the partial findings go to the next call as evidence, not as coverage",
         (("review-state.md#Completed calls and coverage", "carrying any partial findings as evidence, not as coverage."),
          ("code-review.md", "when the previous call did not complete, supply instead the full range from the claim's base revision with earlier and partial findings as evidence.")),
         ()),
        ("a completed review, then a follow-up call fails, then another call",
         "the next call reviews the full scope from the base revision; earlier and partial findings are evidence",
         (("review-state.md#Completed calls and coverage", "After a call that did not complete, the next call reviews the claim's full scope from its base revision (for plan review, the whole plan), carrying any partial findings as evidence, not as coverage."),
          ("code-review.md", "when the previous call did not complete, supply instead the full range from the claim's base revision with earlier and partial findings as evidence."),
          ("reviewer.md", "When it does not, because that call failed, was interrupted, broke protocol or returned no verdict, review the full scope from the base revision")),
         (("reviewer.md", "an earlier review of this claim completed"),
          ("review-state.md#Completed calls and coverage", "and that range starts at the last commit a completed review judged."))),
        ("a plan review call fails, then the next call",
         "analyst reviews the whole plan",
         (("analyst.md", "when it does not, because that call failed, was interrupted, broke protocol or returned no verdict, review the whole plan and treat earlier and partial findings supplied as evidence only."),
          ("plan-review.md", "analyst narrows its review only when the brief says it did, and otherwise reviews the whole plan,")),
         (("analyst.md", "On a second review, verify resolved blockers"),)),
        ("as many consecutive automatic calls as the Stop threshold fail (budget exhausted)",
         "the step stops and waits for the user's explicit request; nothing changes the budget",
         (("review-state.md#Stop", "As many consecutive automatic calls without a pass as the Stop threshold in effect stop the step for that work; it waits for the user's explicit request."),
          ("review-state.md#Completed calls and coverage", "Every attempted call still counts as under What counts as a call, and the budgets are unchanged.")),
         ()),
        ("off mode, an active handoff records the claim as unreviewed, an explicit code review returns APPROVED",
         "the note becomes pending acceptance and the claim stays gated; no verification starts",
         (("review-state.md#Pending acceptance", "A gated claim stays gated after either single pass, and a Security-critical claim after both until it also has a valid HELD."),
          ("code-review.md", "When a later call passes it, replace that note with a pending-acceptance note naming what is still missing;"),
          ("code-review.md", "An explicit user request for code review applies in either mode and does not start verification."),
          ("README.md#Not passed", "so an approval alone, as from an explicit review in `off`, never lets the claim reach the default branch.")),
         (("code-review.md", 'Once the claim is resolved, because a later call passes it or the user decides'),)),
        ("off mode, an active handoff records the claim as unverified, an explicit verification returns CONFIRMED",
         "the note becomes pending acceptance and the claim stays gated",
         (("outcome-verification.md", "When a later call passes it, replace that note with a pending-acceptance note naming what is still missing;"),
          ("review-state.md#Pending acceptance", "A gated claim stays gated after either single pass, and a Security-critical claim after both until it also has a valid HELD.")),
         (("outcome-verification.md", 'Once the claim is resolved, because a later call passes it or the user decides'),)),
        ("both passes, not yet landed",
         "the pending-acceptance note stays until the claim is landed, released or reported complete",
         (("review-state.md#Pending acceptance", "Main removes the note only when the claim is landed, released or reported complete, or cancelled with its commits disposed of;"),),
         ()),
        ("a relevant edit after a pass",
         "code review and outcome verification reopen for the claim",
         (("review-state.md", "A later change to a claim's files or to what they depend on reopens code review and outcome verification for that claim;"),),
         ()),
        ("a resumed session finds a pending-acceptance note",
         "the claim stays gated and needs passes from the new session unless the note records accept and land that still holds",
         (("review-state.md#Pending acceptance", "A resumed session that finds a pending-acceptance note keeps the claim under the gate and obtains passes from the current session, as passing verdicts do not cross sessions, unless the note records an accept-and-land decision that still holds or the claim's ticket is exempt as under Resumed sessions."),
          ("README.zh-TW.md#恢復的 session", "交接記錄為待驗收的 claim 仍受把關，在新的 session 要重新通過兩關")),
         ()),
        ("off mode, accept and land recorded in the note, then a relevant change before landing",
         "the claim stays gated: the note keeps it and returns to pending acceptance",
         (("review-state.md#Pending acceptance", "An accept-and-land decision does not remove the note: main records the decision in it, turning an unreviewed or unverified note into a pending-acceptance note, and the note then counts as the record that keeps the claim under the gate until it is landed."),
          ("review-state.md#Pending acceptance", "When a relevant change ends an accept-and-land decision, the note returns to pending acceptance, naming what is missing.")),
         ()),
        ("negative control: an explicit code review of ungated work in off",
         "it judges the workspace change and starts no verification; nothing is committed for it",
         (("code-review.md", "An explicit user request for code review applies in either mode and does not start verification."),
          ("review-state.md", "A call for work the gate does not cover, such as an explicit review of unplanned edits or of work in off that no active handoff restricts, judges the workspace change from the base revision, except that an Adversarial review run through [the adversarial-review command](../../adversarial-review/SKILL.md) reviews the range that command defines, and main does not commit that work to review it.")),
         ()),
        ("the user accepts a gated claim that lacks a pass (accept and land)",
         "main records the commit, missing passes and risk; the claim may then be landed, released or completed",
         (("review-state.md#User decisions", "Accept and land is the user's explicit acceptance of a named gated claim without one or both passes or, for a Security-critical claim, without a valid HELD."),
          ("review-state.md#Commit and completion", "or with the user's accept-and-land decision for it."),
          ("README.zh-TW.md#你的決定", "之後驗收把關就不再擋下該 claim 的合併、release 或完成")),
         (("review-state.md#User decisions", "re-review, deferral, cancellation, changed acceptance or waiver,"),)),
        ("accept and land recorded in an active handoff, resumed session, no relevant change since",
         "the decision still satisfies the gate",
         (("review-state.md#User decisions", "so one recorded in an active handoff still satisfies the gate in a resumed session while no relevant change has followed the commit it names."),
          ("README.md#Your decisions", "and one recorded in an active handoff still holds in a resumed session until such a change.")),
         ()),
        ("accept and land, then a relevant change to the claim",
         "the decision ends; the claim needs passes or a new decision",
         (("review-state.md#User decisions", "A later relevant change to the claim ends it, as for a pass."),),
         ()),
        ("the user casually says the work is done",
         "main confirms and records accept and land before it counts; otherwise the work is only not redone",
         (("review-state.md#User decisions", "A user statement that work is done counts as acceptance only after main confirms it with the user and records it as accept and land; otherwise it means the work is not to be redone."),
          ("review-state.md#Ticket status", "Finished means not redone, not accepted:")),
         (("review-state.md#Resumed sessions", "a claim whose ticket is finished is not redone and counts as accepted for landing and release"),)),
        ("a waiver of a missing pass on a gated claim, then a work-in-progress push the user allows",
         "the waiver does not complete the claim; the push neither releases nor completes it",
         (("review-state.md#User decisions", "A waiver does not complete a claim the acceptance gate covers: such a claim is landed on the default branch, released or reported complete only after a later pass or an accept-and-land decision."),
          ("review-state.md#User decisions", "it satisfies neither release nor completion.")),
         (("review-state.md#User decisions", "or pushed to the default branch as a work-in-progress push the user allows with its commits labelled"),)),
        ("a cancelled claim leaves commits on a branch",
         "they stay listed as unaccepted until the user decides; the ticket gets a won't-do value, which is not acceptance",
         (("review-state.md#Commit and completion", "A cancelled claim's commits that remain on a branch are listed as unaccepted, in the report and in any active handoff, until the user decides their disposition:"),
          ("review-state.md#Commit and completion", "a value for work that will not be done is set only on the user's recorded cancellation and never counts as acceptance."),
          ("issue-tracker.md", "never counts as acceptance.")),
         (("review-state.md#Commit and completion", "a cancelled claim's commits stay on the branch until the user decides otherwise"),)),
        ("off mode, a claim an active handoff records as unreviewed, main wants to push or open a pull request",
         "main asks first; the local commit a gated call needs is allowed",
         (("review-state.md#Commits before the passes", "For a claim the gate covers only because an active handoff records it, main may make the local commit a gated call needs without asking, while pushes and pull requests follow off-mode behaviour, so main asks."),
          ("README.md#Commit", "and asks before pushes and pull requests, as in `off`.")),
         (("README.md#Commit", "for any claim an active handoff records as unreviewed or unverified, main may commit a claim before its passes and push it"),)),
        ("auto, a push to a remote branch that existed before and that main did not create",
         "main asks first",
         (("review-state.md#Commits before the passes", "Before pushing to a remote branch that already existed and that main did not create, it asks the user;"),
          ("README.md#Commit", "It asks before pushing to a branch that already existed and that it did not create;"),
          ("README.zh-TW.md#Commit 條件", "要推到原本就存在、不是它建立的 branch 前，會先問你；")),
         (("review-state.md#Commits before the passes", "push it to any branch other than a default branch"),)),
        ("the user says not to push or not to commit",
         "the instruction wins; a gated call left without its commit is reported blocked",
         (("review-state.md#Repository authority", "An explicit user instruction not to commit or not to push overrides this authority within its scope; when it leaves a gated call without the commit it needs, main reports the claim blocked rather than reviewing an uncommitted workspace."),
          ("README.md#Commit", "your explicit instruction not to commit or not to push wins; a claim whose review or verification then lacks its commit is reported blocked."),
          ("README.zh-TW.md#Commit 條件", "你明確說不要 commit 或不要 push 時，以你的指示為準")),
         ()),
    )

    def test_transition_scenarios_are_decided_by_their_sentences(self):
        for scenario, outcome, deciding, contradicting in self.TRANSITION_SCENARIOS:
            for place, sentence in deciding:
                with self.subTest(scenario=scenario[:50], place=place, sentence=sentence[:50]):
                    self.assertIn(sentence, self.source(place), outcome)
            for place, sentence in contradicting:
                with self.subTest(scenario=scenario[:50], place=place, removed=sentence[:50]):
                    self.assertNotIn(sentence, self.source(place), outcome)


class PostFixReviewTests(unittest.TestCase):
    """0.19.0 C3 (docs/specs/review-followups-0-19-0.md): one rule for the code review of a fix after REFUTED or
    BROKEN, the findings its briefs carry at the decided disclosure level, and verification after an incomplete call."""

    REFERENCES = feather_support.POST_FIX_REFERENCES
    AGENTS = feather_support.POST_FIX_AGENTS

    source = staticmethod(feather_support.post_fix_source)

    sentences = staticmethod(feather_support.sentences)

    def assert_whole_sentence(self, sentence, text):
        self.assertRegex(text, rf"(?:^|(?<=\s)){re.escape(sentence)}(?=\s|$)", sentence[:60])

    def assert_pinned(self, pins):
        for place, sentences in pins.items():
            text = self.source(place)
            for sentence in sentences:
                with self.subTest(place=place, sentence=sentence[:60]):
                    self.assert_whole_sentence(sentence, text)

    # Item 1: the one rule for the review of a fix, stated in code review.
    FIX_RULE = ("When the immediately preceding code review call for the claim completed, the review of the fix is a "
                "narrowed second review whose judged range starts at the commit that call judged, with the full diff from "
                "the claim's base revision supplied as context; when that call did not complete, or when no code review "
                "call for the claim preceded the fix, as after an early explicit BROKEN, the call reviews the claim's full "
                "scope from its base revision, as [review state](review-state.md)'s Completed calls and coverage describes.")
    FIX_ENTRY = ("A fix made after the verifier refutes the claim, or after Adversarial review breaks it, comes back to this "
                 "procedure before outcome verification checks it again.")
    # Item 2: the findings in the brief, what the reviewer checks and what it does not adjudicate.
    FIX_BRIEF = (
        "The brief carries the verifier's or adversary's findings with main's FIX or REJECT disposition for each.",
        "The reviewer checks that each FIX finding is addressed in the code and that the fix introduces no regression.",
        "It does not adjudicate a rejection of a verifier or adversary finding, which stays with that role; it keeps its own "
        "authority to uphold its own earlier findings and to report any blocking defect it finds in the fix.",
    )
    # Item 8.3: REFUTED findings on a Security-critical claim get the same default.
    REFUTED_DISCLOSURE = ("For a Security-critical claim, the verifier's REFUTED findings, whose evidence may be a reproducing "
                          "command, are passed to this review with the same disclosure default, masking and limits on added "
                          "exploit steps that [Adversarial review](adversarial-review.md) step 7 sets for findings after BROKEN.")
    # Item 8.1 (Q18): every public or possibly public record after a BROKEN follows step 10; reports to main are not.
    CODE_REVIEW_RECORDS = (
        "After a BROKEN, every public or possibly public record main writes from the findings or from the reports on the fix "
        "follows [Adversarial review](adversarial-review.md) step 10 and gets only a summary unless the user agrees: the "
        "fix's commit messages, the notes of a tracked handoff, follow-up items in a tracked handoff or in a tracked or "
        "public tracker, such as those steps 5 and 6 write, notes on such a ticket, an ADR and the validation entry's "
        "review history.",
        "The reviewer's report to main is not such a record: it may carry the evidence the brief and the reviewer role "
        "allow, and what main writes from it follows step 10.",
    )

    # Items 4 and 6: outcome verification states completion in its brief, points to the rule and rechecks in full
    # after an incomplete call.
    VERIFICATION_STEP_2 = ("On a later call for the same claim, state whether the previous call for the claim completed with "
                           "a verdict, as [review state](review-state.md)'s Completed calls and coverage describes.")
    VERIFICATION_STEP_4 = (
        "A fix goes to [code review](code-review.md) first, under that procedure's rule for the review of a fix, and "
        "returns to this recheck only once code review approves it; if that review stops without APPROVED, the claim is "
        "unreviewed under that procedure.",
        "When the previous verification call completed, use the next call to recheck the original failure plus a bounded "
        "regression check; after a verification call that did not complete, the next call verifies the claim's full "
        "acceptance rather than only the original failure.",
        "A fix after BROKEN also comes to this procedure once code review approves it, with a brief that carries the "
        "adversary's findings as [Adversarial review](adversarial-review.md) step 7 describes.",
        "After a BROKEN, every public or possibly public record main writes from the findings or from the verifier's "
        "report, such as those [code review](code-review.md) lists for the review of a fix, follows [Adversarial "
        "review](adversarial-review.md) step 10 and gets only a summary unless the user agrees; the verifier's report to "
        "main is not such a record.",
    )

    # Items 4, 5, 8.1 and 8.2: Adversarial review step 7 points to the rule and sets what the briefs after BROKEN carry.
    STEP_7_POINTER = ("Its code review follows [code review](code-review.md)'s rule for the review of a fix, and the code "
                      "review and outcome verification briefs after BROKEN carry the adversary's findings with main's FIX "
                      "or REJECT disposition for each, at the disclosure level the next sentences set.")
    STEP_7_DISCLOSURE = (
        "By default, each finding passed to code review or outcome verification carries the violated invariant, the "
        "location, the root cause and the observed and expected behaviour, without exploit steps.",
        "Exploit steps are the inputs, payloads, request sequences, commands or code that trigger the violation; observed "
        "and expected behaviour is stated as outcomes, not as those inputs.",
        "A brief never carries an unmasked secret, credential or real data, and main masks any it finds in a report before "
        "passing it.",
        "Main adds non-public supporting detail when a role needs it to judge the fix.",
        "Main adds exploit steps only to a role that needs them to judge whether the fix closes the finding, names that "
        "role and the reason in the brief, and marks the added detail as subject to step 10.",
        "This default never forbids the verifier's reproduction and counterexample duties, including the command its "
        "REFUTED gives.",
    )
    STEP_7_RECORDS = ("What main writes from these findings, or from the reviewer's and verifier's reports on the fix, into "
                      "any public or possibly public record follows step 10.")

    # Items 3 and 8.4: the reviewer role.
    REVIEWER_FIX = (
        "When the brief is for a fix after {{name:verifier}} refuted the claim or {{name:adversary}} broke it, it carries "
        "that role's findings with the main Agent's FIX or REJECT disposition for each; whether you narrow the review "
        "still depends on the brief saying the previous call completed, as above.",
        "Check that each FIX finding is addressed in the code and that the fix introduces no regression.",
        "Do not adjudicate the main Agent's rejection of a verifier or adversary finding, which stays with that role; you "
        "keep your authority to uphold your own earlier findings and to report any blocking defect you find in the fix.",
    )
    MASKING = feather_support.ADVERSARY_SAFETY_LIMITS["secrets masked, exploit details kept to the report"]

    # Wording the rule replaces: a fix review keyed on the approved review, and a recheck that is always narrowed.
    REMOVED = {
        "code-review.md": ("what changed since the approved review", "comes back to this procedure before the verifier rechecks it"),
        "outcome-verification.md": ("Use the next call to recheck the original failure plus a bounded regression check, and send it",),
    }

    def test_code_review_states_the_fix_rule_once(self):
        self.assert_pinned({"code-review.md#fix": (self.FIX_ENTRY, self.FIX_RULE)})
        self.assertIn("Its count continues from where it stands", self.source("code-review.md#fix"))
        # Stated once: no other procedure or role restates the narrowed range or the no-preceding-review case.
        for path in sorted(self.REFERENCES.glob("*.md")) + [self.AGENTS / "reviewer.md", self.AGENTS / "verifier.md"]:
            text = path.read_text(encoding="utf-8")
            for phrase in ("whose judged range starts at the commit that call judged", "no code review call for the claim preceded the fix"):
                with self.subTest(path=path.name, phrase=phrase[:40]):
                    self.assertEqual(text.count(phrase), 1 if path.name == "code-review.md" else 0)

    def test_the_fix_brief_carries_the_findings_and_bounds_the_reviewer(self):
        self.assert_pinned({"code-review.md#fix": self.FIX_BRIEF})

    def test_the_reviewer_role_states_the_fix_review_and_masks(self):
        self.assert_pinned({"reviewer.md#fix": self.REVIEWER_FIX, "reviewer.md": (self.MASKING,)})
        self.assertIn(self.MASKING, self.source("adversary.md"), "the same sentence as the adversary role")
        reviewer = self.source("reviewer.md")
        # Item 3: the existing sentence keyed on "the previous call for this claim" stays a single line, which the
        # 0.16.0 fixture replaces; the new paragraph does not repeat the key.
        self.assertEqual([line for line in reviewer.split("\n") if "the previous call for this claim" in line],
                         [line for line in reviewer.split("\n") if line.startswith("When the brief says the previous call for this claim completed")])
        self.assertEqual(len([line for line in reviewer.split("\n") if "the previous call for this claim" in line]), 1)
        self.assertIn(ReviewRulesFollowUpTests.RETRY_COVERAGE["reviewer.md"][0], reviewer)
        for prefix in ("", "cc-"):
            with self.subTest(prefix=prefix):
                rendered = config._render("reviewer", {"model": "sonnet", "effort": "high"}, prefix).decode("utf-8")
                self.assertIn(f"When the brief is for a fix after {prefix}verifier refuted the claim or {prefix}adversary broke it,", rendered)
                self.assertIn(self.MASKING, rendered)

    def test_the_procedures_point_to_the_rule(self):
        self.assert_pinned({"outcome-verification.md#4": self.VERIFICATION_STEP_4[:1] + self.VERIFICATION_STEP_4[2:3],
                            "adversarial-review.md#7": (self.STEP_7_POINTER,)})
        for place in ("outcome-verification.md#4", "adversarial-review.md#7"):
            with self.subTest(place=place):
                self.assertIn("rule for the review of a fix", self.source(place))
                self.assertNotIn("narrowed second review", self.source(place))
        # The existing step 7 pin keeps its sentence.
        self.assertIn(feather_support.ADVERSARIAL_REVIEW_FIXES["adversarial-review.md"][1], self.source("adversarial-review.md#7"))

    def test_findings_after_broken_carry_the_minimal_disclosure_default(self):
        self.assert_pinned({"adversarial-review.md#7": self.STEP_7_DISCLOSURE, "code-review.md#fix": (self.REFUTED_DISCLOSURE,)})

    def test_no_sentence_passes_exploit_steps_outside_the_default(self):
        """Abuse check (items 5 and 8.2): in the review procedures and the reviewer role, every sentence that mentions
        exploit steps or details is one of the decided ones, so no brief gets exploit steps by another route."""
        allowed = {self.STEP_7_DISCLOSURE[0], self.STEP_7_DISCLOSURE[1], self.STEP_7_DISCLOSURE[4], self.REFUTED_DISCLOSURE,
                   self.MASKING, feather_support.ADVERSARIAL_REVIEW_DISCLOSURE["adversarial-review.md"][1]}
        for place in ("code-review.md", "outcome-verification.md", "adversarial-review.md", "reviewer.md"):
            for sentence in self.sentences(self.source(place)):
                if re.search(r"\bexploit (?:steps?|details?)\b", sentence, re.I):
                    with self.subTest(place=place, sentence=sentence[:60]):
                        self.assertIn(sentence, allowed)

    def test_the_verifier_keeps_its_reproduction_duties(self):
        """Item 5: the disclosure default never forbids the verifier's reproduction and counterexample duties, and the
        verifier role is unchanged (item 6)."""
        verifier = self.source("verifier.md")
        for duty in ("REFUTED: a reproduced failure contradicts the claim. Give the command, observed and expected results, and the smallest scope of the failure.",
                     "then probe counterexamples that could refute the claim:"):
            with self.subTest(duty=duty[:40]):
                self.assertIn(duty, verifier)
        self.assertNotIn("previous call", verifier)
        self.assertNotIn("exploit", verifier)

    def test_records_after_broken_follow_step_10(self):
        self.assert_pinned({"code-review.md#fix": self.CODE_REVIEW_RECORDS,
                            "outcome-verification.md#4": self.VERIFICATION_STEP_4[3:],
                            "adversarial-review.md#7": (self.STEP_7_RECORDS,)})
        # Step 10's own text is not rewritten: its pinned sentences stay in step 10.
        for sentence in feather_support.ADVERSARIAL_REVIEW_DISCLOSURE["adversarial-review.md"]:
            with self.subTest(sentence=sentence[:60]):
                self.assert_whole_sentence(sentence, self.source("adversarial-review.md#10"))

    def test_verification_after_an_incomplete_call_covers_the_full_acceptance(self):
        self.assert_pinned({"outcome-verification.md#2": (self.VERIFICATION_STEP_2,),
                            "outcome-verification.md#4": self.VERIFICATION_STEP_4[1:2]})

    def test_replaced_wording_is_gone(self):
        for place, phrases in self.REMOVED.items():
            for phrase in phrases:
                with self.subTest(place=place, phrase=phrase[:60]):
                    self.assertNotIn(phrase, self.source(place))

    # Item 7: each scenario names the outcome and the sentences that decide it; replaced wording must be gone.
    SCENARIOS = (
        ("a fix after REFUTED, whose preceding code review call completed with APPROVED",
         "a narrowed second review from the commit that call judged, with the full diff from base as context",
         (("code-review.md#fix", FIX_RULE),
          ("code-review.md#fix", FIX_BRIEF[0]),
          ("review-state.md#Completed calls and coverage", "A second review, narrowed to the earlier findings and the fixes, and the range from the previously judged commit follow only when the previous call completed."),
          ("reviewer.md", "When the brief says the previous call for this claim completed with a verdict,")),
         (("code-review.md", "what changed since the approved review"),)),
        ("a fix after BROKEN on a Security-critical claim",
         "code review, then outcome verification, then Adversarial review again; both briefs carry the findings at the "
         "minimal-disclosure default, and public records get only a summary",
         (("adversarial-review.md#7", feather_support.ADVERSARIAL_REVIEW_FIXES["adversarial-review.md"][1]),
          ("adversarial-review.md#7", STEP_7_POINTER),
          ("adversarial-review.md#7", STEP_7_DISCLOSURE[0]),
          ("adversarial-review.md#7", STEP_7_DISCLOSURE[4]),
          ("outcome-verification.md#4", VERIFICATION_STEP_4[2]),
          ("code-review.md#fix", CODE_REVIEW_RECORDS[0])),
         ()),
        ("the code review call of a fix fails, then the next call",
         "the next call reviews the claim's full scope from its base revision",
         (("code-review.md#fix", FIX_RULE),
          ("review-state.md#Completed calls and coverage", "After a call that did not complete, the next call reviews the claim's full scope from its base revision (for plan review, the whole plan), carrying any partial findings as evidence, not as coverage."),
          ("reviewer.md", ReviewRulesFollowUpTests.RETRY_COVERAGE["reviewer.md"][0])),
         ()),
        ("an early explicit BROKEN with no preceding code review call, then a fix",
         "the review of the fix covers the claim's full scope from its base revision",
         (("code-review.md#fix", FIX_RULE),
          ("adversarial-review.md#1", "An explicit call the user requests for a claim that does not yet have a valid APPROVED and a valid CONFIRMED at the same commit still runs,")),
         ()),
        ("main rejects a verifier finding with evidence, then the review of the fix",
         "the reviewer does not adjudicate the rejection, which the verifier judges; it still upholds its own findings and reports blocking defects",
         (("code-review.md#fix", FIX_BRIEF[2]),
          ("reviewer.md#fix", REVIEWER_FIX[2]),
          ("outcome-verification.md#4", "The verifier may uphold a rejection; an upheld finding can be rejected again only with new evidence.")),
         ()),
        ("an outcome verification call is interrupted, then the recheck",
         "the brief says the previous call did not complete and the next call verifies the full acceptance",
         (("outcome-verification.md#2", VERIFICATION_STEP_2),
          ("outcome-verification.md#4", VERIFICATION_STEP_4[1]),
          ("outcome-verification.md#3", "failed, interrupted and protocol-failure calls count,")),
         (("outcome-verification.md", "Use the next call to recheck the original failure plus a bounded regression check, and send it"),)),
    )

    def test_scenarios_are_decided_by_their_sentences(self):
        for scenario, outcome, deciding, contradicting in self.SCENARIOS:
            for place, sentence in deciding:
                with self.subTest(scenario=scenario[:50], place=place, sentence=sentence[:50]):
                    self.assertIn(sentence, self.source(place), outcome)
            for place, sentence in contradicting:
                with self.subTest(scenario=scenario[:50], place=place, removed=sentence[:50]):
                    self.assertNotIn(sentence, self.source(place), outcome)


class StopThresholdProceduresTests(unittest.TestCase):
    """Configurable Stop threshold C2: the procedures stop at K, resolve and state it, apply one rule for the next
    automatic call, handle a change of K, give costs in K, and the READMEs and decision records say so."""

    REFERENCES = feather_support.STOP_THRESHOLD_REFERENCES
    ADR = feather_support.STOP_THRESHOLD_ADR

    source = staticmethod(feather_support.stop_threshold_source)

    assert_whole_sentence = feather_support.stop_threshold_assert_whole_sentence

    assert_pinned = feather_support.stop_threshold_assert_pinned

    # Item 3: the one rule, stated once in review state and applied wherever a request used to be derived.
    NEXT_CALL_RULE = ("A step's next automatic call for a work needs the user's explicit request exactly while that step's "
                      "count for the work is at or above the Stop threshold in effect, and is made without one while it is below.")

    # Item 1: resolution, never changed by main, invalid guidance skipped, unknown choice treated like Unknown state.
    RESOLUTION = {
        "review-state.md#section": (
            "The Stop threshold, written K in formulas, is the number of consecutive automatic calls without a pass that stops a step: one integer from 2 to 10 that applies to plan review, code review, outcome verification and Adversarial review alike.",
        ),
        "review-state.md#Resolution": (
            "The Stop threshold in effect is, in order: the user's task choice, for that task; otherwise the user's session choice; otherwise the value the loaded project guidance states; otherwise the value the loaded user guidance states; otherwise 2.",
            "Main never raises or lowers the Stop threshold on its own; a task or session choice comes only from the user's own words in this conversation.",
            "A guidance value that is not an integer from 2 to 10 is not used: main takes the next source and reports the invalid value.",
        ),
        "review-state.md#Unknown threshold": (
            "When main cannot establish whether a task or session choice exists, for example after context compaction, it treats the Stop threshold as unknown, as Unknown state does for counts: affected steps are treated as stopped and main asks the user.",
            "A step whose count is below 2 is not affected, since no Stop threshold is lower.",
        ),
        "plan-review.md": (
            "Resolve the Stop threshold in effect, the number of consecutive automatic calls without a pass that stops each step, as [review state](review-state.md) describes, and state it and its source whenever a review decision comes up.",
        ),
        "delegation SKILL.md": (
            "Each step of the automatic flow stops at the Stop threshold, which main resolves, states and applies to a change as [review state](references/review-state.md) describes and never changes on its own.",
        ),
    }

    # Item 2: every step stops at K.
    STOPPING = {
        "review-state.md": (
            "| Consecutive non-pass count | Automatic calls in a row that did not pass, including failed, interrupted and protocol-failure calls. A count that reaches the Stop threshold in effect stops the step. |",
        ),
        "review-state.md#Stop": (
            "As many consecutive automatic calls without a pass as the Stop threshold in effect stop the step for that work; it waits for the user's explicit request.",
        ),
        "plan-review.md#3": (
            "A count that reaches the Stop threshold in effect without READY stops automatic submission (step 6).",
        ),
        "plan-review.md#6": (
            "Once the count reaches the Stop threshold in effect without READY, stop automatic submission.",
            "While the count stays at or above the Stop threshold, further review requires an explicit user request, and an explicit call is outside the count; an explicit READY clears the stop and lets work continue, as [review state](review-state.md) describes.",
        ),
        "code-review.md#3": (
            "A count that reaches the Stop threshold in effect without APPROVED stops automatic review (step 6); the Stop threshold is resolved and stated as [review state](review-state.md) describes.",
        ),
        "code-review.md#6": (
            "When the count reaches the Stop threshold in effect without APPROVED, for any reason (a retry counts as a call), the claim is unreviewed: stop automatic review, do not start automatic outcome verification, do not land it on the default branch, release it or report it complete, report its open findings and require an explicit user request for another call.",
        ),
        "outcome-verification.md#3": (
            "A count that reaches the Stop threshold in effect without CONFIRMED stops automatic verification (step 6), so, with K the Stop threshold, a claim refuted K times in a row stops after K − 1 automatically rechecked fixes.",
        ),
        "outcome-verification.md#6": (
            "When the count reaches the Stop threshold in effect without CONFIRMED, stop automatic verification, report the claim as unverified with the findings, do not land it on the default branch, release it or report it complete, and require an explicit user request for another call.",
        ),
        "adversarial-review.md#4": (
            "A count that reaches the Stop threshold in effect without HELD stops automatic Adversarial review (step 8).",
        ),
        "adversarial-review.md#5": ("Either next call counts toward the stop of step 4.",),
        "adversarial-review.md#8": (
            "When the count reaches the Stop threshold in effect without HELD, stop automatic Adversarial review, report the claim with its Adversarial review missing and its open findings, do not land it on the default branch, release it or report it complete, and require an explicit user request for another call.",
        ),
    }

    # Item 3: the single rule and each place that used to derive a request from a count left where it stopped.
    NEXT_CALL = {
        "review-state.md#Next automatic call": (
            NEXT_CALL_RULE,
            "This one rule decides it after an explicit pass that cleared a stop, for a reopened call, for a review after a material deviation, for the review of a fix and for work that inherits an overlapping plan's count and stop.",
        ),
        "review-state.md#Clearing a stop": (
            "An explicit call that passes clears the stop and leaves the count unchanged, and in auto the automatic flow continues to the next step.",
            "A later automatic call in the same step for the same work, such as a reopened review or the review of a fix, follows Next automatic call: while the count is at or above the Stop threshold in effect it needs the user's explicit request; that requested call is still an automatic call of the flow, so a pass resets the count and a non-pass stops the step again.",
        ),
        "review-state.md#Reopened calls": (
            "A reopened call continues the step's count from where it stands, which is zero after an automatic pass and unchanged after an explicit pass that cleared a stop.",
            "It follows Next automatic call: a reopened automatic call needs the user's explicit request exactly while that count is at or above the Stop threshold in effect.",
        ),
        "review-state.md#Overlap": (
            "Work that overlaps a stopped plan keeps that plan's count and stop, and its next automatic call follows Next automatic call, so it gains no new automatic calls while that count is at or above the Stop threshold in effect: an automatic READY of the widened plan does not clear the inherited stop for the overlapping work, while an explicit pass covering it does.",
        ),
        "plan-review.md#5": (
            "The same applies when implementation deviates from the plan: a material deviation stops dependent work for another review of the revised plan, counted from the reset of the last automatic READY, or from the unchanged count after an explicit READY that cleared a stop, and the user's approval.",
            "That review needs the user's explicit request exactly while the count is at or above the Stop threshold in effect, as [review state](review-state.md)'s Next automatic call describes.",
            "When the count is already at or above the Stop threshold, report the deviation and keep dependent work stopped; another review then needs an explicit user request, as in step 6.",
        ),
        "code-review.md": (
            "Its count continues from where it stands, which is zero after an automatic APPROVED and unchanged after an explicit APPROVED that cleared a stop.",
            "The review of the fix follows [review state](review-state.md)'s Next automatic call: a reopened automatic call needs the user's explicit request exactly while that count is at or above the Stop threshold in effect.",
        ),
        "outcome-verification.md#3": (
            "Whether the next automatic call, such as the recheck after a fix or a reopened verification, needs the user's explicit request follows [review state](review-state.md)'s Next automatic call.",
        ),
        "adversarial-review.md#4": (
            "Whether the next automatic call, such as the call after a fix for BROKEN or a reopened one, needs the user's explicit request follows [review state](review-state.md)'s Next automatic call.",
        ),
    }

    # Items 4 and 5: a change of K, a saved change re-resolving, and stating K with its source.
    CHANGE = {
        "review-state.md#Changing it": (
            "A change of the Stop threshold never changes a count; Next automatic call is applied with the new value at once.",
            "A stopped step whose count is now below the new value resumes automatically, because the change is the user's own act.",
            "A step whose count reaches or exceeds the new value stops at once, which means only that its next automatic call now needs the user's request under Next automatic call: a step an explicit pass had cleared stays cleared, and a call the user then requests is classified as Clearing a stop describes.",
            "Main lists the steps the change resumed or stopped in its reply.",
        ),
        "review-state.md#Saved in this conversation": (
            "A value the user saves in project or user scope in this conversation replaces any earlier task or session choice in this conversation, and the Stop threshold in effect is resolved again from the saved values in the order of Resolution, so this session uses what a new session would.",
            "A user value saved where the project states its own is reported as overridden by it.",
            "This is the reverse of the Review mode, whose saved change keeps a separate task or session override.",
        ),
        "review-state.md#Stating it": (
            "Whenever a review decision comes up, main states the Stop threshold in effect and its source (task, session, project, user or default), as it does for the Review mode.",
            "A session choice does not cross sessions and is not written into a handoff; a resumed session resolves the Stop threshold again from its loaded guidance.",
        ),
        "setup.md#section": (
            "In a session, main uses the user's task or session choice, then the value the loaded project guidance states, then the value the loaded user guidance states, then 2, and states the value in effect and its source at each review decision; a session choice writes nothing and does not reach a new or resumed session.",
            "A value saved in project or user scope during a conversation replaces any earlier task or session choice in that conversation, and main resolves the Stop threshold again from the saved values, so the session uses what a new session would.",
            "This is the reverse of the review mode, where a separate task or session override still takes precedence over a saved change.",
            "Changing the Stop threshold never changes a count: a stopped step whose count is below the new value resumes, a step whose count reaches or exceeds it stops at once, and main lists those steps; the delegation skill's review state holds the rules.",
        ),
        "setup.md": (
            "The automatic limits for plan review, code review, outcome verification and Adversarial review (each step stops once its consecutive automatic calls without a pass reach the Stop threshold, 2 by default, and an automatic pass resets the count) are agent instructions, not a hook-enforced counter.",
        ),
    }

    # Item 6: the security analysis is not counted.
    NOT_COUNTED = {
        "review-state.md#Not counted": (
            "The security analysis before plan review is not a counted step, and the Stop threshold does not apply to it.",
        ),
        "plan-review.md": (
            "The security analysis is not a counted step, and the Stop threshold does not apply to it.",
        ),
    }

    # Item 7: the preview states K, its source and the bounds.
    PREVIEW = {
        "preview.md": (
            "- **Stop threshold:** resolve it as [review state](review-state.md) describes: a task or session choice, then the value the project guidance states, then the value the user guidance states, then 2, with a value saved in this conversation resolved again from the saved values.",
            "A task or session choice takes precedence over the saved values reported by `show`.",
            "State the number of Plans, Claims and Security-critical claims covered, that the security analysis runs once per Plan or per trust boundary that several Security-critical claims share, the Stop threshold in effect, written K, with its source (task, session, project, user or default), and that each step stops after K consecutive automatic calls without a pass, per Plan for plan review and per Claim for code review, outcome verification and Adversarial review, an automatic pass resetting the count.",
            "Under the [code review](code-review.md), [outcome verification](outcome-verification.md) and [adversarial review](adversarial-review.md) procedures, in one uninterrupted attempt, a Claim makes at most K(K+1) automatic calls (up to K verification calls, between which up to K − 1 fixes each get up to K code reviews, plus up to K code reviews before the first verification), a Security-critical claim at most K³ + K² + K (also up to K Adversarial reviews, between which up to K − 1 fixes after BROKEN each get up to K(K+1) code review and verification calls), and a Plan with N Claims of which S are Security-critical about K + K(K+1)N + K³S.",
            "Each reopened Claim or approved Material deviation adds calls, including up to K plan reviews for each deviation.",
        ),
    }

    # Item 8: each README paragraph that stated the fixed number, paired (English, Traditional Chinese).
    README_PAIRS = (
        ("Budget", "次數上限",
         "An automatic pass resets the count; when the count reaches the [Stop threshold](#stop-threshold), 2 by default, the step stops, which never counts as passing, and the work waits for you.",
         "自動呼叫通過就歸零；次數達到[停止門檻](#停止門檻)（預設 2）時，該步驟停下，不等於通過，工作會等你決定。"),
        ("Budget", "次數上限",
         "A step's next automatic call for the same work needs your request exactly while its count is at or above the Stop threshold, and runs without one while it is below.",
         "同一份工作在某個步驟的下一次自動呼叫，恰好在該步驟的次數大於或等於停止門檻時需要你要求，低於門檻時不需要你要求就會進行。"),
        ("Re-review during implementation", "施工中的重審",
         "Dependent work stops, and the revised plan must pass plan review and get your approval before that work continues; that plan review needs your request only while plan review's count is at or above the Stop threshold.",
         "受影響的後續工作會停下，修訂後的計畫要通過計畫審查並經你同意才繼續；只有在計畫審查的次數大於或等於停止門檻時，那次計畫審查才需要你要求。"),
        ("Not passed", "未通過",
         "Verification keeps counting across fixes and resets only on an automatic CONFIRMED, so, with K the Stop threshold, a claim refuted K times in a row stops after K − 1 automatically rechecked fixes.",
         "驗證次數跨修正累計，只有自動的 CONFIRMED 才歸零，所以停止門檻為 K 時，連續 K 次 REFUTED 的 claim 在 K − 1 輪自動複驗的修正後就會停下。"),
        ("Validity", "有效範圍",
         "A reopened step continues its count, which is zero after an automatic pass and unchanged after an explicit pass that cleared a stop; the reopened call needs your request again exactly while that count is at or above the Stop threshold.",
         "重新打開的步驟沿用原本的次數，自動通過後是零，明確通過解除停止後則維持不變；恰好在這個次數大於或等於停止門檻時，重新打開的呼叫仍需要你再要求。"),
        ("After a stop", "停下之後",
         "Any later automatic call in that step for the same work, such as the review of a fix, needs your request exactly while the count is at or above the Stop threshold; that call is still part of the automatic flow, so a pass resets the count and a non-pass stops the step again.",
         "同一份工作在該步驟之後的自動呼叫（例如修正後的審查），恰好在次數大於或等於停止門檻時都需要你要求；那次呼叫仍屬於自動流程，通過就歸零，沒通過就再次停下。"),
        ("Partial overlap", "部分重疊",
         "Where that plan had stopped, the overlapping work keeps its count and stop and gains no new automatic calls while that count is at or above the Stop threshold: an automatic READY of the new plan does not clear that stop, while an explicit pass covering the work does.",
         "若既有計畫已停下，重疊的工作保留它的次數與停止狀態，在這個次數大於或等於停止門檻時，不會多出新的自動呼叫：新計畫的自動 READY 不會解除那個停止，涵蓋這些工作的明確通過才會。"),
        ("Cost", "成本",
         "At the default K = 2 that is, in one uninterrupted attempt, at most 6 calls per claim, 14 per Security-critical claim and about 2 + 6N + 8S per plan; at K = 10 it is 110, 1110 and about 10 + 110N + 1000S.",
         "預設 K = 2 時，一次不中斷的完成過程中每個 claim 最多 6 次、安全關鍵 claim 最多 14 次，整份計畫約 2 + 6N + 8S 次；K = 10 時則是 110 次、1110 次與約 10 + 110N + 1000S 次。"),
        ("Cost", "成本",
         "The bounds grow faster than K because each fix is reviewed and verified again.",
         "因為每次修正都要重新審查與驗證，上限增加得比 K 快。"),
        ("Cost", "成本",
         "A plan with a Security-critical claim also gets one security analysis by analyst per plan or shared trust boundary before plan review; each reopened claim or material deviation you approve adds calls, including up to K plan reviews for each deviation; the default roles run on opus/high.",
         "有安全關鍵 claim 的計畫，在計畫審查前還會由 analyst 對每份計畫或共用的信任邊界做一次安全分析；重新打開的 claim 與每次經你同意的重大偏離都會再增加呼叫，每次偏離最多 K 次計畫審查；預設角色都是 opus/high。"),
        ("section", "section",
         "The Stop threshold is how many consecutive automatic calls without a pass stop a step of the automatic flow: one number from 2 to 10 for plan review, code review, outcome verification and Adversarial review alike, 2 by default.",
         "停止門檻是自動流程的一個步驟連續幾次自動呼叫沒通過就停下：一個 2 到 10 的數字，計畫審查、程式碼審查、結果驗證與對抗式審查都適用同一個值，預設 2。"),
        ("section", "section",
         "Tell main a value for the current task or session, which writes nothing, or save one in project or user scope with the configuration tool's `review --stop-threshold` (see [Stop threshold](docs/setup.md#stop-threshold)), where `default` removes the saved value.",
         "你可以告訴主 Agent 目前任務或 session 要用的值，這不會寫入任何檔案；也可以用設定工具的 `review --stop-threshold` 儲存在 project 或 user 範圍（見[停止門檻](docs/setup.md#stop-threshold)），`default` 會移除已儲存的值。"),
        ("section", "section",
         "Main uses your task or session choice, then the value the project guidance states, then the value the user guidance states, then 2, so a project's saved value overrides your user value.",
         "主 Agent 依序採用你的任務或 session 選擇、project 指引寫明的值、user 指引寫明的值，最後才是 2，所以 project 儲存的值優先於你的 user 值。"),
        ("section", "section",
         "Main never changes it on its own and states it and its source whenever a review decision comes up; a session choice does not carry into a new or resumed session and is not written into a handoff.",
         "主 Agent 絕不自行更改它，每次要做審查決定時都會說明目前的值與來源；session 選擇不會帶到新的或恢復的 session，也不會寫進交接。"),
        ("section", "section",
         "A guidance value outside 2–10 is skipped and reported; when main cannot tell whether you made a task or session choice, for example after context compaction, it treats the affected steps as stopped and asks you.",
         "指引中不在 2–10 的值會被略過並回報；主 Agent 無法確定你是否做過任務或 session 選擇時（例如 context 壓縮後），會把受影響的步驟視為已停下並問你。"),
        ("section", "section",
         "Changing the Stop threshold never changes a count.",
         "變更停止門檻絕不會改變次數。"),
        ("section", "section",
         "A stopped step whose count is now below the new value resumes, a step whose count reaches or exceeds it stops at once, a step an explicit pass had cleared stays cleared, and main lists the steps that resumed or stopped.",
         "已停下、次數低於新值的步驟會繼續；次數達到或超過新值的步驟立即停下；明確通過已解除停止的步驟仍維持解除；主 Agent 會列出因此繼續或停下的步驟。"),
        ("section", "section",
         "A value you save in project or user scope in this conversation replaces any earlier task or session choice in this conversation, and the Stop threshold is resolved again from the saved values, so this session uses what a new session would; a user value saved where the project states its own is reported as overridden by it.",
         "你在這段對話中儲存到 project 或 user 範圍的值，會取代這段對話先前的任務或 session 選擇，並依已儲存的值重新決定停止門檻，所以這個 session 會用新 session 會用的值；project 已寫明自己的值時，你儲存的 user 值會被回報為被它覆寫。"),
        ("section", "section",
         "This is the reverse of the review mode, where a saved change keeps a separate task or session override.",
         "這與審查模式相反：審查模式的已儲存變更會保留另行指定的任務或 session 選擇。"),
    )

    # Item 9: ADR 0010 and the amendment notes, appended without rewriting the earlier decisions.
    DECISION = (
        "- **One number.** The Stop threshold is one integer K from 2 to 10 that applies to plan review, code review, outcome verification and Adversarial review alike.",
        "The Stop threshold in effect is the user's task choice, for that task; otherwise the user's session choice; otherwise the value the loaded project guidance states; otherwise the value the loaded user guidance states; otherwise 2.",
        NEXT_CALL_RULE,
        "A change of K never changes a count; the rule above is applied with the new K at once.",
        "A value the user saves in project or user scope in a conversation replaces any earlier task or session choice in that conversation, and K is resolved again from the saved values, so the session uses what a new session would.",
        "In one uninterrupted attempt, a Claim makes at most K(K+1) automatic calls: up to K verification calls, between which up to K − 1 fixes each get up to K code reviews, plus up to K code reviews before the first verification.",
        "A Security-critical claim makes at most K³ + K² + K: also up to K Adversarial reviews, between which up to K − 1 fixes after BROKEN each get up to K(K+1) code review and verification calls.",
        "A Plan with N Claims of which S are Security-critical makes about K + K(K+1)N + K³S, and each reopened Claim or approved Material deviation adds calls, including up to K plan reviews for each deviation.",
        "The user kept the range 2–10 knowing these bounds.",
        "The minimum is 2 because a single non-pass can be a transient interruption or a protocol failure, and stopping on it would interrupt the user for noise.",
        "There is no unlimited value because ADR 0004 rejected an unbounded loop: the user is asked at some point.",
        "There is one number rather than one per step because no need for separate values is known and four values would turn the cost formula into four variables; a later per-step override could be added without breaking a single saved value.",
        "- **Keep a fixed two**:", "- **One value per step**:", "- **Allow 1, or an unlimited value**:", "- **A smaller maximum**:",
        "- **A saved value acting as a session choice**:", "- **Main reading the saved value with the configuration tool at each decision**:",
    )
    AMENDMENTS = {
        "0002-session-scoped-review-counts.md": "(Amended by ADR 0010: the two more automatic calls a resume may run are the value at the default Stop threshold of 2; the Stop threshold is now one user-configurable number from 2 to 10, and a resume starts a fresh count toward the Stop threshold in effect.)",
        "0003-review-cost-and-independence-stay-user-configured.md": "(Amended by ADR 0010: the two-call budget is the value at the default Stop threshold of 2; the Stop threshold is now one user-configurable number from 2 to 10, the README gives the number of automatic calls in terms of it, and switching a role's model never resets a step's count toward it.)",
        "0004-consecutive-failure-review-budget.md": "(Amended by ADR 0010: two consecutive automatic calls, six calls per Claim, about 2 + 6N per Plan and up to two plan reviews for each Material deviation are the values at the default Stop threshold of 2; with Stop threshold K, from 2 to 10, a step stops after K consecutive automatic calls without a pass, a Claim makes at most K(K+1) automatic calls in one uninterrupted attempt, a Claim refuted K times in a row stops after K − 1 automatically rechecked fixes, and each Material deviation adds up to K plan reviews.)",
        "0006-review-state-validity-and-completion.md": "(Amended by ADR 0010: the fixed two calls and the bound of six per Claim are the values at the default Stop threshold of 2, and the bound is K(K+1) at Stop threshold K. A step's next automatic call for a work needs the user's explicit request exactly while that step's count for the work is at or above the Stop threshold in effect, and is made without one while it is below; this one rule replaces the derivation of a needed request from a count left where it stopped, after an explicit pass that cleared a stop, for a reopened call, for a review after a Material deviation, for the review of a fix and for work that inherits an overlapping Plan's count and stop.)",
        "0009-security-critical-claims-get-an-adversarial-review.md": "(Amended by ADR 0010: the two consecutive non-passes that stop Adversarial review and the fourteen automatic calls per Security-critical claim are the values at the default Stop threshold of 2; with Stop threshold K, from 2 to 10, the step stops after K consecutive automatic calls without a pass and a Security-critical claim makes at most K³ + K² + K automatic calls in one uninterrupted attempt.)",
    }
    # The original decision text each amended ADR keeps.
    KEPT = {
        "0002-session-scoped-review-counts.md": "A resume may run up to two more automatic calls for the same plan or claim.",
        "0003-review-cost-and-independence-stay-user-configured.md": "Switching a role's model never resets a step's two-call budget.",
        "0004-consecutive-failure-review-budget.md": "A Claim makes at most six automatic calls: code review twice before the fix and twice after it, and verification twice.",
        "0006-review-state-validity-and-completion.md": "The bound of six automatic calls per Claim holds for one uninterrupted completion attempt;",
        "0009-security-critical-claims-get-an-adversarial-review.md": "A Security-critical claim makes at most fourteen automatic calls in one uninterrupted attempt,",
    }

    # Item 10: wording that states the fixed number as a rule, retired from shipped skill files, READMEs and the
    # setup document. The README's K = 2 example writes its bounds as numerals, so only "2 + 6N + 8S" needs an exception.
    RETIRED = re.compile(
        r"two consecutive automatic calls|two in a row|two-call|six automatic calls|at most six|six calls|fourteen"
        r"|refuted twice|up to two plan reviews|count stays where it stopped|because the count stays"
        r"|count is unchanged, so a reopened|保留它的次數與停止狀態，不會多出新的自動呼叫"
        r"|連續兩次|最多六次|十四次|兩次計畫審查|因為次數沒有歸零", re.I)
    SHIPPED_PATHSPECS = ("skills", "README.md", "README.zh-TW.md", "docs/setup.md")
    shipped_files = feather_support.shipped_files

    def test_review_state_resolves_the_stop_threshold_and_main_never_changes_it(self):
        self.assert_pinned(self.RESOLUTION)

    def test_every_step_stops_at_the_stop_threshold(self):
        self.assert_pinned(self.STOPPING)

    def test_one_rule_decides_the_next_automatic_call(self):
        self.assert_pinned(self.NEXT_CALL)
        # The rule is stated once, in review state, and the procedures point to it by name.
        self.assertEqual(self.source("review-state.md").count(self.NEXT_CALL_RULE), 1)
        for name in ("plan-review.md", "code-review.md", "outcome-verification.md", "adversarial-review.md"):
            with self.subTest(procedure=name):
                self.assertIn("[review state](review-state.md)'s Next automatic call", self.source(name))

    def test_a_change_of_the_stop_threshold_and_stating_it(self):
        self.assert_pinned(self.CHANGE)

    def test_the_security_analysis_is_not_counted(self):
        self.assert_pinned(self.NOT_COUNTED)

    def test_the_preview_states_the_stop_threshold_and_bounds_in_k(self):
        self.assert_pinned(self.PREVIEW)

    def test_readmes_state_the_stop_threshold_rules_in_both_languages(self):
        for en_label, zh_label, english, chinese in self.README_PAIRS:
            for place, sentence in ((f"README.md#{en_label}", english), (f"README.zh-TW.md#{zh_label}", chinese)):
                with self.subTest(place=place, sentence=sentence[:40]):
                    self.assert_whole_sentence(sentence, self.source(place))

    def test_the_bounds_hold_for_every_stop_threshold(self):
        # The stated formulas agree with the per-step counts they are derived from, and the README examples with them.
        for k in range(2, 11):
            with self.subTest(k=k):
                claim = k + (k - 1) * k + k  # code reviews before verification and per fix, plus verifications
                self.assertEqual(claim, k * (k + 1))
                self.assertEqual(claim + k + (k - 1) * claim, k ** 3 + k ** 2 + k)
        self.assertEqual((2 * 3, 2 ** 3 + 2 ** 2 + 2, 2 ** 3), (6, 14, 8))
        self.assertEqual((10 * 11, 10 ** 3 + 10 ** 2 + 10, 10 ** 3), (110, 1110, 1000))

    def test_adr_0010_records_the_decision_and_earlier_adrs_are_amended(self):
        decision = self.source("ADR 0010")
        self.assertTrue(decision.startswith("# The Stop threshold is one user-configurable number from 2 to 10\n"))
        for phrase in self.DECISION:
            with self.subTest(phrase=phrase[:50]):
                self.assertIn(phrase, decision)
        for heading in ("\n## Considered Options\n", "\n## Consequences\n"):
            with self.subTest(heading=heading.strip()):
                self.assertIn(heading, decision)
        for name, note in self.AMENDMENTS.items():
            text = (self.ADR / name).read_text(encoding="utf-8")
            with self.subTest(adr=name):
                self.assertIn(note, text.splitlines())
                self.assertIn(self.KEPT[name], text)

    def test_fixed_number_wording_is_retired_from_shipped_documents(self):
        files = [path for path in self.shipped_files() if path.suffix == ".md"]
        names = {path.relative_to(config.ROOT).as_posix() for path in files}
        self.assertTrue({"skills/delegation/references/review-state.md", "skills/delegation/references/preview.md",
                         "README.md", "README.zh-TW.md", "docs/setup.md"} <= names, "Git must list the shipped files")
        for path in files:
            text = path.read_text(encoding="utf-8")
            with self.subTest(path=path.relative_to(config.ROOT).as_posix()):
                self.assertIsNone(self.RETIRED.search(text))
                # The fixed Plan bound appears only in the K = 2 example.
                for clause in re.split(r"[.;。；] ?", text):
                    if "2 + 6N + 8S" in clause:
                        self.assertIn("K = 2", clause)

    def test_the_retired_pattern_matches_the_0_19_0_wording(self):
        for phrase in ("Two consecutive automatic calls without APPROVED stop automatic review",
                       "two in a row without a pass stop the step", "counts toward the two-call stop of step 4",
                       "at most six automatic calls per Claim, or fourteen for a Security-critical claim",
                       "a claim refuted twice in a row stops after one rechecked fix",
                       "including up to two plan reviews for each deviation",
                       "Because the count stays where it stopped, any later automatic call",
                       "連續兩次沒通過", "每個 claim 最多六次", "安全關鍵 claim 最多十四次", "每次偏離最多兩次計畫審查",
                       "因為次數沒有歸零",
                       "after an explicit APPROVED that cleared a stop the count is unchanged, so a reopened automatic call needs the user's explicit request",
                       "重疊的工作保留它的次數與停止狀態，不會多出新的自動呼叫"):
            with self.subTest(phrase=phrase):
                self.assertIsNotNone(self.RETIRED.search(phrase))


class ReviewerInconclusiveTests(unittest.TestCase):
    """Repository safety C3: reviewer can answer INCONCLUSIVE, code review counts and retries it like outcome
    verification, the call after it covers every gap it named, and every list of reviewer's verdicts has all three."""

    @staticmethod
    def source(name: str) -> str:
        """'reviewer.md', 'CONTEXT.md#<term>', '<README>#roles' (the reviewer row of the role table), or any place
            stop_threshold_source reads: '<procedure>', '<procedure>#<step>', a review-state bullet or a README rule."""
        path, _, part = name.partition("#")
        if path == "reviewer.md":
            return (config.ROOT / "templates" / "agents" / "reviewer.md").read_text(encoding="utf-8")
        if path == "CONTEXT.md":
            return feather_support.glossary_entries((config.ROOT / "CONTEXT.md").read_text(encoding="utf-8"))[part]
        if part == "roles":
            text = (config.ROOT / path).read_text(encoding="utf-8")
            return next(line for line in text.splitlines() if line.startswith("| reviewer |"))
        return feather_support.stop_threshold_source(name)

    assert_whole_sentence = feather_support.stop_threshold_assert_whole_sentence

    assert_pinned = feather_support.stop_threshold_assert_pinned

    # Item 1: the verdict, and CHANGES_REQUESTED when a blocking finding comes with gaps.
    VERDICT = {
        "reviewer.md": (
            "- APPROVED: no blocking finding remains and no evidence the review needs is missing.",
            "- INCONCLUSIVE: evidence the review needs could not be obtained, safely or at all, and you have no blocking finding.",
            "Name the missing evidence and list any non-blocking findings; INCONCLUSIVE proves no defect.",
            "When you have a blocking finding and evidence the review needs is also missing, answer CHANGES_REQUESTED and list the gaps with it.",
        ),
        "code-review.md": (
            "This procedure governs main's orchestration. Reviewer's role definition governs review criteria and its APPROVED, CHANGES_REQUESTED or INCONCLUSIVE report.",
        ),
    }

    # Item 2: counted like outcome verification, no FIX or REJECT obligation, retried only after the evidence changed.
    COUNTING = {
        "code-review.md#3": (
            "An automatic INCONCLUSIVE counts as a call without a pass, as in [outcome verification](outcome-verification.md).",
        ),
        "code-review.md#4": (
            "An INCONCLUSIVE proves no defect and creates no FIX or REJECT obligation: make the next call only after the named missing evidence has changed, and otherwise report the claim unreviewed.",
        ),
        "outcome-verification.md#5": (
            "On INCONCLUSIVE, use the next call only after the named missing evidence, prerequisite or environment has changed; otherwise report the claim unverified.",
        ),
        "CONTEXT.md#Code review": (
            "An independent check of the code implementing a Claim, answered APPROVED, CHANGES_REQUESTED or INCONCLUSIVE.",
            "INCONCLUSIVE means evidence the review needs could not be obtained, safely or at all; it is not a pass and does not prove a defect.",
        ),
        "CONTEXT.md#Unreviewed claim": (
            "A Claim whose Code review stopped at its Stop threshold without APPROVED, or ended INCONCLUSIVE while the evidence it named as missing has not changed.",
        ),
    }

    # Item 3: no narrowing past a gap, beside the narrowed-review rule in review state, the procedure and the role.
    NARROWING = {
        "review-state.md#Completed calls and coverage": (
            "A second review, narrowed to the earlier findings and the fixes, and the range from the previously judged commit follow only when the previous call completed.",
            "The code review after an INCONCLUSIVE covers every gap that call named, even though that call completed: a narrowed follow-up never closes a gap it did not examine, and no APPROVED is given while a named gap is unexamined.",
        ),
        "code-review.md#2": (
            "On a later call for the same claim, state whether the previous call completed with a verdict; the reviewer narrows its review only when the brief says it did, as [review state](review-state.md)'s Completed calls and coverage describes.",
            "When the previous call answered INCONCLUSIVE, the brief names every gap that call named, and the next call covers each of them even though that call completed; a narrowed follow-up never closes a gap it did not examine, and no APPROVED is given while a named gap is unexamined.",
        ),
        "reviewer.md": (
            "When the previous call answered INCONCLUSIVE, cover every gap it named, even though that call completed: a narrowed review never closes a gap you did not examine, and you do not answer APPROVED while a named gap is unexamined.",
        ),
    }

    # Item 4: every list of reviewer's verdicts names all three, the READMEs in both languages.
    LISTS = {
        "README.md#roles": ("APPROVED/CHANGES_REQUESTED/INCONCLUSIVE",),
        "README.zh-TW.md#roles": ("APPROVED／CHANGES_REQUESTED／INCONCLUSIVE",),
    }

    README_PAIRS = (
        ("Budget", "次數上限",
         "A code review that returns INCONCLUSIVE counts as not passing too, but proves no defect and asks for no fix: its next call waits until the missing evidence it names has changed, and until then the claim is unreviewed.",
         "程式碼審查回覆 INCONCLUSIVE 也算沒通過，但不代表有缺陷，也不要求修正；下一次呼叫要等它指出的缺少證據有所改變，在那之前 claim 都算未審查。"),
    )

    # A list of reviewer's verdicts that stops at two.
    TWO_VERDICTS = re.compile(r"APPROVED(?:/|／|, | or )CHANGES_REQUESTED(?!(?:/|／| or )INCONCLUSIVE)")
    SHIPPED_PATHSPECS = ("skills", "templates", "README.md", "README.zh-TW.md", "CONTEXT.md", "docs/setup.md")
    shipped_files = feather_support.shipped_files

    def test_reviewer_answers_inconclusive_and_changes_requested_takes_precedence(self):
        self.assert_pinned(self.VERDICT)

    def test_code_review_counts_and_retries_inconclusive_like_outcome_verification(self):
        self.assert_pinned(self.COUNTING)

    def test_the_call_after_inconclusive_covers_every_named_gap(self):
        self.assert_pinned(self.NARROWING)
        # The rule sits beside the narrowed-review rule: in the same review-state bullet, procedure step and role paragraph.
        reviewer = self.source("reviewer.md")
        paragraph = next(part for part in reviewer.split("\n\n")
                         if part.startswith("When the brief says the previous call for this claim completed with a verdict"))
        self.assertIn(self.NARROWING["reviewer.md"][0], paragraph)

    def test_every_list_of_reviewer_verdicts_names_all_three(self):
        for place, phrases in self.LISTS.items():
            for phrase in phrases:
                with self.subTest(place=place):
                    self.assertIn(phrase, self.source(place))
        for en_label, zh_label, english, chinese in self.README_PAIRS:
            for place, sentence in ((f"README.md#{en_label}", english), (f"README.zh-TW.md#{zh_label}", chinese)):
                with self.subTest(place=place, sentence=sentence[:40]):
                    self.assert_whole_sentence(sentence, self.source(place))
        files = [path for path in self.shipped_files() if path.suffix == ".md"]
        names = {path.relative_to(config.ROOT).as_posix() for path in files}
        self.assertTrue({"templates/agents/reviewer.md", "skills/delegation/references/code-review.md",
                         "README.md", "README.zh-TW.md", "CONTEXT.md"} <= names, "Git must list the shipped files")
        for path in files:
            with self.subTest(path=path.relative_to(config.ROOT).as_posix()):
                self.assertIsNone(self.TWO_VERDICTS.search(path.read_text(encoding="utf-8")))

    def test_the_two_verdict_pattern_matches_the_earlier_wording(self):
        for phrase in ("its APPROVED/CHANGES_REQUESTED report", "APPROVED／CHANGES_REQUESTED |",
                       "answered APPROVED or CHANGES_REQUESTED.", "APPROVED/CHANGES_REQUESTED |"):
            with self.subTest(phrase=phrase):
                self.assertIsNotNone(self.TWO_VERDICTS.search(phrase))
        for phrase in ("APPROVED/CHANGES_REQUESTED/INCONCLUSIVE", "APPROVED, CHANGES_REQUESTED or INCONCLUSIVE",
                       "APPROVED／CHANGES_REQUESTED／INCONCLUSIVE"):
            with self.subTest(phrase=phrase):
                self.assertIsNone(self.TWO_VERDICTS.search(phrase))

    def test_installed_reviewer_renders_the_verdict_and_the_gap_rule(self):
        choice = {"model": "sonnet", "effort": "high"}
        for prefix in ("", "cc-"):
            rendered = config._render("reviewer", choice, prefix).decode("utf-8")
            for sentence in (self.VERDICT["reviewer.md"][1], self.VERDICT["reviewer.md"][3], self.NARROWING["reviewer.md"][0]):
                with self.subTest(prefix=prefix, sentence=sentence[:40]):
                    self.assertIn(sentence, rendered)


if __name__ == "__main__":
    unittest.main()
