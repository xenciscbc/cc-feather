"""Delegation dedupe ticket 01 (docs/specs/delegation-dedupe.md, Runtime part, the expand step; Acceptance items 2, 4
and 8 for this ticket, the D7 item of item 6, Security invariants S1–S4 and test target T3, with the condition inventory
docs/specs/delegation-dedupe-inventory.md sections 0–6): each condition the inventory marks MOVES is stated at its
rule's owner with its original predicate, one predicate per destination; main is told, at every place item 4 names, to
read review state in full before a decision, brief or gate operation that depends on it; review state's Resolution
points to Saved in this conversation (D7); and every brief requirement of the inventory's S2 index still stands in the
procedure that writes the brief. A short read sentence is repeated at each place on purpose, since a command entry may
run without the delegation skill loaded; as ticket 02 revised it (the user's decision of 2026-10-20, option 1), each one
keeps its trigger, the full read and "in off and in auto", and points to review state's Reading it rule, the first rule
of review state, which states the details of the read once.

Ticket 02 (the contract step; Acceptance items 1, 3, 5, 6 and 8, S1–S4 and T3) adds DelegationDedupeContractTests: each
rule the inventory's section 1 lists is stated once, at its owner; every other copy is a pointer that names an owner part
that exists, in the explicit-read form for an owner other than review state; the restatements and item 5's historical
phrases are gone from the runtime files under skills/; and the H and D items carry the inventory's replacement texts.
Brief requirements, preview's own summaries, the command's own classification text and ticket 01's read sentences are
not owner statements, so the once and absence pins are chosen from the rules' own conditions and leave them alone."""

from __future__ import annotations

import re
import subprocess
import unittest

from tests import feather_support
from tests.feather_support import config


DELEGATION = config.ROOT / "skills" / "delegation"
REFERENCES = DELEGATION / "references"
# The short name of each runtime file in item 1's scope, and its repository path.
PATHS = {
    "delegation SKILL.md": "skills/delegation/SKILL.md",
    "review-state.md": "skills/delegation/references/review-state.md",
    "plan-review.md": "skills/delegation/references/plan-review.md",
    "code-review.md": "skills/delegation/references/code-review.md",
    "outcome-verification.md": "skills/delegation/references/outcome-verification.md",
    "adversarial-review.md": "skills/delegation/references/adversarial-review.md",
    "preview.md": "skills/delegation/references/preview.md",
    "adversarial-review SKILL.md": "skills/adversarial-review/SKILL.md",
    "delegation-preview SKILL.md": "skills/delegation-preview/SKILL.md",
    "stop-threshold SKILL.md": "skills/stop-threshold/SKILL.md",
    "setup stop-threshold.md": "skills/setup/references/stop-threshold.md",
}
# How each file links to review state.
REVIEW_STATE_LINK = {
    "delegation SKILL.md": "references/review-state.md",
    "plan-review.md": "review-state.md",
    "code-review.md": "review-state.md",
    "outcome-verification.md": "review-state.md",
    "adversarial-review.md": "review-state.md",
    "preview.md": "review-state.md",
    "adversarial-review SKILL.md": "../delegation/references/review-state.md",
    "delegation-preview SKILL.md": "../delegation/references/review-state.md",
    "stop-threshold SKILL.md": "../delegation/references/review-state.md",
    "setup stop-threshold.md": "../../delegation/references/review-state.md",
}
TAG = "v0.29.0"
# The reference's read-only Git prefix (repository safety's Safe Git invocation), as the other modules use it.
GIT_READ = ("git", "--no-pager", "--no-optional-locks", "-c", "core.fsmonitor=", "-c", "core.quotePath=true",
            "-c", "log.showSignature=false", "-c", "mailmap.file=", "-c", "mailmap.blob=",
            "-c", "blame.ignoreRevsFile=", "-c", "diff.orderFile=/dev/null", "-c", "submodule.recurse=false")


def place_text(name: str, text: str) -> str:
    """One place of a file's text: '<file>' is the whole file, '<file>#<n>' its numbered step n, '<file>#@<opening>'
    the one line (paragraph, step or bullet) that starts with <opening>, and '<file>#<label>' its '- **<label>.**'
    bullet."""
    _, _, part = name.partition("#")
    if not part:
        return text
    lines = text.splitlines()
    if part.isdigit():
        prefix = f"{part}. "
    elif part.startswith("@"):
        prefix = part[1:]
    else:
        prefix = f"- **{part}.**"
    found = [line for line in lines if line.lstrip().startswith(prefix)]
    if len(found) != 1:
        raise AssertionError(f"{name}: {len(found)} lines start with {prefix!r}")
    return found[0]


def source(name: str) -> str:
    return place_text(name, (config.ROOT / PATHS[name.partition("#")[0]]).read_text(encoding="utf-8"))


# Acceptance item 4's read, as ticket 02 revised it (the user's decision of 2026-10-20, option 1): the details of reading
# review state are stated once, in review state's Reading it rule, the first rule of the file and before its table of
# steps, so that the first part of any read includes it.
READING_IT = (
    "- **Reading it.** Main reads review state in full, every line, and when one read returns only part of the file it "
    "reads the rest before acting. A full read whose text is still in main's context serves later places until main "
    "reads review state again, which it does after any context compaction, at the start of a new or resumed session and "
    "whenever it cannot quote the owner's sentence it is about to apply. This holds in off and in auto."
)
# The parts ticket 01's Acceptance 4 lists, each a phrase of the Reading it rule.
READ_PARTS = {
    "reading in full": "Main reads review state in full, every line",
    "in parts when one read returns part": "when one read returns only part of the file it reads the rest before acting",
    "reuse of a full read still in context":
        "A full read whose text is still in main's context serves later places until main reads review state again",
    "rereading after a compaction": "after any context compaction",
    "rereading at a new or resumed session": "at the start of a new or resumed session",
    "rereading when main cannot quote the owner's sentence":
        "whenever it cannot quote the owner's sentence it is about to apply",
    "off and auto": "This holds in off and in auto.",
}
# Every place states the read in one short sentence: what the read precedes at that place (its trigger), then this
# text, then, where the place covers dispatch, that a scout or Explore lookup needs no such read. Reading is the
# default; the sentence states no exception and points to Reading it for when an earlier full read still serves.
READ_TAIL = (", in off and in auto, main reads [review state]({link}) in full; review state's Reading it says when an "
             "earlier full read still serves")
SCOUT = "; a scout or Explore lookup needs no such read"
# Wording the short sentence never carries: the rule's own details and any exception stated at the place.
READ_NOT_AT_PLACE = ("every line", "returns only part", "serves here", "serves later places", "context compaction",
                     "new or resumed session", "cannot quote", "unless", "except", "need not", "needs no read")
# Each place item 4 names, with what the read precedes there and whether the place covers dispatch.
READ_PLACES = {
    # The delegation skill's Select and prepare, a security analysis's brief and its workspace reads included.
    "delegation SKILL.md#@For requested security analysis": (
        "Before any decision or brief in this section that depends on a rule review state owns, a security analysis's "
        "brief and its workspace reads included", True),
    # Dispatch.
    "delegation SKILL.md#@Give the child a goal": (
        "Before any brief or dispatch decision in this section that depends on a rule review state owns, such as an "
        "implementation brief's reading set or Serial within a working tree", True),
    # Accept or recover: accepting or reusing a verdict.
    "delegation SKILL.md#@Compare the child's report with its brief": ("Before accepting or reusing a verdict", False),
    # Accept or recover: retrying or recovering a call.
    "delegation SKILL.md#@Classify a blocker": ("Before retrying or recovering a call", True),
    # Accept or recover: resuming the automatic flow after an explicit pass, and every gate operation, stated once.
    "delegation SKILL.md#@When the automatic flow requires them": (
        "Before resuming the automatic flow after an explicit pass, and before every gate operation (landing, merging, "
        "releasing or tagging, reporting a claim or the whole task complete, setting a ticket done, or Accept and "
        "land)", True),
    # Accept or recover: Implemented before plan review and the classification of a review request.
    "delegation SKILL.md#@When the user asks for a \"review\" without naming one": (
        "Before deciding which review an unnamed request runs, asking under Implemented before plan review or "
        "classifying the call", True),
    # Plan review, and the final check.
    "delegation SKILL.md#@When the installed policy, a session preference that turns automatic review on (": (
        "Before any decision or brief this section governs that depends on a rule review state owns, and before the "
        "final check", True),
    "delegation SKILL.md#@When the installed policy, a session preference that turns automatic review on or": (
        "Before any code-review decision or brief that depends on a rule review state owns", True),
    "delegation SKILL.md#@For automatic verification of plan-driven work": (
        "Before any outcome-verification decision or brief that depends on a rule review state owns", True),
    "delegation SKILL.md#@For automatic Adversarial review of a Security-critical claim": (
        "Before any Adversarial review decision or brief that depends on a rule review state owns, the classification "
        "of an explicit call included", True),
    # The procedures of plan review, code review, outcome verification and Adversarial review.
    "plan-review.md#@This procedure governs main's orchestration.": (
        "Before any decision or brief of this procedure that depends on a rule review state owns", True),
    "code-review.md#@This procedure governs main's orchestration.": (
        "Before any decision or brief of this procedure that depends on a rule review state owns", True),
    "outcome-verification.md#@This procedure governs main's orchestration.": (
        "Before any decision or brief of this procedure that depends on a rule review state owns", True),
    "adversarial-review.md#@This procedure governs main's orchestration.": (
        "Before any decision or brief of this procedure that depends on a rule review state owns", True),
    # Preview, which dispatches no child.
    "preview.md#@This procedure runs only through": (
        "Before resolving a value or writing any part of the preview that depends on a rule review state owns, such "
        "as the Stop threshold", False),
    # The three command skills, before their classification or resolution steps.
    "adversarial-review SKILL.md#@Run an Adversarial review in the current conversation": (
        "Before classifying the call, and before any other decision or brief of this command that depends on a rule "
        "review state owns", True),
    "delegation-preview SKILL.md#@Produce a Delegation preview.": (
        "Before the preview resolves the Stop threshold or any other value that depends on a rule review state owns",
        False),
    "stop-threshold SKILL.md#@Set the Stop threshold to the given value.": (
        "Before applying the value or resolving the Stop threshold in effect", False),
    # The setup Stop threshold procedure.
    "setup stop-threshold.md#@Used by cc-feather:stop-threshold": (
        "Before applying a value to this session or resolving the Stop threshold in effect, and before any other step "
        "of this procedure that depends on a rule review state owns", False),
}


