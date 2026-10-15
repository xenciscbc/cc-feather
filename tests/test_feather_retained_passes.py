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
turning automatic review off during a Plan reopens fixed passes. The reviewer template is unchanged."""

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


if __name__ == "__main__":
    unittest.main()
