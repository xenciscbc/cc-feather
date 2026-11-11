"""Resource-risk runs ticket 03 (docs/specs/resource-risk-runs.md, Acceptance items 3 where a record is kept, 5 for the
floor, 7 without its last sentence, 8, 10, 11, 13 for the Unbounded probe, Observed resource risk and Runner entries, and
17): the floor paragraph each of the verifier, adversary, executor and security-executor definitions carries, and its
absence from the other roles; the resource-risk runs reference that owns main's side (the Runner path and limits in a
brief, main's floor, the Observed resource risk record, the Runner's boundary and the permission notes); the pointers
ADR 0017 requires from review state's Execution and Dispatch record, the outcome-verification and Adversarial review
procedures and the delegation skill's dispatch steps; and the three CONTEXT.md entries. These tests pin the shipped
text a model reads; they cannot show that a model always follows it."""

from __future__ import annotations

import re
import unittest

from tests import feather_support
from tests.feather_support import config

ROOT = config.ROOT
AGENTS = ROOT / "templates" / "agents"
DELEGATION = ROOT / "skills" / "delegation"
REFERENCES = DELEGATION / "references"
REFERENCE = REFERENCES / "resource-risk-runs.md"
LINK = "[resource-risk runs reference](resource-risk-runs.md)"
SKILL_LINK = "[resource-risk runs reference](references/resource-risk-runs.md)"
READ_REFERENCE = f"read the {LINK} and follow it."

# Acceptance item 5: the one paragraph, identical across the four roles apart from the opening that says what it limits
# and the role-specific outcome words.
OPENING_REVIEW = "**Resources.** This adds limits to what Execution allows and never widens it. "
OPENING_IMPLEMENTER = ("**Resources.** This adds limits to what your assignment allows, adds no Execution determination "
                       "and never widens what the assignment allows. ")
BODY = (
    "Before you run a new or modified test or probe, whoever wrote it, judge whether it is an Unbounded probe: any part "
    "of it, the input generator, the code under test, a reference implementation or control, callbacks, measurement, "
    "output collection and descendant processes, has no established bound on total work or retained data, or the peak "
    "memory and time that the bound allows do not fit the budget your brief carries or, without one, the project's "
    "resource guidance. An unknown bound counts as none; a bounded input size, a bounded outer loop or a timeout alone is "
    "not a bound; a check the plan lists that you change counts as modified. Do not run an Unbounded probe: return it to "
    "the main Agent with what is unbounded, and return in the same way a probe you cannot judge against any budget or "
    "guidance. For each bounded probe you write and run against a budget, state its estimated peak memory and time and "
    "the basis of the estimate. Never raise a limit and rerun. A run the Runner reports as contained, timed out or "
    "refused, or whose evidence is missing, is inconclusive evidence judged from the Runner's result, not from the "
    "target's exit code; a non-zero exit with no limit event is a failure, and results established independently of "
    "that run stand. "
)
OUTCOME = {
    "verifier": "Report what a returned probe or a stopped run leaves undecided as INCONCLUSIVE. ",
    "adversary": ("Report what a returned probe or a stopped run leaves undecided as INCONCLUSIVE or as a gap left open "
                  "in your coverage. "),
    "executor": "Report the task partial or blocked for what a returned probe or a stopped run leaves undecided. ",
    "security-executor": "Report the task partial or blocked for what a returned probe or a stopped run leaves undecided. ",
}
REPORT = "Your report names every probe you returned and every run a limit stopped, with the reason."
# resource-risk-runs ticket 04: the Resource-risk claim sentences follow the opening, with the role's own words for an
# insufficient Execution method (tests/test_feather_resource_method.py pins their decisions).
METHOD = (
    "For a Resource-risk claim, run its risky part only as the approved Execution method in your brief describes and "
    "only inside the Runner with the brief's limits, and never change it: no raised limit, no larger or different "
    "experiment. Still judge whether the claim holds, ordinary acceptance checks and counterexample probes included, and "
    "whether the approved Execution method can establish it. When you judge the method insufficient or wrong, do not "
    "work around it: {outcome} with your proposed method and the reason. "
)
METHOD_OUTCOME = {
    "verifier": "report INCONCLUSIVE",
    "adversary": "report INCONCLUSIVE",
    "executor": "report the task partial or blocked",
    "security-executor": "report the task partial or blocked",
}
FLOOR_ROLES = ("verifier", "adversary", "executor", "security-executor")
# Where the paragraph sits: the paragraph it follows, by its opening.
BESIDE = {
    "verifier": "**Execution.** ",
    "adversary": "**Execution.** ",
    "executor": "Own local engineering decisions inside the assigned scope.",
    "security-executor": "Own only assigned files, preserve other contributors' changes",
}
OTHER_ROLES = tuple(role for role in config.ROLES if role not in FLOOR_ROLES)