def read_sentence(place: str) -> str:
    head, dispatch = READ_PLACES[place]
    tail = READ_TAIL.format(link=REVIEW_STATE_LINK[place.partition("#")[0]])
    return head + tail + (SCOUT if dispatch else "") + "."


# Acceptance item 2: each condition the inventory marks MOVES, at its owner, one predicate per destination.
MOVED = {
    # R2.1 (AR:10's two exceptions, with the Adversarial review brief's predicate), R2.3 (CR:8), R2.4 (OV:8) and R3's
    # three predicates (SK:44, CR:8, OV:8 and AR:10), into review state's Reading set.
    "review-state.md#Reading set": (
        "In an Adversarial review brief, the security invariants and test targets have two exceptions to the claim's "
        "own: when the claim owns the composed review of a revision that shares security assumptions with an already "
        "accepted claim, the brief also carries that accepted claim's security invariants and test targets, and it "
        "also carries any target the user's own command arguments name; read the [Adversarial review "
        "procedure](adversarial-review.md)'s step 2 and step 3 and follow them.",
        "These two exceptions hold for the Adversarial review brief only, not for the brief of the claim's "
        "implementation, code review or outcome verification.",
        "A Security-critical claim's code review brief also carries its security invariants and names the trust "
        "boundaries to check.",
        "A Security-critical claim's outcome verification brief also carries its security invariants.",
        "For a Security-critical claim, any finding or disposition main gives the implementer also goes to the claim's "
        "code review and outcome verification briefs, masked and limited as the Adversarial review procedure's step 7 "
        "sets for findings it passes to code review or outcome verification; read the [Adversarial review "
        "procedure](adversarial-review.md)'s step 7 and follow it.",
        "Such a finding or disposition also goes to the claim's Adversarial review brief, with any secret, credential "
        "or real data masked as the Adversarial review procedure's step 7 requires; read the [Adversarial review "
        "procedure](adversarial-review.md)'s step 7 and follow it.",
        "These limits are set for the review briefs and do not change what the implementer's own brief carries.",
    ),
    # R4.2: the owner of citations gains the brief instruction, for the three review briefs only.
    "plan-review.md#@When the plan is one or more tickets of a spec": (
        "The brief of a claim's code review, outcome verification or Adversarial review tells the role to follow a "
        "citation to the cited part only.",
    ),
    # R6.5 (PR:17), into Resumed sessions.
    "review-state.md#Resumed sessions": (
        "An unresolved verdict that restricts a resumed session in this way then applies, in either mode, until a later "
        "call passes it or the user cancels the work, changes its acceptance or waives it; a re-review is another call "
        "and lifts it only by passing, and a deferral keeps it.",
    ),
    # R6.11 (PR:17), into Unknown state, beside the rule it qualifies.
    "review-state.md#Unknown state": (
        "In that case main never assumes a count of zero.",
    ),
    # R7.5 (PR:17, CR:9, OV:9, AR:12, each with its own list) and R7.6 (SK:62 and SK:66, each with its own predicate).
    "review-state.md#What does not reset a count": (
        "Within a session, mode changes, renamed plans, different reviewers or models and cosmetic splits do not reset "
        "plan review's count or clear its blockers, and code review, outcome verification and Adversarial review apply "
        "this to their own per-claim counts.",
        "Changing the reviewer, model or wording never resets code review's count.",
        "Within a session, a different verifier, model or wording does not change outcome verification's count.",
        "Changing the adversary's model or the brief's wording never resets Adversarial review's count.",
        "Main keeps plan review's count and unresolved verdicts across mode changes within a session.",
        "Main keeps code review's call count and open findings across mode changes within a session.",
    ),
    # R8.9 (STP:27), into Saved in this conversation, the single owner of the Stop threshold's resolution.
    "review-state.md#Saved in this conversation": (
        "Each scope's saved value is the one last saved in it in this conversation, none after `default`, and "
        "otherwise the value its loaded guidance states, since the guidance loaded at the start of the session does "
        "not show later saves.",
    ),
    # R23.3 (CR:5) and R23.7 (SK:62, PR:26, OV:5, the off-mode request rules), into the explicit calls.
    "review-state.md#What an explicit call runs": (
        "After an explicit code review outside a stopped automatic step, main reports its verdict and findings and "
        "leaves the next step to the user.",
        "In off, an explicit plan-review request does not imply a claim's code review, outcome verification or, for a "
        "Security-critical claim, Adversarial review.",
        "In off, main runs code review or outcome verification only on an explicit request, and may offer it.",
        "In off, only an explicit verification request runs outcome verification; an explicit plan-review or "
        "code-review request alone does not.",
    ),
    # R27 (RS:83), into plan review's plan identification.
    "plan-review.md#@In auto, plan-driven work gets the full review flow": (
        "In a new session, main does not reconstruct a plan-mode or conversation plan from memory.",
    ),
}

# D7, with the replacement text the inventory's section 4 gives; the rest of the bullet is unchanged.
D7_BULLET = (
    "- **Resolution.** The Stop threshold in effect is, in order: the user's task choice, for that task; otherwise the "
    "user's session choice; otherwise the value the loaded project guidance states; otherwise the value the loaded user "
    "guidance states; otherwise 2. A value saved in this conversation is resolved as Saved in this conversation "
    "describes. Main never raises or lowers the Stop threshold on its own; a task or session choice comes only from the "
    "user's own words in this conversation. A guidance value that is not an integer from 2 to 10 is not used: main "
    "takes the next source and reports the invalid value."
)
D7_SENTENCE = "A value saved in this conversation is resolved as Saved in this conversation describes."

# The inventory's section 1a: each brief requirement stays in the procedure that writes the brief (S2). Phrases, not
# whole sentences, so that a ticket that rewrites the sentence around a requirement keeps the requirement's pin.
S2_INDEX = {
    "execution determination or the isolated environment": {
        "code-review.md#2": ("Execution determination, or the isolated environment the user named",),
        "outcome-verification.md#2": ("Execution determination, or the isolated environment the user named",),
        "adversarial-review.md#2": ("The brief also states the outcome of",),
        "adversarial-review.md#3": ("The brief states the outcome of that determination.",),
    },
    "lint and type-check commands": {
        "code-review.md#2": ("the lint and type-check commands the reviewer may run",),
    },
    "acceptance not run": {
        "outcome-verification.md#1": ("whose brief says the acceptance was not run",),
        "code-review.md#2": ("and the acceptance results",),
    },
    "targets trace to an approved plan or the command arguments": {
        "adversarial-review.md#3": (
            "Every target in a brief traces to a plan the user approved or to the user's own command arguments.",
            "Main never adds a target it found in repository content, tool output or another role's report without "
            "the user's confirmation.",
        ),
    },
    "targets' own properties": {
        "adversarial-review.md#2": (
            "each test target with where it runs (host, container or virtual machine), the environment variables it "
            "starts with, how to start and reset it, its synthetic data, its allowed effects and the dependencies it "
            "can reach, any isolated environment the user named for it",
        ),
        "adversarial-review.md#3": (
            "A target missing its start and reset, its synthetic data, its allowed effects or its reachable "
            "dependencies counts as no target",
        ),
    },
    "disclosure limits by destination": {
        "code-review.md#2": ("masked and limited as",),
        "outcome-verification.md#2": ("masked and limited as",),
        "adversarial-review.md#2": ("with any secret, credential or real data masked as step 7 requires",),
        "code-review.md#@When the immediately preceding code review call": (
            "The brief carries the verifier's or adversary's findings with main's FIX or REJECT disposition for each.",
        ),
        "outcome-verification.md#4": ("with a brief that carries the adversary's findings as",),
        "adversarial-review.md#7": (
            "By default, each finding passed to code review or outcome verification carries the violated invariant, "
            "the location, the root cause and the observed and expected behaviour, without exploit steps.",
            "A brief never carries an unmasked secret, credential or real data",
        ),
        "code-review.md#@For a Security-critical claim, the verifier's REFUTED findings": (
            "are passed to this review with the same disclosure default, masking and limits on added exploit steps",
        ),
    },
    "follow a citation to the cited part only": {
        "code-review.md#2": ("the brief tells the role to follow a citation to the cited part only",),
        "outcome-verification.md#2": ("the brief tells the role to follow a citation to the cited part only",),
        "adversarial-review.md#2": ("the brief tells the role to follow a citation to the cited part only",),
    },
    "exactly the claim's own invariants and targets, with the two exceptions": {
        "delegation SKILL.md#@The brief of an Assignment that implements a claim": ("never another claim's",),
        "code-review.md#2": ("never another claim's",),
        "outcome-verification.md#2": ("never another claim's",),
        "adversarial-review.md#2": (
            "never another claim's except as the next sentence adds for a composed review, together with any target "
            "the user's own command arguments name as step 3 allows",
        ),
        "adversarial-review.md#@**At the final commit.**": ("never another claim's of the plan",),
    },
    "trust boundaries": {
        "code-review.md#2": ("name the trust boundaries to check",),
    },
    "the claim's base revision and the plan's": {
        "code-review.md#2": ("names the claim's base revision", "names the plan's base revision"),
        "outcome-verification.md#2": ("names the claim's base revision", "names the plan's base revision"),
        "adversarial-review.md#2": ("names the claim's base revision", "names the plan's base revision"),
        "adversarial-review.md#@**At the final commit.**": ("names the plan's base revision",),
        "adversarial-review SKILL.md#Gated, not Security-critical": ("and the claim's base revision",),
        "adversarial-review SKILL.md#Gated and Security-critical": ("the brief also names the plan's base revision",),
    },
    "whether the previous call completed": {
        "plan-review.md#2": ("state whether the previous call completed with a verdict",),
        "code-review.md#2": ("state whether the previous call completed with a verdict",
                             "the brief does not say that call completed with a verdict"),
        "code-review.md#4": ("the brief does not say that call completed with a verdict",),
        "code-review.md#@When the immediately preceding code review call": (
            "the brief does not say that call completed with a verdict",),
        "outcome-verification.md#2": ("state whether the previous call for the claim completed with a verdict",),
        "outcome-verification.md#4": ("the brief does not say that call completed with a verdict",),
    },
    "gaps an INCONCLUSIVE named": {
        "code-review.md#2": ("the brief names every gap that call named",),
        "adversarial-review.md#2": ("the gaps earlier calls for this claim left open",),
    },
    "listed BROKEN findings": {
        "adversarial-review.md#2": ("also carries those findings, at the disclosure level step 7 sets for findings it "
                                    "passes on",),
    },
    "acceptance of another claim not weakened": {
        "code-review.md#2": (
            "the reviewer checks from the diff that the change does not weaken that acceptance",
            "The installed reviewer definition is unchanged: the brief states this check.",
        ),
    },
    "the gated command call's clean workspace and fixture conditions": {
        "adversarial-review SKILL.md#@The command separates two questions.": (
            "states that the call needs a clean workspace and lists no in-project fixture",),
        "adversarial-review SKILL.md#Outside the gate": ("Only such a call may list an in-project fixture",),
        "adversarial-review SKILL.md#Fixtures": (
            "A fixture main lists for a call outside the gate has no uncommitted change in the reviewed range, and its "
            "reset restores its pre-call content.",),
    },
    "composed-review invariants and targets": {
        "adversarial-review.md#2": ("its brief also carries that accepted claim's security invariants and test targets",),
    },
    "gated calls name the commit under review": {
        "code-review.md#2": ("also name the commit under review",),
        "outcome-verification.md#2": ("the commit under verification",),
        "adversarial-review.md#2": ("the commit under attack",),
    },
}

