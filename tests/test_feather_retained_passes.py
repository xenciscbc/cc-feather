"""Retained passes ticket 01 (docs/specs/retained-passes.md, Acceptance items 1, 2 and 3 and the parts of items 16, 17
and 18 for these rules): in auto, each Claim's code review and then outcome verification run once that Claim is
implemented and committed, as the only review timing in auto, replacing the rule that reviews start once the reviewed
Plan is implemented; a Claim that lists another under Blocked by, or otherwise depends on it as its Plan states, waits for that Claim's valid APPROVED and CONFIRMED, a
Plan that states no dependencies is followed in order, and a stopped upstream Claim stops the Claims that depend on it
until the user decides, a decision recorded as a deferral of the upstream Claim. The verifier template and the
installed policy are unchanged, since no ticket of the spec changes them.

Retained passes ticket 02 (Acceptance items 4, 5 and 15, the parts of items 14, 16, 17 and 18 for these rules, and
security invariants S5 and S7): in auto, a Claim's APPROVED and CONFIRMED stay fixed for a change within the range
another Claim of the same Plan had judged by a completed code review and outcome verification that both passed; any
other change, and every change in off, keeps file-level reopening; a Claim changes another Claim's acceptance checks
only where its reading set says so, and its code review brief then carries that acceptance for a weakening check;
turning automatic review off during a Plan reopens fixed passes. The reviewer template is unchanged.

Retained passes ticket 03 (Acceptance items 6, 7 and 15, the parts of items 10, 14, 16, 17 and 18 for these rules, and
security invariants S1, S3 and S4): in auto, main confirms each Claim's reading set before the final check, which also
reruns every Claim's primary acceptance; an attributed failure is fixed by its Claim through its reviews, an unattributed
one by a fix Claim main adds without asking, which never changes what it is judged by; no other Claim is reopened, and a
final check that keeps failing at new commits stops at the Stop threshold's value. Every review brief names the Plan's
base revision, and main judges from Git whether a finding reported as pre-existing was introduced after it. Off keeps
today's final check. The adversary template is unchanged.

Retained passes ticket 04 (Acceptance items 8, 9 and 15, the parts of items 14, 16, 17 and 18 for these rules, and
security invariant S2): in auto, once the final check has passed at the final commit with the workspace equal to it, each
Security-critical claim other than a fix Claim gets one Adversarial review there; only a call made then gives the Claim's
result, an earlier or other commit's result and an earlier explicit call counting as not run; a BROKEN is recorded in the
Follow-up record rather than fixed in the Plan, and its findings stay listed until a HELD at the commit to be landed
replaces them. Off keeps the same-commit premise, a BROKEN fixed before completion and the command's off rule. Ticket 03's
pin of the unchanged adversary template covers this ticket too.

Retained passes ticket 05 (Acceptance items 11, 12 and 15, the parts of items 13, 14, 16, 17 and 18 for these rules, and
the residual risk "The dispatch record is trusted"): in auto, main keeps one dispatch record per Plan under
`.feather/dispatch/`, holding what a later session needs and no counts, exploit details or secrets, written only between
review calls and kept out of Git; a resumed session, and main after a context compaction, take the Plan's READY, reading
sets, passes, Adversarial review results and the user's decisions from it as if received in this session, while counts,
the Stop threshold and the final check's state still come only from this session. Off writes none and keeps the earlier
cross-session rules. The handoff skill and its tool are unchanged."""

from __future__ import annotations

import hashlib
import subprocess
import unittest

from tests import feather_support
from tests.feather_support import config


class PerClaimTimingTests(unittest.TestCase):
    """Whole-sentence pins of the new statements, absence pins of the replaced timing, pins of the unchanged verifier
    template and installed policy, and a check that every new pin fails on the text at tag v0.25.0."""

    ADR_0015 = "0015-each-claim-is-reviewed-when-done-and-keeps-its-passes.md"
    ADR_0013 = "0013-only-what-a-claims-acceptance-needs-holds-its-completion.md"
    # The repository path behind each place, for reading the same place at the tag.
    PATHS = {
        "review-state.md": "skills/delegation/references/review-state.md",
        "plan-review.md": "skills/delegation/references/plan-review.md",
        "code-review.md": "skills/delegation/references/code-review.md",
        "outcome-verification.md": "skills/delegation/references/outcome-verification.md",
        "SKILL.md": "skills/delegation/SKILL.md",
        "CONTEXT.md": "CONTEXT.md",
        "README.md": "README.md",
        "README.zh-TW.md": "README.zh-TW.md",
        "ADR 0015": f"docs/adr/{ADR_0015}",
        "ADR 0013": f"docs/adr/{ADR_0013}",
    }
    TAG = "v0.25.0"
    # The reference's read-only Git prefix (repository safety's Safe Git invocation).
    GIT_READ = ("git", "--no-pager", "--no-optional-locks", "-c", "core.fsmonitor=", "-c", "core.quotePath=true",
                "-c", "log.showSignature=false", "-c", "mailmap.file=", "-c", "mailmap.blob=",
                "-c", "blame.ignoreRevsFile=", "-c", "diff.orderFile=/dev/null", "-c", "submodule.recurse=false")

    @classmethod
    def source(cls, name: str) -> str:
        """'<file>', 'review-state.md#<bullet label>', 'CONTEXT.md#<term>', '<README>#<rule label>', 'SKILL.md#<heading>'
            (a section of the delegation skill), 'ADR 0015', 'ADR 0015#options' (its Considered Options) or
            'ADR 0013'."""
        path, _, part = name.partition("#")
        if path.startswith("ADR ") or path == "SKILL.md":
            text = (config.ROOT / cls.PATHS[path]).read_text(encoding="utf-8")
            if path == "SKILL.md" and part:
                return text.split(f"\n## {part}\n", 1)[1].split("\n## ", 1)[0]
            if part == "options":
                return text.split("\n## Considered Options\n", 1)[1].split("\n## ", 1)[0]
            return text
        return feather_support.review_rules_source(name)

    assert_whole_sentence = feather_support.stop_threshold_assert_whole_sentence

    assert_pinned = feather_support.stop_threshold_assert_pinned

    # Acceptance item 1: per-Claim timing is the only review timing in auto, a single-Claim Plan is unchanged, and the
    # serial rule holds under it.
    TIMING = {
        "review-state.md#Per-claim timing": (
            "In auto, each claim of plan-driven work gets its code review and then its outcome verification once that "
            "claim is implemented and committed, not once the whole plan is implemented.",
            "This is the only review timing in auto: no setting or plan statement selects another.",
            "A plan with a single claim is unchanged.",
            "Implementation and reviews in one working tree stay serial as Serial within a working tree states, so a "
            "claim with no dependency still waits for a review call running in the same working tree.",
            "Which claim starts next follows Dependent claims.",
        ),
        "plan-review.md": (
            "Once a claim is implemented, its reviews judge it against the completion criteria [review "
            "state](review-state.md) states: its acceptance as written is met; existing behaviour is not broken, shown by "
            "a failing test or a reproduction judged against the claim's base revision; it introduces no security problem "
            "and no data loss; and it has no deviation from the plan.",
            "In auto, each claim of the reviewed plan gets [code review](code-review.md), then [outcome "
            "verification](outcome-verification.md) and, for a Security-critical claim, then [Adversarial "
            "review](adversarial-review.md) before main reports it complete; its code review and outcome verification "
            "run once that claim is implemented and committed, without waiting for the rest of the plan, as [review "
            "state](review-state.md)'s Per-claim timing describes.",
            "This is the only review timing in auto, and no setting or plan statement selects another; a claim that "
            "depends on another starts as [review state](review-state.md)'s Dependent claims describes.",
        ),
        "code-review.md": (
            "In auto, a claim's code review runs once that claim is implemented and committed, without waiting for the "
            "rest of the plan, as [review state](review-state.md)'s Per-claim timing describes; this is the only review "
            "timing in auto.",
        ),
        "outcome-verification.md": (
            "In auto, a claim's outcome verification runs once that claim is implemented and committed and its code "
            "review has returned APPROVED, without waiting for the rest of the plan, as [review "
            "state](review-state.md)'s Per-claim timing describes; this is the only review timing in auto.",
        ),
        "SKILL.md#Plan review": (
            "In auto, each claim of plan-driven work also needs code review and then outcome verification once that "
            "claim is implemented and committed, and a Security-critical claim then Adversarial review; in off, an "
            "explicit plan-review request does not imply them.",
            "This per-claim timing is the only review timing in auto, and reviews and implementation in one working tree "
            "stay serial.",
        ),
    }

    # Acceptance item 2: the Blocked by wait, no wait for independent Claims and the Plan's order as the default.
    DEPENDENT = {
        "review-state.md#Dependent claims": (
            "In auto, a claim that lists another under `Blocked by`, or otherwise depends on it as its plan states, "
            "starts only after that claim has a valid APPROVED and a valid CONFIRMED.",
            "A claim with no such dependency does not wait for other claims' passes.",
            "Where a plan states no dependencies between its claims, main follows the plan's order and treats each claim "
            "as depending on those before it.",
        ),
        "SKILL.md#Plan review": (
            "A claim that lists another under `Blocked by`, or otherwise depends on it as its plan states, starts only "
            "after that claim has a valid APPROVED and "
            "CONFIRMED, a plan that states no dependencies is followed in order, and when a claim stops, the claims that "
            "depend on it stop and main asks the user, who may let named dependent claims proceed as a deferral of the "
            "stopped claim, as [review state](references/review-state.md)'s Per-claim timing and Dependent claims "
            "describe.",
        ),
    }

    # Acceptance item 3: a stopped upstream Claim stops its dependants, main asks, and the user's decision is a deferral
    # of the upstream Claim whose scope names the dependants allowed to start.
    STOPPED_UPSTREAM = {
        "review-state.md#Dependent claims": (
            "When a claim's code review or outcome verification stops, its outcome verification cannot be resolved, it "
            "has a Deviation, or it would need accept and land, every claim that depends on it stops and main asks the "
            "user.",
            "The user may decide that named dependent claims proceed: main records it under User decisions as a deferral "
            "of the upstream claim whose scope names the dependent claims allowed to start, and only those start.",
            "The upstream claim stays a Pending-acceptance claim until its passes become valid or the user decides on it "
            "at the end of the plan, as Accept and land at the end of the plan describes.",
        ),
        "review-state.md#User decisions": (
            "A deferral of a stopped upstream claim names in its scope the dependent claims allowed to start, as "
            "Dependent claims describes.",
        ),
    }

    # Acceptance item 16, for these rules: the glossary entries state per-Claim timing.
    CONTEXT = {
        "CONTEXT.md#Automatic flow": (
            "Each Claim's Code review and then Outcome verification run once that Claim is implemented and committed; "
            "this is the only review timing in auto.",
            "A Claim that lists another under Blocked by, or otherwise depends on it as its Plan states, starts only "
            "after that Claim has a valid APPROVED and "
            "CONFIRMED, and a Plan that states no dependencies is followed in order; when a Claim stops, every Claim that "
            "depends on it stops and main asks the user, who may let named dependent Claims proceed as a deferral of the "
            "stopped Claim.",
        ),
        "CONTEXT.md#Code review": (
            "In the Automatic flow it runs once the Claim is implemented and committed, without waiting for the rest of "
            "the Plan.",
        ),
        "CONTEXT.md#Outcome verification": (
            "In the Automatic flow it follows the Claim's APPROVED once the Claim is implemented and committed, without "
            "waiting for the rest of the Plan.",
        ),
    }

    # Acceptance item 16, for these rules: ADR 0015's part on per-Claim timing amends ADR 0013's deferral of it.
    ADR = {
        "ADR 0015": (
            "This record is written in parts, each by the ticket that implements its rule, so that its implementation "
            "and reviews can check it against the procedures they change.",
            "This part records per-Claim timing.",
            "The user decided (2026-10-14 and 2026-10-15; the [spec](../specs/retained-passes.md) carries the "
            "acceptance):",
            "In the Automatic flow, each Claim's code review and then outcome verification run once that Claim is "
            "implemented and committed, replacing the rule that reviews start once the reviewed Plan is implemented.",
            "It is the only review timing in auto: no setting or Plan statement selects another.",
            "A single-Claim Plan is unchanged.",
            "Implementation and reviews in one working tree stay serial, so a Claim with no dependency still waits for a "
            "review call running in the same working tree.",
            "A Claim that lists another under Blocked by, or otherwise depends on it as its Plan states, starts only "
            "after that Claim has valid APPROVED and CONFIRMED.",
            "Claims with no such dependency do not wait for other Claims' passes.",
            "Where a Plan states no dependencies between its Claims, main follows the Plan's order and treats each Claim "
            "as depending on those before it.",
            "When a Claim's code review or outcome verification stops, its outcome verification cannot be resolved, it "
            "has a Deviation, or it would need Accept and land, every Claim that depends on it stops and main asks the "
            "user.",
            "The user may decide that named dependent Claims proceed; main records it under User decisions as a deferral "
            "of the upstream Claim whose scope names the dependent Claims allowed to start, and the upstream Claim stays "
            "a Pending-acceptance claim until the user's decision at the end of the Plan or until its passes become "
            "valid.",
            "This amends [ADR 0013](0013-only-what-a-claims-acceptance-needs-holds-its-completion.md): per-Claim review "
            "timing, which it deferred to separate work on retained passes, is now the only review timing in auto.",
        ),
        "ADR 0015#options": (
            "- **Review after the whole Plan is implemented**: a problem in an early Claim is found only after later "
            "Claims were built on it.",
            "- **A setting or Plan statement that chooses the timing**: two timings double the rules and tests.",
        ),
    }
    ADR_0013_NOTE = ("(Amended by ADR 0015: per-Claim review timing, deferred above to separate work on retained passes, "
                     "is now the only review timing in auto: each Claim's code review and then outcome verification run "
                     "once that Claim is implemented and committed, and a Claim that depends on another waits for its "
                     "valid APPROVED and CONFIRMED.)")

    # Acceptance item 17, for these rules: (English label, Chinese label, English sentence, Chinese sentence).
    README_PAIRS = (
        ("Per-claim timing", "依 claim 審查的時機",
         "in auto, each claim gets its code review and then its verification as soon as that claim is implemented and "
         "committed, not after the whole plan is implemented, so a problem in an early claim is found before later "
         "claims build on it.",
         "在 auto 下，每個 claim 一實作完成並 commit，就接著做它的程式碼審查，再做結果驗證，不等整份計畫實作完，所以早期 "
         "claim 的問題會在後面的 claim 建立在它之上之前被發現。"),
        ("Per-claim timing", "依 claim 審查的時機",
         "This is the only timing in auto: no setting or plan statement chooses another, and a plan with a single claim "
         "works as before.",
         "這是 auto 唯一的審查時機：沒有任何設定或計畫寫法能選擇別的時機，只有一個 claim 的計畫照舊。"),
        ("Per-claim timing", "依 claim 審查的時機",
         "Reviews and implementation in one working tree still take turns, as Serial reviews says, so even a claim that "
         "depends on no other waits while a review runs in the same working tree.",
         "同一個工作樹裡的審查與實作仍然輪流進行，如「審查依序進行」所說，所以即使不依賴任何 claim，也要等同一個工作樹裡"
         "正在進行的審查結束。"),
        ("Dependent claims", "相依的 claim",
         "a claim that lists another under `Blocked by`, or otherwise depends on it as its plan states, starts only "
         "after that claim has a valid APPROVED and CONFIRMED; a claim with no such dependency does not wait for other "
         "claims' passes.",
         "在 `Blocked by` 列出另一個 claim，或依計畫所述以其他方式依賴它的 claim，要等那個 claim 拿到有效的 APPROVED 與 "
         "CONFIRMED 才開始；沒有這種相依的 claim 不必等其他 claim 通過。"),
        ("Dependent claims", "相依的 claim",
         "When a plan states no dependencies between its claims, main follows the plan's order and treats each claim as "
         "depending on those before it.",
         "計畫沒寫 claim 之間的相依時，主 Agent 依計畫順序進行，把每個 claim 都視為依賴排在它前面的 claim。"),
        ("Dependent claims", "相依的 claim",
         "When a claim's code review or verification stops, its verification cannot be resolved, it has a deviation or "
         "it would need your accept-and-land decision, every claim that depends on it stops and main asks you.",
         "某個 claim 的程式碼審查或驗證停下、驗證無法解決、出現偏離，或需要你決定接受並合併時，所有依賴它的 claim "
         "都會停下，主 Agent 會問你。"),
        ("Dependent claims", "相依的 claim",
         "You may let named dependent claims proceed: main records that as a deferral of the upstream claim whose scope "
         "names the claims allowed to start, and the upstream claim stays pending acceptance until its passes become "
         "valid or you decide on it at the end of the plan.",
         "你可以讓指定的相依 claim 繼續：主 Agent 會把這記為上游 claim 的延後，範圍寫明允許開始的 claim，而上游 claim "
         "維持待驗收，直到它的審查與驗證重新有效，或你在計畫最後對它做出決定。"),
    )

    # Acceptance item 18: the replaced statements that reviews start once the reviewed Plan is implemented.
    REPLACED = {
        "plan-review.md": (
            "In auto, once the reviewed plan is implemented, follow",
            "Once a plan is implemented, each claim's reviews judge it",
        ),
        "SKILL.md#Plan review": (
            "plan-driven work also needs code review and then outcome verification once implemented,",
        ),
    }

    # Acceptance item 18 and the Testing Decisions: the verifier template and the installed policy are unchanged, as
    # at v0.25.0 (line endings normalised to LF, as .gitattributes stores them).
    UNCHANGED = {
        "templates/agents/verifier.md": "7d8fb644a46bc824244d012c147fa2a357d00ee2c588bf0111c1655e43f78fb0",
        "templates/review-auto.md": "74d02a9476bf4013f9f474eed0a0d98d5e7ae5c370f49044313c20ca39b49c97",
    }

    def new_pins(self):
        pins = {}
        for group in (self.TIMING, self.DEPENDENT, self.STOPPED_UPSTREAM, self.CONTEXT, self.ADR):
            for place, sentences in group.items():
                pins.setdefault(place, []).extend(sentences)
        pins.setdefault("ADR 0013", []).append(self.ADR_0013_NOTE)
        for en_label, zh_label, english, chinese in self.README_PAIRS:
            pins.setdefault(f"README.md#{en_label}", []).append(english)
            pins.setdefault(f"README.zh-TW.md#{zh_label}", []).append(chinese)
        return pins

    def test_per_claim_timing_is_the_only_timing_in_auto(self):
        self.assert_pinned(self.TIMING)

    def test_a_dependent_claim_waits_for_its_upstream_passes(self):
        self.assert_pinned(self.DEPENDENT)

    def test_a_stopped_upstream_claim_stops_its_dependants_until_the_user_defers_it(self):
        self.assert_pinned(self.STOPPED_UPSTREAM)

    def test_the_timing_rules_sit_beside_the_serial_rule(self):
        # Per-claim timing and Dependent claims come right before Serial within a working tree, which they rely on.
        text = (config.ROOT / self.PATHS["review-state.md"]).read_text(encoding="utf-8")
        section = text.split("## Validity and completion", 1)[1].split("\n## ", 1)[0]
        labels = [line.split("**", 2)[1] for line in section.splitlines() if line.startswith("- **")]
        index = labels.index("Per-claim timing.")
        self.assertEqual(labels[index:index + 3],
                         ["Per-claim timing.", "Dependent claims.", "Serial within a working tree."])

    def test_glossary_states_per_claim_timing(self):
        self.assert_pinned(self.CONTEXT)

    def test_adr_0015_records_per_claim_timing_and_amends_adr_0013(self):
        self.assert_pinned(self.ADR)
        lines = self.source("ADR 0013").splitlines()
        self.assertIn(self.ADR_0013_NOTE, lines)
        self.assertEqual(sum(line.startswith("(Amended by ADR 0015:") for line in lines), 1)

    def test_both_readmes_explain_per_claim_timing_and_dependent_claims(self):
        for en_label, zh_label, english, chinese in self.README_PAIRS:
            for place, sentence in ((f"README.md#{en_label}", english), (f"README.zh-TW.md#{zh_label}", chinese)):
                with self.subTest(place=place, sentence=sentence[:40]):
                    self.assert_whole_sentence(sentence, self.source(place))

    def test_reviews_no_longer_start_once_the_plan_is_implemented(self):
        for place, phrases in self.REPLACED.items():
            text = self.source(place)
            for phrase in phrases:
                with self.subTest(place=place, phrase=phrase[:60]):
                    self.assertNotIn(phrase, text)

    def test_the_verifier_template_and_the_installed_policy_are_unchanged(self):
        for path, digest in self.UNCHANGED.items():
            text = (config.ROOT / path).read_text(encoding="utf-8").replace("\r\n", "\n")
            with self.subTest(path=path):
                self.assertEqual(hashlib.sha256(text.encode("utf-8")).hexdigest(), digest)

    def tagged(self, place, path=None):
        """The whole file behind a place (or a repository path) at the tag, '' when it did not exist there; skips
            without the tag."""
        path = path or self.PATHS[place.partition("#")[0]]
        try:
            shown = subprocess.run([*self.GIT_READ, "cat-file", "blob", f"{self.TAG}:{path}"], cwd=config.ROOT,
                                   stdin=subprocess.DEVNULL, capture_output=True, timeout=60)
            known = subprocess.run([*self.GIT_READ, "rev-parse", "--verify", "--quiet", f"{self.TAG}^{{commit}}"],
                                   cwd=config.ROOT, stdin=subprocess.DEVNULL, capture_output=True, timeout=60)
        except (OSError, subprocess.TimeoutExpired) as error:
            self.skipTest(f"Git cannot be run, so the {self.TAG} text cannot be read: {error}")
        if known.returncode != 0:
            self.skipTest(f"no {self.TAG} in this checkout")
        return shown.stdout.decode("utf-8") if shown.returncode == 0 else ""

    def test_every_new_pin_fails_on_the_v0_25_0_text(self):
        for place, sentences in self.new_pins().items():
            text = self.tagged(place)
            for sentence in sentences:
                with self.subTest(place=place, sentence=sentence[:60]):
                    self.assertFalse(sentence in text, f"{place} already said this at {self.TAG}")

    def test_every_absence_pin_matches_the_v0_25_0_text(self):
        for place, phrases in self.REPLACED.items():
            text = self.tagged(place)
            for phrase in phrases:
                with self.subTest(place=place, phrase=phrase[:60]):
                    self.assertIn(phrase, text)

    def test_the_unchanged_pins_match_the_v0_25_0_text(self):
        for path, digest in self.UNCHANGED.items():
            text = self.tagged(path, path).replace("\r\n", "\n")
            with self.subTest(path=path):
                self.assertEqual(hashlib.sha256(text.encode("utf-8")).hexdigest(), digest)