def paragraph(role: str) -> str:
    opening = OPENING_REVIEW if role in ("verifier", "adversary") else OPENING_IMPLEMENTER
    return opening + METHOD.format(outcome=METHOD_OUTCOME[role]) + BODY + OUTCOME[role] + REPORT


def normalised(text: str) -> str:
    return text.replace("\r\n", "\n")


def role_text(role: str) -> str:
    return normalised((AGENTS / f"{role}.md").read_text(encoding="utf-8"))


def reference() -> str:
    return normalised(REFERENCE.read_text(encoding="utf-8"))


def section(text: str, heading: str) -> str:
    return text.split(f"\n## {heading}\n", 1)[1].split("\n## ", 1)[0]


def bullet(text: str, label: str) -> str:
    found = [line for line in text.splitlines() if line.startswith(f"- **{label}.**")]
    if len(found) != 1:
        raise AssertionError(f"{len(found)} bullets labelled {label!r}")
    return found[0]


class RoleFloorTests(unittest.TestCase):
    """Acceptance item 5: the paragraph, its placement, the outcome words and its absence from the other roles."""

    assert_whole_sentence = feather_support.stop_threshold_assert_whole_sentence

    def test_each_floor_role_carries_the_paragraph_once(self):
        for role in FLOOR_ROLES:
            lines = role_text(role).split("\n")
            with self.subTest(role=role):
                self.assertEqual([line for line in lines if line.startswith("**Resources.** ")], [paragraph(role)])

    def test_the_paragraph_sits_beside_execution_or_the_scope_instructions(self):
        for role, opening in BESIDE.items():
            lines = role_text(role).split("\n")
            anchor = [index for index, line in enumerate(lines) if line.startswith(opening)]
            with self.subTest(role=role):
                self.assertEqual(len(anchor), 1)
                self.assertEqual(lines[anchor[0] + 1], "")
                self.assertEqual(lines[anchor[0] + 2], paragraph(role))

    def test_the_paragraphs_differ_only_in_the_opening_and_the_outcome_words(self):
        bodies = set()
        for role in FLOOR_ROLES:
            text = paragraph(role)
            opening = OPENING_REVIEW if role in ("verifier", "adversary") else OPENING_IMPLEMENTER
            text = text.replace(METHOD.format(outcome=METHOD_OUTCOME[role]), METHOD)
            bodies.add(text.removeprefix(opening).replace(OUTCOME[role], ""))
        self.assertEqual(len(bodies), 1)

    def test_the_outcome_words_match_each_roles_report(self):
        for role in ("verifier", "adversary"):
            with self.subTest(role=role):
                self.assertIn("as INCONCLUSIVE", OUTCOME[role])
                self.assertNotIn("partial or blocked", OUTCOME[role])
        self.assertIn("gap left open in your coverage", OUTCOME["adversary"])
        for role in ("executor", "security-executor"):
            with self.subTest(role=role):
                self.assertIn("partial or blocked", OUTCOME[role])
                self.assertNotIn("INCONCLUSIVE", OUTCOME[role])
                # Their report line already names task outcome as completed, partial or blocked.
                self.assertIn("Report task outcome (completed, partial or blocked)", role_text(role))

    def test_the_implementers_get_limits_and_no_execution_determination(self):
        for role in ("executor", "security-executor"):
            text = role_text(role)
            with self.subTest(role=role):
                self.assertNotIn("**Execution.** ", text)
                self.assertIn("adds no Execution determination and never widens what the assignment allows.",
                              paragraph(role))
        for role in ("verifier", "adversary"):
            with self.subTest(role=role):
                self.assertTrue(paragraph(role).startswith(OPENING_REVIEW))

    def test_the_paragraph_states_each_decision(self):
        text = paragraph("verifier")
        for sentence in (
            "An unknown bound counts as none; a bounded input size, a bounded outer loop or a timeout alone is not a "
            "bound; a check the plan lists that you change counts as modified.",
            "Never raise a limit and rerun.",
            "For each bounded probe you write and run against a budget, state its estimated peak memory and time and the "
            "basis of the estimate.",
            REPORT,
        ):
            with self.subTest(sentence=sentence[:50]):
                self.assert_whole_sentence(sentence, text)
        for phrase in ("whoever wrote it", "the input generator, the code under test, a reference implementation or "
                       "control, callbacks, measurement, output collection and descendant processes",
                       "no established bound on total work or retained data",
                       "the budget your brief carries or, without one, the project's resource guidance",
                       "Do not run an Unbounded probe: return it to the main Agent",
                       "a probe you cannot judge against any budget or guidance",
                       "judged from the Runner's result, not from the target's exit code",
                       "a non-zero exit with no limit event is a failure",
                       "results established independently of that run stand"):
            with self.subTest(phrase=phrase[:50]):
                self.assertIn(phrase, text)

    def test_the_installed_roles_render_the_paragraph(self):
        for role in FLOOR_ROLES:
            for prefix in ("", config.ROLE_PREFIX):
                rendered = normalised(config._render(role, {"model": "sonnet", "effort": "high"}, prefix).decode("utf-8"))
                with self.subTest(role=role, prefix=prefix):
                    self.assertEqual(rendered.count(paragraph(role)), 1)

    def test_the_other_roles_do_not_carry_it(self):
        self.assertEqual(set(OTHER_ROLES), {"reviewer", "analyst", "scout", "mech-executor", "Explore"})
        for role in OTHER_ROLES:
            text = role_text(role)
            with self.subTest(role=role):
                self.assertNotIn("**Resources.**", text)
                self.assertNotIn("Unbounded probe", text)
                self.assertNotIn("Runner", text)