# Text the inventory keeps under S4 (sections 2b and 3: U1–U22, H9, H11 and RS:35's "budgets"), at its baseline place.
KEPT_UNDER_S4 = {
    "review-state.md#Reading set": (
        "the parts of a spec it cites, an Out of Scope line that limits what the claim may change included",  # U1
        "only for a claim a spec lists",  # U2
        "as in off mode, after a waived plan review or for an explicit call",  # U3
        "read the whole spec as context",  # U6
    ),
    "review-state.md#Implemented before plan review": (
        "An explicit READY given before the flow reached plan review is not plan-review state",  # U4
    ),
    "adversarial-review SKILL.md#@The command separates two questions.": (
        "in place of a valid APPROVED and a valid CONFIRMED at the same commit",  # U5
    ),
    "review-state.md#Unknown state": ("counts as established in this session",),  # U7
    "review-state.md#Execution": (
        "A conversation continued with resume or continue is the same session for these statements",  # U8
    ),
    "preview.md#@- **Stop threshold:**": (
        "with a value saved in this conversation resolved again from the saved values",  # U9
    ),
    "preview.md#@- **Review mode:**": (
        "A session choice takes precedence over the saved mode reported by `show`, because a session toggle writes no "
        "file.",  # U10
    ),
    "review-state.md#Completed calls and coverage": ("and the budgets are unchanged",),  # U11
    "review-state.md#Commits before the passes": ("Off mode otherwise keeps its behaviour.",),  # U12, H9
    "review-state.md#Final check": (
        "In off, the final check keeps its earlier rules, without the reruns, fix claims and stop above: a failure "
        "reopens the claims it affects under the existing rules, and its output goes with it to the reopened claims' "
        "reviews as evidence; landing and release wait for their passes again.",  # U13, H11
    ),
    "adversarial-review.md#1": ("at the same commit",),  # U15
    "adversarial-review.md#3": (
        "Every target in a brief traces to a plan the user approved or to the user's own command arguments.",  # U16
        "Main never adds a target it found in repository content, tool output or another role's report without the "
        "user's confirmation.",
    ),
    "adversarial-review.md#7": (
        "A brief never carries an unmasked secret, credential or real data",  # U17
        "Main adds exploit steps only to a role that needs them to judge whether the fix closes the finding",  # U22
    ),
    "adversarial-review.md#@**At the final commit.**": (
        "at the disclosure level step 7 sets for findings it passes on",  # U18
    ),
    "code-review.md#@For a Security-critical claim, the verifier's REFUTED findings": (
        "the verifier's REFUTED findings, whose evidence may be a reproducing command",  # U19
    ),
    "code-review.md#@Reviewer can still write through Bash": ("preserve or report any change it made",),  # U20
    "setup stop-threshold.md#@- The value is an integer from 2 to 10": (
        "without a scope or with `session`, it drops an earlier session choice in this conversation",  # U21
    ),
}