class FixedPassesTests(unittest.TestCase):
    """Ticket 02: whole-sentence pins of fixed passes, S5, S7, off mode and the brief for another Claim's acceptance
    checks, absence pins of the replaced file-level reopening in auto, a pin of the unchanged reviewer template, and a
    check that every new pin fails on the text at tag v0.25.0. It reuses ticket 01's readers rather than changing them."""

    ADR_0006 = "0006-review-state-validity-and-completion.md"
    PATHS = {**PerClaimTimingTests.PATHS, "ADR 0006": f"docs/adr/{ADR_0006}"}
    TAG = PerClaimTimingTests.TAG
    GIT_READ = PerClaimTimingTests.GIT_READ
    PART = "Fixed passes"

    @classmethod
    def source(cls, name: str) -> str:
        """As ticket 01's reader, plus 'ADR 0015#part' (this ticket's part of ADR 0015) and 'ADR 0006'."""
        if name == "ADR 0015#part":
            text = (config.ROOT / cls.PATHS["ADR 0015"]).read_text(encoding="utf-8")
            return text.split(f"\n## {cls.PART}\n", 1)[1].split("\n## ", 1)[0]
        if name == "ADR 0006":
            return (config.ROOT / cls.PATHS[name]).read_text(encoding="utf-8")
        return PerClaimTimingTests.source(name)

    assert_whole_sentence = feather_support.stop_threshold_assert_whole_sentence

    assert_pinned = feather_support.stop_threshold_assert_pinned

    tagged = PerClaimTimingTests.tagged

    # Acceptance item 4 and S5: fixed passes in auto, their condition, who fixes a finding and what still reopens.
    FIXED = {
        "review-state.md#What a pass covers": (
            "A later change to a claim's files or to what they depend on reopens code review and outcome verification "
            "for that claim, except where its passes stay fixed in auto as described below;",
            "In auto, a claim's valid APPROVED and CONFIRMED are a judgement of the commit they judged and stay fixed: "
            "they are not reopened by a change to the claim's files or to what they depend on that lies within the range "
            "judged by another claim's completed code review and outcome verification of the same plan, both of which "
            "passed; a fix claim counts as another claim.",
            "A Blocking finding in that other claim's reviews is that claim's to fix.",
            "Which files of another claim's acceptance checks a claim may change, and what its code review then checks, "
            "are as [code review](code-review.md) step 2 describes.",
            "Any other change keeps the file-level rules above, such as an edit outside the plan's claims, a rebase, an "
            "environment or test target change, a change to the claim's reading set, or a change whose claim ends without "
            "both passes.",
            "Fixed passes do not change what reopens a Security-critical claim's HELD.",
        ),
    }
    S5 = ("Passes stay fixed only for a change inside the range judged by another claim's completed code review and "
          "outcome verification of the same plan that both passed: when that claim's review stops, is cancelled, is "
          "deferred or ends in accept and land without both passes, its changes reopen the claims whose files or "
          "dependencies they touch, under the file-level rules above.")
    # Acceptance item 15 for these rules: off keeps file-level reopening whichever claim made the change.
    OFF = ("Fixed passes hold in auto only: in off, a later change to a claim's files or to what they depend on reopens "
           "its code review and outcome verification under the file-level rules above, whichever claim made it.")
    S7 = ("When automatic review is turned off for a plan before the user's decision at the end of the plan, as Accept "
          "and land at the end of the plan describes, every fixed pass whose claim's files or dependencies another claim "
          "changed after it is reopened under the file-level rules above, and the cross-session rules of off apply from "
          "then on, as Resumed sessions describes.")
    # Acceptance item 14, the limits of fixed passes.
    LIMITS = ("Fixed passes have limits this flow does not check: a later claim's reviewer reads only its own reading set "
              "and may not know an earlier claim's design intent, and a property of an earlier claim that no acceptance "
              "check the final check runs covers can be broken without the final check noticing.")

    # Acceptance item 5: the reading-set condition, how main decides the files, the brief's stated exception and the
    # weakening check; review state's Reading set points to it.
    ACCEPTANCE_CHECKS = {
        "code-review.md": (
            "In auto, a claim may change a file that another claim's acceptance checks run or read, such as its tests, "
            "expected values, fixtures, discovery or runner configuration and their support code, only where the "
            "changing claim's own reading set states that it does; otherwise the change is a Deviation and a Blocking "
            "finding.",
            "Main decides which files these are from the changing claim's commit, files it adds included, and counts a "
            "file it cannot rule out as one of them.",
            "When the changing claim's diff changes such a file, the brief names those files and also carries the "
            "acceptance of each claim whose checks the file serves, as a stated exception to the rule that a brief "
            "carries only the recorded reading set, and the reviewer checks from the diff that the change does not "
            "weaken that acceptance, for example by loosening an assertion, replacing a fixture or turning off discovery; "
            "a weakening is a Blocking finding.",
            "The installed reviewer definition is unchanged: the brief states this check.",
        ),
        "review-state.md#Reading set": (
            "In auto, a code review brief also carries another claim's acceptance where [code review](code-review.md) "
            "step 2 adds it for a claim that changes that claim's acceptance checks.",
        ),
    }

    # Acceptance item 16, for these rules: the glossary entries state fixed passes.
    CONTEXT = {
        "CONTEXT.md#Code review": (
            "In the Automatic flow its APPROVED stays fixed when another Claim of the same Plan changes the Claim's files "
            "or what they depend on within the range that Claim's own completed Code review and Outcome verification "
            "judged, both of which passed; any other change, and in off any change to the Claim's files or what they "
            "depend on, reopens it.",
        ),
        "CONTEXT.md#Outcome verification": (
            "In the Automatic flow its CONFIRMED stays fixed when another Claim of the same Plan changes the Claim's "
            "files or what they depend on within the range that Claim's own completed Code review and Outcome "
            "verification judged, both of which passed; any other change, and in off any change to the Claim's files or "
            "what they depend on, reopens it.",
        ),
    }

    # Acceptance item 16, for these rules: ADR 0015's part on fixed passes and S5 amends ADR 0006 (what a pass covers).
    ADR = {
        "ADR 0015#part": (
            "This part records fixed passes.",
            "The user decided (2026-10-14 and 2026-10-15, the second day after a security analysis; the "
            "[spec](../specs/retained-passes.md) carries the acceptance and its security invariants):",
            "- **Passes stay fixed.** In auto, a Claim's valid APPROVED and CONFIRMED are a judgement of the commit they "
            "judged and are not reopened by a change to the Claim's files or to what they depend on that lies within the "
            "range judged by another Claim's completed code review and outcome verification of the same Plan, both of "
            "which passed; a fix Claim counts as another Claim.",
            "A Blocking finding in that other Claim's reviews is that Claim's to fix.",
            "- **A fixed pass needs a passing review of the change.** A Claim's passes stay fixed only for a change "
            "inside that range.",
            "When that other Claim's review stops, is cancelled, is deferred or ends in Accept and land without both "
            "passes, its changes reopen the Claims whose files or dependencies they touch, under the earlier rules.",
            "- **What still reopens.** Any other change keeps the earlier rules: an edit outside the Plan's Claims, a "
            "rebase, an environment or test target change, a change to the Claim's reading set, or a change whose Claim "
            "ends without both passes.",
            "What reopens a Security-critical claim's HELD is unchanged by this part.",
            "- **Another Claim's acceptance checks.** A Claim may change a file that another Claim's acceptance checks "
            "run or read, such as its tests, expected values, fixtures, discovery or runner configuration and their "
            "support code, only where the changing Claim's own reading set states that it does; otherwise the change is "
            "a Deviation and a Blocking finding.",
            "Main decides which files these are from the changing Claim's commit, files it adds included, and counts a "
            "file it cannot rule out as one of them.",
            "When the changing Claim's diff changes such a file, its code review brief also carries the acceptance of "
            "each Claim whose checks the file serves, as a stated exception to the rule that a brief carries only the "
            "recorded reading set, and the reviewer checks from the diff that the change does not weaken that "
            "acceptance; a weakening is a Blocking finding.",
            "The installed reviewer definition is unchanged; the code review procedure states this in the brief.",
            "- **Off mode and leaving auto.** Fixed passes hold in auto only, and off keeps the earlier rules.",
            "When automatic review is turned off for a Plan before the user's decision at the end of the Plan, every "
            "fixed pass whose Claim's files or dependencies another Claim changed after it is reopened under the earlier "
            "rules, and the cross-session rules of off apply from then on.",
            "- **Limits.** A later Claim's reviewer reads only its own reading set and may not know an earlier Claim's "
            "design intent, and a property of an earlier Claim that no acceptance check the final check runs covers can "
            "be broken without the final check noticing.",
            "This amends [ADR 0006](0006-review-state-validity-and-completion.md) (what a pass covers): in auto, a "
            "change to a Claim's files or dependencies within the range another Claim's passing code review and outcome "
            "verification of the same Plan judged no longer reopens the Claim's code review and outcome verification.",
            "- **Keep file-level reopening in auto**: it chains reviews through shared files.",
            "- **Carry every earlier Claim's acceptance into later reviews**: it widens every review.",
        ),
    }
    ADR_0006_NOTE = ("(Amended by ADR 0015: in auto, a Claim's valid APPROVED and CONFIRMED are not reopened by a change "
                     "to its files or dependencies that lies within the range another Claim of the same Plan had judged "
                     "by a completed code review and outcome verification that both passed; every other change, and "
                     "every change in off, still reopens them as above.)")

    # Acceptance item 17, for these rules: (English label, Chinese label, English sentence, Chinese sentence).
    README_PAIRS = (
        ("Fixed passes", "固定的通過",
         "in auto, once a claim has a valid APPROVED and CONFIRMED, they stay fixed: when another claim of the same "
         "plan, a fix claim included, changes its files or what they depend on, they are not reopened as long as that "
         "change lies within what that other claim's own completed code review and verification judged, and both "
         "passed.",
         "在 auto 下，claim 一拿到有效的 APPROVED 與 CONFIRMED，它們就保持固定：同一份計畫的另一個 claim（包括修正用的 "
         "claim）改動它的檔案或其相依項目時，只要這項改動落在那個 claim 自己完成的程式碼審查與驗證所審過的範圍內，而且兩者"
         "都通過，就不會重新打開它們。"),
        ("Fixed passes", "固定的通過",
         "A problem the change causes is that other claim's to fix, in its own reviews.",
         "這項改動造成的問題，由那個 claim 在它自己的審查中修正。"),
        ("Fixed passes", "固定的通過",
         "A pass stays fixed only for a change a passing review judged: when that other claim's review stops, is "
         "cancelled, is deferred or ends in your accept-and-land decision without both passes, its changes reopen the "
         "claims whose files or dependencies they touch, as Validity says.",
         "只有通過的審查審過的改動，才會讓通過保持固定：那個 claim 的審查停下、被取消、被延後，或沒拿到兩項通過就以你決定"
         "接受並合併結束時，它的改動會依「有效範圍」重新打開它碰到的檔案或相依項目所屬的 claim。"),
        ("Fixed passes", "固定的通過",
         "Every other change still reopens as Validity says, such as your own edit outside the plan's claims, a rebase, "
         "an environment or test target change, a change to the claim's reading set, or a change whose claim ends "
         "without both passes; fixed passes do not change what reopens a HELD.",
         "其他改動仍依「有效範圍」重新打開，例如你在計畫的 claim 以外所做的修改、rebase、環境或測試目標的變更、claim 閱讀"
         "範圍的變更，或所屬 claim 沒拿到兩項通過就結束的改動；固定的通過也不改變什麼會重新打開 HELD。"),
        ("Fixed passes", "固定的通過",
         "A claim may change a file another claim's acceptance checks run or read, such as its tests, expected values, "
         "fixtures, test discovery or runner configuration and their support code, only where its own reading set says "
         "it does; otherwise that is a deviation and blocks.",
         "claim 只有在它自己的閱讀範圍寫明時，才能改動另一個 claim 的驗收檢查會執行或讀取的檔案，例如它的測試、預期值、"
         "fixture、測試探索或執行器設定，以及它們的輔助程式碼；否則就是偏離，會擋下。"),
        ("Fixed passes", "固定的通過",
         "Main decides which files these are from the changing claim's commit, files it adds included, and counts any "
         "file it cannot rule out; that claim's code review then also reads the acceptance of each claim whose checks it "
         "changed and checks that the change does not weaken it, for example by loosening an assertion, replacing a "
         "fixture or turning off discovery, and a weakening blocks.",
         "主 Agent 從做出改動的 claim 的 commit 判斷是哪些檔案，包括它新增的檔案，無法排除的檔案也算在內；該 claim 的程式碼"
         "審查接著也會讀每個驗收檢查被它改動的 claim 的驗收條件，並檢查這項改動沒有削弱它，例如放寬斷言、換掉 fixture 或關掉"
         "測試探索，削弱就會擋下。"),
        ("Fixed passes", "固定的通過",
         "Fixed passes hold in auto only: in `off`, any change to a claim's files or what they depend on still reopens "
         "its code review and verification as Validity says, and turning automatic review off for a plan before your "
         "decision at the end of the plan reopens every fixed pass whose claim's files or dependencies another claim "
         "changed after it, with `off`'s rules for resumed sessions from then on.",
         "固定的通過只在 auto 下成立：在 `off` 下，改動 claim 的檔案或其相依項目，仍依「有效範圍」重新打開它的程式碼審查與"
         "驗證；在你對計畫做出最後決定之前就關掉自動審查，會重新打開每一個在通過之後被另一個 claim 改動了檔案或相依項目的"
         "固定通過，之後恢復 session 的規則也改用 `off` 的。"),
        ("Fixed passes", "固定的通過",
         "Fixed passes have limits: a later claim's reviewer reads only its own reading set and may not know an earlier "
         "claim's design intent, and a property of an earlier claim that no acceptance check the final check runs covers "
         "can be broken without the final check noticing.",
         "固定的通過有其限制：後面 claim 的 reviewer 只讀它自己的閱讀範圍，可能不知道前面 claim 的設計用意；前面 claim 的某項"
         "性質，若沒有任何最終檢查執行的驗收檢查涵蓋，就可能被破壞而最終檢查沒有發現。"),
        ("Validity", "有效範圍",
         "Changing a claim's files or what they depend on reopens its code review and verification, except where its "
         "passes stay fixed in auto, as Fixed passes says;",
         "改動 claim 的檔案或其相依項目，會重新打開程式碼審查與驗證，但 auto 下依「固定的通過」保持固定的通過除外；只改環境"
         "則只重新打開驗證；其他改動，主 Agent 會說明為什麼通過仍然有效。"),
    )

    # Acceptance item 18: the replaced statements of file-level reopening in auto, which said any later change to a
    # claim's files reopens its passes.
    REPLACED = {
        "review-state.md": (
            "A later change to a claim's files or to what they depend on reopens code review and outcome verification "
            "for that claim;",
        ),
        "README.md": ("Changing a claim's files or what they depend on reopens its code review and verification;",),
        "README.zh-TW.md": ("改動 claim 的檔案或其相依項目，會重新打開程式碼審查與驗證；",),
    }

    # Acceptance item 5 and the Implementation Decisions "Unchanged": the reviewer template is unchanged, as at v0.25.0
    # (line endings normalised to LF, as .gitattributes stores them).
    UNCHANGED = {"templates/agents/reviewer.md": "5c1684aed6bb3371beaf083f51232ed58e14fa383507f30deaa0d0469ad2beff"}

    def new_pins(self):
        pins = {}
        for group in (self.FIXED, self.ACCEPTANCE_CHECKS, self.CONTEXT, self.ADR):
            for place, sentences in group.items():
                pins.setdefault(place, []).extend(sentences)
        pins["review-state.md#What a pass covers"].extend((self.S5, self.OFF, self.S7, self.LIMITS))
        pins.setdefault("ADR 0006", []).append(self.ADR_0006_NOTE)
        for en_label, zh_label, english, chinese in self.README_PAIRS:
            pins.setdefault(f"README.md#{en_label}", []).append(english)
            pins.setdefault(f"README.zh-TW.md#{zh_label}", []).append(chinese)
        return pins

    def test_passes_stay_fixed_in_auto_and_every_other_change_keeps_file_level_reopening(self):
        self.assert_pinned(self.FIXED)

    def test_s5_a_fixed_pass_needs_a_passing_review_of_the_change(self):
        self.assert_pinned({"review-state.md#What a pass covers": (self.S5,)})

    def test_off_mode_keeps_file_level_reopening(self):
        # Fails if off loses file-level reopening: the off sentence and the rule it keeps must both stand.
        self.assert_pinned({"review-state.md#What a pass covers": (self.OFF, self.FIXED[
            "review-state.md#What a pass covers"][0])})

    def test_s7_leaving_auto_during_a_plan_reopens_fixed_passes(self):
        self.assert_pinned({"review-state.md#What a pass covers": (self.S7,)})

    def test_the_limits_of_fixed_passes_are_stated(self):
        self.assert_pinned({"review-state.md#What a pass covers": (self.LIMITS,)})

    def test_another_claims_acceptance_checks_get_a_weakening_check(self):
        self.assert_pinned(self.ACCEPTANCE_CHECKS)
        # The brief's rule that it carries only the recorded reading set still stands beside the stated exception.
        self.assertIn("Before dispatch, main confirms that the reading set is unchanged and supplies only the reading "
                      "set it recorded, as [review state](review-state.md)'s Reading set describes.",
                      self.source("code-review.md"))
        self.assertIn("and the briefs use only the recorded reading set, except as [adversarial review]"
                      "(adversarial-review.md) step 2 adds for a claim that owns a composed review.",
                      self.source("review-state.md#Reading set"))

    def test_glossary_states_fixed_passes(self):
        self.assert_pinned(self.CONTEXT)

    def test_adr_0015_records_fixed_passes_and_amends_adr_0006(self):
        self.assert_pinned(self.ADR)
        text = self.source("ADR 0015")
        self.assertEqual(text.count(f"\n## {self.PART}\n"), 1)
        # This part follows ticket 01's part, after its Consequences.
        self.assertLess(text.index("\n## Consequences\n"), text.index(f"\n## {self.PART}\n"))
        lines = self.source("ADR 0006").splitlines()
        self.assertIn(self.ADR_0006_NOTE, lines)
        self.assertEqual(sum(line.startswith("(Amended by ADR 0015:") for line in lines), 1)

    def test_both_readmes_explain_fixed_passes(self):
        for en_label, zh_label, english, chinese in self.README_PAIRS:
            for place, sentence in ((f"README.md#{en_label}", english), (f"README.zh-TW.md#{zh_label}", chinese)):
                with self.subTest(place=place, sentence=sentence[:40]):
                    self.assert_whole_sentence(sentence, self.source(place))

    def test_the_fixed_passes_bullet_follows_ticket_01s_bullets(self):
        for path, label, previous in (("README.md", "Fixed passes", "Dependent claims"),
                                      ("README.zh-TW.md", "固定的通過", "相依的 claim")):
            labels = [line[4:].split("**", 1)[0].rstrip(":：") for line in self.source(path).splitlines()
                      if line.startswith("- **")]
            with self.subTest(path=path):
                self.assertEqual(labels[labels.index(previous) + 1], label)

    def test_file_level_reopening_in_auto_is_replaced(self):
        for place, phrases in self.REPLACED.items():
            text = self.source(place)
            for phrase in phrases:
                with self.subTest(place=place, phrase=phrase[:60]):
                    self.assertNotIn(phrase, text)

    def test_the_reviewer_template_is_unchanged(self):
        for path, digest in self.UNCHANGED.items():
            text = (config.ROOT / path).read_text(encoding="utf-8").replace("\r\n", "\n")
            with self.subTest(path=path):
                self.assertEqual(hashlib.sha256(text.encode("utf-8")).hexdigest(), digest)

    def tagged_place(self, place):
        """The whole file behind a place at the tag; this ticket's ADR part and ADR 0006 included."""
        name = place.partition("#")[0]
        return self.tagged(place, self.PATHS[name])

    def test_every_new_pin_fails_on_the_v0_25_0_text(self):
        for place, sentences in self.new_pins().items():
            text = self.tagged_place(place)
            for sentence in sentences:
                with self.subTest(place=place, sentence=sentence[:60]):
                    self.assertFalse(sentence in text, f"{place} already said this at {self.TAG}")

    def test_every_absence_pin_matches_the_v0_25_0_text(self):
        for place, phrases in self.REPLACED.items():
            text = self.tagged_place(place)
            for phrase in phrases:
                with self.subTest(place=place, phrase=phrase[:60]):
                    self.assertIn(phrase, text)

    def test_the_reviewer_template_matches_the_v0_25_0_text(self):
        for path, digest in self.UNCHANGED.items():
            text = self.tagged(path, path).replace("\r\n", "\n")
            with self.subTest(path=path):
                self.assertEqual(hashlib.sha256(text.encode("utf-8")).hexdigest(), digest)