class ReferenceTests(unittest.TestCase):
    """Acceptance items 7, 8, 10 and 11 and Implementation Decisions "One owner on main's side", "Execution, not
    authorship" and "Runner form": the reference that owns main's side."""

    assert_whole_sentence = feather_support.stop_threshold_assert_whole_sentence

    def test_the_reference_adds_to_execution_and_reads_review_state(self):
        text = reference()
        self.assertTrue(text.startswith("# Resource-risk runs\n"))
        for sentence in (
            # resource-risk-runs ticket 04 names the approved Execution method as part of "here".
            "It adds to [review state](review-state.md)'s Execution and never replaces it: nothing here, an approved "
            "Execution method included, allows a run that Execution does not, lifts a restriction the user stated, or "
            "makes the Runner an isolated environment the user named.",
            "Before any decision or brief of this reference that depends on a rule review state owns, in off and in "
            "auto, main reads [review state](review-state.md) in full; review state's Reading it says when an earlier "
            "full read still serves.",
        ):
            with self.subTest(sentence=sentence[:50]):
                self.assert_whole_sentence(sentence, text)
        self.assertEqual([line for line in text.splitlines() if line.startswith("## ")],
                         # resource-risk-confirmation ticket 01 adds Proposed marks before Execution method.
                         ["## Proposed marks", "## Execution method", "## The Runner", "## Main's floor",
                          "## Observed resource risk"])

    def test_main_gives_the_resolved_runner_path_and_the_limits_in_the_brief(self):
        runner = section(reference(), "The Runner")
        self.assertIn("Resolve it relative to this loaded skill: `scripts/runner.py`.", runner)
        self.assertIn("`${CLAUDE_PLUGIN_ROOT}/skills/delegation/scripts/runner.py`", runner)
        self.assertIn("python -B <skill>/scripts/runner.py --memory-mib N --time-seconds S --output-bytes B --cwd DIR "
                      "-- COMMAND ...", runner)
        self.assertIn("with the target command as plain arguments after the separator", runner)
        self.assertTrue((DELEGATION / "scripts" / "runner.py").is_file())
        self.assert_whole_sentence(
            "When a brief is for a role that may execute code and the role may run part of its work inside the Runner, "
            "main gives in it the resolved Runner path and the memory, time and output limits to run with.",
            bullet(runner, "In the brief"))

    def test_the_runner_boundary_is_named(self):
        text = bullet(section(reference(), "The Runner"), "Its boundary")
        for sentence in (
            "Only processes inside the Runner's containment are limited.",
            "Work handed to an already running service, such as a daemon, a container runtime, WSL, a build server, a "
            "database or a remote service, and tools that execute code outside the shell, such as an MCP server, are "
            "outside it.",
            "Two runs started at the same time each check available memory on their own, so their total is not limited; "
            "that is a known limitation of this release.",
        ):
            with self.subTest(sentence=sentence[:50]):
                self.assert_whole_sentence(sentence, text)

    def test_the_permission_notes(self):
        text = bullet(section(reference(), "The Runner"), "Permissions")
        for sentence in (
            "A Runner invocation goes through the host's normal permission handling like any other command, and "
            "cc-feather adds no permission rule.",
            "Because the target command is plain text in the invocation, whatever decides the permission sees what will "
            "run.",
            "cc-feather advises against a permission rule that allows every Runner invocation, because such a rule "
            "allows any command through the Runner.",
            "A rule written for the target alone no longer matches once the target is wrapped in the Runner.",
        ):
            with self.subTest(sentence=sentence[:50]):
                self.assert_whole_sentence(sentence, text)

    def test_mains_floor_follows_execution_and_binds_reruns_and_reproductions(self):
        floor = section(reference(), "Main's floor")
        for sentence in (
            "The floor follows execution, not authorship: it covers a new or modified test or probe whoever wrote it.",
            "It binds main when main runs a test or probe a role returned and when main reproduces a failure a role "
            "reported.",
        ):
            with self.subTest(sentence=sentence[:50]):
                self.assert_whole_sentence(sentence, floor)
        unbounded = bullet(floor, "What is unbounded")
        for phrase in ("the input generator, the code under test, a reference implementation or control, callbacks, "
                       "measurement, output collection and descendant processes",
                       "no established bound on total work or retained data",
                       "An unknown bound counts as none; a bounded input size, a bounded outer loop or a timeout alone "
                       "is not a bound; a check the Plan lists that is changed counts as modified."):
            with self.subTest(phrase=phrase[:50]):
                self.assertIn(phrase, unbounded)

    def test_a_returned_probe_is_redesigned_or_run_in_the_runner(self):
        floor = section(reference(), "Main's floor")
        self.assert_whole_sentence(
            "Main runs a returned Unbounded probe only after redesigning it so that every part is bounded within the "
            "budget, or inside the Runner with the budget's limits.", bullet(floor, "A returned probe"))
        self.assert_whole_sentence("It never runs it as it is and never with a timeout alone: a timeout limits time, "
                                   "not memory.", bullet(floor, "A returned probe"))
        judging = bullet(floor, "Judging the run")
        self.assert_whole_sentence("Main never raises a limit and reruns.", judging)
        self.assertIn("judged from the Runner's result, not from the target's exit code; a non-zero exit with no limit "
                      "event is a failure, and results established independently of that run stand.", judging)

    def test_the_observed_resource_risk_record(self):
        record = section(reference(), "Observed resource risk")
        pins = {
            "Recording it": (
                "When a role's report names a probe it returned or a run a limit stopped, or a run of main's own stops "
                "on a limit, main records an Observed resource risk on that Claim.",
                "It names the run and its test or probe, the reason, how it was handled (returned, redesigned, run "
                "within a budget, stopped by a limit), the budget and any peak the Runner observed.",
                "The record does not assume that plan review missed the risk: a probe invented during execution, or a "
                "run in off, had no plan review to miss it.",
            ),
            "Where it is kept": (
                "In auto, main keeps it in the Plan's dispatch record, as [review state](review-state.md)'s Dispatch "
                "record describes; in off, in the Active handoff when one exists, and otherwise in the session's state.",
                "It is never written into the Claim's text: writing it into the Plan or a ticket needs the user's "
                "agreement.",
            ),
            "Telling the user": ("Main tells the user about it in its next reply.",),
            # resource-risk-runs ticket 04: the carry is stated once, for every execution condition, in Execution
            # method's Carrying the conditions; this bullet points to it.
            "Carrying it": (
                "It is one of the Claim's execution conditions, carried into every later brief of that Claim and "
                "applied to main's own runs for it as Execution method's Carrying the conditions states.",
                "It stays until the Plan ends.",
            ),
            "At the end of the Plan": (
                "Main lists every Observed resource risk of the Plan in the decision or completion report at the end of "
                "the Plan.",
            ),
        }
        for label, sentences in pins.items():
            text = bullet(record, label)
            for sentence in sentences:
                with self.subTest(label=label, sentence=sentence[:50]):
                    self.assert_whole_sentence(sentence, text)