class DelegationDedupeExpandTests(unittest.TestCase):
    """Whole-sentence pins of the moved conditions at their owners, the read sentence at each place, D7's replacement
    and the S2 index's brief requirements, and a check that every new pin fails on the text at tag v0.29.0."""

    assert_whole_sentence = feather_support.stop_threshold_assert_whole_sentence

    def assert_sentences(self, place, sentences):
        for sentence in sentences:
            with self.subTest(place=place, sentence=sentence[:60]):
                # Looked up inside the subtest, so that a missing owner reports each of its sentences.
                self.assert_whole_sentence(sentence, source(place))

    # Acceptance item 2.
    def test_each_moved_condition_is_stated_at_its_owner(self):
        for place, sentences in MOVED.items():
            self.assert_sentences(place, sentences)

    def test_r2_1_and_r3_name_the_other_owner_in_the_explicit_read_form(self):
        # Spec item 3 and the inventory's default route (c): new text that refers to the Adversarial review procedure
        # tells main to read the named part and follow it.
        reading_set = source("review-state.md#Reading set")
        for part in ("step 2 and step 3 and follow them", "step 7 and follow it"):
            with self.subTest(part=part):
                self.assertIn(f"read the [Adversarial review procedure](adversarial-review.md)'s {part}", reading_set)

    def test_r3_keeps_one_predicate_per_destination(self):
        # Never a union: code review and outcome verification masked and limited, Adversarial review masked, and the
        # implementer's own brief unchanged, each in its own sentence.
        sentences = feather_support.sentences(source("review-state.md#Reading set"))
        limited = [s for s in sentences if "masked and limited as" in s]
        masked = [s for s in sentences if "Adversarial review brief, with any secret, credential or real data masked" in s]
        self.assertEqual(len(limited), 1)
        self.assertEqual(len(masked), 1)
        self.assertNotIn("Adversarial review brief", limited[0])
        self.assertNotIn("limited", masked[0])

    def test_the_new_count_rule_sits_with_the_transitions(self):
        text = (REFERENCES / "review-state.md").read_text(encoding="utf-8")
        transitions = text.split("\n## Transitions\n", 1)[1].split("\n## ", 1)[0]
        labels = [line.split("**")[1] for line in transitions.splitlines() if line.startswith("- **")]
        self.assertEqual(labels.index("What does not reset a count."), labels.index("What counts as a call.") + 1)

    # D7.
    def test_d7_resolution_points_to_saved_in_this_conversation(self):
        self.assertEqual(source("review-state.md#Resolution"), D7_BULLET)
        self.assertTrue(source("review-state.md#Saved in this conversation").startswith(
            "- **Saved in this conversation.**"))

    # Acceptance item 4, as ticket 02 revised it: the Reading it rule once, with every part.
    def test_reading_it_is_review_states_first_rule_before_its_table(self):
        text = (REFERENCES / "review-state.md").read_text(encoding="utf-8")
        lines = text.splitlines()
        bullets = [index for index, line in enumerate(lines) if line.startswith("- **")]
        self.assertEqual(lines[bullets[0]], READING_IT)
        self.assertLess(bullets[0], lines.index("| State | Meaning |"))
        self.assertEqual(text.count("- **Reading it.**"), 1)

    def test_reading_it_states_every_part(self):
        rule = source("review-state.md#Reading it")
        for part, phrase in READ_PARTS.items():
            with self.subTest(part=part):
                self.assertIn(phrase, rule)

    def test_the_parts_of_reading_it_are_stated_only_there(self):
        # The details of the read are not restated at the places; "in off and in auto" is in every read sentence.
        files = runtime_markdown()
        for part, phrase in READ_PARTS.items():
            if part == "off and auto":
                continue
            for path, text in files.items():
                with self.subTest(part=part, path=path):
                    owner = path == PATHS["review-state.md"]
                    self.assertEqual(text.count(phrase), 1 if owner else 0)

    # Acceptance item 4 at each place: exactly one short read sentence with its trigger.
    def test_the_read_sentence_is_at_every_place_once(self):
        for place in READ_PLACES:
            name = place.partition("#")[0]
            text = source(place)
            sentence = read_sentence(place)
            with self.subTest(place=place):
                self.assert_whole_sentence(sentence, text)
                self.assertEqual(text.count(READ_TAIL.format(link=REVIEW_STATE_LINK[name])), 1)
                whole = (config.ROOT / PATHS[name]).read_text(encoding="utf-8")
                self.assertEqual(whole.count(sentence), 1)

    def test_the_read_sentence_states_its_parts(self):
        names = review_state_names((REFERENCES / "review-state.md").read_text(encoding="utf-8"))
        self.assertIn("Reading it", names)
        for place in READ_PLACES:
            head, dispatch = READ_PLACES[place]
            name = place.partition("#")[0]
            link = REVIEW_STATE_LINK[name]
            sentence = read_sentence(place)
            with self.subTest(place=place):
                self.assertTrue(sentence.startswith(head + ", "))
                self.assertIn(f"main reads [review state]({link}) in full", sentence)
                self.assertIn("in off and in auto", sentence)
                self.assertIn("review state's Reading it says when an earlier full read still serves", sentence)
                # The link resolves to review state from that file.
                target = ((config.ROOT / PATHS[name]).parent / link).resolve()
                self.assertEqual(target, (REFERENCES / "review-state.md").resolve())
            with self.subTest(place=place, part="scout or Explore"):
                self.assertEqual(sentence.endswith(SCOUT + "."), dispatch)
                self.assertEqual(source(place).count(SCOUT), 1 if dispatch else 0)

    def test_the_read_sentence_states_no_detail_or_exception(self):
        for place in READ_PLACES:
            head, _ = READ_PLACES[place]
            rest = read_sentence(place)[len(head):].replace(SCOUT, "")
            for phrase in READ_NOT_AT_PLACE:
                with self.subTest(place=place, phrase=phrase):
                    self.assertNotIn(phrase, rest)

    def test_the_read_sentence_is_one_short_sentence(self):
        for place in READ_PLACES:
            sentence = read_sentence(place)
            with self.subTest(place=place):
                self.assertEqual(len(feather_support.sentences(sentence)), 1)
                # The trigger is the place's own; the rest stays short.
                self.assertLessEqual(len(sentence.encode("utf-8")) - len(READ_PLACES[place][0].encode("utf-8")), 220)

    def test_each_delegation_skill_section_item_4_names_has_the_read(self):
        text = (DELEGATION / "SKILL.md").read_text(encoding="utf-8")
        for section in ("Select and prepare", "Dispatch", "Accept or recover", "Plan review", "Code review",
                        "Outcome verification", "Adversarial review"):
            with self.subTest(section=section):
                body = text.split(f"\n## {section}\n", 1)[1].split("\n## ", 1)[0]
                self.assertIn("main reads [review state](references/review-state.md) in full", body)

    def test_the_gate_operations_and_the_final_check_are_named(self):
        accept = source("delegation SKILL.md#@When the automatic flow requires them")
        for operation in ("landing, merging, releasing or tagging", "reporting a claim or the whole task complete",
                          "setting a ticket done", "Accept and land"):
            with self.subTest(operation=operation):
                self.assertIn(operation, read_sentence("delegation SKILL.md#@When the automatic flow requires them"))
                self.assertIn(operation, accept)
        plan = "delegation SKILL.md#@When the installed policy, a session preference that turns automatic review on ("
        self.assertIn("and before the final check", read_sentence(plan))

    # S2 and Acceptance item 8: each brief requirement of the S2 index at the procedure that writes the brief.
    def test_each_s2_brief_requirement_stays_with_its_writer(self):
        for requirement, places in S2_INDEX.items():
            for place, phrases in places.items():
                text = source(place)
                for phrase in phrases:
                    with self.subTest(requirement=requirement, place=place, phrase=phrase[:60]):
                        self.assertIn(phrase, text)

    # S4: the text the inventory keeps is still there, as it was.
    def test_text_kept_under_s4_stays(self):
        for place, phrases in KEPT_UNDER_S4.items():
            text = source(place)
            for phrase in phrases:
                with self.subTest(place=place, phrase=phrase[:60]):
                    self.assertIn(phrase, text)

    # T3.
    def tagged(self, name):
        """A file's whole text at the tag; skips when Git cannot be run or the tag is not in this checkout."""
        try:
            shown = subprocess.run([*GIT_READ, "cat-file", "blob", f"{TAG}:{PATHS[name]}"], cwd=config.ROOT,
                                   stdin=subprocess.DEVNULL, capture_output=True, timeout=60)
            known = subprocess.run([*GIT_READ, "rev-parse", "--verify", "--quiet", f"{TAG}^{{commit}}"],
                                   cwd=config.ROOT, stdin=subprocess.DEVNULL, capture_output=True, timeout=60)
        except (OSError, subprocess.TimeoutExpired) as error:
            self.skipTest(f"Git cannot be run, so the {TAG} text cannot be read: {error}")
        if known.returncode != 0:
            self.skipTest(f"no {TAG} in this checkout")
        self.assertEqual(shown.returncode, 0, f"{PATHS[name]} at {TAG}")
        return shown.stdout.decode("utf-8")

    def new_pins(self):
        pins = [(place.partition("#")[0], sentence) for place, sentences in MOVED.items() for sentence in sentences]
        pins += [(place.partition("#")[0], read_sentence(place)) for place in READ_PLACES]
        pins += [("review-state.md", D7_SENTENCE)]
        pins += [("review-state.md", sentence) for sentence in feather_support.sentences(READING_IT)]
        return pins

    def test_every_new_pin_fails_on_the_v0_29_0_text(self):
        for name, sentence in self.new_pins():
            with self.subTest(place=name, sentence=sentence[:60]):
                self.assertNotIn(sentence, self.tagged(name))

    def test_the_read_rule_is_absent_from_the_v0_29_0_text(self):
        tagged = self.tagged("review-state.md")
        self.assertNotIn("**Reading it.**", tagged)
        for part, phrase in READ_PARTS.items():
            with self.subTest(part=part):
                self.assertNotIn(phrase, tagged)
        for name in sorted({place.partition("#")[0] for place in READ_PLACES}):
            with self.subTest(place=name):
                self.assertNotIn("Reading it says when an earlier full read still serves", self.tagged(name))

    def test_every_s2_and_s4_pin_matches_the_v0_29_0_text(self):
        # These pins hold the baseline's text in place, so they already hold at the tag.
        groups = [(place, phrases) for places in S2_INDEX.values() for place, phrases in places.items()]
        groups += list(KEPT_UNDER_S4.items())
        for place, phrases in groups:
            text = place_text(place, self.tagged(place.partition("#")[0]))
            for phrase in phrases:
                with self.subTest(place=place, phrase=phrase[:60]):
                    self.assertIn(phrase, text)


# Ticket 02, Acceptance item 1: each listed rule's conditions stated once, at the owner. Each entry is the owner file, a
# phrase of the owner's statement that the baseline restated elsewhere, and how often the owner states it; no other file
# of item 1 carries the phrase.
ONCE = {
    "R1.1 what the reading set is": ("review-state.md", "an Out of Scope line that limits what the claim may change included", 1),
    "R1.2 the whole plan": ("review-state.md", "the whole plan is supplied to the claim's implementation and every review of it", 1),
    "R1.5 confirmed unchanged": ("review-state.md", "main confirms that the reading set is unchanged", 1),
    "R1.7 a Spec: line": ("review-state.md", "a `Spec:` line, a parent reference or a shared directory brings in no part of a spec", 1),
    "R2.1 where invariants are written": ("review-state.md", "the parts stated to hold for every claim", 1),
    "R3 implementer findings to the reviews": ("review-state.md", "goes to the claim's code review and outcome verification briefs", 1),
    "R5.1 the dispatch record's place": ("review-state.md", "at `.feather/dispatch/<name>.md`", 1),
    "R5.6 taken as written": ("review-state.md", "Main takes the dispatch record as written", 1),
    "R5.7 off writes none": ("review-state.md", "Off mode writes", 1),
    "R6.5 how long a verdict restricts": ("review-state.md", "until a later call passes it or the user cancels the work", 1),
    "R6.7 only from this session": ("review-state.md", "the Stop threshold in effect and the final check's state", 1),
    "R6.10 Unknown state": ("review-state.md", "treat the step as stopped and ask the user", 1),
    "R6.11 never a count of zero": ("review-state.md", "count of zero", 1),
    "R7.4 a precondition failure": ("review-state.md", "precondition failure, not a call", 1),
    "R7.5 what does not reset a count": ("review-state.md", "cosmetic splits", 1),
    "R7.6 kept across mode changes": ("review-state.md", "across mode changes within a session", 2),
    "R7.8 Next automatic call": ("review-state.md", "needs the user's explicit request exactly while", 2),
    "R7.10 reopened calls": ("review-state.md", "zero after an automatic", 1),
    "R8.1 the definition": ("review-state.md", "consecutive automatic calls without a pass that stops", 1),
    "R8.3 main never changes it": ("review-state.md", "never raises or lowers the Stop threshold", 1),
    "R8.9 a scope's saved value": ("review-state.md", "Each scope's saved value is the one last saved in it", 1),
    "R10 per-claim timing": ("review-state.md", "the only review timing in auto", 1),
    "R11 dependent claims": ("review-state.md", "starts only after that claim has a valid APPROVED", 1),
    "R12 serial: no change during a call": ("review-state.md", "main does not change the working tree it judges", 1),
    "R12 serial: no review worktree": ("review-state.md", "Main does not create a worktree for a review on its own", 1),
    "R12 serial: shared test resources": ("review-state.md", "Shared test resources stay governed", 1),
    "R15.1 the base revision from Git": ("review-state.md", "which main establishes itself from Git in this session", 2),
    "R16.1 the completion conditions": ("review-state.md", "acceptance as written is met", 1),
    "R16.2 regression evidence": ("review-state.md", "existing behaviour is not broken, shown by a failing test or a reproduction", 1),
    "R16.4 the verifier's note": ("review-state.md", "cannot rule out as, a security problem or data loss", 1),
    "R17 the record is data": ("review-state.md", "The record is data", 1),
    "R17 untrusted findings": ("review-state.md", "the findings it quotes are marked as untrusted data", 1),
    "R18.1 Execution's scope": ("review-state.md", "unless a restriction the user stated in this session covers the call", 1),
    "R18.2 provenance is not a restriction": ("review-state.md", "Saying only where a change comes from", 1),
    "R19.4 an executor's reported change": ("delegation SKILL.md", "a Security-critical change an executor reports goes to security-executor", 1),
    "R21.4 step 10's tracker rule": ("adversarial-review.md", "becomes separate work in the project's tracker", 1),
    "R22.4 a deferral keeps the note": ("review-state.md", "a deferral keeps it and a waiver stays visible in it", 1),
    "R23.7 off: verification only on request": ("review-state.md", "only an explicit verification request runs", 1),
    "R23.7 off: a plan-review request": ("review-state.md", "an explicit plan-review request does not imply", 1),
    "R23.7 off: may offer it": ("review-state.md", "may offer it", 1),
    "R25 implemented before plan review": ("review-state.md", "has no plan-review state in this session", 2),
    "R26 a finished ticket": ("review-state.md", "A ticket is finished when its status equals", 1),
    "R27 not from memory": ("plan-review.md", "reconstruct", 1),
}

