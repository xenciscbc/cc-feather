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
today's final check. The adversary template is unchanged."""

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


if __name__ == "__main__":
    unittest.main()