class PointerTests(unittest.TestCase):
    """Acceptance item 8 and Implementation Decision "One owner on main's side": review state's Dispatch record lists
    Observed resource risks, and every place ADR 0017 names points to the reference instead of restating it."""

    assert_whole_sentence = feather_support.stop_threshold_assert_whole_sentence

    @staticmethod
    def text(path: str) -> str:
        return normalised((REFERENCES / path).read_text(encoding="utf-8"))

    def test_the_dispatch_record_holds_observed_resource_risks(self):
        record = bullet(self.text("review-state.md"), "Dispatch record")
        # resource-risk-runs ticket 04 adds the approved Execution methods.
        self.assertIn("each fix claim with its problem and a summary of the fix; each claim's approved Execution method "
                      "and Observed resource risks; the branches main created for the work;", record)
        self.assert_whole_sentence(
            "What an approved Execution method and an Observed resource risk name, and when main records them, are as "
            f"the resource-risk runs reference states: {READ_REFERENCE}", record)

    def test_execution_points_to_mains_floor(self):
        self.assert_whole_sentence(
            "Main's floor for running a test or probe a role returned or reproducing a failure a role reported, the "
            "Runner path and limits a brief needs, and a claim's execution conditions, its approved Execution method "
            "included, are main's side of resource-risk runs: " + READ_REFERENCE,
            bullet(self.text("review-state.md"), "Execution"))

    def test_the_procedures_point_to_the_reference(self):
        brief = ("For the Runner path and limits the brief needs and the claim's execution conditions it carries, its "
                 "approved Execution method and Observed resource risks included, " + READ_REFERENCE)
        pins = {
            ("outcome-verification.md", "2. "): brief,
            ("outcome-verification.md", "4. "): (
                "Main reproduces a failure, and runs a probe the verifier returned, only within its own floor, and "
                "records a probe the verifier returned or a run a limit stopped: " + READ_REFERENCE),
            ("adversarial-review.md", "2. "): brief,
            ("adversarial-review.md", "6. "): (
                "Main reproduces a BROKEN, and runs a probe the adversary returned, only within its own floor, and "
                "records a probe the adversary returned or a run a limit stopped: " + READ_REFERENCE),
        }
        for (path, step), sentence in pins.items():
            lines = [line for line in self.text(path).splitlines() if line.startswith(step)]
            with self.subTest(path=path, step=step):
                self.assertEqual(len(lines), 1)
                self.assert_whole_sentence(sentence, lines[0])

    def test_the_delegation_skills_dispatch_points_to_the_reference(self):
        text = normalised((DELEGATION / "SKILL.md").read_text(encoding="utf-8"))
        dispatch = text.split("\n## Dispatch\n", 1)[1].split("\n## ", 1)[0]
        self.assert_whole_sentence(
            "For the Runner path and limits a brief of a role that may execute code needs, the claim's execution "
            "conditions it carries, its approved Execution method and Observed resource risks included, and a probe a "
            "role returned or a run a limit stopped, read the "
            f"{SKILL_LINK} and follow it.", dispatch)

    def test_the_rules_are_stated_only_in_the_reference(self):
        # ADR 0017: the pointers carry no condition of the rules they point to.
        owned = ("never with a timeout alone", "does not assume that plan review missed the risk",
                 "Only processes inside the Runner's containment are limited", "needs the user's agreement",
                 "allows every Runner invocation", "in its next reply")
        for path in sorted(DELEGATION.rglob("*.md")):
            text = normalised(path.read_text(encoding="utf-8"))
            for phrase in owned:
                with self.subTest(path=path.name, phrase=phrase):
                    self.assertEqual(text.count(phrase), 1 if path == REFERENCE else 0)

    def test_every_link_to_the_reference_resolves(self):
        found = 0
        for path in sorted(DELEGATION.rglob("*.md")):
            for link in re.findall(r"\]\(([^)]*resource-risk-runs\.md)\)", path.read_text(encoding="utf-8")):
                with self.subTest(path=path.name, link=link):
                    self.assertEqual((path.parent / link).resolve(), REFERENCE.resolve())
                found += 1
        # resource-risk-runs ticket 04 adds plan review's pointer; resource-risk-confirmation ticket 01 adds plan
        # review's step 2 and step 5 pointers and the Dispatch record's pointer for decisions on proposed marks.
        self.assertEqual(found, 11)