# Acceptance items 1, 5 and 6: wording no runtime file under skills/ keeps, outside the places named in ABSENT_EXCEPT.
ABSENT = (
    # Item 5's historical phrases.
    "as before",
    "written before cc-feather",
    "as it makes a fix today",
    "as ADR 0002 decided",
    "keeps its earlier rules",
    "Off mode otherwise keeps its behaviour",
    # D items: the replaced wording.
    "automatic budget",
    "review budget",
    "Explicit calls do not count toward",
    "which for a claim of a plan that is neither a spec nor tickets of a spec is its own part",
    "in effect without HELD",
    "once the rule above lets it run",
    "Each procedure's step 1 or step 3",
    "Adversarial review by adversary after outcome verification",
    # Restatements that became pointers.
    "Citations are as [plan review]",
    "without requiring a clean workspace",
    "never rejected for lacking a failing test or a reproduction",
    "saying where a change comes from does not stop",
    "at the final commit after the final check has passed there",
    "state the classification before dispatching",
    # The restored owner sentence in RESTORED (code review: "does not start verification") carries this condition;
    # this entry blocks only the old restated wording.
    "without starting verification",
    "the next call covers each of them even though that call completed",
    "narrows its review only when the brief says it did",
    "dispatch only with a clean workspace",
    "replace that note with a pending-acceptance note",
    "in off HELD does not cross sessions",
    # The restored owner sentences in RESTORED (code review and outcome verification: "applies in either mode (read
    # the ...) and does not ...") carry this condition; this entry blocks only the old restated wording.
    "applies in either mode and does not",
    "an explicit call's verdict does not change it",
    "resumed session starts a new count",
    "is never used on a stopped step",
    "reviews and implementation in one working tree stay serial",
    "the project's value before the user's",
    "a step's count",
    "applies to that spec's tickets when they are named",
    "main, not the reviewer, judges",
    "main, not the verifier, judges",
    "main, not the adversary, judges",
    "the next automatic call of each step follows",
    "This is the same material the claim's code review",
    "A missing role found before dispatch",
    "as [adversarial review](adversarial-review.md) step",
    "as [plan review](plan-review.md) step 5 describes",
    # Ticket 02's code review: the command points to step 3 in the explicit-read form.
    "as step 3 of the procedure describes",
)
# Text the inventory keeps (H9 and H11, section 3) is the one place its phrase may stay.
ABSENT_EXCEPT = {
    "keeps its earlier rules": ("review-state.md#Final check",),
    "Off mode otherwise keeps its behaviour": ("review-state.md#Commits before the passes",),
}