class FinalCheckAndFixClaimsTests(unittest.TestCase):
    """Ticket 03: whole-sentence pins of the final check's reruns, attributed fixes, fix Claims, S4 and the stop, the
    Plan's base revision in every brief (S1), the reading-set confirmation (S3), findings about an earlier Claim, off
    keeping today's final check, a pin of the unchanged adversary template, and a check that every new pin fails on the
    text at tag v0.25.0. It reuses ticket 01's readers rather than changing them."""

    PATHS = {**PerClaimTimingTests.PATHS,
             "adversarial-review.md": "skills/delegation/references/adversarial-review.md"}
    TAG = PerClaimTimingTests.TAG
    GIT_READ = PerClaimTimingTests.GIT_READ
    PART = "The final check and fix Claims"

    @classmethod
    def source(cls, name: str) -> str:
        """As ticket 01's reader, plus '<procedure>#<step number>', 'adversarial-review.md' (the whole procedure) and
            'ADR 0015#part' (this ticket's part of ADR 0015)."""
        if name == "ADR 0015#part":
            text = (config.ROOT / cls.PATHS["ADR 0015"]).read_text(encoding="utf-8")
            return text.split(f"\n## {cls.PART}\n", 1)[1].split("\n## ", 1)[0]
        path, _, part = name.partition("#")
        if part.isdigit() or path == "adversarial-review.md":
            return feather_support.post_fix_source(name)
        return PerClaimTimingTests.source(name)

    assert_whole_sentence = feather_support.stop_threshold_assert_whole_sentence

    assert_pinned = feather_support.stop_threshold_assert_pinned

    tagged = PerClaimTimingTests.tagged

    FINAL = "review-state.md#Final check"

    # S3 and Acceptance item 7: the reading-set confirmation before the final check, and the reruns.
    S3 = ("In auto, before the final check main confirms that each claim's reading set is unchanged from its recorded "
          "content or hash, as Reading set describes; a change the user did not authorise is a material deviation, as "
          "[plan review](plan-review.md) step 5 describes.")
    RERUNS = ("In auto, the final check also reruns every claim's primary acceptance at the commit to be landed or "
              "tagged, taken from the claim's recorded reading set, within the same Execution rules.")

    # Acceptance item 7: the attributed fix, the fix Claim for an unattributed failure, the rerun and the stop.
    FIXES = (
        "In auto, a failure attributed with evidence to a claim is fixed by that claim: the fix goes through that claim's "
        "code review and outcome verification, with the failure's output as evidence, their counts continuing as for a "
        "reopened call, as Reopened calls describes, and no other claim is reopened.",
        "In auto, a failure that cannot be attributed with evidence is fixed as a fix claim, and no claim is reopened.",
        "The final check runs again after each fix.",
        "When the final check fails at as many different commits in a row as the Stop threshold in effect, without "
        "passing in between, main stops fixing and asks the user.",
    )

    # Acceptance item 7: what a fix Claim is, added without asking, classified by what it changes.
    FIX_CLAIM = (
        "A fix claim is a claim main adds to the plan for one fix: its acceptance is that the failing check passes, or, "
        "for a defect [code review](code-review.md) step 5 assigns to a fix claim, that the reported defect is fixed; its "
        "reading set is the plan's text with that failure or defect; and it gets code review and outcome verification "
        "with counts of its own.",
        "Main adds a fix claim without asking, as it makes a fix today: it gets no plan review and no ticket, and main "
        "keeps it in the session's state and in any active handoff; a fix beyond the plan's scope is a Deviation, as "
        "Deviations describes.",
        "A fix claim is classified as Security-critical by what it changes, and main still does not ask: a fix claim that "
        "changes a security control gets no Adversarial review, so it needs accept and land for its missing HELD, and "
        "main discloses it, with its problem and a summary of the fix, in the decision Accept and land at the end of the "
        "plan describes.",
    )

    # S4: a fix Claim never changes what it is judged by.
    S4 = ("A fix claim never changes the check whose failure it fixes or another claim's acceptance checks, the files "
          "[code review](code-review.md) step 2 describes; a fix that needs to is a Deviation and stops main to ask the "
          "user.")

    # Acceptance item 14 for the final check, and the residual risks "Check output" and "Security-critical fix Claims".
    LIMITS = (
        "The final check does not repeat everything at the final commit: acceptance items other than a claim's primary "
        "acceptance are not rerun there, and an acceptance check that cannot be rerun, such as a manual check, is not "
        "repeated there.",
        "Repository code that a check runs controls its own output, so it can make a check pass that should fail, hide "
        "that a check ran fewer tests, or make a failure point at the wrong claim; the last only misdirects a fix, after "
        "which the final check runs again.",
        "A fix claim that changes a security control gets no plan review, security analysis or Adversarial review; it is "
        "disclosed at the end, and the user decides whether to land with it.",
    )

    # Acceptance item 15: off keeps today's final check, a failure that cannot be attributed reopening every claim. These
    # replace completion criteria ticket 02's two failure sentences, whose pins (S8) now name off.
    OFF = (
        "In off, the final check keeps its earlier rules, without the reruns, fix claims and stop above: a failure "
        "reopens the claims it affects under the existing rules, and its output goes with it to the reopened claims' "
        "reviews as evidence; landing and release wait for their passes again.",
        "In off, a failure that cannot be attributed with evidence reopens every claim the check covers.",
    )

    # The Stop threshold section's "Not counted": still not a counted step, while the stop uses the value.
    NOT_COUNTED = ("In auto, the stop after the final check fails at as many different commits in a row as the Stop "
                   "threshold in effect, as Final check describes, uses the Stop threshold's value, while the final "
                   "check is still not a counted step: its runs change no step's count.")

    # S1 and Acceptance item 6: the Plan's base revision in every brief, main's judgement from Git, and a defect
    # introduced after it fixed rather than only recorded.
    S1 = {
        "review-state.md#Evidence for a regression": (
            "In auto, every such brief also names, beside the claim's base revision, the plan's base revision, the "
            "commit the plan's implementation started from, which main establishes itself from Git in this session.",
            "Main, not the role, judges from Git whether a finding a role reports as pre-existing was introduced after "
            "the plan's base revision; such a finding is a defect of the plan, handled as [code review](code-review.md) "
            "step 5 describes, or, for a broken security invariant, a BROKEN of the claim whose invariant it breaks.",
        ),
        "code-review.md#2": (
            "In auto, every such brief also names the plan's base revision beside the claim's base revision, as that "
            "bullet describes, and main, not the reviewer, judges from Git whether a finding the reviewer reports as "
            "pre-existing was introduced after it.",
        ),
        "outcome-verification.md#2": (
            "In auto, every such brief also names the plan's base revision beside the claim's base revision, as that "
            "bullet describes, and main, not the verifier, judges from Git whether a finding the verifier reports as "
            "pre-existing was introduced after it.",
        ),
        "adversarial-review.md#2": (
            "In auto, every such brief also names the plan's base revision beside the claim's base revision, as that "
            "bullet describes, and main, not the adversary, judges from Git whether a vulnerability the adversary "
            "reports as pre-existing was introduced after it; one introduced after it that breaks a security invariant "
            "is a BROKEN of the claim whose invariant it breaks, not separate pre-existing work.",
        ),
    }
    EARLIER_CLAIM = {
        "code-review.md#5": (
            "In auto, when a claim's review finds a problem in an earlier claim of the same plan, main judges from Git "
            "whether it predates the plan's base revision, as [review state](review-state.md)'s Evidence for a "
            "regression describes.",
            "A problem that predates the plan's base revision is a Non-blocking finding, recorded in the Follow-up "
            "record, and the later claim fixes it only when its own acceptance needs it, reviewed in its own reviews.",
            "A defect introduced after the plan's base revision is not a pre-existing issue and is not only recorded: "
            "when the later claim's acceptance needs it fixed, the later claim fixes it within its own reviews; "
            "otherwise main fixes it as a fix claim, as [review state](review-state.md)'s Final check describes, "
            "without reopening the earlier claim.",
            "A security problem or data loss that the later claim's change introduces into what an earlier claim "
            "delivers is the later claim's Blocking finding, as [review state](review-state.md)'s Security findings "
            "describes; when a later claim changes a security control, main classifies it again as Security-critical "
            "by what the change does, as [plan review](plan-review.md) describes.",
        ),
        "review-state.md#Non-blocking findings": (
            "In auto, a defect that an earlier claim of the same plan introduced after the plan's base revision is not a "
            "pre-existing issue and is not only recorded: it is fixed as [code review](code-review.md) step 5 describes, "
            "without reopening the earlier claim.",
        ),
        "adversarial-review.md": (
            "In auto, a fix claim gets no Adversarial review even when it is Security-critical, as [review "
            "state](review-state.md)'s Final check describes.",
        ),
    }

    # Acceptance item 16, for these rules: the glossary states fix Claims, the Plan's base revision and the stop.
    CONTEXT = {
        "CONTEXT.md#Claim": (
            "In the Automatic flow, main may add a fix Claim to a Plan for one fix that the final check or a later "
            "Claim's review needs, without asking; it is a Claim with its own acceptance, reading set and counts, as "
            "review state's Final check states.",
        ),
        "CONTEXT.md#Non-blocking finding": (
            "In the Automatic flow, a defect that an earlier Claim of the same Plan introduced after the Plan's base "
            "revision is not a pre-existing issue, and is fixed rather than only recorded.",
        ),
        "CONTEXT.md#Stop threshold": (
            "In the Automatic flow, the final check, which is not a counted step, also stops for the user when it fails "
            "at that many different commits in a row.",
        ),
    }

    # Acceptance item 16, for these rules: ADR 0015's part on the final check, fix Claims and the Plan's base revision,
    # amending ADR 0013 (the unattributed final check failure).
    ADR = {
        "ADR 0015#part": (
            "This part records the final check's reruns, fix Claims and the Plan's base revision.",
            "The user decided (2026-10-14 and 2026-10-15, the second day after a security analysis; the "
            "[spec](../specs/retained-passes.md) carries the acceptance and its security invariants):",
            "- **Reruns.** Before the final check, main confirms that each Claim's reading set is unchanged from its "
            "recorded content or hash; a change the user did not authorise is a material Deviation.",
            "In auto the final check runs at the final commit, as before, and also reruns every Claim's primary "
            "acceptance there, taken from its recorded reading set, within repository safety's Execution rules.",
            "- **Attributed failures.** A failure attributed with evidence to a Claim is fixed by that Claim: the fix "
            "goes through that Claim's code review and outcome verification, their counts continuing as for a reopened "
            "call, and no other Claim is reopened.",
            "- **Fix Claims.** A failure that cannot be attributed with evidence is fixed as a fix Claim, and no Claim is "
            "reopened.",
            "A fix Claim is a Claim main adds to the Plan for one fix: its acceptance is that the failing check passes, "
            "or, for a defect a later Claim's review found, that the reported defect is fixed; its reading set is the "
            "Plan's text with that failure or defect; and it gets code review and outcome verification with counts of "
            "its own.",
            "Main adds it without asking, as it makes a fix today: it gets no plan review and no ticket; a fix beyond the "
            "Plan's scope is a Deviation.",
            "A fix Claim never changes the check whose failure it fixes or another Claim's acceptance checks; a fix that "
            "needs to is a Deviation and stops main to ask the user.",
            "A fix Claim that changes a security control is classified as Security-critical by what it does, and main "
            "still does not ask: it gets no Adversarial review and is disclosed at the end with its problem and a "
            "summary of the fix.",
            "- **The stop.** The final check runs again after each fix.",
            "When it fails at as many different commits in a row as the Stop threshold in effect, without passing in "
            "between, main stops fixing and asks the user.",
            "The final check is still not a counted step; this stop only uses the Stop threshold's value.",
            "- **The Plan's base revision.** Every brief of a Claim's code review, outcome verification and Adversarial "
            "review names, besides the Claim's base revision, the Plan's base revision, which main establishes itself "
            "from Git in this session.",
            "Main, not the role, judges from Git whether a finding a role reports as pre-existing was introduced after "
            "it; such a finding is a defect of the Plan or, for a broken security invariant, a BROKEN of the Claim whose "
            "invariant it breaks.",
            "When a later Claim's review finds a problem in an earlier Claim of the same Plan, a problem that predates "
            "the Plan's base revision is a Non-blocking finding that the later Claim fixes only when its own acceptance "
            "needs it; a defect introduced after it is not a pre-existing issue: the later Claim fixes it when its "
            "acceptance needs it, and otherwise main fixes it as a fix Claim, without reopening the earlier Claim.",
            "A later Claim that changes a security control is classified again as Security-critical by what the change "
            "does.",
            "- **Off mode.** These rules hold in auto only: in off the final check keeps the earlier rules, a failure "
            "that cannot be attributed with evidence reopening every Claim the check covers.",
            "- **Limits.** Acceptance items other than the primary acceptance, and acceptance checks that cannot be "
            "rerun, such as a manual check, are not repeated at the final commit.",
            "- **Check output.** Repository code that a check runs controls its own output, so it can make a check pass "
            "that should fail, hide that a check ran fewer tests, or make a failure point at the wrong Claim; the last "
            "only misdirects a fix, after which the final check runs again.",
            "- **Security-critical fix Claims.** A fix Claim that changes a security control gets no plan review, "
            "security analysis or Adversarial review; it is disclosed at the end, and the user decides whether to land "
            "with it.",
            "This amends [ADR 0013](0013-only-what-a-claims-acceptance-needs-holds-its-completion.md) (the unattributed "
            "final check failure): in auto, a final check failure that cannot be attributed with evidence no longer "
            "reopens every Claim the check covers but is fixed as a fix Claim, and an attributed failure is fixed by its "
            "Claim without reopening any other.",
            "- **Reopen an earlier Claim for a defect it introduced**: it restores the chain fixed passes remove.",
            "- **Count a fix's own review calls to stop fixes that break each other**: each fix can pass its own "
            "reviews, so the count never reaches the Stop threshold.",
            "- **A new glossary term for a fix outside every Claim**: a fix Claim works as any Claim.",
            "- **Ask the user before a fix Claim that changes a security control**: it stops the Plan for a fix whose "
            "purpose is to make it work, so it is disclosed at the end instead.",
            "- **A forced fix round in which every Claim must pass a step before the next**: it adds a global ordering "
            "and ignores stops, INCONCLUSIVE, REJECT and deferral.",
        ),
    }
    # This ticket's note on ADR 0013's part on the final check, a line of its own beside ticket 01's note.
    ADR_0013_NOTE = ("(Further amended by ADR 0015: in auto, a final check failure that cannot be attributed with evidence "
                     "no longer reopens every Claim the check covers: it is fixed as a fix Claim, an attributed failure "
                     "is fixed by its Claim without reopening any other, and the final check also reruns every Claim's "
                     "primary acceptance.)")

    # Acceptance item 17, for these rules: (English label, Chinese label, English sentence, Chinese sentence).
    README_PAIRS = (
        ("Final check", "最終檢查",
         "In auto it still counts toward no step, but it stops at the Stop threshold's value, as below.",
         "在 auto 下它仍不計入任何步驟，但會依停止門檻的值停下，如下所述。"),
        ("Final check", "最終檢查",
         "In auto, before the check main confirms that each claim's reading set is unchanged from what it recorded, and "
         "the check also reruns every claim's primary acceptance at that commit, taken from the claim's recorded reading "
         "set.",
         "在 auto 下，檢查之前主 Agent 會確認每個 claim 的閱讀範圍與它記錄的相同，檢查也會在該 commit 上重跑每個 claim "
         "的主要驗收，依據的是該 claim 記錄下來的閱讀範圍。"),
        ("Final check", "最終檢查",
         "A failure main attributes with evidence to a claim is fixed by that claim, through its code review and "
         "verification, whose counts continue as for a reopened call, and no other claim is reopened.",
         "主 Agent 以證據歸因於某個 claim 的失敗，由那個 claim 修正，並經過它的程式碼審查與驗證，次數像重新打開的呼叫一樣接續"
         "計算，其他 claim 都不會重新打開。"),
        ("Final check", "最終檢查",
         "A failure main cannot attribute with evidence is fixed by a fix claim, and no claim is reopened.",
         "主 Agent 無法以證據歸因的失敗，由修正用的 claim 修正，任何 claim 都不會重新打開。"),
        ("Final check", "最終檢查",
         "A fix claim is a claim main adds to the plan for one fix, without asking you and with no plan review and no "
         "ticket: its acceptance is that the failing check passes, or that a defect a later claim's review found is "
         "fixed, its reading set is the plan's text with that failure or defect, and it gets code review and "
         "verification with counts of its own.",
         "修正用的 claim 是主 Agent 為一項修正加進計畫的 claim，不會先問你，也沒有計畫審查與 ticket：它的驗收條件是失敗的"
         "檢查通過，或後面 claim 的審查找到的缺陷已修正；它的閱讀範圍是計畫的文字加上那項失敗或缺陷；它有自己的程式碼審查"
         "與驗證，次數也自己計算。"),
        ("Final check", "最終檢查",
         "A fix claim never changes the check whose failure it fixes or another claim's acceptance checks; a fix that "
         "needs to, or a fix beyond the plan's scope, is a deviation, and main asks you.",
         "修正用的 claim 絕不改動它所修正的那項失敗檢查，也不改動其他 claim 的驗收檢查；需要改動它們的修正，或超出計畫範圍"
         "的修正，都是偏離，主 Agent 會問你。"),
        ("Final check", "最終檢查",
         "A fix claim that changes a security control is Security-critical, but main still adds it without asking: it "
         "gets no plan review, security analysis or Adversarial review, and main discloses it at the end with its problem "
         "and a summary of the fix, so you decide whether to land with it.",
         "修正用的 claim 若改動安全控制，就屬於安全關鍵，但主 Agent 仍不先問你就加入：它沒有計畫審查、安全分析或對抗式審查，"
         "主 Agent 會在最後揭露它，附上問題與修正摘要，由你決定是否帶著它合併。"),
        ("Final check", "最終檢查",
         "The check runs again after each fix, and when it fails at as many different commits in a row as the Stop "
         "threshold, without passing in between, main stops fixing and asks you.",
         "每次修正後檢查都會再執行一次；檢查在連續幾個不同的 commit 上失敗，次數達到停止門檻，而且其間沒有通過時，主 Agent "
         "就停止修正並問你。"),
        ("Final check", "最終檢查",
         "The check does not repeat everything at the final commit: acceptance items other than a claim's primary "
         "acceptance are not rerun, and an acceptance check that cannot be rerun, such as a manual check, is not "
         "repeated.",
         "檢查不會在最後的 commit 上重做所有事：claim 主要驗收以外的驗收項目不會重跑，無法重跑的驗收檢查（例如手動檢查）"
         "也不會重做。"),
        ("Final check", "最終檢查",
         "Repository code a check runs controls its own output, so it can make a check pass that should fail, hide that "
         "a check ran fewer tests, or make a failure point at the wrong claim; the last only misdirects a fix, after "
         "which the check runs again.",
         "檢查所執行的儲存庫程式碼掌控自己的輸出，所以它可以讓該失敗的檢查通過、隱藏檢查少跑了測試，或讓失敗指向錯誤的 "
         "claim；最後這種只會讓修正找錯對象，修正之後檢查會再執行一次。"),
        ("Final check", "最終檢查",
         "In `off`, a failure reopens the claims it affects, with its output as evidence for their reviews, and landing "
         "and release wait for their passes again; a failure main cannot attribute with evidence reopens every claim the "
         "check covers.",
         "在 `off` 下，檢查失敗會重新打開受影響的 claim，並把輸出當作它們審查的證據，進入預設 branch 與 release 都要等它們"
         "再次通過；主 Agent 無法以證據歸因的失敗，會重新打開這項檢查涵蓋的每個 claim。"),
        ("Findings", "問題分級",
         "In auto, every review brief also names the plan's base revision, and main, not the role, judges from Git "
         "whether a finding reported as pre-existing was introduced after it.",
         "在 auto 下，每份審查的 brief 也會寫明計畫的基準版本，由主 Agent 而不是角色依 Git 判斷被回報為先前就存在的問題，"
         "是否在那之後才引入。"),
        ("Findings", "問題分級",
         "A problem in an earlier claim of the same plan that predates the plan's base revision is non-blocking, and a "
         "later claim fixes it only when its own acceptance needs it; a defect an earlier claim introduced after it is "
         "fixed by the later claim when its acceptance needs it and otherwise by a fix claim, as Final check says, "
         "without reopening the earlier claim.",
         "同一份計畫中前面 claim 的問題若早於計畫的基準版本，就是非阻擋問題，後面的 claim 只在自己的驗收需要時才修正；前面 "
         "claim 在那之後引入的缺陷，後面 claim 的驗收需要時由它修正，否則依「最終檢查」由修正用的 claim 修正，都不會重新打開"
         "前面的 claim。"),
        ("Findings", "問題分級",
         "When a later claim changes a security control, main classifies it again as Security-critical by what the "
         "change does.",
         "後面的 claim 改動安全控制時，主 Agent 會依改動的作用重新判斷它是否屬於安全關鍵。"),
    )

    # Acceptance item 18: the replaced statement that a failure reopens claims in either mode; in auto no claim is
    # reopened by the final check.
    REPLACED = {
        FINAL: (
            " A failure reopens the claims it affects under the existing rules,",
            " A failure that cannot be attributed with evidence reopens every claim the check covers.",
        ),
        "README.md#Final check": (" A failure reopens the claims it affects,",),
        "README.zh-TW.md#最終檢查": ("。檢查失敗會重新打開受影響的 claim",),
    }

    # The Implementation Decisions "Unchanged": the adversary template is unchanged, as at v0.25.0 (line endings
    # normalised to LF, as .gitattributes stores them).
    UNCHANGED = {"templates/agents/adversary.md": "9652dc3cde73dad6853c83ae93aa4be7eafb1fea6685cbc969ca2dae1b3f1bf2"}

    def new_pins(self):
        pins = {self.FINAL: [self.S3, self.RERUNS, *self.FIXES, *self.FIX_CLAIM, self.S4, *self.LIMITS, *self.OFF],
                "review-state.md#Not counted": [self.NOT_COUNTED]}
        for group in (self.S1, self.EARLIER_CLAIM, self.CONTEXT, self.ADR):
            for place, sentences in group.items():
                pins.setdefault(place, []).extend(sentences)
        pins.setdefault("ADR 0013", []).append(self.ADR_0013_NOTE)
        for en_label, zh_label, english, chinese in self.README_PAIRS:
            pins.setdefault(f"README.md#{en_label}", []).append(english)
            pins.setdefault(f"README.zh-TW.md#{zh_label}", []).append(chinese)
        return pins

    def test_s3_reading_sets_are_confirmed_before_the_final_check_which_reruns_every_primary_acceptance(self):
        self.assert_pinned({self.FINAL: (self.S3, self.RERUNS)})
        # The confirmation and the reruns come before the final check's own rules, which still run first.
        text = self.source(self.FINAL)
        self.assertLess(text.index("It is main's own run, not a review step"), text.index(self.S3))
        self.assertLess(text.index(self.RERUNS), text.index("It runs only when the workspace equals"))

    def test_a_failure_is_fixed_by_its_claim_or_a_fix_claim_and_the_final_check_stops_at_the_threshold(self):
        self.assert_pinned({self.FINAL: self.FIXES})

    def test_a_fix_claim_is_a_claim_main_adds_without_asking(self):
        self.assert_pinned({self.FINAL: self.FIX_CLAIM})

    def test_s4_a_fix_claim_does_not_change_what_it_is_judged_by(self):
        self.assert_pinned({self.FINAL: (self.S4,)})

    def test_the_final_checks_limits_and_residual_risks_are_stated(self):
        self.assert_pinned({self.FINAL: self.LIMITS})

    def test_off_keeps_todays_final_check(self):
        # Fails if off loses today's final check: its run, its fail-closed state and an unattributed failure reopening
        # every claim must all stand beside the off sentences.
        self.assert_pinned({self.FINAL: (
            *self.OFF,
            "Before landing or release, main runs the plan's overall acceptance checks, such as the full test suite, at "
            "the commit to be landed or tagged, within [repository safety](repository-safety.md)'s Execution rules.",
            "Once it has failed at a commit, that commit's state is failed, and a later pass at the same commit lets "
            "landing proceed only through an accept-and-land decision that names the failure.",
        )})

    def test_the_final_check_is_still_not_a_counted_step(self):
        self.assert_pinned({"review-state.md#Not counted": (
            "The final check before landing or release, as Validity and completion's Final check describes, is not a "
            "counted step either.", self.NOT_COUNTED)})

    def test_s1_every_brief_names_the_plans_base_revision_and_main_judges_pre_existing_findings(self):
        self.assert_pinned(self.S1)
        # The claim's base revision is still named beside it in every procedure.
        for place in ("code-review.md#2", "outcome-verification.md#2", "adversarial-review.md#2"):
            with self.subTest(place=place):
                self.assertIn("names the claim's base revision, which main establishes itself from Git in this session",
                              self.source(place))

    def test_findings_about_an_earlier_claim_follow_the_plans_base_revision(self):
        self.assert_pinned(self.EARLIER_CLAIM)
        # The completion conditions themselves are unchanged.
        self.assertIn("A claim's reviews judge it against these conditions: its acceptance as written is met; existing "
                      "behaviour is not broken, shown by a failing test or a reproduction; it introduces no security "
                      "problem and no data loss, as Security findings below describes; and it has no deviation from the "
                      "plan.", self.source("review-state.md#Completion conditions"))

    def test_glossary_states_fix_claims_and_the_plans_base_revision(self):
        self.assert_pinned(self.CONTEXT)

    def test_adr_0015_records_the_final_check_and_fix_claims_and_amends_adr_0013(self):
        self.assert_pinned(self.ADR)
        text = self.source("ADR 0015")
        self.assertEqual(text.count(f"\n## {self.PART}\n"), 1)
        # This part follows ticket 02's part.
        self.assertLess(text.index(f"\n## {FixedPassesTests.PART}\n"), text.index(f"\n## {self.PART}\n"))
        text = self.source("ADR 0013")
        lines = text.splitlines()
        self.assertIn(self.ADR_0013_NOTE, lines)
        self.assertEqual(sum(line.startswith("(Further amended by ADR 0015:") for line in lines), 1)
        # The note sits in ADR 0013's part on the serial rule and the final check, after its considered options.
        part = text.split("\n## Serial reviews and the final check\n", 1)[1].split("\n## ", 1)[0]
        self.assertLess(part.index("Considered options for this part:"), part.index(self.ADR_0013_NOTE))
        self.assertLess(part.index(self.ADR_0013_NOTE), part.index("Consequences of this part:"))

    def test_both_readmes_explain_the_final_checks_reruns_fix_claims_and_stop(self):
        for en_label, zh_label, english, chinese in self.README_PAIRS:
            for place, sentence in ((f"README.md#{en_label}", english), (f"README.zh-TW.md#{zh_label}", chinese)):
                with self.subTest(place=place, sentence=sentence[:40]):
                    self.assert_whole_sentence(sentence, self.source(place))

    def test_the_unqualified_reopening_sentences_are_gone_and_only_off_reopens(self):
        for place, phrases in self.REPLACED.items():
            text = self.source(place)
            for phrase in phrases:
                with self.subTest(place=place, phrase=phrase[:60]):
                    self.assertNotIn(phrase, text)

    def test_the_adversary_template_is_unchanged(self):
        for path, digest in self.UNCHANGED.items():
            text = (config.ROOT / path).read_text(encoding="utf-8").replace("\r\n", "\n")
            with self.subTest(path=path):
                self.assertEqual(hashlib.sha256(text.encode("utf-8")).hexdigest(), digest)

    def tagged_place(self, place):
        """The whole file behind a place at the tag; this ticket's ADR part included."""
        return self.tagged(place, self.PATHS[place.partition("#")[0]])

    def test_every_new_pin_fails_on_the_v0_25_0_text(self):
        for place, sentences in self.new_pins().items():
            text = self.tagged_place(place)
            for sentence in sentences:
                with self.subTest(place=place, sentence=sentence[:60]):
                    self.assertFalse(sentence in text, f"{place} already said this at {self.TAG}")

    def test_every_absence_pin_matches_the_v0_25_0_text(self):
        for place, phrases in self.REPLACED.items():
            text = self.tagged_place(place)
            for phrase in phrases:
                with self.subTest(place=place, phrase=phrase[:60]):
                    self.assertIn(phrase, text)

    def test_the_adversary_template_matches_the_v0_25_0_text(self):
        for path, digest in self.UNCHANGED.items():
            text = self.tagged(path, path).replace("\r\n", "\n")
            with self.subTest(path=path):
                self.assertEqual(hashlib.sha256(text.encode("utf-8")).hexdigest(), digest)