class GlossaryTests(unittest.TestCase):
    """Acceptance item 13: the Unbounded probe, Observed resource risk and Runner entries."""

    def setUp(self):
        self.entries = feather_support.glossary_entries((ROOT / "CONTEXT.md").read_text(encoding="utf-8"))

    def test_the_three_entries_are_defined_once(self):
        text = (ROOT / "CONTEXT.md").read_text(encoding="utf-8")
        for term in ("Unbounded probe", "Observed resource risk", "Runner"):
            with self.subTest(term=term):
                self.assertIn(term, self.entries)
                self.assertEqual(text.count(f"**{term}**:"), 1)
        terms = list(self.entries)
        start = terms.index("Unbounded probe")
        self.assertEqual(terms[start:start + 3], ["Unbounded probe", "Observed resource risk", "Runner"])

    def test_the_entries_carry_their_decisions(self):
        pins = {
            "Unbounded probe": ("whoever wrote it", "no established bound on total work or retained data",
                                "An unknown bound counts as none, and a bounded input size, a bounded outer loop or a "
                                "timeout alone is not a bound.", "never with a timeout alone"),
            "Observed resource risk": ("It does not assume that plan review missed the risk.",
                                       "never in the Claim's text", "lists it at the end of the Plan"),
            "Runner": ("a memory limit for its whole process tree", "Only processes inside its containment are limited",
                       "never the isolated environment the user named"),
        }
        for term, phrases in pins.items():
            for phrase in phrases:
                with self.subTest(term=term, phrase=phrase[:40]):
                    self.assertIn(phrase, self.entries[term])


if __name__ == "__main__":
    unittest.main()