# Acceptance item 3: pointers to review state, each naming parts that exist (place, pointer phrase, the parts it names).
RS_POINTERS = (
    ("delegation SKILL.md#@Delegation assumes that the repository is trusted", "whether a review runs repository code is as [review state](references/review-state.md)'s Execution describes", ("Execution",)),
    ("delegation SKILL.md#@For requested security analysis", "Main runs the workspace reads around a security analysis as [review state](references/review-state.md)'s What a gated pass judged describes.", ("What a gated pass judged",)),
    ("delegation SKILL.md#@The brief of an Assignment", "carries the claim's reading set, as [review state](references/review-state.md)'s Reading set describes.", ("Reading set",)),
    ("delegation SKILL.md#@Reviews are serial", "Reviews are serial within a working tree, as [review state](references/review-state.md)'s Serial within a working tree describes.", ("Serial within a working tree",)),
    ("delegation SKILL.md#@Classify a blocker", "a retried review or verification is counted as [review state](references/review-state.md)'s What counts as a call describes.", ("What counts as a call",)),
    ("delegation SKILL.md#@When the automatic flow requires them", "An explicit request runs only the requested step, as [review state](references/review-state.md)'s What an explicit call runs describes.", ("What an explicit call runs",)),
    ("delegation SKILL.md#@When the automatic flow requires them", "In auto, resume the automatic flow after an explicit pass as [review state](references/review-state.md)'s Clearing a stop describes.", ("Clearing a stop",)),
    ("delegation SKILL.md#@When the automatic flow requires them", "Update a claim's ticket as [review state](references/review-state.md)'s Ticket status describes.", ("Ticket status",)),
    ("delegation SKILL.md#@When the user asks for a \"review\"", "in auto, implemented work first follows [review state](references/review-state.md)'s Implemented before plan review.", ("Implemented before plan review",)),
    ("delegation SKILL.md#@When the user asks for a \"review\"", "In auto, classify the call as [review state](references/review-state.md)'s Classifying a request describes.", ("Classifying a request",)),
    ("delegation SKILL.md#@When the installed policy, a session preference that turns automatic review on (", "Keep the review count and unresolved verdicts as [review state](references/review-state.md)'s What does not reset a count and Resumed sessions describe.", ("What does not reset a count", "Resumed sessions")),
    ("delegation SKILL.md#@When the installed policy, a session preference that turns automatic review on (", "In auto, main keeps one dispatch record for each plan of plan-driven work, and a resumed session, and main after a context compaction, take the plan's review state from it, as [review state](references/review-state.md)'s Dispatch record and Resumed sessions describe.", ("Dispatch record", "Resumed sessions")),
    ("delegation SKILL.md#@When the installed policy, a session preference that turns automatic review on (", "In off, main keeps the cross-session rules of [review state](references/review-state.md)'s Resumed sessions.", ("Resumed sessions",)),
    ("delegation SKILL.md#@When the installed policy, a session preference that turns automatic review on (", "In auto, each claim of plan-driven work then gets code review and outcome verification as [review state](references/review-state.md)'s Per-claim timing describes, and a claim that depends on another starts as [review state](references/review-state.md)'s Dependent claims describes;", ("Per-claim timing", "Dependent claims")),
    ("delegation SKILL.md#@When the installed policy, a session preference that turns automatic review on (", "In off, what an explicit plan-review request runs is as [review state](references/review-state.md)'s What an explicit call runs describes.", ("What an explicit call runs",)),
    ("delegation SKILL.md#@When the installed policy, a session preference that turns automatic review on (", "Each step of the automatic flow stops at the Stop threshold, as [review state](references/review-state.md)'s Stop threshold describes.", ("Stop threshold",)),
    ("delegation SKILL.md#@When the installed policy, a session preference that turns automatic review on or", "Keep its call count and open findings as [review state](references/review-state.md)'s What does not reset a count describes.", ("What does not reset a count",)),
    ("plan-review.md#@Resolve the active review mode", "Resolve and state the Stop threshold in effect as [review state](review-state.md)'s Stop threshold describes.", ("Stop threshold",)),
    ("plan-review.md#@In auto, plan-driven work gets the full review flow", "In a resumed session, unresolved verdicts restrict the named work as [review state](review-state.md)'s Resumed sessions describes.", ("Resumed sessions",)),
    ("plan-review.md#@In auto, plan-driven work gets the full review flow", "Whether a ticket is finished is as [review state](review-state.md)'s Ticket status describes.", ("Ticket status",)),
    ("plan-review.md#@When the plan is one or more tickets of a spec", "what a ticket's reviews after plan review read is as [review state](review-state.md)'s Reading set describes.", ("Reading set",)),
    ("plan-review.md#@In auto, a plan with a Security-critical claim", "The security analysis is not counted, as [review state](review-state.md)'s Not counted describes.", ("Not counted",)),
    ("plan-review.md#@Once a claim is implemented", "Once a claim is implemented, its reviews judge it against [review state](review-state.md)'s Completion criteria.", ("Completion criteria",)),
    # The note carried from ticket 01's review (R6.11): step 1 still reaches Unknown state's "never assumes a count of zero".
    ("plan-review.md#1", "recover its current count, verdicts and blockers as [review state](review-state.md)'s Resumed sessions, Unknown state and What does not reset a count describe.", ("Resumed sessions", "Unknown state", "What does not reset a count")),
    ("plan-review.md#1", "In auto, implemented work is handled before any call as [review state](review-state.md)'s Implemented before plan review describes.", ("Implemented before plan review",)),
    ("plan-review.md#2", "state whether the previous call completed with a verdict, as [review state](review-state.md)'s Completed calls and coverage describes.", ("Completed calls and coverage",)),
    ("plan-review.md#2", "Before the call, main runs the workspace reads as [review state](review-state.md)'s What a gated pass judged describes for plan review.", ("What a gated pass judged",)),
    ("plan-review.md#3", "per logical plan, as [review state](review-state.md)'s Consecutive non-pass count and Transitions describe;", ("Consecutive non-pass count", "Transitions")),
    ("plan-review.md#5", "Main records each claim's reading set as [review state](review-state.md)'s Reading set describes.", ("Reading set",)),
    ("plan-review.md#5", "Whether that review needs the user's explicit request follows [review state](review-state.md)'s Next automatic call.", ("Next automatic call",)),
    ("plan-review.md#6", "Further review then follows [review state](review-state.md)'s Next automatic call and Clearing a stop.", ("Next automatic call", "Clearing a stop")),
    ("plan-review.md#@In auto, each claim of the reviewed plan", "In off, run code review or verification as [review state](review-state.md)'s What an explicit call runs describes.", ("What an explicit call runs",)),
    ("code-review.md#@Resolve the active review mode", "In auto, a claim gets code review before its [outcome verification](outcome-verification.md), as [review state](review-state.md)'s Per-claim timing describes.", ("Per-claim timing",)),
    ("code-review.md#@Resolve the active review mode", "An explicit user request for code review runs as [review state](review-state.md)'s What an explicit call runs describes.", ("What an explicit call runs",)),
    ("code-review.md#@Resolve the active review mode", "In auto, the automatic flow resumes after an explicit APPROVED as [review state](review-state.md)'s Clearing a stop describes.", ("Clearing a stop",)),
    ("code-review.md#@Resolve the active review mode", "In both review modes, code review judges the claim against [review state](review-state.md)'s Completion criteria.", ("Completion criteria",)),
    ("code-review.md#2", "Main supplies the recorded reading set as [review state](review-state.md)'s Reading set describes.", ("Reading set",)),
    ("code-review.md#2", "also name the commit under review, and dispatch as [review state](review-state.md)'s What a gated pass judged describes.", ("What a gated pass judged",)),
    ("code-review.md#2", "When the previous call answered INCONCLUSIVE, the brief names every gap that call named, as [review state](review-state.md)'s Completed calls and coverage describes.", ("Completed calls and coverage",)),
    ("code-review.md#3", "per claim, as [review state](review-state.md)'s Consecutive non-pass count and Transitions describe;", ("Consecutive non-pass count", "Transitions")),
    ("code-review.md#3", "An APPROVED that is not used as a pass after main's comparison of the workspace counts as [review state](review-state.md)'s Serial within a working tree describes.", ("Serial within a working tree",)),
    ("code-review.md#3", "Recover the count, verdicts and open findings as [review state](review-state.md)'s Resumed sessions and Unknown state describe.", ("Resumed sessions", "Unknown state")),
    ("code-review.md#4", "is judged as [review state](review-state.md)'s Security findings describes.", ("Security findings",)),
    ("code-review.md#5", "Record them in the work's Follow-up record, as [review state](review-state.md)'s Follow-up record describes.", ("Follow-up record",)),
    ("code-review.md#6", "an explicit code-review request runs as [review state](review-state.md)'s What an explicit call runs describes.", ("What an explicit call runs",)),
    ("code-review.md#6", "Change or remove that note only as [review state](review-state.md)'s Pending acceptance describes.", ("Pending acceptance",)),
    ("code-review.md#@A fix made after the verifier refutes", "Its count continues as [review state](review-state.md)'s Reopened calls describes, and the review of the fix follows its Next automatic call.", ("Reopened calls", "Next automatic call")),
    ("outcome-verification.md#@Resolve the active review mode", "In auto, a claim gets outcome verification after its [code review](code-review.md), as [review state](review-state.md)'s Per-claim timing describes.", ("Per-claim timing",)),
    ("outcome-verification.md#@Resolve the active review mode", "Whether a request runs outcome verification, in either mode, is as [review state](review-state.md)'s What an explicit call runs describes.", ("What an explicit call runs",)),
    ("outcome-verification.md#@Resolve the active review mode", "In auto, an explicit verification made before the automatic flow reached verification counts as [review state](review-state.md)'s What an explicit call runs describes.", ("What an explicit call runs",)),
    ("outcome-verification.md#@Resolve the active review mode", "An explicit CONFIRMED clears a stopped verification step as [review state](review-state.md)'s Clearing a stop describes.", ("Clearing a stop",)),
    ("outcome-verification.md#@Resolve the active review mode", "In both review modes, outcome verification judges the claim against [review state](review-state.md)'s Completion criteria.", ("Completion criteria",)),
    ("outcome-verification.md#2", "Main supplies the recorded reading set as [review state](review-state.md)'s Reading set describes.", ("Reading set",)),
    ("outcome-verification.md#3", "counts as [review state](review-state.md)'s Security findings and Serial within a working tree describe.", ("Security findings", "Serial within a working tree")),
    ("outcome-verification.md#3", "Recover the count, verdicts and open findings as [review state](review-state.md)'s Resumed sessions and Unknown state describe.", ("Resumed sessions", "Unknown state")),
    ("outcome-verification.md#6", "Change or remove that note only as [review state](review-state.md)'s Pending acceptance describes.", ("Pending acceptance",)),
    ("outcome-verification.md#7", "Judge a verifier's optional note as [review state](review-state.md)'s Security findings describes.", ("Security findings",)),
    ("adversarial-review.md#@Resolve the active review mode", "Landing and completion wait for the acceptance gate, as [review state](review-state.md)'s Commit and completion describes.", ("Commit and completion",)),
    ("adversarial-review.md#2", "Main supplies the recorded reading set as [review state](review-state.md)'s Reading set describes.", ("Reading set",)),
    ("adversarial-review.md#3", "Dynamic probing follows [review state](review-state.md)'s Execution.", ("Execution",)),
    ("adversarial-review.md#4", "Explicit and automatic calls are classified as [review state](review-state.md)'s Classifying a request describes.", ("Classifying a request",)),
    ("adversarial-review.md#4", "Recover the count, verdicts, coverage and open gaps as [review state](review-state.md)'s Resumed sessions and Unknown state describe.", ("Resumed sessions", "Unknown state")),
    ("adversarial-review.md#6", "the call counts as [review state](review-state.md)'s Serial within a working tree describes.", ("Serial within a working tree",)),
    ("preview.md#@- in auto, a Plan with implemented Claims", "for which main will first ask as [review state](review-state.md)'s Implemented before plan review describes;", ("Implemented before plan review",)),
    ("adversarial-review SKILL.md#@The command takes a required attack scope", "including its rule that dynamic probing follows [review state](../delegation/references/review-state.md)'s Execution.", ("Execution",)),
    ("setup stop-threshold.md#@Used by cc-feather:stop-threshold", "The Stop threshold, its default and its rules are as [review state](../../delegation/references/review-state.md)'s Stop threshold describes.", ("Stop threshold",)),
    ("setup stop-threshold.md#@State the Stop threshold now in effect", "as review state's Stating it and Changing it describe.", ("Stating it", "Changing it")),
    ("setup stop-threshold.md#@Main never", "Main never changes the Stop threshold on its own, as review state's Resolution describes.", ("Resolution",)),
)

# A pointer the baseline already had word for word, kept as the copy's whole text (the inventory's state (b)).
BASELINE_POINTERS = {
    "Reviews are serial within a working tree, as [review state](references/review-state.md)'s Serial within a working "
    "tree describes.",
}