class AdversarialReviewAtTheFinalCommitTests(unittest.TestCase):
    """Ticket 04: whole-sentence pins of Adversarial review at the final commit, S2, the recorded BROKEN, item 14's
    limits for it, off keeping today's rules, the glossary, ADR 0015's part and the notes on ADR 0009 and ADR 0013, both
    READMEs, absence pins of the replaced same-commit and fix-before-landing statements, and a check that every new pin
    fails on the text at tag v0.25.0. The adversary template stays pinned by ticket 03's
    test_the_adversary_template_is_unchanged, which this ticket reuses rather than duplicates."""

    PATHS = {**PerClaimTimingTests.PATHS,
             "adversarial-review.md": "skills/delegation/references/adversarial-review.md",
             "command": "skills/adversarial-review/SKILL.md",
             "ADR 0009": "docs/adr/0009-security-critical-claims-get-an-adversarial-review.md"}
    TAG = PerClaimTimingTests.TAG
    GIT_READ = PerClaimTimingTests.GIT_READ
    PART = "Adversarial review at the final commit"
    FINAL_LABEL = "**At the final commit.**"

    @classmethod
    def source(cls, name: str) -> str:
        """As ticket 01's reader, plus 'adversarial-review.md' (whole), 'adversarial-review.md#<step number>',
            'adversarial-review.md#final' (its At the final commit paragraph), 'outcome-verification.md#<step number>',
            'command' (the adversarial-review command),
            'command#<bullet label>', 'command#classifying', 'command#results', '<README>#disclosure' (the third-step
            paragraph), 'ADR 0015#part' (this ticket's part), 'ADR 0009' and 'ADR 0013'."""
        path, _, part = name.partition("#")
        if name == "ADR 0015#part":
            text = (config.ROOT / cls.PATHS["ADR 0015"]).read_text(encoding="utf-8")
            return text.split(f"\n## {cls.PART}\n", 1)[1].split("\n## ", 1)[0]
        if path in ("ADR 0009", "ADR 0013"):
            return (config.ROOT / cls.PATHS[path]).read_text(encoding="utf-8")
        if path == "adversarial-review.md":
            if part == "final":
                text = (config.ROOT / cls.PATHS[path]).read_text(encoding="utf-8")
                return next(line for line in text.splitlines() if line.startswith(cls.FINAL_LABEL))
            return feather_support.post_fix_source(name)
        if path == "outcome-verification.md" and part.isdigit():
            return feather_support.post_fix_source(name)
        if path == "command":
            text = (config.ROOT / cls.PATHS[path]).read_text(encoding="utf-8")
            if not part:
                return text
            if part == "classifying":
                return next(line for line in text.splitlines() if line.startswith("The command separates two questions."))
            if part == "results":
                return text.split("\n## Results\n", 1)[1]
            return next(line for line in text.splitlines() if line.startswith(f"- **{part}.**"))
        if part == "disclosure":
            return feather_support.adversarial_retries_source(name)
        return PerClaimTimingTests.source(name)

    assert_whole_sentence = feather_support.stop_threshold_assert_whole_sentence

    assert_pinned = feather_support.stop_threshold_assert_pinned

    tagged = PerClaimTimingTests.tagged

    FINAL = "adversarial-review.md#final"

    # Acceptance item 8: the timing at the final commit, fix Claims excluded, the records of APPROVED and CONFIRMED, the
    # brief, the composed review, the break whichever Claim caused it, and INCONCLUSIVE.
    TIMING = {
        "adversarial-review.md": (
            "In auto, each Security-critical claim of plan-driven work, other than a fix claim, gets one Adversarial "
            "review at the final commit, once the final check has passed there and the workspace equals it, and before "
            "main reports it complete, as At the final commit below describes.",
        ),
        FINAL: (
            "In auto, once the final check has passed at the final commit and the workspace equals it, as [review "
            "state](review-state.md)'s Final check describes, each Security-critical claim of the plan, other than a fix "
            "claim, gets one Adversarial review there, replacing the requirement of a valid APPROVED and a valid "
            "CONFIRMED at the same commit: the claim's APPROVED and CONFIRMED are a record of the commits they judged, and "
            "a HELD judges only the final commit.",
            "The brief carries only the claim's own security invariants and test targets, as step 2 describes, never "
            "another claim's of the plan, and names the plan's base revision; the composed review of an already accepted "
            "claim is unchanged, as step 9 describes.",
            "A break of the claim's security invariant at the final commit is the claim's BROKEN whichever claim's change "
            "caused it, and a break introduced after the plan's base revision is not a pre-existing issue.",
            "INCONCLUSIVE follows steps 4 and 5 within the Stop threshold in effect.",
        ),
        "adversarial-review.md#1": (
            "In auto, dispatch a call that can give the claim's result only after the final check has passed at the "
            "commit to be landed, with the workspace equal to that commit, as At the final commit describes; an explicit "
            "call the user requests before then still runs, against the commit the user names, or HEAD when the user names "
            "none, with the workspace equal to that commit, but it counts as not run.",
        ),
        "outcome-verification.md": (
            "In off, for a Security-critical claim, [Adversarial review](adversarial-review.md) follows a valid CONFIRMED "
            "at the same commit before main reports it complete; in auto, it runs once the final check has passed at the "
            "final commit, as its At the final commit describes.",
        ),
        "outcome-verification.md#6": (
            "With CONFIRMED, continue to completion under the existing authority; for a Security-critical claim in the "
            "automatic flow, [Adversarial review](adversarial-review.md) follows at the final commit once the final check "
            "has passed there, as its At the final commit describes.",
        ),
        # The carried note: the delegation skill and plan review state the fix-Claim exception for auto.
        "SKILL.md#Plan review": (
            "In auto, that Adversarial review runs once, at the final commit after the final check has passed there, for "
            "each Security-critical claim except a fix claim, which gets none, as [the adversarial-review "
            "procedure](references/adversarial-review.md) describes.",
        ),
        "plan-review.md": (
            "In auto, a Security-critical claim's Adversarial review runs once, at the final commit after the final check "
            "has passed there, and a fix claim gets none, as [Adversarial review](adversarial-review.md) describes.",
        ),
    }

    # S2: only a call made after the final check passed at the commit to be landed gives the result; an earlier or other
    # commit's result and an earlier explicit call count as not run; a BROKEN's findings stay listed until a HELD at the
    # commit to be landed replaces them; the command states the same.
    S2 = {
        FINAL: (
            "Only a call made after the final check passed at the commit to be landed, with the workspace equal to it, "
            "gives the claim's result; a result from an earlier or another commit, and an explicit call made before then, "
            "count as not run, so the claim needs accept and land or a new call.",
            "A BROKEN's findings stay listed until a HELD at the commit to be landed replaces them.",
        ),
        "review-state.md#What a gated pass judged": (
            "In auto, an Adversarial review gives the claim's result only when it is made after the final check passed at "
            "the commit to be landed, with the workspace equal to it, and judges that commit; the claim's APPROVED and "
            "CONFIRMED are a record of the commits they judged, and a result from an earlier or another commit, or an "
            "explicit call made before then, counts as not run, as [adversarial review](adversarial-review.md)'s At the "
            "final commit describes.",
        ),
        "review-state.md#What a pass covers": (
            "In auto, a Security-critical claim's HELD judges only the commit it attacked, the commit to be landed: when "
            "the commit to be landed is another commit, the claim's Adversarial review result counts as not run, so the "
            "claim needs accept and land or a new call, and a BROKEN's findings stay listed, carried in every later "
            "call's brief and treated as open, until a HELD at the commit to be landed that covered them replaces them, as "
            "[adversarial review](adversarial-review.md)'s At the final commit describes.",
        ),
        "review-state.md#Clearing a stop": (
            "In auto, an explicit HELD obtained before the final check passed at the commit to be landed, with the "
            "workspace equal to it, does not clear a stop either, since it counts as not run, as [adversarial "
            "review](adversarial-review.md)'s At the final commit describes.",
        ),
        "review-state.md#What an explicit call runs": (
            "In auto, an explicit Adversarial review made before the final check passed at the commit to be landed, with "
            "the workspace equal to it, counts as not run even after the claim's valid APPROVED and CONFIRMED, as "
            "[adversarial review](adversarial-review.md)'s At the final commit describes.",
        ),
        "command#classifying": (
            "In auto, such a call needs, in place of a valid APPROVED and a valid CONFIRMED at the same commit, the final "
            "check to have passed at the commit to be landed, with the workspace equal to it, as the procedure's At the "
            "final commit describes.",
        ),
        "command#Gated and Security-critical": (
            "Both must meet the procedure's prerequisites, in off a valid APPROVED and a valid CONFIRMED at the same "
            "commit with a clean workspace and in auto the final check passed at the commit to be landed with the "
            "workspace equal to it, and their HELD counts like any pass of that step, so an explicit HELD clears a stop "
            "and, in off, resolves the handoff's missing Adversarial review.",
            "In auto, the claim's commit is the commit to be landed, and the brief also names the plan's base revision.",
        ),
        "command#Before the passes": (
            "A call in auto for a Security-critical claim the gate covers made before the final check passed at the "
            "commit to be landed, with the workspace equal to it, runs as an explicit call against the commit the user "
            "names, or HEAD when the user names none, with the workspace equal to that commit, and counts as not run, as "
            "review state's What an explicit call runs and the procedure's At the final commit describe; only a call made "
            "after then gives the claim's result.",
        ),
        "command#results": (
            "In auto, a result from an earlier or another commit than the commit to be landed counts as not run, a BROKEN "
            "that gives the claim's result is recorded in the work's Follow-up record rather than fixed in the plan, and "
            "its findings stay listed, carried in every later call's brief and treated as open, until a HELD at the "
            "commit to be landed that covered them replaces them, as the procedure's At the final commit describes.",
        ),
    }

    # Acceptance item 9: a BROKEN is recorded, not fixed, counted, not repeated on unchanged code, written under step 10,
    # and the Claim stays a Pending-acceptance claim listed in the decision at the end of the plan.
    RECORDED = {
        FINAL: (
            "A BROKEN is not fixed in the plan, and step 7 does not apply to it: it counts as a call without a pass, main "
            "does not repeat a call on unchanged code to reach the Stop threshold, and its findings go to the work's "
            "Follow-up record, written as step 10 requires, so a tracked record carries only their summary unless the "
            "user agrees.",
            "The claim stays a Pending-acceptance claim with its Adversarial review result, and main lists that result, a "
            "BROKEN with its findings as the adversary stated them, in the decision [review state](review-state.md)'s "
            "Accept and land at the end of the plan describes.",
        ),
        "adversarial-review.md#4": (
            "In auto, a BROKEN at the final commit counts as a call without a pass, and main does not repeat a call on "
            "unchanged code to reach the Stop threshold, as At the final commit describes.",
        ),
    }

    # S2 and code review call 1's B1: while a claim has listed BROKEN findings, every later call for it carries them at
    # step 7's disclosure level, step 10 applying, and step 6 treats each as open, so only a HELD that covered it replaces
    # it.
    LISTED_FINDINGS = {
        FINAL: (
            "While a claim has listed BROKEN findings, every later Adversarial review call for it, automatic or explicit "
            "and at any commit, carries those findings in its brief, at the disclosure level step 7 sets for findings it "
            "passes on, with step 10 applying as usual, and step 6 treats each listed finding as open: a HELD replaces a "
            "listed finding only when the call covered it, and a HELD that leaves one uncovered is treated as "
            "INCONCLUSIVE with it open, as step 6 does for an uncovered earlier gap.",
        ),
        "adversarial-review.md#2": (
            "In auto, while the claim has listed BROKEN findings, as At the final commit describes, the brief of every "
            "later call for it, automatic or explicit and at any commit, also carries those findings, at the disclosure "
            "level step 7 sets for findings it passes on, and step 10 applies as usual.",
        ),
        "adversarial-review.md#6": (
            "In auto, main also treats each listed BROKEN finding of the claim as open, as At the final commit describes: "
            "a HELD replaces a listed finding only when the call covered it, and a HELD that leaves one uncovered is not "
            "accepted, and main treats the call as INCONCLUSIVE with that finding open.",
        ),
    }

    # Code review call 1's N3: a call that counts as not run establishes no coverage and is never the previously judged
    # call a narrowed follow-up starts from.
    NOT_RUN_COVERAGE = {
        FINAL: ("A call that counts as not run establishes no coverage, so it is never the previously judged call that a "
                "narrowed follow-up starts from.",),
        "adversarial-review.md#5": (
            "In auto, a call that counts as not run under At the final commit establishes no coverage, so it is never the "
            "previously judged call that a narrowed follow-up starts from.",
        ),
        "command#Gated and Security-critical": (
            "A call that counts as not run under the procedure's At the final commit establishes no coverage, so it is "
            "never the previously judged call a narrowed follow-up starts from.",
        ),
    }

    # Acceptance item 14, for these rules.
    LIMITS = ("This flow does not check everything: the commit an Adversarial review attacks was not judged as a whole by "
              "the claim's own code review and outcome verification, and its findings are not fixed in the plan.")

    # Acceptance item 15: off keeps the same-commit premise, a BROKEN fixed before completion and the command's off rule.
    OFF = {
        FINAL: (
            "These rules hold in auto only: in off, the same-commit premise of step 1, a BROKEN fixed under step 7 before "
            "completion and [the adversarial-review command](../../adversarial-review/SKILL.md)'s rule for off are kept.",
        ),
        "adversarial-review.md": (
            "In off, an Adversarial review that counts as the step's pass for a Security-critical claim follows a valid "
            "APPROVED from [code review](code-review.md) and a valid CONFIRMED from [outcome "
            "verification](outcome-verification.md), at the same unchanged commit.",
        ),
        "adversarial-review.md#1": (
            "In off, dispatch a call that can count as the step's pass only for a claim with a valid APPROVED and a valid "
            "CONFIRMED at the same commit, with the workspace equal to that commit as [review state](review-state.md)'s "
            "What a gated pass judged describes.",
            "In off, an explicit call the user requests for a claim that does not yet have a valid APPROVED and a valid "
            "CONFIRMED at the same commit still runs, against the commit the user names, or HEAD when the user names none, "
            "with the workspace equal to that commit, but it does not count as the step's pass.",
        ),
        "adversarial-review.md#7": (
            "On BROKEN, other than a BROKEN at the final commit in auto, which is not fixed in the plan as At the final "
            "commit describes, disposition each finding as FIX, correcting it within the authorized scope, or REJECT with "
            "concrete evidence: a failed reproduction within the brief's limits, a source citation or the claim's own "
            "scope, never preference.",
            "A fix goes through [code review](code-review.md), then [outcome verification](outcome-verification.md), then "
            "Adversarial review again; if code review or outcome verification stops, the claim is unreviewed or unverified "
            "under that procedure.",
        ),
        "review-state.md#What a gated pass judged": (
            "In off, an Adversarial review that can count as the step's pass also needs a valid APPROVED and a valid "
            "CONFIRMED at that same commit, so it follows them, as [adversarial review](adversarial-review.md) describes; "
            "an explicit one the user requests before them runs but does not count.",
        ),
        "command#Before the passes": (
            "A call in off for a Security-critical claim the gate covers that does not yet have a valid APPROVED and a "
            "valid CONFIRMED at the same commit runs as an explicit call against the commit the user names, or HEAD when "
            "the user names none, with the workspace equal to that commit, and does not count as the step's pass, as "
            "review state's What an explicit call runs says of explicit calls made before the flow reached a step.",
        ),
    }

    # Acceptance item 18 for review state's Completion criteria: the statements that BROKEN is unchanged now defer to the
    # procedure, while the completion conditions themselves stay as they are.
    DEFERRAL = {
        "review-state.md#Completion conditions": (
            "Plan review checks a plan before these reviews, and Adversarial review and its BROKEN follow the [adversarial "
            "review](adversarial-review.md) procedure.",
        ),
        "review-state.md#Security findings": (
            "The adversary's BROKEN is handled as the [adversarial review](adversarial-review.md) procedure describes, and "
            "a pre-existing vulnerability still becomes separate work in the project's tracker, as its step 10 describes.",
        ),
    }

    # Acceptance item 16, for these rules: the glossary's Adversarial review and Pending-acceptance claim entries, the
    # latter also covering ticket 01's upstream Claim that has passed no step yet.
    CONTEXT = {
        "CONTEXT.md#Adversarial review": (
            "In the Automatic flow it is made once, at the final commit, after the final check has passed there with the "
            "workspace equal to it, for each Security-critical claim of the Plan other than a fix Claim; the Claim's "
            "APPROVED and CONFIRMED are a record of the commits they judged, only a call made then gives the Claim's "
            "result, and a result from an earlier or another commit, or an explicit call made before then, counts as not "
            "run.",
            "In the Automatic flow, a break of the Claim's security invariant at the final commit is its BROKEN whichever "
            "Claim's change caused it, and a BROKEN there is not fixed in the Plan: its findings are recorded in the work's "
            "Follow-up record and stay listed, carried into every later attack on the Claim and treated as open there, "
            "until a HELD at the commit to be landed that covered them replaces them; in off, a BROKEN is fixed before "
            "completion.",
        ),
        "CONTEXT.md#Pending-acceptance claim": (
            "It also covers an upstream Claim that has passed no step yet and stays pending because the user let named "
            "dependent Claims proceed after it stopped, as a deferral of it, and, in the Automatic flow, a "
            "Security-critical claim whose Adversarial review at the final commit returned BROKEN, which stays pending "
            "with that result and its findings listed until the user's decision at the end of the Plan.",
        ),
    }

    # Acceptance item 16, for these rules: ADR 0015's part, amending ADR 0009 (BROKEN holds the Claim) and ADR 0013
    # (Adversarial review timing).
    ADR = {
        "ADR 0015#part": (
            "This part records Adversarial review at the final commit and its recorded findings.",
            "The user decided (2026-10-14 and 2026-10-15, the second day after a security analysis; the "
            "[spec](../specs/retained-passes.md) carries the acceptance and its security invariants):",
            "- **Timing.** In auto, once the final check has passed at the final commit and the workspace equals it, each "
            "Security-critical claim of the Plan, other than a fix Claim, gets one Adversarial review there, replacing the "
            "requirement of a valid APPROVED and CONFIRMED at the same commit: the Claim's APPROVED and CONFIRMED are a "
            "record of the commits they judged, and a HELD judges only the final commit.",
            "- **The premise.** Only an Adversarial review call made after the final check passed at the commit to be "
            "landed, with the workspace equal to it, gives that Claim's result; a result from an earlier or another "
            "commit, and an explicit call made before then, counts as not run, so the Claim needs Accept and land or a new "
            "call.",
            "The adversarial-review command's rule for when a call counts as the step's pass states the same.",
            "- **The brief.** The brief carries only the Claim's own security invariants and test targets and the Plan's "
            "base revision, and the composed review of an already accepted Claim is unchanged.",
            "A break of a Claim's invariant at the final commit is reported whichever Claim's change caused it, and a "
            "break introduced after the Plan's base revision is not a pre-existing issue.",
            "- **Recorded findings.** A BROKEN is not fixed in the Plan: it counts as a call without a pass, main does not "
            "repeat a call on unchanged code to reach the Stop threshold, and its findings go to the work's Follow-up "
            "record, written as Adversarial review step 10 requires, so a tracked record carries only their summary unless "
            "the user agrees.",
            "The Claim stays a Pending-acceptance claim with its Adversarial review result, which the user's decision at "
            "the end of the Plan lists, and a BROKEN's findings stay listed, carried into every later Adversarial review "
            "of the Claim and treated as open there, until a HELD at the commit to be landed that covered them replaces "
            "them.",
            "- **Off mode.** These rules hold in auto only: in off, Adversarial review keeps its premise of a valid "
            "APPROVED and CONFIRMED at the same commit, a BROKEN is fixed before completion, and the adversarial-review "
            "command keeps its rule for off.",
            "- **Limits.** The commit an Adversarial review attacks was not judged as a whole by the Claim's own code "
            "review and outcome verification, and its findings are not fixed in the Plan.",
            "This amends [ADR 0009](0009-security-critical-claims-get-an-adversarial-review.md) (BROKEN holds the Claim): "
            "in auto, a BROKEN at the final commit no longer starts a fix within the Plan but is recorded in the Follow-up "
            "record, and the Claim stays pending acceptance with it until the user decides at the end of the Plan.",
            "It also amends [ADR 0013](0013-only-what-a-claims-acceptance-needs-holds-its-completion.md) (Adversarial "
            "review timing): in auto, Adversarial review no longer keeps its timing after a Claim's APPROVED and CONFIRMED "
            "at the same commit, but runs once at the final commit.",
            "- **Adversarial review after each Claim**: it attacks a commit that will not land, and its HELD would need its "
            "own reopening rules.",
            "- **Fix BROKEN within the Plan**: it restarts the loop at its costliest step.",
        ),
    }
    ADR_0009_NOTE = (
        "(Amended by ADR 0015: in auto, Adversarial review runs once, at the final commit after the final check has passed "
        "there, for each Security-critical claim other than a fix Claim, rather than after a valid APPROVED and CONFIRMED "
        "at the same unchanged commit; a BROKEN there is not fixed within the Plan but recorded in the work's Follow-up "
        "record, and the Claim stays pending acceptance with it until the user's decision at the end of the Plan, so a "
        "known flaw still ships only through the user's explicit Accept and land. In off, the third step and a BROKEN's "
        "fix are unchanged.)")
    # A line of its own, so that tickets 01's and 03's notes on ADR 0013 stay as they are.
    ADR_0013_NOTE = (
        "(Also amended by ADR 0015: in auto, Adversarial review no longer keeps its timing above: it runs once, at the "
        "final commit after the final check has passed there, for each Security-critical claim other than a fix Claim, "
        "and a BROKEN there is recorded in the work's Follow-up record rather than fixed within the Plan; BROKEN keeps its "
        "meaning, and off keeps the timing above.)")
    # ADR 0013's statement that Adversarial review keeps its timing stays as history.
    ADR_0013_HISTORY = "BROKEN keeps its meaning, Adversarial review keeps its timing,"

    # Acceptance item 17, for these rules: (README place, Chinese place, English sentence, Chinese sentence).
    README_PAIRS = (
        ("README.md#disclosure", "README.zh-TW.md#disclosure",
         "Adversarial review is the third step: adversary tries to break the claim and answers HELD, BROKEN or "
         "INCONCLUSIVE; in `off`, a call counts only after a valid APPROVED and CONFIRMED at the same commit, and in auto "
         "it runs at the end, as below.",
         "對抗式審查是第三步：adversary 嘗試攻破這個 claim，回覆 HELD、BROKEN 或 INCONCLUSIVE；在 `off` 下，要在同一個 commit "
         "拿到有效的 APPROVED 與 CONFIRMED 之後才算數，在 auto 下則在最後執行，如下所述。"),
        ("README.md#disclosure", "README.zh-TW.md#disclosure",
         "In auto, Adversarial review runs once, at the end: when the final check has passed at the final commit with the "
         "workspace equal to it, each Security-critical claim of the plan except a fix claim gets one Adversarial review "
         "there, whose brief carries only that claim's own security invariants and test targets and the plan's base "
         "revision.",
         "在 auto 下，對抗式審查只在最後執行一次：最終檢查在最後的 commit 上通過、且工作區與它相同時，計畫中除了修正用的 "
         "claim 以外，每個安全關鍵 claim 都在那裡做一次對抗式審查，brief 只帶該 claim 自己的安全不變條件與測試目標，以及計畫"
         "的基準版本。"),
        ("README.md#disclosure", "README.zh-TW.md#disclosure",
         "The claim's APPROVED and CONFIRMED are then a record of the commits they judged, and only a call made after the "
         "final check passed at the commit to be landed gives the claim's result: a result from an earlier or another "
         "commit, or an explicit call made before then, counts as not run, so the claim needs a new call or your "
         "accept-and-land decision.",
         "這時 claim 的 APPROVED 與 CONFIRMED 是它們所審 commit 的紀錄，只有在最終檢查於要進入預設 branch 的 commit 上通過之後"
         "才做的呼叫，才給出該 claim 的結果：來自較早或其他 commit 的結果，或在那之前明確要求的呼叫，都視為沒有執行，所以這個 "
         "claim 需要重新呼叫，或你決定接受並合併。"),
        ("README.md#disclosure", "README.zh-TW.md#disclosure",
         "A break of the claim's security invariant at that commit is reported whichever claim's change caused it, and one "
         "introduced after the plan's base revision is not pre-existing; an INCONCLUSIVE is handled as in any Adversarial "
         "review, within the Stop threshold.",
         "在那個 commit 上破壞 claim 的安全不變條件，不論是哪個 claim 的改動造成的都會回報，在計畫的基準版本之後才引入的也不算"
         "先前就存在；INCONCLUSIVE 和任何對抗式審查一樣處理，在停止門檻之內。"),
        ("README.md#disclosure", "README.zh-TW.md#disclosure",
         "A BROKEN there is recorded, not fixed in the plan: it counts as a call without a pass, main does not repeat the "
         "call on unchanged code, and its findings go to the work's Follow-up record, with only a summary in any tracked "
         "record unless you agree.",
         "在那裡得到的 BROKEN 只記錄、不在這份計畫中修正：它算一次沒通過的呼叫，程式碼沒變時主 Agent 不會重複呼叫，它的發現"
         "寫進這項工作的後續紀錄，任何有追蹤的紀錄只寫摘要，除非你同意。"),
        ("README.md#disclosure", "README.zh-TW.md#disclosure",
         "The claim stays pending acceptance with its result, which main lists when it asks you at the end of the plan, "
         "and the findings stay listed, and go with every later attack on the claim, until a HELD at the commit to be "
         "landed that covered them replaces them.",
         "這個 claim 帶著它的結果維持待驗收，主 Agent 在計畫最後問你時會列出這個結果，而這些發現會一直列著，也會隨之後每次"
         "對它的攻擊提供，直到要進入預設 branch 的 commit 上涵蓋了它們的 HELD 取代它們。"),
        ("README.md#disclosure", "README.zh-TW.md#disclosure",
         "This has limits: the commit an Adversarial review attacks was not judged as a whole by the claim's own code "
         "review and verification, and its findings are not fixed in the plan.",
         "這有其限制：對抗式審查攻擊的 commit，沒有整體經過該 claim 自己的程式碼審查與驗證，它的發現也不在這份計畫中修正。"),
        ("README.md#Not passed", "README.zh-TW.md#未通過",
         "A Security-critical claim without a valid HELD is not landed, released or reported complete either; in `off`, "
         "the fix for a BROKEN goes through code review, verification and Adversarial review again, while in auto a "
         "BROKEN is recorded rather than fixed, as [Security-critical work](#security-critical-work) says, and when that "
         "step stops or a BROKEN stays unresolved, an active handoff records that the claim is pending acceptance with "
         "its Adversarial review missing, even if it had no note before.",
         "沒有有效 HELD 的安全關鍵 claim 同樣不進入預設 branch、不 release、不回報完成；在 `off` 下，BROKEN 的修正要重新經過"
         "程式碼審查、驗證與對抗式審查，在 auto 下 BROKEN 則只記錄、不修正，如[安全關鍵工作](#安全關鍵工作)所說，而該步驟停下"
         "或 BROKEN 仍未解決時，進行中的交接會記下這個 claim 待驗收、缺少對抗式審查，即使之前沒有記錄也一樣。"),
        ("README.md#Findings", "README.zh-TW.md#問題分級",
         "Security findings still block as before: a security problem the change introduced or made exploitable, even "
         "through code outside the diff, and data loss it introduced block whatever the acceptance says and need no "
         "reproduction, so a removed or weakened security control blocks; BROKEN and Adversarial review follow the "
         "adversarial-review procedure, and a vulnerability that predates the change becomes separate work in your "
         "tracker.",
         "安全問題照舊擋下：這次變更引入或使其可被利用的安全問題（即使經由 diff 以外的程式碼），以及它引入的資料遺失，不論驗收"
         "條件怎麼寫都會擋下，也不需要重現，所以移除或削弱安全控制也會擋下；BROKEN 與對抗式審查依對抗式審查程序處理，變更之前"
         "就存在的漏洞則成為 tracker 中另外的工作。"),
        ("README.md", "README.zh-TW.md",
         "| Adversarial review | For a Security-critical claim: in auto, once at the end, after the final check passes at "
         "the final commit; in `off`, after APPROVED and CONFIRMED at the same commit | adversary | HELD |",
         "| 對抗式審查 | 安全關鍵 claim：在 auto 下，最終檢查在最後的 commit 上通過後，最後做一次；在 `off` 下，在同一個 commit "
         "拿到 APPROVED 與 CONFIRMED 之後 | adversary | HELD |"),
    )

    # Acceptance item 18: the replaced statements of the same-commit premise in auto, a BROKEN fixed before landing in
    # auto, and that the Adversarial review procedure and its BROKEN are unchanged.
    REPLACED = {
        "adversarial-review.md": (
            "In auto, each Security-critical claim of plan-driven work gets Adversarial review after a valid APPROVED",
            "1. Dispatch a call that can count as the step's pass only for a claim with a valid APPROVED",
            "7. On BROKEN, disposition each finding",
        ),
        "review-state.md": (
            "the Adversarial review procedure and its BROKEN are unchanged.",
            "The adversary's BROKEN and the [adversarial review](adversarial-review.md) procedure are unchanged,",
            "during the call. An Adversarial review that can count as the step's pass also needs",
        ),
        "command": ("A call in either mode for a Security-critical claim",
                    "Both must meet the procedure's prerequisites, a valid APPROVED and a valid CONFIRMED at the same commit"),
        "outcome-verification.md": ("continue first to [Adversarial review](adversarial-review.md) at the same commit.",
                                    "For a Security-critical claim, [Adversarial review](adversarial-review.md) follows a "
                                    "valid CONFIRMED"),
        "CONTEXT.md#Adversarial review": ("made in the Automatic flow after it is approved and confirmed at the same commit",),
        "README.md": ("BROKEN and Adversarial review are unchanged", "is BROKEN and goes back to a fix;",
                      "Adversarial review is the third step: after a valid APPROVED and CONFIRMED at the same commit,",
                      "| Adversarial review | After APPROVED and CONFIRMED at the same commit,",
                      "either; the fix for a BROKEN goes through"),
        "README.zh-TW.md": ("BROKEN 與對抗式審查不變", "都是 BROKEN，要回頭修正；",
                            "對抗式審查是第三步：在同一個 commit 拿到有效的 APPROVED 與 CONFIRMED 之後，",
                            "| 對抗式審查 | 安全關鍵 claim 在同一個 commit 拿到 APPROVED 與 CONFIRMED 之後 |",
                            "不回報完成；BROKEN 的修正要重新經過"),
    }

    def new_pins(self):
        pins = {}
        for group in (self.TIMING, self.S2, self.RECORDED, self.LISTED_FINDINGS, self.NOT_RUN_COVERAGE, self.OFF,
                      self.DEFERRAL, self.CONTEXT, self.ADR):
            for place, sentences in group.items():
                pins.setdefault(place, []).extend(sentences)
        pins[self.FINAL].append(self.LIMITS)
        pins.setdefault("ADR 0009", []).append(self.ADR_0009_NOTE)
        pins.setdefault("ADR 0013", []).append(self.ADR_0013_NOTE)
        for english_place, chinese_place, english, chinese in self.README_PAIRS:
            pins.setdefault(english_place, []).append(english)
            pins.setdefault(chinese_place, []).append(chinese)
        # The off sentence that keeps a fix after BROKEN is unchanged text in a step that now names auto's exception;
        # the off pin checks it stands, and it is not a new statement.
        pins["adversarial-review.md#7"].remove(self.OFF["adversarial-review.md#7"][1])
        return pins

    def test_adversarial_review_runs_once_at_the_final_commit_in_auto(self):
        self.assert_pinned(self.TIMING)
        # The At the final commit paragraph comes before the steps it governs.
        text = self.source("adversarial-review.md")
        self.assertEqual(sum(line.startswith(self.FINAL_LABEL) for line in text.splitlines()), 1)
        self.assertLess(text.index(self.FINAL_LABEL), text.index("\n1. "))
        # Ticket 03's statement that a fix claim gets no Adversarial review still stands beside it.
        self.assertIn("In auto, a fix claim gets no Adversarial review even when it is Security-critical, as [review "
                      "state](review-state.md)'s Final check describes.", text)

    def test_s2_only_a_call_at_the_commit_to_be_landed_gives_the_result(self):
        self.assert_pinned(self.S2)

    def test_a_broken_at_the_final_commit_is_recorded_not_fixed(self):
        self.assert_pinned(self.RECORDED)
        # Step 10's disclosure rule, which the recorded findings follow, still stands.
        self.assertIn(feather_support.ADVERSARIAL_REVIEW_DISCLOSURE["adversarial-review.md"][1],
                      self.source("adversarial-review.md#10"))

    def test_listed_broken_findings_go_with_every_later_call_and_stay_open_until_a_held_covers_them(self):
        self.assert_pinned(self.LISTED_FINDINGS)
        # Step 6's check of every earlier open gap, and step 7's disclosure default, still stand beside it.
        self.assertIn("Before accepting a HELD, main checks it against every security invariant and every earlier open "
                      "gap; a HELD that leaves one uncovered is not accepted, and main treats the call as INCONCLUSIVE "
                      "with each uncovered invariant or gap open.", self.source("adversarial-review.md#6"))
        self.assertIn("By default, each finding passed to code review or outcome verification carries the violated "
                      "invariant, the location, the root cause and the observed and expected behaviour, without exploit "
                      "steps.", self.source("adversarial-review.md#7"))

    def test_a_call_that_counts_as_not_run_is_never_the_previously_judged_call(self):
        self.assert_pinned(self.NOT_RUN_COVERAGE)

    def test_the_limits_of_adversarial_review_at_the_final_commit_are_stated(self):
        self.assert_pinned({self.FINAL: (self.LIMITS,)})

    def test_off_keeps_the_same_commit_premise_the_fix_after_broken_and_the_commands_off_rule(self):
        # Fails if off loses the same-commit premise, a BROKEN fixed before completion or the command's off rule.
        self.assert_pinned(self.OFF)
        self.assertTrue(self.source("adversarial-review.md#7").startswith("7. " + self.OFF["adversarial-review.md#7"][0]))
        self.assertIn("Off mode starts no automatic Adversarial review; existing notes, counts and obligations persist.",
                      self.source("adversarial-review.md"))

    def test_the_completion_criteria_defer_to_the_adversarial_review_procedure(self):
        self.assert_pinned(self.DEFERRAL)
        # The completion conditions themselves are unchanged.
        self.assertIn("A claim's reviews judge it against these conditions: its acceptance as written is met; existing "
                      "behaviour is not broken, shown by a failing test or a reproduction; it introduces no security "
                      "problem and no data loss, as Security findings below describes; and it has no deviation from the "
                      "plan.", self.source("review-state.md#Completion conditions"))

    def test_glossary_states_the_final_commit_and_the_recorded_findings(self):
        self.assert_pinned(self.CONTEXT)

    def test_adr_0015_records_adversarial_review_at_the_final_commit_and_amends_adr_0009_and_adr_0013(self):
        self.assert_pinned(self.ADR)
        text = self.source("ADR 0015")
        self.assertEqual(text.count(f"\n## {self.PART}\n"), 1)
        # This part follows ticket 03's part.
        self.assertLess(text.index(f"\n## {FinalCheckAndFixClaimsTests.PART}\n"), text.index(f"\n## {self.PART}\n"))
        self.assertIn(self.ADR_0009_NOTE, self.source("ADR 0009").splitlines())
        lines = self.source("ADR 0013").splitlines()
        self.assertIn(self.ADR_0013_NOTE, lines)
        # Tickets 01's and 03's notes keep their own lines, and ADR 0013's statement stays as history.
        self.assertEqual(sum(line.startswith("(Amended by ADR 0015:") for line in lines), 1)
        self.assertEqual(sum(line.startswith("(Further amended by ADR 0015:") for line in lines), 1)
        self.assertIn(self.ADR_0013_HISTORY, self.source("ADR 0013"))

    def test_both_readmes_explain_adversarial_review_at_the_end_with_recorded_findings(self):
        for english_place, chinese_place, english, chinese in self.README_PAIRS:
            for place, sentence in ((english_place, english), (chinese_place, chinese)):
                with self.subTest(place=place, sentence=sentence[:40]):
                    self.assert_whole_sentence(sentence, self.source(place))

    def test_the_replaced_statements_are_gone(self):
        for place, phrases in self.REPLACED.items():
            text = self.source(place)
            for phrase in phrases:
                with self.subTest(place=place, phrase=phrase[:60]):
                    self.assertNotIn(phrase, text)

    def tagged_place(self, place):
        """The whole file behind a place at the tag; this ticket's ADR part included."""
        return self.tagged(place, self.PATHS[place.partition("#")[0]])

    def test_every_new_pin_fails_on_the_v0_25_0_text(self):
        for place, sentences in self.new_pins().items():
            text = self.tagged_place(place)
            for sentence in sentences:
                with self.subTest(place=place, sentence=sentence[:60]):
                    self.assertFalse(sentence in text, f"{place} already said this at {self.TAG}")

    def test_every_absence_pin_matches_the_v0_25_0_text(self):
        for place, phrases in self.REPLACED.items():
            text = self.tagged_place(place)
            for phrase in phrases:
                with self.subTest(place=place, phrase=phrase[:60]):
                    self.assertIn(phrase, text)