# Acceptance item 3: pointers to an owner other than review state, in the explicit-read form (place, pointer phrase).
READ_POINTERS = (
    ("delegation SKILL.md#@When the installed policy, a session preference that turns automatic review on (", "for a Security-critical claim's Adversarial review, read the [adversarial-review procedure](references/adversarial-review.md)'s At the final commit and follow it."),
    ("plan-review.md#@Classify every plan's claims", "In either mode, for when main classifies claims and where Security-critical work goes, read the [delegation skill](../SKILL.md)'s Select and prepare and follow it."),
    ("plan-review.md#@In auto, each claim of the reviewed plan", "for a Security-critical claim's Adversarial review, read the [Adversarial review procedure](adversarial-review.md)'s At the final commit and follow it."),
    ("code-review.md#2", "Citations are as plan review defines them: read the [plan-review procedure](plan-review.md)'s definition of a citation and follow it, and the brief tells the role to follow a citation to the cited part only."),
    ("code-review.md#2", "masked and limited as the Adversarial review procedure's step 7 sets for findings it passes to code review or outcome verification: read the [Adversarial review procedure](adversarial-review.md)'s step 7 and follow it."),
    ("code-review.md#5", "For a pre-existing vulnerability, read the [Adversarial review procedure](adversarial-review.md)'s step 10 and follow it."),
    ("code-review.md#@When the immediately preceding code review call", "For findings after BROKEN, read the [Adversarial review procedure](adversarial-review.md)'s step 7 and follow it."),
    ("outcome-verification.md#@Resolve the active review mode", "For when a Security-critical claim's Adversarial review follows, read the [Adversarial review procedure](adversarial-review.md)'s step 1 and At the final commit and follow them."),
    ("outcome-verification.md#2", "Citations are as plan review defines them: read the [plan-review procedure](plan-review.md)'s definition of a citation and follow it, and the brief tells the role to follow a citation to the cited part only."),
    ("outcome-verification.md#2", "masked and limited as the Adversarial review procedure's step 7 sets for findings it passes to code review or outcome verification: read the [Adversarial review procedure](adversarial-review.md)'s step 7 and follow it."),
    ("outcome-verification.md#4", "with a brief that carries the adversary's findings as the Adversarial review procedure's step 7 describes: read the [Adversarial review procedure](adversarial-review.md)'s step 7 and follow it."),
    ("outcome-verification.md#6", "for a Security-critical claim in the automatic flow, read the [Adversarial review procedure](adversarial-review.md)'s At the final commit and follow it."),
    ("adversarial-review.md#2", "Citations are as plan review defines them: read the [plan-review procedure](plan-review.md)'s definition of a citation and follow it, and the brief tells the role to follow a citation to the cited part only."),
    ("preview.md#@- **Review mode:**", "read the [plan-review procedure](plan-review.md)'s review mode resolution and follow it."),
    ("review-state.md#Reading set", "Citations are as plan review defines them: read the [plan-review procedure](plan-review.md)'s definition of a citation and follow it;"),
    ("review-state.md#Reading set", "except as the Adversarial review procedure's step 2 adds for a claim that owns a composed review: read the [Adversarial review procedure](adversarial-review.md)'s step 2 and follow it."),
    ("review-state.md#Reading set", "where the code-review procedure's step 2 adds it for a claim that changes that claim's acceptance checks: read the [code-review procedure](code-review.md)'s step 2 and follow it."),
    ("review-state.md#Security findings", "For the adversary's BROKEN, read the [Adversarial review procedure](adversarial-review.md) and follow it; for a pre-existing vulnerability, read its step 10 and follow it."),
    ("review-state.md#Deviations", "for a material deviation, read the [plan-review procedure](plan-review.md)'s step 5 and follow it."),
    ("review-state.md#Follow-up record", "For what it records about a vulnerability, read the [Adversarial review procedure](adversarial-review.md)'s step 10 and follow it."),
    ("review-state.md#Conversation plans", "In a new session, main identifies a plan-mode or conversation plan as plan review does: read the [plan-review procedure](plan-review.md)'s plan identification and follow it."),
    ("adversarial-review SKILL.md#@A BROKEN from a call on a gated claim", "(read the [plan-review procedure](../delegation/references/plan-review.md)'s step 5 and follow it)"),
    # Ticket 02's code review: references ticket 02 wrote as a bare "as ... describes" now use the explicit-read form.
    ("review-state.md#Accept and land at the end of the plan", "For each Security-critical claim's Adversarial review result, read the [Adversarial review procedure](adversarial-review.md)'s At the final commit and follow it. The list states the final check's state at the commit to be landed,"),
    ("review-state.md#Accept and land at the end of the plan", "treats each Adversarial review result that no longer judges the commit to be landed as not run, and asks again; read the [Adversarial review procedure](adversarial-review.md)'s At the final commit and follow it."),
    ("review-state.md#Deviation scope", "the review of the revised plan after a material deviation (read the [plan-review procedure](plan-review.md)'s step 5 and follow it) covers the changed tickets"),
    ("review-state.md#Deviation scope", "For the count, the Stop threshold and the user's approval of the revised plan, read the [plan-review procedure](plan-review.md)'s step 5 and follow it."),
    ("code-review.md#@Resolve the active review mode", "It applies in either mode (read the [plan-review procedure](plan-review.md)'s review mode resolution and follow it) and does not start verification."),
    ("outcome-verification.md#@Resolve the active review mode", "An explicit verification request applies in either mode (read the [plan-review procedure](plan-review.md)'s review mode resolution and follow it) and does not require code review first."),
    ("adversarial-review SKILL.md#@The command takes a required attack scope", "Targets named in the arguments enter the brief only under step 3 of the procedure: read the [adversarial-review procedure](../delegation/references/adversarial-review.md)'s step 3 and follow it, including its rule that dynamic probing follows"),
)
# Ticket 02's code review: references in review state that ticket 02 wrote naming another owner with a bare "as ...
# describes". This wording is not in the v0.29.0 text, so it is checked here rather than in ABSENT.
BARE_OTHER_OWNER = re.compile(r"as the (?:Adversarial review|plan-review|code-review) procedure's [^.;:]+? describes")

# Ticket 02's code review: baseline conditions ticket 02 lost, restored at their owner with their original predicate
# (place, whole sentences).
RESTORED = {
    # Outcome verification's own precondition, the baseline OV:5 text itself (OV:5 at f4671bd); inventory R10.1 lists
    # OV:5 only as a copy of the per-claim timing.
    "only after code review returns APPROVED": (
        "outcome-verification.md#@Resolve the active review mode",
        "In auto, plan-driven work gets outcome verification only after [code review](code-review.md) returns APPROVED."),
    # CR:5 at f4671bd; inventory R9.4 (owner: plan review's mode resolution).
    "an explicit code review applies in either mode and does not start verification": (
        "code-review.md#@Resolve the active review mode",
        "An explicit user request for code review runs as [review state](review-state.md)'s What an explicit call runs "
        "describes. It applies in either mode (read the [plan-review procedure](plan-review.md)'s review mode "
        "resolution and follow it) and does not start verification."),
    # OV:5 at f4671bd; inventory R9.4 (owner: plan review's mode resolution).
    "an explicit verification applies in either mode and does not require code review first": (
        "outcome-verification.md#@Resolve the active review mode",
        "Whether a request runs outcome verification, in either mode, is as [review state](review-state.md)'s What an "
        "explicit call runs describes. An explicit verification request applies in either mode (read the "
        "[plan-review procedure](plan-review.md)'s review mode resolution and follow it) and does not require code "
        "review first."),
    # AR:11 at f4671bd; inventory R18.11 (owner AR:11).
    "static analysis and INCONCLUSIVE without an isolated environment": (
        "adversarial-review.md#3",
        "Dynamic probing follows [review state](review-state.md)'s Execution. When a restriction covers the call, "
        "dynamic probing runs only in an isolated environment the user's own message names; without one, the role "
        "analyses statically and reports INCONCLUSIVE for what needs execution."),
}
# How a named part of an owner other than review state is found in that owner's text.
NAMED_PARTS = {
    "At the final commit": "\n**At the final commit.** ",
    "definition of a citation": "A citation is explicit:",
    "review mode resolution": "Resolve the active review mode in this order:",
    "plan identification": "In a new session, a plan-mode or conversation plan is identified only from",
    "checklist": "It uses the spec only as a checklist",
    "Select and prepare": "\n## Select and prepare\n",
}
READ_FORM = re.compile(r"read the \[[^\]]+\]\(([^)]+)\)'s (.+?) and follow (?:it|them)")

# Acceptance items 5 and 6: the inventory's replacement texts (sections 3 and 4), each a whole sentence at its place.
REPLACEMENTS = {
    "H2": ("review-state.md#Reading set",
           "For a claim of a plan that is neither a spec nor tickets of a spec, such as a plan file, a plan-mode plan or a "
           "conversation plan with several claims, the text the claim is written in is the whole plan: the whole plan is "
           "supplied to the claim's implementation and every review of it, and main records and compares it, with any "
           "part of a spec the claim cites, as the claim's reading set, so a change to another claim's part of that plan "
           "is a change to the reading set."),
    "H3": ("review-state.md#Reading set",
           "When a ticket of a spec is implemented or reviewed without a READY for its plan in this session, as in off "
           "mode, after a waived plan review or for an explicit call, the checklist has not passed, so its implementation "
           "and every review of it read the whole spec as context, and main records and compares the ticket and the "
           "whole spec as its reading set, while its security invariants and test targets stay those named above."),
    "H7": ("plan-review.md#@Classify every plan's claims",
           "For any other plan, including one whose claims were not classified when it was written, such as a spec or "
           "ticket the user wrote or a conversation plan, main classifies its claims before the first plan review of that "
           "plan in the session or, for implemented work, before its code review."),
    "H8": ("review-state.md#Security findings",
           "They block on the reviewer's evidence: the rule that a regression needs a failing test or a reproduction "
           "applies only to regressions that are neither security problems nor data loss, so a removed or weakened "
           "security control is a Blocking finding without a reproduction."),
    "H10": ("review-state.md#Final check",
            "Main adds a fix claim without asking: it gets no plan review and no ticket, and main keeps it in the session's "
            "state and in any active handoff; a fix beyond the plan's scope is a Deviation, as Deviations describes."),
    "H12": ("review-state.md#Accept and land at the end of the plan",
            "When nothing listed needs it, the question is only the user's authority to land, which landing needs as "
            "Repository authority describes, and nothing is recorded as accept and land."),
    "H13": ("review-state.md#Resumed sessions",
            "Counts still restart in each session, and the Stop threshold in effect and the final check's state come only "
            "from this session, so main runs the final check again in the new session before landing, as Final check "
            "describes."),
    "D1": ("review-state.md#Reading set",
           "A Security-critical claim's security invariants and test targets are those written in the claim's own text "
           "(for a claim of a plan that is neither a spec nor tickets of a spec, its own part of that plan), the parts it "
           "cites and, for a claim a spec or other plan lists, the parts stated to hold for every claim; a claim of such a "
           "plan takes no other claim's invariants or targets from the rest of that plan."),
    "D2 review state": ("review-state.md#@| Call source |", "Explicit calls are outside the count."),
    "D2 plan review": ("plan-review.md#@Resolve the active review mode", "Explicit calls are outside the count below."),
    "D2 outcome verification": ("outcome-verification.md#@Resolve the active review mode",
                                "Explicit calls are outside the count below."),
    "D2 preview": ("preview.md#@Main produces the preview alone.",
                   "It dispatches no child, including scout or Explore, starts no review, adds to no count and writes no "
                   "file, handoff or configuration."),
    "D2 code review": ("code-review.md#@Resolve the active review mode",
                       "Explicit calls are outside the count below, and the unreviewed rule in step 6 applies only to the "
                       "automatic flow, while [review state](review-state.md)'s acceptance gate still covers, in either "
                       "mode, a claim an active handoff records as unreviewed, unverified or pending acceptance, and the "
                       "handoff note changes after a pass as [review state](review-state.md)'s Pending acceptance "
                       "describes in either mode; after an explicit review outside a stopped automatic step, report its "
                       "verdict and findings and leave the next step to the user."),
    "D3 step 4": ("adversarial-review.md#4",
                  "A count that reaches the Stop threshold in effect without an automatic HELD main accepts under step 6 "
                  "stops automatic Adversarial review (step 8)."),
    "D3 step 8": ("adversarial-review.md#8",
                  "When the count reaches the Stop threshold in effect without an automatic HELD main accepts under step "
                  "6, stop automatic Adversarial review, report the claim with its Adversarial review missing and its open "
                  "findings, do not land it on the default branch, release it or report it complete, and require an "
                  "explicit user request for another call."),
    "D4": ("adversarial-review.md#5",
           "After any INCONCLUSIVE, when main's comparison after the previous call found a change to a file the claim "
           "depends on, the next call, once the rules above on the cause of an INCONCLUSIVE let it run, covers the claim's "
           "full scope from its base revision, not only the uncovered invariants and gaps."),
    "D8": ("preview.md#3",
           "One review section, listed once rather than under each Claim: plan review by analyst, code review by reviewer "
           "and outcome verification by verifier, and, when a Plan has a Security-critical claim, the security analysis "
           "by analyst before plan review and Adversarial review by adversary, in off after outcome verification and in "
           "auto at the final commit after the final check, as [the adversarial-review procedure](adversarial-review.md)'s "
           "At the final commit describes, each with model, effort and source."),
    "D9": ("review-state.md#@State lives in the current session's task.",
           "Each procedure's step 1, step 3 or, for Adversarial review, step 4 says how to recover this state before "
           "another automatic call."),
}


def runtime_markdown():
    """Every runtime Markdown file under skills/, by repository path."""
    root = config.ROOT / "skills"
    return {path.relative_to(config.ROOT).as_posix(): path.read_text(encoding="utf-8")
            for path in sorted(root.rglob("*.md"))}


def review_state_names(text: str) -> set[str]:
    """The parts of review state a pointer may name: its bold items, table rows and section headings."""
    names = set(re.findall(r"^\s*- \*\*([^*]+?)\.\*\*", text, re.M))
    names |= set(re.findall(r"^\| ([^|]+?) \|", text, re.M))
    names |= set(re.findall(r"^## (.+)$", text, re.M))
    return names


def named_part_exists(target: str, part: str) -> bool:
    step = re.fullmatch(r"step (\d+)", part)
    if step:
        return re.search(rf"^{step.group(1)}\. ", target, re.M) is not None
    return NAMED_PARTS[part] in target


class DelegationDedupeContractTests(unittest.TestCase):
    """Ticket 02: owner-once, pointer and absence pins, the H and D replacement texts, the auto-only pointer K1 keeps,
    and a check that the new pins fail on the text at tag v0.29.0."""

    assert_whole_sentence = feather_support.stop_threshold_assert_whole_sentence
    tagged = DelegationDedupeExpandTests.tagged

    @staticmethod
    def current():
        return {name: (config.ROOT / path).read_text(encoding="utf-8") for name, path in PATHS.items()}

    @staticmethod
    def once_holds(texts, owner, phrase, count):
        return all(text.count(phrase) == (count if name == owner else 0) for name, text in texts.items())

    # Acceptance item 1.
    def test_each_listed_rule_is_stated_once_at_its_owner(self):
        texts = self.current()
        for rule, (owner, phrase, count) in ONCE.items():
            for name, text in texts.items():
                with self.subTest(rule=rule, place=name):
                    self.assertEqual(text.count(phrase), count if name == owner else 0, phrase)

    # Acceptance items 1, 5 and 6.
    def test_restatements_and_historical_phrases_are_gone_from_skills(self):
        files = runtime_markdown()
        self.assertIn("skills/delegation/references/review-state.md", files)
        for phrase in ABSENT:
            allowed = ABSENT_EXCEPT.get(phrase, ())
            for path, text in files.items():
                expected = sum(source(place).count(phrase) for place in allowed
                               if PATHS[place.partition("#")[0]] == path)
                with self.subTest(phrase=phrase, path=path):
                    self.assertEqual(text.count(phrase), expected)
            for place in allowed:
                with self.subTest(phrase=phrase, kept=place):
                    self.assertEqual(source(place).count(phrase), 1)

    # Acceptance item 3: pointers to review state.
    def test_pointers_to_review_state_name_parts_that_exist(self):
        names = review_state_names((REFERENCES / "review-state.md").read_text(encoding="utf-8"))
        for place, pointer, parts in RS_POINTERS:
            with self.subTest(place=place, pointer=pointer[:60]):
                self.assertIn(pointer, source(place))
                self.assertIn("review state", pointer)
            for part in parts:
                with self.subTest(place=place, part=part):
                    self.assertIn(part, names)

    # Acceptance item 3: pointers to other owners use the explicit-read form and name parts that exist.
    def test_pointers_to_other_owners_use_the_explicit_read_form(self):
        for place, pointer in READ_POINTERS:
            with self.subTest(place=place, pointer=pointer[:60]):
                self.assertIn(pointer, source(place))
                self.assertRegex(pointer, r"read (?:the \[[^\]]+\]\([^)]+\)|its)(?:'s [^.;]+?)? and follow (?:it|them)")

    def test_every_explicit_read_pointer_resolves(self):
        found = 0
        for name, path in PATHS.items():
            text = (config.ROOT / path).read_text(encoding="utf-8")
            for link, parts in READ_FORM.findall(text):
                target_path = ((config.ROOT / path).parent / link).resolve()
                with self.subTest(place=name, link=link, parts=parts):
                    self.assertTrue(target_path.is_file(), link)
                    target = target_path.read_text(encoding="utf-8")
                    # A part named "Select and prepare" resolves whole; "step 2 and step 3" names two parts.
                    for part in ([parts] if parts in NAMED_PARTS else parts.split(" and ")):
                        self.assertTrue(named_part_exists(target, part), part)
                found += 1
        self.assertGreater(found, len(READ_POINTERS))

    # Item 3: no reference ticket 02 wrote in review state names another owner with a bare "as ... describes" in place
    # of the explicit-read form.
    def test_review_state_names_other_owners_in_the_explicit_read_form(self):
        self.assertEqual(BARE_OTHER_OWNER.findall((REFERENCES / "review-state.md").read_text(encoding="utf-8")), [])

    # S1 and item 2: the conditions ticket 02 lost are stated again at their owner, with their original predicate.
    def test_the_conditions_ticket_02_lost_are_restored_at_their_owner(self):
        for condition, (place, sentences) in RESTORED.items():
            with self.subTest(condition=condition, place=place):
                self.assert_whole_sentence(sentences, source(place))

    # Inventory K1 and spec item 3: the delegation skill's pointer to Dependent claims, and its Adversarial review
    # pointer, stay in sentences the baseline qualified as auto-only.
    def test_auto_only_pointers_keep_their_qualifier(self):
        plan = source("delegation SKILL.md#@When the installed policy, a session preference that turns automatic review on (")
        for part in ("Dependent claims describes", "'s At the final commit and follow it"):
            with self.subTest(part=part):
                sentence = next(s for s in feather_support.sentences(plan) if part in s)
                self.assertTrue(sentence.startswith("In auto, "), sentence)
        self.assertIn("for a Security-critical claim in the automatic flow, read the [Adversarial review "
                      "procedure](adversarial-review.md)'s At the final commit", source("outcome-verification.md#6"))

    # The note carried from ticket 01's review (R6.11): the only source of "never assumes a count of zero" stays where
    # plan review's step 1 points.
    def test_plan_review_step_1_reaches_unknown_state(self):
        self.assertIn("Unknown state", source("plan-review.md#1"))
        self.assertIn("In that case main never assumes a count of zero.", source("review-state.md#Unknown state"))

    # Acceptance items 5 and 6.
    def test_the_h_and_d_items_carry_the_inventorys_replacement_texts(self):
        for item, (place, sentence) in REPLACEMENTS.items():
            with self.subTest(item=item, place=place):
                self.assert_whole_sentence(sentence, source(place))

    # T3.
    def test_every_once_pin_fails_on_the_v0_29_0_text(self):
        tagged = {name: self.tagged(name) for name in PATHS}
        for rule, (owner, phrase, count) in ONCE.items():
            with self.subTest(rule=rule):
                self.assertFalse(self.once_holds(tagged, owner, phrase, count), phrase)

    def test_every_absence_pin_fails_on_the_v0_29_0_text(self):
        # The phrases H9 and H11 keep (ABSENT_EXCEPT) hold at the tag too, so only the others are checked here.
        tagged = "\n".join(self.tagged(name) for name in PATHS)
        for phrase in ABSENT:
            if phrase in ABSENT_EXCEPT:
                continue
            with self.subTest(phrase=phrase):
                self.assertGreater(tagged.count(phrase), 0)

    def test_every_pointer_and_replacement_is_absent_from_the_v0_29_0_text(self):
        pins = [(place, pointer) for place, pointer, _ in RS_POINTERS if pointer not in BASELINE_POINTERS]
        pins += list(READ_POINTERS)
        pins += list(REPLACEMENTS.values())
        for place, text in pins:
            with self.subTest(place=place, text=text[:60]):
                self.assertNotIn(text, self.tagged(place.partition("#")[0]))


if __name__ == "__main__":
    unittest.main()