class DispatchRecordTests(unittest.TestCase):
    """Ticket 05: whole-sentence pins of the dispatch record, what crosses sessions and compaction through it in auto,
    the branches a resumed session takes from it, item 13's interim record, the notes carried from tickets 03 and 04 (the
    Plan's base revision, fix Claims and listed BROKEN findings), item 14's limit and the residual risk "The dispatch
    record is trusted", off keeping the earlier cross-session rules, the glossary, ADR 0015's part and the note on ADR
    0002, both READMEs, absence pins of the replaced statements, the unchanged handoff skill and tool, and a check that
    every new pin fails on the text at tag v0.25.0.

    The existing pins this ticket replaces, updated so that they hold for off only (item 18): in test_feather_config,
    FeatherConfigTests.test_resumed_sessions_and_plan_changes_follow_the_review_state_rules (the review-state, plan-review
    and README phrases that passing verdicts do not cross sessions and that no restriction carries over without an active
    handoff record), FOLLOW_UP_SENTENCES (plan review step 1's two sentences and the whole Resumed sessions bullet),
    ACCEPTANCE_GATE_SENTENCES and test_acceptance_gates_landing_release_and_completion_not_commits (the Commits before the
    passes bullet's branch sentence and "Before a gated operation"), ACCEPTANCE_GATE_README (Commit and Resumed session in
    both languages) and ClaimsAtImplementationTests.KEPT (plan review's restriction across a spec and its tickets); in
    test_feather_review_rules, ReviewRulesFollowUpTests.REPOSITORY_AUTHORITY (the branch sentence in review state and both
    READMEs), GATE_LIFETIME (Pending acceptance, both READMEs' Resumed session and the Active handoff entry) and the
    transition scenario of a resumed session finding a pending-acceptance note; in test_feather_security_review,
    AdversarialReviewTests' pins of Adversarial review step 4's recovery sentence and of the two-pass statements in Resumed
    sessions and both READMEs' Resumed session. README_RULES in test_feather_config gains the Dispatch record bullet."""

    PART = "The dispatch record"
    PATHS = {**PerClaimTimingTests.PATHS,
             "adversarial-review.md": "skills/delegation/references/adversarial-review.md",
             "ADR 0002": "docs/adr/0002-session-scoped-review-counts.md"}
    TAG = PerClaimTimingTests.TAG
    GIT_READ = PerClaimTimingTests.GIT_READ

    @classmethod
    def source(cls, name: str) -> str:
        """As ticket 04's reader, plus '<procedure>#<step number>' for plan review and code review,
            'review-state.md' (whole), 'ADR 0015#part' (this ticket's part) and 'ADR 0002'."""
        path, _, part = name.partition("#")
        if name == "ADR 0015#part":
            text = (config.ROOT / cls.PATHS["ADR 0015"]).read_text(encoding="utf-8")
            return text.split(f"\n## {cls.PART}\n", 1)[1].split("\n## ", 1)[0]
        if path == "ADR 0002":
            return (config.ROOT / cls.PATHS[path]).read_text(encoding="utf-8")
        if path in ("plan-review.md", "code-review.md") and part.isdigit():
            return feather_support.post_fix_source(name)
        return AdversarialReviewAtTheFinalCommitTests.source(name)

    assert_whole_sentence = feather_support.stop_threshold_assert_whole_sentence

    assert_pinned = feather_support.stop_threshold_assert_pinned

    tagged = PerClaimTimingTests.tagged

    # Acceptance item 11: the dispatch record's place and name, content, what it never holds, writing only between
    # review calls, the ignore rule, never staged or committed, written by main and not the handoff tool, and its role
    # in place of an active handoff's notes in auto.
    RECORD = {
        "review-state.md#Dispatch record": (
            "In auto, main keeps one dispatch record for each plan of plan-driven work, at `.feather/dispatch/<name>.md` "
            "in the project, named after the plan: the spec's slug when the plan is a spec or tickets of it, the "
            "ticket's slug for a single ticket, the plan file's name, or, for a plan-mode or conversation plan, a short "
            "name main states to the user.",
            "It holds what a later session needs: the plan, its base revision and its plan-review READY; for each claim, "
            "its classification, its reading set's hash, its base revision, and each review call's judged commit and "
            "verdict with a one-line summary; each fix claim with its problem and a summary of the fix; the branches "
            "main created for the work; and the user's decisions with their scope.",
            "It holds no counts, and no exploit details or secrets, which follow [adversarial "
            "review](adversarial-review.md) step 10.",
            "Main writes it only between review calls, as Serial within a working tree states for handoff records, and "
            "keeps it out of Git: when no rule already ignores it, main adds `/.feather/dispatch/` to `.gitignore`, and "
            "it never stages or commits the record.",
            "Main writes it itself; the handoff tool does not write it.",
            "In auto it replaces an active handoff's notes as the place review state crosses sessions; an active handoff "
            "records progress and names the dispatch record.",
        ),
        "SKILL.md#Plan review": (
            "In auto, main keeps one dispatch record for each plan of plan-driven work, at `.feather/dispatch/<name>.md`, "
            "named after the plan, holding the plan, its base revision and READY, each claim's classification, reading "
            "set hash, base revision and review calls with their judged commits and verdicts, the fix claims, the "
            "branches main created and the user's decisions, but no counts, exploit details or secrets; main writes it "
            "only between review calls, keeps it out of Git and never stages or commits it, as [review "
            "state](references/review-state.md)'s Dispatch record describes.",
        ),
    }

    # Acceptance item 12: what a resumed session and main after a compaction take from the record, as if received in
    # this session; counts, the Stop threshold and the final check's state from this session only; Unknown state where
    # the record lacks what main needs; the replaced rules named; and every place that restated the earlier rules.
    ACROSS_SESSIONS = {
        "review-state.md": (
            "In auto, a plan's review state crosses sessions through its dispatch record, as Dispatch record and Resumed "
            "sessions describe.",
            "In auto, a plan whose READY its dispatch record holds has plan-review state in a resumed session or after a "
            "context compaction, as Resumed sessions describes, so main does not ask.",
        ),
        "review-state.md#Resumed sessions": (
            "In auto, a resumed session reviews an unfinished plan again before implementing it unless the plan's "
            "dispatch record holds its READY; in either mode it does not redo tickets that are finished.",
            "In either mode, an unresolved verdict that an active handoff records for a spec's plan restricts that "
            "spec's tickets when they are named, and one recorded for a ticket's plan still restricts that ticket when "
            "the whole spec is named, and in auto one that a plan's dispatch record holds restricts in the same way; in "
            "off, without an active handoff record, no restriction carries into a resumed session.",
            "For a plan in auto, a resumed session, and main after a context compaction, take the plan's READY, each "
            "claim's reading set, its passes, its Adversarial review results and the user's decisions from the plan's "
            "dispatch record, as Dispatch record describes, and they count as if received in this session: a claim is "
            "not reviewed again for having passed in an earlier session, and implemented work whose READY the record "
            "holds does not ask again under Implemented before plan review.",
            "Counts still restart in each session, as ADR 0002 decided, and the Stop threshold in effect and the final "
            "check's state come only from this session, so main runs the final check again in the new session before "
            "landing, as Final check describes.",
            "Where the dispatch record lacks what main needs, Unknown state applies.",
            "For a plan in auto, this replaces the rules above that passing verdicts do not cross sessions and that an "
            "unresolved verdict reaches a resumed session only through an active handoff, and the rule that the list "
            "Accept and land at the end of the plan describes is never built from a record in the working tree: what "
            "main takes from the dispatch record counts as received in this session.",
        ),
        "review-state.md#Unknown state": (
            "In auto, what a plan's dispatch record holds counts as established in this session, after a context "
            "compaction too, as Resumed sessions describes; the record holds no counts, so after a context compaction a "
            "count that cannot be established from this session still makes its step stopped, and where the dispatch "
            "record lacks what main needs, this rule applies.",
        ),
        "review-state.md#Pending acceptance": (
            "In auto, a plan's dispatch record, not these notes, is where its claims' review state crosses sessions: main "
            "records each claim's pass state there, and a resumed session takes the claim's passes and the user's "
            "decisions from it, as Resumed sessions describes, while a note an active handoff still holds keeps "
            "restricting the claim as Existing handoff notes describes.",
        ),
        "plan-review.md#1": (
            "In off, passing verdicts do not cross sessions either; in auto, a resumed session reviews an unfinished "
            "plan again before implementing it unless the plan's dispatch record holds its READY; in either mode, "
            "finished tickets are not redone, as [review state](review-state.md) describes.",
            "In auto, a resumed session, and main after a context compaction, take the plan's READY, its claims' "
            "reading sets, passes and Adversarial review results, unresolved verdicts and the user's decisions from the "
            "plan's dispatch record, and they count as if received in this session, while counts, the Stop threshold in "
            "effect and the final check's state still come only from this session, as [review "
            "state](review-state.md)'s Resumed sessions describes.",
            "In off, an unresolved verdict restricts a resumed session only when an active handoff records it, and in "
            "auto when an active handoff or the plan's dispatch record records it; it then applies, in either mode, "
            "until a later call passes it or the user cancels the work, changes its acceptance or waives it.",
        ),
        "plan-review.md": (
            "In a resumed session, an unresolved verdict that an active handoff records for a spec's plan applies to "
            "that spec's tickets when they are named; one recorded for a ticket's plan still restricts that ticket when "
            "the whole spec is named, and in off, without such a record no restriction carries over; in auto, an "
            "unresolved verdict a plan's dispatch record holds restricts in the same way, as [review "
            "state](review-state.md)'s Resumed sessions describes.",
        ),
        "code-review.md#3": (
            "Recover the count, verdicts and open findings as in [plan review](plan-review.md) step 1: counts are per "
            "session, a resumed session starts a new count, an in-session state that cannot be established makes the "
            "step stopped until the user decides, and in off an unresolved verdict restricts a resumed session only when "
            "an active handoff records it; in auto, a resumed session, and main after a context compaction, take the "
            "claim's passes, verdicts and open findings from the plan's dispatch record as if received in this session, "
            "as [review state](review-state.md)'s Resumed sessions describes.",
        ),
        "outcome-verification.md#3": (
            "Recover the count, verdicts and open findings as in [plan review](plan-review.md) step 1: counts are per "
            "session, a resumed session starts a new count, an in-session state that cannot be established makes the "
            "step stopped until the user decides, and in off an unresolved verdict restricts a resumed session only when "
            "an active handoff records it; in auto, a resumed session, and main after a context compaction, take the "
            "claim's passes, verdicts and open findings from the plan's dispatch record as if received in this session, "
            "as [review state](review-state.md)'s Resumed sessions describes.",
        ),
        "adversarial-review.md#4": (
            "Recover the count, verdicts, coverage and open gaps as in [plan review](plan-review.md) step 1: counts are "
            "per session, a resumed session starts a new count, in off HELD does not cross sessions, an in-session state "
            "that cannot be established makes the step stopped until the user decides, and in off an unresolved verdict "
            "restricts a resumed session only when an active handoff records it; in auto, a resumed session, and main "
            "after a context compaction, take the claim's Adversarial review result and a BROKEN's listed findings, by "
            "their one-line summary, from the plan's dispatch record as if received in this session, their details "
            "staying where step 10 puts them, as [review state](review-state.md)'s Resumed sessions describes.",
        ),
        "SKILL.md#Plan review": (
            "Keep the review count and unresolved verdicts across mode changes within a session; a resumed session "
            "starts a new count, while unresolved verdicts recorded in an active handoff still apply and, in auto, so "
            "does what the plan's dispatch record holds.",
            "A resumed session, and main after a context compaction, take the plan's READY, reading sets, passes, "
            "Adversarial review results and the user's decisions from it as if received in this session, while counts, "
            "the Stop threshold in effect and the final check's state still come only from this session, as [review "
            "state](references/review-state.md)'s Resumed sessions describes; an active handoff records progress and "
            "names the dispatch record.",
        ),
    }

    # In auto, a resumed session takes the branches main created for the work from the dispatch record, in place of an
    # active handoff.
    COMMITS = {
        "review-state.md#Commits before the passes": (
            "Before pushing to a remote branch that already existed and that main did not create, it asks the user; in a "
            "resumed session main treats a branch as its own only when a record shows that main created it for this "
            "work, and otherwise asks: in auto the plan's dispatch record, in place of an active handoff, as Dispatch "
            "record describes, and in off an active handoff.",
        ),
    }

    # Acceptance item 13's interim record, pointing to the existing Accept and land at the end of the plan.
    INTERIM = {
        "review-state.md#Dispatch record": (
            "Until the user's decision at the end of the plan, as Accept and land at the end of the plan describes, main "
            "records each claim's pass state in it.",
        ),
    }

    # The notes carried from tickets 03 and 04: the Plan's base revision may come from the record (S1), fix Claims are
    # kept in it, and listed BROKEN findings stay listed in a resumed session.
    CARRIED = {
        "review-state.md#Evidence for a regression": (
            "In auto, main may instead take the plan's base revision from the plan's dispatch record, as Dispatch record "
            "describes.",
        ),
        "review-state.md#Final check": (
            "In auto, main keeps each fix claim, with its problem and a summary of the fix, in the plan's dispatch "
            "record, as Dispatch record describes.",
        ),
        "review-state.md#Resumed sessions": (
            "Unresolved verdicts and open findings the record holds restrict their claims as if received in this "
            "session, and a BROKEN's findings that the record lists by their one-line summary stay listed, their details "
            "staying where [adversarial review](adversarial-review.md) step 10 puts them.",
            "Main may also take the plan's base revision and the branches it created for the work from it, as Evidence "
            "for a regression and Commits before the passes describe.",
        ),
        "adversarial-review.md#final": (
            "In a resumed session, and after a context compaction, they stay listed from the plan's dispatch record, "
            "which holds each BROKEN's one-line summary, and from the work's Follow-up record, which holds what step 10 "
            "allows, as [review state](review-state.md)'s Resumed sessions describes.",
        ),
    }

    # Acceptance item 14's limit and the residual risk "The dispatch record is trusted".
    TRUSTED = {
        "review-state.md#Dispatch record": (
            "Main takes the dispatch record as written, so an edit to it, by repository code a review or the final check "
            "runs or by a person, changes which passes and results main believes; this flow does not defend against "
            "that.",
        ),
        "SKILL.md#Plan review": ("Main takes the dispatch record as written, so an edit to it changes what main believes.",),
    }

    # Acceptance item 15: off writes no dispatch record and keeps the earlier cross-session rules.
    OFF = {
        "review-state.md#Dispatch record": (
            "Off mode writes none, and in off the cross-session rules of Resumed sessions hold without it.",
        ),
        "review-state.md": (
            "Counts are per session; in off, an unresolved verdict reaches a resumed session only through an active "
            "handoff record.",
        ),
        "review-state.md#Resumed sessions": (
            "Counts do not cross sessions.",
            "In off, passing verdicts do not cross sessions either.",
            "In off, before a gated operation, a claim needs valid passes from this session, so a claim that passed in "
            "an earlier session is reviewed and verified again, and a Security-critical claim gets Adversarial review "
            "again, counted as usual.",
        ),
        "review-state.md#Pending acceptance": (
            "In off, a resumed session that finds a pending-acceptance note keeps the claim under the gate and obtains "
            "passes from the current session, as passing verdicts do not cross sessions, unless the note records an "
            "accept-and-land decision that still holds or the claim's ticket is exempt as under Resumed sessions.",
        ),
        "SKILL.md#Plan review": (
            "Off mode writes no dispatch record and keeps the cross-session rules of [review "
            "state](references/review-state.md)'s Resumed sessions for off.",
        ),
        "README.md#Dispatch record": ("In `off`, main writes none and the rules under Resumed session hold as before.",),
        "README.zh-TW.md#派工紀錄": ("在 `off` 下，主 Agent 不寫派工紀錄，「恢復的 session」的規則照舊。",),
        "README.md#Resumed session": (
            "In `off`, passing verdicts do not carry over either, and without an active handoff record no restriction "
            "carries over.",
            "In `off`, before landing, release or completion, a claim that passed in an earlier session is reviewed and "
            "verified again, and a Security-critical claim gets Adversarial review again, unless its ticket was set to a "
            "done value after both passes (plus HELD for a Security-critical claim) or your accept-and-land decision and "
            "nothing relevant changed since.",
        ),
        "README.zh-TW.md#恢復的 session": (
            "在 `off` 下，通過的結論也不會帶到新的 session，沒有進行中的交接記錄時，不會有任何限制帶過去。",
        ),
        "CONTEXT.md#Active handoff": ("In off, it is how unresolved verdicts and gate notes reach a resumed session.",),
    }

    # Acceptance item 16, for these rules: the Dispatch record entry and the Active handoff and Pending-acceptance claim
    # entries.
    CONTEXT = {
        "CONTEXT.md#Dispatch record": (
            "Main's record of one Plan's review state in the Automatic flow, at `.feather/dispatch/<name>.md` in the "
            "project, named after the Plan.",
            "It holds the Plan, its base revision and READY; each Claim's classification, reading set hash and base "
            "revision, and each review call's judged commit and verdict with a one-line summary; each fix Claim with its "
            "problem and a summary of the fix; the branches main created for the work; and the user's decisions with "
            "their scope; never counts, exploit details or secrets.",
            "Main writes it only between review calls and keeps it out of Git, never staging or committing it.",
            "A resumed session, and main after a context compaction, take the Plan's READY, reading sets, passes, "
            "Adversarial review results and the user's decisions from it as if received in this session, while counts, "
            "the Stop threshold in effect and the final check's state still come only from this session.",
            "Main takes it as written, so an edit to it changes what main believes.",
            "Off mode writes none.",
        ),
        "CONTEXT.md#Active handoff": (
            "In the Automatic flow, a Plan's review state crosses sessions through its Dispatch record instead, and an "
            "Active handoff records progress and names the Dispatch record.",
        ),
        "CONTEXT.md#Pending-acceptance claim": (
            "In the Automatic flow, main records each Claim's pass state in the Plan's Dispatch record until the user's "
            "decision at the end of the Plan, and a resumed session takes it from there rather than from an Active "
            "handoff note.",
        ),
    }

    # Acceptance item 16, for these rules: ADR 0015's part on the dispatch record amends ADR 0002.
    ADR = {
        "ADR 0015#part": (
            "This part records the dispatch record.",
            "- **The record.** In auto, main keeps one dispatch record for each Plan of Plan-driven work, at "
            "`.feather/dispatch/<name>.md`, named after the Plan: the spec's slug when the Plan is a spec or tickets of "
            "it, the ticket's slug for a single ticket, the plan file's name, or for a plan-mode or conversation plan a "
            "short name main states to the user.",
            "It holds no counts and no exploit details or secrets, which follow Adversarial review step 10.",
            "- **Writing it.** Main writes it only between review calls, as Serial within a working tree states for "
            "handoff records, and keeps it out of Git: when no rule already ignores it, main adds `/.feather/dispatch/` "
            "to `.gitignore`, and it never stages or commits the record.",
            "Until the user's decision at the end of the Plan, main records each Claim's pass state in it.",
            "- **A new session.** A resumed session, and main after a context compaction, take the Plan's READY, reading "
            "sets, passes, Adversarial review results and the user's decisions from the dispatch record, and they count "
            "as if received in this session: a Claim is not reviewed again for having passed in an earlier session, and "
            "implemented work whose READY the record holds does not ask again under Implemented before plan review.",
            "Counts restart in each session, as ADR 0002 decided, and the Stop threshold in effect and the final check's "
            "state still come only from this session, so main runs the final check again in the new session before "
            "landing.",
            "For a Plan in auto this replaces the rules that passing verdicts do not cross sessions, that the Accept and "
            "land list is never built from a record in the working tree, and that an unresolved verdict reaches a "
            "resumed session only through an Active handoff.",
            "- **Off mode.** These rules hold in auto only: off writes no dispatch record and keeps the earlier "
            "cross-session rules.",
            "- **Trusted.** Main takes the dispatch record as written.",
            "Repository code a review or the final check runs, or a person, can edit it and so change which passes and "
            "results main believes; cc-feather does not defend against that.",
            "This amends [ADR 0002](0002-session-scoped-review-counts.md) (what crosses sessions): in auto, a Plan's "
            "READY, reading sets, passes, Adversarial review results and the user's decisions cross sessions through its "
            "dispatch record, not only an unresolved verdict an active handoff records.",
            "- **Carry counts across sessions**: ADR 0002 restarts them on resume.",
        ),
    }
    ADR_0002_NOTE = ("(Amended by ADR 0015: in auto, a Plan's review state crosses sessions through its dispatch record "
                     "under `.feather/dispatch/`: a resumed session, and main after a context compaction, take the Plan's "
                     "READY, reading sets, passes, Adversarial review results and the user's decisions from it as if "
                     "received in that session, while counts still restart in each session; in off, only an unresolved "
                     "verdict an active handoff records crosses sessions, as above.)")

    # Acceptance item 17, for these rules: (English place, Chinese place, English sentence, Chinese sentence).
    README_PAIRS = (
        ("README.md#Dispatch record", "README.zh-TW.md#派工紀錄",
         "in auto, main keeps one dispatch record for each plan at `.feather/dispatch/<name>.md`, named after the plan: "
         "the spec's slug for a spec or its tickets, the ticket's slug for a single ticket, the plan file's name, or a "
         "short name main tells you for a plan-mode or conversation plan.",
         "在 auto 下，主 Agent 為每份計畫保留一份派工紀錄，放在 `.feather/dispatch/<name>.md`，以計畫命名：spec 或它的 "
         "ticket 用 spec 的 slug，單一 ticket 用該 ticket 的 slug，計畫檔用檔名，plan mode 或對話中的計畫則用主 Agent "
         "告訴你的簡短名稱。"),
        ("README.md#Dispatch record", "README.zh-TW.md#派工紀錄",
         "It holds what a later session needs: the plan, its base revision and its plan-review READY; for each claim, "
         "its classification, its reading set's hash, its base revision, and each review call's judged commit and "
         "verdict with a one-line summary; each fix claim with its problem and a summary of the fix; the branches main "
         "created for the work; and your decisions with their scope.",
         "它保存之後的 session 需要的內容：計畫、計畫的基準版本與計畫審查的 READY；每個 claim 的分類、閱讀範圍的雜湊、"
         "基準版本，以及每次審查呼叫所審的 commit 與結論，附一行摘要；每個修正用的 claim 及其問題與修正摘要；主 Agent "
         "為這項工作建立的 branch；以及你的決定和範圍。"),
        ("README.md#Dispatch record", "README.zh-TW.md#派工紀錄",
         "It holds no counts, exploit details or secrets, and until your decision at the end of the plan it holds each "
         "claim's pass state.",
         "它不保存次數、攻擊細節或機密，而在你對計畫做出最後決定之前，它保存每個 claim 的通過狀態。"),
        ("README.md#Dispatch record", "README.zh-TW.md#派工紀錄",
         "Main writes it only between review calls and keeps it out of Git: when no rule already ignores it, main adds "
         "`/.feather/dispatch/` to `.gitignore`, and it never stages or commits the record.",
         "主 Agent 只在審查呼叫之間寫入它，並讓它不進 Git：沒有規則已經忽略它時，主 Agent 會把 `/.feather/dispatch/` "
         "加進 `.gitignore`，且從不 stage 或 commit 這份紀錄。"),
        ("README.md#Dispatch record", "README.zh-TW.md#派工紀錄",
         "In auto it, not an active handoff's notes, is where review state crosses sessions; an active handoff records "
         "progress and names the dispatch record.",
         "在 auto 下，審查狀態是靠它、而不是進行中交接的記錄帶到新的 session；進行中的交接記錄進度，並寫明派工紀錄。"),
        ("README.md#Dispatch record", "README.zh-TW.md#派工紀錄",
         "A new session, and main after context compaction, take the plan's READY, reading sets, passes, Adversarial "
         "review results and your decisions from it as if received in that session, so a claim that passed earlier is "
         "not reviewed again and implemented work whose READY it holds is not asked about again, and the unresolved "
         "verdicts and a BROKEN's listed findings it holds stay with their claims.",
         "新的 session，以及 context 壓縮後的主 Agent，會從它取得計畫的 READY、閱讀範圍、通過、對抗式審查結果與你的決定，"
         "視同在該 session 中收到，所以之前通過的 claim 不會重新審查，它記有 READY 的已實作工作也不會再問一次，而它記錄的"
         "未解決結論與 BROKEN 列出的發現仍跟著各自的 claim。"),
        ("README.md#Dispatch record", "README.zh-TW.md#派工紀錄",
         "Counts still restart in each session, and the Stop threshold and the final check's state come only from the "
         "current session, so main runs the final check again before landing; where the record lacks what main needs, "
         "main treats the step as stopped and asks you.",
         "次數仍在每個 session 重新計算，停止門檻與最終檢查的狀態只來自目前的 session，所以主 Agent 會在進入預設 branch "
         "前重新執行最終檢查；紀錄缺少主 Agent 需要的內容時，主 Agent 會視為已停下並問你。"),
        ("README.md#Dispatch record", "README.zh-TW.md#派工紀錄",
         "Main takes the dispatch record as written, so an edit to it, by repository code a review or the final check "
         "runs or by a person, changes which passes and results main believes; cc-feather does not defend against that.",
         "主 Agent 照紀錄所寫的內容採信，所以有人或審查、最終檢查執行的儲存庫程式碼修改它，就會改變主 Agent 相信哪些通過"
         "與結果；cc-feather 不防範這一點。"),
        ("README.md#Resumed session", "README.zh-TW.md#恢復的 session",
         "In auto, an unfinished plan is reviewed again unless its dispatch record holds its READY, and the plan's "
         "passes, Adversarial review results, unresolved verdicts and your decisions carry over through the dispatch "
         "record, as Dispatch record says.",
         "在 auto 下，未完成的計畫會重新審查，除非它的派工紀錄記有 READY，而計畫的通過、對抗式審查結果、未解決的結論與你的"
         "決定都透過派工紀錄帶過去，如「派工紀錄」所說。"),
        ("README.md#Resumed session", "README.zh-TW.md#恢復的 session",
         "Counts do not carry over, and in either mode finished tickets are not redone.",
         "次數不會帶到新的 session，而且不論哪種模式，已完成的 ticket 都不會重做。"),
        ("README.md#Commit", "README.zh-TW.md#Commit 條件",
         "It asks before pushing to a branch that already existed and that it did not create; in a resumed session a "
         "branch counts as its own only when a record shows that it created it for this work: in auto the dispatch "
         "record, in place of an active handoff, and in `off` an active handoff.",
         "要推到原本就存在、不是它建立的 branch 前，會先問你；恢復的 session 裡，只有紀錄顯示它為這項工作建立了該 branch，"
         "才算它自己的 branch：在 auto 下看派工紀錄，取代進行中的交接，在 `off` 下看進行中的交接。"),
        ("README.md#Implemented before plan review", "README.zh-TW.md#實作完才做計畫審查",
         "In auto, a plan whose dispatch record holds its READY counts as reviewed in a new session or after context "
         "compaction too, so main does not ask.",
         "在 auto 下，派工紀錄記有 READY 的計畫，在新的 session 或 context 壓縮後也算已審查，主 Agent 不會再問。"),
    )

    # Acceptance item 18: the replaced statements that passing verdicts and HELD do not cross sessions and that an
    # unresolved verdict, or a branch main created, reaches a resumed session only through an active handoff, unscoped.
    REPLACED = {
        "review-state.md": (
            "Counts and passing verdicts do not cross sessions.",
            "Counts are per session; an unresolved verdict reaches a resumed session only through an active handoff "
            "record.",
            "is named; without an active handoff record, no restriction carries into a resumed session.",
            "Before a gated operation, a claim needs valid passes from this session",
            "the note returns to pending acceptance, naming what is missing. A resumed session that finds a "
            "pending-acceptance note",
            "in a resumed session main treats a branch as its own only when an active handoff records that main created "
            "it for this work, and otherwise asks.",
        ),
        "plan-review.md": (
            "Passing verdicts do not cross sessions either:",
            "An unresolved verdict restricts a resumed session only when an active handoff records it;",
            "is named, and without such a record no restriction carries over.",
        ),
        "code-review.md": ("and an unresolved verdict restricts a resumed session only when an active handoff records it.",),
        "outcome-verification.md": (
            "and an unresolved verdict restricts a resumed session only when an active handoff records it.",
        ),
        "adversarial-review.md": (
            "a resumed session starts a new count, HELD does not cross sessions,",
            "and an unresolved verdict restricts a resumed session only when an active handoff records it.",
        ),
        "CONTEXT.md#Active handoff": ("It is how unresolved verdicts and gate notes reach a resumed session.",),
        "README.md": (
            "Counts and passing verdicts do not carry over",
            "in a resumed session a branch counts as its own only when an active handoff records that it created it for "
            "this work.",
        ),
        "README.zh-TW.md": (
            "次數與通過的結論不會帶到新的 session",
            "恢復的 session 裡，只有進行中的交接記錄了它為這項工作建立該 branch，才算它自己的 branch。",
        ),
    }

    # The handoff skill and its tool are unchanged: the dispatch record is written by main, not by the handoff tool (as
    # at v0.25.0, line endings normalised to LF, as .gitattributes stores them).
    UNCHANGED = {
        "skills/handoff/SKILL.md": "b750854f9770a8e96bba8617748d74445705191a3fc9cae624a1da39d66d665d",
        "skills/handoff/scripts/handoff.py": "cb18fa4a4d3c350e1cba2f13162a5d03d87262651c6be5ae09e3d3abaeeeb491",
    }

    def new_pins(self):
        pins = {}
        for group in (self.RECORD, self.ACROSS_SESSIONS, self.COMMITS, self.INTERIM, self.CARRIED, self.TRUSTED,
                      self.OFF, self.CONTEXT, self.ADR):
            for place, sentences in group.items():
                pins.setdefault(place, []).extend(sentences)
        pins.setdefault("ADR 0002", []).append(self.ADR_0002_NOTE)
        for english_place, chinese_place, english, chinese in self.README_PAIRS:
            pins.setdefault(english_place, []).append(english)
            pins.setdefault(chinese_place, []).append(chinese)
        return pins

    def test_the_dispatch_record_is_kept_in_auto_out_of_git_and_written_between_calls(self):
        self.assert_pinned(self.RECORD)
        # It sits first among the rules for resumed sessions, which it feeds.
        text = (config.ROOT / self.PATHS["review-state.md"]).read_text(encoding="utf-8")
        section = text.split("## Resumed sessions and plan changes", 1)[1].split("\n## ", 1)[0]
        labels = [line.split("**", 2)[1] for line in section.splitlines() if line.startswith("- **")]
        self.assertEqual(labels[:2], ["Dispatch record.", "Resumed sessions."])

    def test_a_resumed_session_and_a_compaction_take_review_state_from_the_record(self):
        self.assert_pinned(self.ACROSS_SESSIONS)

    def test_a_resumed_session_takes_the_branches_main_created_from_the_record_in_auto(self):
        self.assert_pinned(self.COMMITS)

    def test_until_the_decision_at_the_end_main_records_each_claims_pass_state(self):
        self.assert_pinned(self.INTERIM)

    def test_the_base_revision_fix_claims_and_listed_broken_findings_go_through_the_record(self):
        self.assert_pinned(self.CARRIED)
        # Ticket 03's statement that main establishes the Plan's base revision from Git, and ticket 04's that a BROKEN's
        # findings stay listed, still stand beside the new sentences.
        self.assertIn("which main establishes itself from Git in this session. In auto, main may instead take the "
                      "plan's base revision from the plan's dispatch record",
                      self.source("review-state.md#Evidence for a regression"))
        self.assertIn("A BROKEN's findings stay listed until a HELD at the commit to be landed replaces them. In a resumed "
                      "session, and after a context compaction, they stay listed", self.source("adversarial-review.md#final"))

    def test_the_dispatch_record_is_trusted_as_written(self):
        # Item 14's limit and the residual risk "The dispatch record is trusted", with no control against forgery.
        self.assert_pinned(self.TRUSTED)

    def test_off_writes_no_dispatch_record_and_keeps_the_earlier_cross_session_rules(self):
        # Fails if off loses the earlier cross-session rules or starts writing a dispatch record.
        self.assert_pinned(self.OFF)
        self.assertTrue(self.source("review-state.md#Dispatch record").startswith(
            "- **Dispatch record.** In auto, main keeps one dispatch record"))
        self.assertTrue(self.source("README.md#Dispatch record").startswith(" in auto, main keeps one dispatch record"))
        self.assertTrue(self.source("README.zh-TW.md#派工紀錄").startswith("在 auto 下，主 Agent 為每份計畫保留一份派工紀錄"))
        self.assertTrue(self.source("CONTEXT.md#Dispatch record").startswith(
            "Main's record of one Plan's review state in the Automatic flow"))
        # The toggle procedure and the installed policy name no dispatch record, so turning auto off writes none.
        for path in ("skills/setup/references/auto-review.md", "templates/review-auto.md"):
            with self.subTest(path=path):
                self.assertNotIn("dispatch record", (config.ROOT / path).read_text(encoding="utf-8").lower())

    def test_glossary_states_the_dispatch_record_and_its_role(self):
        self.assert_pinned(self.CONTEXT)
        entries = feather_support.glossary_entries((config.ROOT / "CONTEXT.md").read_text(encoding="utf-8"))
        terms = list(entries)
        self.assertEqual(terms[terms.index("Dispatch record") + 1], "Active handoff")

    def test_adr_0015_records_the_dispatch_record_and_amends_adr_0002(self):
        self.assert_pinned(self.ADR)
        text = self.source("ADR 0015")
        self.assertEqual(text.count(f"\n## {self.PART}\n"), 1)
        # This part follows ticket 04's part.
        self.assertLess(text.index(f"\n## {AdversarialReviewAtTheFinalCommitTests.PART}\n"),
                        text.index(f"\n## {self.PART}\n"))
        lines = self.source("ADR 0002").splitlines()
        self.assertIn(self.ADR_0002_NOTE, lines)
        self.assertEqual(sum(line.startswith("(Amended by ADR 0015:") for line in lines), 1)

    def test_both_readmes_explain_the_dispatch_record_and_continuing_in_a_new_session(self):
        for english_place, chinese_place, english, chinese in self.README_PAIRS:
            for place, sentence in ((english_place, english), (chinese_place, chinese)):
                with self.subTest(place=place, sentence=sentence[:40]):
                    self.assert_whole_sentence(sentence, self.source(place))

    def test_the_replaced_statements_are_gone(self):
        for place, phrases in self.REPLACED.items():
            text = self.source(place)
            for phrase in phrases:
                with self.subTest(place=place, phrase=phrase[:60]):
                    self.assertNotIn(phrase, text)

    def digest(self, text):
        return hashlib.sha256(text.replace("\r\n", "\n").encode("utf-8")).hexdigest()

    def test_the_handoff_skill_and_its_tool_are_unchanged(self):
        for path, digest in self.UNCHANGED.items():
            with self.subTest(path=path):
                self.assertEqual(self.digest((config.ROOT / path).read_text(encoding="utf-8")), digest)

    def test_the_handoff_skill_and_its_tool_match_the_v0_25_0_text(self):
        for path, digest in self.UNCHANGED.items():
            with self.subTest(path=path):
                self.assertEqual(self.digest(self.tagged(path, path)), digest)

    def tagged_place(self, place):
        """The whole file behind a place at the tag; this ticket's ADR part included."""
        return self.tagged(place, self.PATHS[place.partition("#")[0]])

    def test_every_new_pin_fails_on_the_v0_25_0_text(self):
        for place, sentences in self.new_pins().items():
            text = self.tagged_place(place)
            for sentence in sentences:
                with self.subTest(place=place, sentence=sentence[:60]):
                    self.assertFalse(sentence in text, f"{place} already said this at {self.TAG}")

    def test_every_absence_pin_matches_the_v0_25_0_text(self):
        for place, phrases in self.REPLACED.items():
            text = self.tagged_place(place)
            for phrase in phrases:
                with self.subTest(place=place, phrase=phrase[:60]):
                    self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
