"""Design and test checks (docs/specs/design-and-test-checks.md). Ticket 01: the user-invoked /cc-feather:test-speedup
command, which reports test speed-ups that keep correctness, lists existing tests with resource risk and measures only
after the user agrees; its manifest position, README listings, reference section and the setup document's skill count.
Since 0.44.0 (docs/specs/test-speedup-smaller-checks.md) the command also offers smaller inputs, replacements in Removals
and profiling in the measurement offer, and the widened removal sentences replace their pins. Ticket 02: the user-invoked
/cc-feather:overdesign-check command, which reports Over-design in a target with each item weighed by the delegation
skill's rule, keeps trust-boundary checks and asks the user about old formats without evidence; the CONTEXT.md
Over-design entry, an unchanged Unbounded probe entry, and the weighing pointed to but restated by neither command.
Ticket 03: neither command is named by an installed policy template or role definition.
Since 0.45.0 (docs/specs/test-run-configuration.md, ticket 01) the command also checks run configurations for each
Unbounded run configuration, looks up defaults in a fixed order, bounds a parallel speed-up and a flagged measurement, and
reports a fourth section; the report's section count moves from three to four.
Since docs/specs/test-design.md, ticket 01, the static pass's speed criteria and the correctness bar, smaller inputs and
the removal rule with replacements included, live in the shared test criteria reference in the test-speedup skill, which
the command points to and restates none of; their pins move with them. The reference adds further criteria, each with
its condition, and the sleep rule, which the static pass checks for; it points to the glossary's resource-risk and suite
entries and to the delegation skill and copies none of them, and the reference section states the new checks.
Ticket 02 of that spec: the user-invoked /cc-feather:test-design command, listed after overdesign-check, which reports a
Test design for one target and changes and runs nothing; its judging rule stated first, its runs-and-sizes, gated-test,
resource-risk, report-section, removal, error-guessing and lookup decisions; its guideline reference with one pin per
guideline group, the three hard prohibitions and no source labels; pointers to the shared test criteria, the delegation
skill, the Unbounded probe entry and test-speedup's lookups that restate none of them; the CONTEXT.md Test design entry;
README listings and a reference section after Over-design check's in both languages, whose introduction now counts three
commands; the setup document's skill count of twenty-two; and no policy template or role definition naming it.
Since docs/specs/test-speedup-record.md, ticket 02, the command keeps a Speed-up record through its bundled script and
continues from it: the report-only paragraph, the reserved first words, `argument-hint`, the reference introduction, the
README listings and the reference sentence on the run-configuration section replace their pins; the report has five
sections, Since the last run first; and a packaging test checks the manifest and the launcher's two paths.
Since docs/specs/test-design-proposal-triage.md, ticket 01, the test-design command grades every proposed test
Recommended or Optional by pointing to the delegation skill's weighing paragraph, lists candidates in one line before it
writes full statements for the Recommended ones, maps behaviour to code, and integrates analyst results into a Lean set;
the judging rule gains its plausibility and observability sentences, the report has eight sections, Acceptance problems
first, the Who analyses rules and the Key examples guideline change, and the guideline reference gains three Test quality
guidelines. The changed pins move to the new wording, the glossary entry, README listings and reference sentences follow,
and a single-owner check shows the weighing paragraph pointed to, restated by neither file and unchanged.
"""

from __future__ import annotations

import json
import re
import unittest

from tests import feather_support
from tests import test_feather_completion_criteria as completion_criteria
from tests.feather_support import config

SKILLS = config.ROOT / "skills"


def manifest_skills():
    return json.loads((config.ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["skills"]


def frontmatter(text):
    assert text.startswith("---\n"), "a skill starts with frontmatter"
    return text.split("---")[1]


class TestSpeedupCommandTests(unittest.TestCase):
    """Ticket 01."""

    COMMAND = SKILLS / "test-speedup" / "SKILL.md"
    CRITERIA = SKILLS / "test-speedup" / "references" / "test-criteria.md"

    def test_command_is_user_invoked_and_listed_after_related_tests(self):
        skills = manifest_skills()
        self.assertIn("./skills/test-speedup", skills)
        self.assertEqual(skills.index("./skills/test-speedup"), skills.index("./skills/related-tests") + 1)
        front = frontmatter(self.COMMAND.read_text(encoding="utf-8"))
        self.assertIn("name: test-speedup\n", front)
        self.assertIn("disable-model-invocation: true\n", front)
        self.assertIn('argument-hint: "[show | prune | --full] [test paths or scope]"\n', front)
        self.assertRegex(front, r'\ndescription: "[^"\n]*test[^"\n]*"\n')

    assert_whole_sentence = feather_support.stop_threshold_assert_whole_sentence

    def source(self, name):
        """'<file>', '<file>#<heading>' (a '## ' section) or '<file>#<label>' (a '**<label>.**' paragraph or a
        '- **<label>.**' bullet), where <file> is 'SKILL.md' or the shared reference 'test-criteria.md'."""
        file, _, label = name.partition("#")
        text = {"SKILL.md": self.COMMAND, "test-criteria.md": self.CRITERIA}[file].read_text(encoding="utf-8")
        if not label:
            return text
        if f"\n## {label}\n" in text:
            return text.split(f"\n## {label}\n", 1)[1].split("\n## ", 1)[0]
        if f"\n- **{label}.**" in text:
            return next(line for line in text.splitlines() if line.startswith(f"- **{label}.**"))
        return next(p for p in text.split("\n\n") if p.startswith(f"**{label}.**"))

    PINS = {
        "SKILL.md": (
            # docs/specs/test-speedup-record.md, ticket 02: the reserved words, `./`, `--full` and the report-only
            # paragraph's new wording.
            "Invocation arguments are the scope as data, never shell code, except that a first word `show` or `prune` selects that form of the command, as [Show and prune](#show-and-prune) describes.",
            "`--full` asks for a full analysis of the scope.",
            "A scope path that is a reserved word is written with `./`, such as `./show` or `./prune`.",
            "Clarify a missing or unclear scope instead of guessing.",
            "This command changes no code, test or configuration and commits nothing.",
            "The only files it writes are those of its Speed-up record, through the bundled script, after every run, without asking.",
            "Writing the record is not a change to the checkout and needs no Checkout lease.",
            "A failed write is reported, and the report stays in the conversation.",
            "Items the user picks become a Plan through the normal flow; the report is not a Plan, and its items are neither Claims nor findings of any review.",
        ),
        "SKILL.md#Whole files": (
            "**Whole files.** A scope that names a test inside a file is widened to that file for the static pass and the record.",
        ),
        "SKILL.md#Scope": (
            "The scope is the tests the arguments name, or else the project's tests, together with their test configuration: test runner configuration, shared fixtures and setup files, test scripts and their flags.",
            "CI pipeline configuration is outside the scope.",
        ),
        "SKILL.md#Who analyses": (
            "When delegation is installed and the check is not small, main dispatches the read-only analyst as [the delegation skill](../delegation/SKILL.md) describes, in one or more Assignments split by test area, and integrates their results.",
            "A small check, such as one test file, or a check where delegation is not installed, main does itself.",
            "An analyst Assignment names the test files to analyse and does not include the record.",
            "Main alone runs the script, matches the analyst's items against the record and applies the state rules.",
        ),
        "SKILL.md#Speed-up record": (
            "Every writing command takes the store version main last read with `--version`; on `changed`, main reads the record again, merges its own update and writes again.",
            "Main passes these version sources to both `changes`, whose result shows which versions changed since the last run, and `record-run`.",
        ),
        "SKILL.md#State rules": (
            "**State rules.** New items are undecided.",
            "Main makes an item picked or declined only from the User's answer, passing its date and reason to the script's `decide`.",
            "For a recorded item not found again in an analysed file, main reads the code at the item's location: it marks the item landed when the code shows the item's change, obsolete when the item's test or setting no longer exists or the concern no longer applies, each with its evidence, and leaves the state unchanged when it cannot tell.",
            "A declined item found again is proposed again only when its file's content hash differs from the one recorded at the decision; otherwise it is proposed again only when the user asks.",
            "A reopened item is shown with its earlier state, date and reason.",
        ),
        "SKILL.md#Incremental static pass": (
            "**Incremental static pass.** Before the static pass, main gets the scope's changes from the script's `changes`, naming each test file in the scope with its shared files: the shared fixtures, setup files, test runner configuration and test scripts within the scope that it is analysed with.",
            "The test files to analyse are the new and changed ones, and those whose shared-set hash differs; among the latter, main analyses only those that use a changed shared file when it can tell, and all of them when it cannot.",
            "A change to the code under test, or to a library the tests import, does not by itself add a file.",
            "Without a record, or with `--full`, the whole scope is analysed; `--full` keeps every item's state.",
        ),
        "SKILL.md#Run configuration every run": (
            "**Run configuration every run.** The check for Unbounded run configurations runs on the whole scope every run, with its lookups, and its items are matched against the record like any others.",
        ),
        "SKILL.md#Upgrade review on request": (
            "**Upgrade review on request.** When the user asks for a review of a test runner or plugin upgrade, main looks up the changes between the two versions in the lookups' order, and reports only those concerning defaults of concurrency, isolation, memory or time, new features that could speed the tests up, fixed bugs the tests or configuration work around, and deprecated or renamed settings the configuration uses, each with its source, the version it applies to and the locations it may affect; the adjustments become Speed-up items.",
            "A query sent outside for it may carry the framework's name, both versions and a setting's name, and nothing else.",
        ),
        "SKILL.md#Show and prune": (
            "`show` passes its arguments to the script's `show` and relays the result; it changes nothing and runs no test.",
            "`prune` runs the dry run, shows it, and removes only after the user confirms in the conversation.",
            "Main passes the confirmed dry run's version with the same selection, so only what the user saw is removed; on `changed`, main shows a new dry run instead and removes nothing until the user confirms it.",
            "Undecided, picked and declined items are never selected, and there is no reset of the whole record.",
        ),
        "SKILL.md#1. Static pass": (
            "The static pass always comes first and runs nothing.",
            "Look for what [the shared test criteria](references/test-criteria.md)'s Speed criteria and Further criteria list, a further criterion only where its condition holds.",
        ),
        "SKILL.md#Correctness bar": (
            "**Correctness bar.** Every speed-up and removal meets [the shared test criteria](references/test-criteria.md)'s Correctness bar, smaller inputs and replacements included.",
        ),
        "test-criteria.md": (
            "The criteria in this reference say what makes a test slower or less robust than it needs to be, and its correctness bar says what a change to an existing test keeps.",
            "A skill that writes, reviews or changes tests points to this reference and does not restate it.",
        ),
        "test-criteria.md#Rules this relies on": (
            "Whether a test or a test run is unbounded is decided by the Unbounded probe and Unbounded run configuration entries in [cc-feather's glossary](../../../CONTEXT.md), and which suites a check runs by its Test suite catalogue and Related-test acceptance entries.",
            "How a finding is weighed, how a test with resource risk is run and how work is reviewed are [the delegation skill](../../delegation/SKILL.md)'s rules.",
            "This reference copies none of them.",
        ),
        "test-criteria.md#Speed criteria": (
            "A test is slower than it needs to be where it has:",
            "- per-test setup that can be shared per module or session;",
            "- fixed sleeps that can wait on an event or a condition;",
            "- real I/O, such as network, disk, processes or databases, that a fake can replace;",
            "- tests that can run in parallel;",
            "- inputs, data sets, iteration counts and fixtures larger than the behaviour needs, which a smaller one can verify;",
            "- behaviour tested again at several levels.",
        ),
        "test-criteria.md#Further criteria": (
            "Each criterion applies under the condition it states, and only there.",
        ),
        "test-criteria.md#No DOM where none is needed": (
            "A frontend test that needs no DOM runs without a DOM environment, such as jsdom or happy-dom.",
            "It applies to a frontend test whose code under test renders no component and uses no DOM or browser API.",
        ),
        "test-criteria.md#Port 0": (
            "A test server binds port 0 rather than a fixed port, and the test reads the port it was given.",
            "It applies to every test that starts a listening server, unless the fixed port is what the test verifies.",
        ),
        "test-criteria.md#Waits with a timeout": (
            "A wait on a channel, promise or condition has a timeout, so that a missing event fails the test instead of hanging it.",
            "It applies to every such wait in a test or its setup that blocks until another goroutine, thread, process or callback acts.",
        ),
        "test-criteria.md#Limited output": (
            "Collected output has a limit.",
            "It applies wherever a test or its setup keeps output it collects, such as a child process's output, logs or captured events, whose size nothing else bounds.",
        ),
        "test-criteria.md#Cleanup on failure paths": (
            "Failure paths clean up goroutines, connections and transactions, as the success path does.",
            "It applies to every test or fixture that starts a goroutine, opens a connection or begins a transaction, and is met by cleanup that runs however the test ends, such as `t.Cleanup`, `defer`, a `finally` block or a fixture's teardown.",
        ),
        "test-criteria.md#Fixed sleeps": (
            "A fixed sleep becomes an event or condition wait, or a fake clock where it verifies the same logic, with real elapsed time kept only when real scheduling or clock integration is the property.",
            "It applies to every fixed sleep in a test or its setup.",
        ),
        "test-criteria.md#Correctness bar": (
            "The correctness bar governs changes to existing tests, speed-ups and removals alike: weakening an assertion, adding a skip, loosening a timeout and reducing generated cases are never offered there.",
            "Each speed-up names the test or assertion that keeps verifying the behaviour it touches.",
            "A speed-up keeps every assertion, test and timeout at least as strict as it is now: weakening an assertion, adding a skip or loosening a timeout is never offered.",
            "A smaller input is offered only when size is not what the test verifies.",
            "A test of performance, of a limit or boundary of size, of a race or concurrency that needs many iterations, or one that generates property-based or fuzz cases keeps its size; reducing the number of generated cases counts as weakening and is never offered.",
            "A smaller-input speed-up names the test that keeps verifying every boundary value the larger input reached.",
            "Removing a test is offered only in the Removals section, each removal either naming the test that covers exactly the same behaviour as evidence or being a replacement, for the user to decide one by one, replacements included.",
            "A replacement describes a smaller test that verifies the same fact and states that fact, then lists everything else the removed test verifies, such as wiring between components, routing or configuration loading, each item with the existing test that keeps verifying it.",
            "A replacement with any item lacking such a test is not offered.",
            "The smaller test is described in the report, not written; a picked replacement's Plan writes it before the heavy test is removed.",
        ),
        "SKILL.md#Existing tests with resource risk": (
            "In a section of its own, list the existing tests that meet the criteria of an Unbounded probe in [cc-feather's glossary](../../CONTEXT.md), applied without a budget since the static pass runs nothing.",
            "Weigh each one as [the delegation skill](../delegation/SKILL.md)'s paragraph on weighing findings describes.",
            "The list is information: it holds nothing back, and the Unbounded probe term and the delegation rules for it are unchanged.",
        ),
        "SKILL.md#Run configurations with resource risk": (
            "The static pass also checks the settings and run parameters within the scope that do not belong to the tests' code, above all those concerning concurrency, isolation, memory and time, for each Unbounded run configuration in [cc-feather's glossary](../../CONTEXT.md).",
            "Each setting is judged by the value in effect, a framework's default included, and a value that cannot be established counts as none.",
            "The scope stays as it is, so CI pipeline configuration stays outside the check.",
            "Hints, as examples and not a closed list: concurrency that is uncapped or follows the machine's core count, such as vitest `pool` and `maxWorkers`, `go test -p` or pytest-xdist `-n auto`; a worker pool or isolation mode known to grow memory, such as vitest `vmThreads` and `vmForks`; per-worker heap settings, such as a raised Node heap limit; multipliers of the run's work, such as retries or `go test -count`; heavy instrumentation, such as `-race` or coverage, on uncapped concurrency; and a limit switched off or absent, such as a zero timeout, a test script in watch mode or a framework without a default timeout.",
            "Weigh each flagged setting as [the delegation skill](../delegation/SKILL.md)'s paragraph on weighing findings describes.",
        ),
        "SKILL.md#Lookups": (
            "Defaults and known problems of the frameworks in scope are looked up only for settings concerning concurrency, isolation, memory and time, in this order: the installed version's own files, such as its bundled documentation or type definitions, read and never run; the official documentation and changelog; the official issue tracker.",
            "A query sent outside carries only the framework's name, its version and the setting's name.",
            "Each conclusion names its source and the version it applies to, and what cannot be found is reported as unknown, which counts as no bound.",
            "The static pass still runs nothing: a fact only a command shows, such as `go help testflag`'s output, is reported as unknown there, and the measurement offer may name that command, which then runs only with the user's agreement under the same rules as measurement.",
            "The lookups follow the Who analyses split: analyst does them in its Assignments when delegation is installed and the check is not small, and main does them otherwise.",
        ),
        "SKILL.md#Parallel speed-ups": (
            "A speed-up that raises concurrency states the worker count it leads to and its memory effect.",
            "A worker count that follows the machine's core count is never offered.",
        ),
        "SKILL.md#2. Report": (
            "**Speed-ups**, ordered by expected gain, each with its location, kind, expected gain (high, medium or low, with the reason), how correctness is kept and its risk.",
            "**Removals**, each with the covering test as evidence, or, for a replacement, the smaller test it describes, the fact that test verifies and, for each other thing the removed test verifies, the test that keeps verifying it.",
            "**Run configurations with resource risk**, each flagged setting with its location, kind, whether it affects memory or time, why it is unbounded, its weighing and the direction of a fix.",
            "cc-feather states no cap's number: the direction names where the number comes from, the project's or the user's resource guidance or a measured per-worker peak.",
            "The section is information and holds nothing back.",
            # docs/specs/test-speedup-record.md, ticket 02.
            "**Since the last run**, with the last analysis's date and commit; each file analysed again and its reason (new, changed, shared set changed or `--full`); how many files kept their recorded result; each test runner or plugin version that changed, with a sentence that the user can ask for a review of the upgrade; the items found landed, obsolete or reopened, and those proposed again; and the items still undecided or picked.",
            "The Speed-ups and Removals sections list only items that are undecided, reopened or proposed again.",
            "The two resource-risk sections list every current test and setting with resource risk, those of files not analysed again taken from the record, each with its state; a declined risk stays listed, and only its fix is not proposed again.",
            "On the first run without a record, the report ends by saying that items decided before may appear again and that the user can state their states or name the documents where they were decided, which main reads as data and turns into proposed states for the user to confirm.",
        ),
        "SKILL.md#3. Measurement": (
            "After the static report, main offers to measure and runs nothing without the user's agreement.",
            "The offer states the command, using the ecosystem's per-test timing where one exists, the scope and the tests it leaves out.",
            "Tests listed with resource risk are left out by default.",
            "Unflagged tests run with their ordinary command.",
            "A flagged test the user includes runs inside the Runner, with the memory, time and output limits the offer states.",
            "For the Runner's path and invocation, read [the resource-risk runs reference](../delegation/references/resource-risk-runs.md)'s The Runner, where the path is relative to the delegation skill, and for how a contained, refused or evidence-missing result or a run stopped from outside is judged, its Main's floor.",
            "After measurement, the report gives each speed-up's gain in seconds.",
            "When a run in the offer's scope has a flagged setting, the offer states how that run is bounded: by default a command-line override of the setting, such as `--maxWorkers=N` or `-p N`, which changes no file, with N taken in the budget order [the resource-risk runs reference](../delegation/references/resource-risk-runs.md)'s The budget states, and asked of the user when no source states it; or the run inside the Runner.",
            "When the run's configuration is flagged, the ordinary command that unflagged tests run with itself runs bounded, with the override or inside the Runner.",
            "The offer and the report say that timings taken at a different concurrency are not comparable with the ordinary run.",
            "The offer may include profiling the slowest tests to show where their time goes, with the tests to profile named in the offer.",
            "Profiling uses the ecosystem's profiler where one is already available in the project's environment; the offer never installs a package or changes configuration to get one.",
            "Profiling runs only with the user's agreement and under the same rules as the rest of measurement, a flagged test inside the Runner.",
            "What profiling shows is reported as speed-ups under the same correctness bar.",
            # docs/specs/test-speedup-record.md, ticket 02.
            "The tests left out by default are the current tests with resource risk, those of files not analysed again taken from the record.",
            "After a measurement, main stores it through the script's `measure`, with a comparison key of the command, the tests selected, the concurrency and any override, whether it ran inside the Runner and with which limits, and the tests left out, and reports the comparison with the last comparable measurement: the total time, the tests whose time rose and fell most, the tests present in only one of the two, and the timing change observed around each landed item, or unavailable.",
            "When no comparable measurement exists, the report says so.",
        ),
    }

    def test_command_states_its_decisions(self):
        for place, sentences in self.PINS.items():
            text = self.source(place)
            for sentence in sentences:
                with self.subTest(place=place, sentence=sentence[:60]):
                    self.assert_whole_sentence(sentence, text)

    def test_the_report_has_five_sections(self):
        report = self.source("SKILL.md#2. Report")
        self.assertIn("The report has five sections:\n", report)
        for count in ("three sections", "four sections"):
            with self.subTest(count=count):
                self.assertNotIn(count, self.source("SKILL.md"))
        sections = [line.split("**")[1] for line in report.splitlines() if line.startswith("- **")]
        self.assertEqual(sections, ["Since the last run", "Speed-ups", "Removals", "Existing tests with resource risk",
                                    "Run configurations with resource risk"])

    def test_run_configuration_hints_leave_out_output_and_outside_services(self):
        hints = self.source("SKILL.md#Run configurations with resource risk")
        for kind in ("output volume", "container runtime", "database"):
            with self.subTest(kind=kind):
                self.assertNotIn(kind, hints)

    def test_the_budget_order_the_measurement_points_to_exists(self):
        runs = (SKILLS / "delegation" / "references" / "resource-risk-runs.md").read_text(encoding="utf-8")
        execution = runs.split("\n## Execution method\n", 1)[1].split("\n## ", 1)[0]
        self.assertIn("\n- **The budget.** The budget comes, in order,", execution)
        self.assertNotIn("The budget comes, in order,", self.source("SKILL.md"))

    def test_removals_keep_no_expected_gain_order(self):
        report = self.source("SKILL.md#2. Report")
        removals = next(line for line in report.splitlines() if line.startswith("- **Removals**"))
        self.assertNotIn("expected gain", removals)
        self.assertNotIn("ordered", removals)

    def test_detection_hints_name_each_ecosystem(self):
        hints = next(p for p in self.source("SKILL.md#1. Static pass").split("\n\n") if p.startswith("Detection hints:"))
        for ecosystem in ("Go", "Python", "pnpm", "Vue"):
            with self.subTest(ecosystem=ecosystem):
                self.assertIn(ecosystem, hints)

    def test_linked_rules_exist_and_are_not_restated(self):
        delegation = (SKILLS / "delegation" / "SKILL.md").read_text(encoding="utf-8")
        weighing = next(p for p in delegation.split("\n\n") if p.startswith("Before proposing or adopting a requirement"))
        runs = (SKILLS / "delegation" / "references" / "resource-risk-runs.md").read_text(encoding="utf-8")
        self.assertIn("\n## The Runner\n", runs)
        self.assertIn("\n## Main's floor\n", runs)
        self.assertIn("**Unbounded probe**:", (config.ROOT / "CONTEXT.md").read_text(encoding="utf-8"))
        command = " ".join(self.source("SKILL.md").split())
        for sentence in feather_support.sentences(weighing):
            with self.subTest(sentence=sentence[:60]):
                self.assertNotIn(sentence, command)
        # The Runner's invocation and the floor's criteria live in the reference and the glossary, not here.
        self.assertNotIn("--memory-mib", command)
        self.assertNotIn("a timeout alone is not a bound", command)

    SHARED_PARTS = ("Speed criteria", "Further criteria", "Correctness bar")

    def shared_statements(self):
        """Each sentence or list item of the shared criteria, with its bullet marker and bold label taken off."""
        for part in self.SHARED_PARTS:
            for line in self.source(f"test-criteria.md#{part}").splitlines():
                line = re.sub(r"^- (\*\*[^*]+\*\* )?", "", line.strip())
                for sentence in feather_support.sentences(line):
                    yield part, sentence.rstrip(";")

    def test_the_command_restates_none_of_the_shared_criteria(self):
        command = " ".join(self.source("SKILL.md").split())
        statements = list(self.shared_statements())
        # Every speed criterion, further criterion and sentence of the bar is checked, not only a sample.
        self.assertGreaterEqual(len(statements), 30)
        for part, statement in statements:
            with self.subTest(part=part, statement=statement[:60]):
                self.assertNotIn(statement, command)
        for part in self.SHARED_PARTS:
            with self.subTest(heading=part):
                self.assertNotIn(f"\n## {part}\n", self.source("SKILL.md"))

    def test_the_further_criteria_are_six_each_with_its_condition(self):
        further = self.source("test-criteria.md#Further criteria")
        labels = [line.split("**")[1] for line in further.splitlines() if line.startswith("- **")]
        self.assertEqual(labels, ["No DOM where none is needed.", "Port 0.", "Waits with a timeout.", "Limited output.",
                                  "Cleanup on failure paths.", "Fixed sleeps."])
        for label in labels:
            with self.subTest(criterion=label):
                self.assertIn(" It applies ", self.source(f"test-criteria.md#{label[:-1]}"))

    def test_the_shared_reference_points_to_the_rules_it_relies_on_and_copies_none(self):
        text = self.source("test-criteria.md")
        flat = " ".join(text.split())
        for link, target in (("../../../CONTEXT.md", config.ROOT / "CONTEXT.md"),
                             ("../../delegation/SKILL.md", SKILLS / "delegation" / "SKILL.md")):
            with self.subTest(link=link):
                self.assertIn(f"]({link})", text)
                self.assertEqual((self.CRITERIA.parent / link).resolve(), target.resolve())
        entries = feather_support.glossary_entries((config.ROOT / "CONTEXT.md").read_text(encoding="utf-8"))
        delegation = (SKILLS / "delegation" / "SKILL.md").read_text(encoding="utf-8")
        weighing = next(p for p in delegation.split("\n\n") if p.startswith("Before proposing or adopting a requirement"))
        copied = [*feather_support.sentences(weighing)]
        for term in ("Unbounded probe", "Unbounded run configuration", "Test suite catalogue",
                     "Related-test acceptance"):
            self.assertIn(term, flat)
            copied += [s for s in feather_support.sentences(entries[term].split("\n_Avoid_")[0])]
        for sentence in copied:
            with self.subTest(sentence=sentence[:60]):
                self.assertNotIn(sentence, flat)
        self.assertNotIn("--memory-mib", flat)
        self.assertNotIn("a timeout alone is not a bound", flat)
        # Written for any skill that points to it: it names no command.
        for command in ("test-speedup", "test-design", "overdesign-check"):
            with self.subTest(command=command):
                self.assertNotIn(command, text)

    SPEEDUP_ENTRIES = {
        "Speed-up record": (
            "A repository's record of `/cc-feather:test-speedup`: for each test file it analysed, the content and the "
            "set of shared files it was last analysed with; its Speed-up items; its analysis runs with the test runner "
            "versions they read; and its measurements. It is kept under the main worktree's `.feather/test-speedup/`, "
            "or under the project directory of a non-Git project, ignored by Git, and is one of cc-feather's own "
            "records, not a change to the checkout.\n_Avoid_: baseline, speedup log, cache"),
        "Speed-up item": (
            "One speed-up, removal, test with resource risk or run configuration with resource risk from a "
            "`/cc-feather:test-speedup` report, recognised across runs by its file, its kind and the test ids or "
            "setting it concerns, with its state: undecided, picked, declined, landed or obsolete. Only the User's "
            "answer makes it picked or declined.\n_Avoid_: finding, suggestion, ticket"),
    }

    def test_glossary_defines_the_speedup_record_and_item_in_the_design_checks_section(self):
        """docs/specs/test-speedup-record.md, ticket 01."""
        text = (config.ROOT / "CONTEXT.md").read_text(encoding="utf-8")
        entries = feather_support.glossary_entries(text)
        section = text.split("\n## Design checks\n", 1)[1].split("\n## ", 1)[0]
        for term, body in self.SPEEDUP_ENTRIES.items():
            with self.subTest(term=term):
                self.assertEqual(entries[term].strip(), body)
                self.assertIn(f"\n**{term}**:\n", section)

    README_LISTINGS = {
        "README.md": "- `/cc-feather:test-speedup [show | prune | --full] [test paths or scope]`: report ways to make the tests, or the part you name, faster without weakening what they verify; only you can run it, and it changes no code, test or configuration and writes only its own record, which Git ignores. It analyses statically first, lists existing tests that could exhaust memory or time, and measures only after you agree; see the [reference](docs/reference.md#design-and-test-checks).",
        # The table cell escapes the hint's `|` so that it renders as one cell.
        "README.zh-TW.md": "| `/cc-feather:test-speedup [show \\| prune \\| --full] [測試路徑或範圍]` | 找出讓測試（或你指定的部分）變快、又不削弱驗證內容的方法；只能由你執行，不改任何程式碼、測試或設定，只寫入它自己的紀錄，Git 會忽略這份紀錄。先做靜態分析，列出可能耗盡記憶體或時間的既有測試，經你同意才量測；見[參考文件](docs/reference.zh-TW.md#設計與測試檢查) |",
    }

    # Each reference section is the text under its heading up to the next heading; sentences are paired by language.
    REFERENCE_SECTIONS = {
        "reference.md": ("\n## Design and test checks\n", "\n### Test speed-ups\n"),
        "reference.zh-TW.md": ("\n## 設計與測試檢查\n", "\n### 測試加速\n"),
    }
    REFERENCE_PAIRS = (
        # docs/specs/test-design.md, ticket 02: the section's third command.
        ("Three commands only you can run help with a project's design and tests: two report weight that has built up in a project, and the third proposes the tests a target needs.",
         "三個只能由你執行的指令協助處理專案的設計與測試：兩個回報專案裡累積下來的負擔，第三個提出一個對象需要的測試。"),
        # docs/specs/test-speedup-record.md, ticket 02: test-speedup writes only its own record.
        ("Each only reports, and what you pick from its report becomes a plan through the normal flow.",
         "它們只出報告，你從報告中挑選的項目，再照一般流程成為計畫。"),
        ("`/cc-feather:overdesign-check` and `/cc-feather:test-design` change no file, and `/cc-feather:test-speedup` changes no code, test or configuration and writes only its own record, which Git ignores.",
         "`/cc-feather:overdesign-check` 與 `/cc-feather:test-design` 不改任何檔案，`/cc-feather:test-speedup` 不改任何程式碼、測試或設定，只寫入它自己的紀錄，Git 會忽略這份紀錄。"),
        ("`/cc-feather:test-speedup` checks the tests you name, or the project's tests, with their test configuration but not CI pipeline configuration.",
         "`/cc-feather:test-speedup` 檢查你指定的測試，或整個專案的測試，連同測試設定，但不含 CI pipeline 設定。"),
        ("It analyses statically first and runs nothing: each speed-up names the test or assertion that keeps verifying what it touches, speed-ups are ordered by expected gain, and weakening an assertion, adding a skip or loosening a timeout is never offered.",
         "它先做靜態分析，不執行任何東西：每條加速建議都指出由哪個測試或斷言繼續驗證它動到的行為，依預期效益排序，而且從不建議削弱斷言、加上 skip 或放寬 timeout。"),
        ("It also looks for inputs, data sets, iteration counts and fixtures larger than the behaviour needs, and offers a smaller one only when size is not what the test verifies, naming the test that keeps verifying every boundary the larger input reached; fewer generated property-based or fuzz cases count as weakening and are never offered.",
         "它也會找出比行為所需更大的輸入、資料集、迭代次數與 fixture，只有在大小不是測試要驗證的對象時才建議改小，並指出由哪個測試繼續驗證較大輸入涵蓋到的每個邊界；減少產生的 property-based 或 fuzz 案例算是削弱，從不建議。"),
        ("Removing a test is offered only in a section of its own, with the covering test as evidence or as a replacement, for you to decide one by one.",
         "刪除測試只列在獨立的一節，附上涵蓋相同行為的測試作為證據，或以替換的形式提出，由你逐條決定。"),
        ("A replacement describes a smaller test that verifies the same fact and lists everything else the heavy test verifies, such as wiring between components, routing or configuration loading, each with the existing test that keeps verifying it; when anything has no such test, the replacement is not offered.",
         "替換會描述一個驗證同一事實的較小測試，並列出較重的測試還驗證的其他每件事，例如元件之間的接線、路由或設定載入，各附上繼續驗證它的既有測試；只要有一件沒有這樣的測試，就不提出這項替換。"),
        # docs/specs/test-design.md, ticket 01: the new checks.
        ("It also checks, each where its condition holds, that a frontend test that needs no DOM runs without a DOM environment, that a test server binds port 0, that a wait on a channel, promise or condition has a timeout, that collected output has a limit and that failure paths clean up goroutines, connections and transactions.",
         "它也會在各自的適用條件成立時檢查：不需要 DOM 的前端測試不使用 DOM 環境、測試用的 server 綁定 port 0、等待 channel、promise 或條件時設有 timeout、收集的輸出有上限，以及失敗路徑會清理 goroutine、連線與 transaction。"),
        ("A fixed sleep becomes an event or condition wait, or a fake clock where that verifies the same logic; real elapsed time stays only when real scheduling or clock integration is what the test verifies.",
         "固定的 sleep 改為等待事件或條件，或在能驗證同樣邏輯時改用 fake clock；只有當真實的排程或時鐘整合正是要驗證的性質時，才保留真實經過的時間。"),
        ("Another section lists existing tests that meet the Unbounded probe criteria, as information that holds nothing back.",
         "另一節列出符合 Unbounded probe 判準的既有測試，只供參考，不擋任何事。"),
        ("It also checks the settings and run parameters that do not belong to the tests' code, above all those concerning concurrency, isolation, memory and time, for an Unbounded run configuration, judged by the value in effect, a framework's default included, with a value it cannot establish counting as none.",
         "它也會檢查不屬於測試程式碼本身的設定與執行參數，尤其是與並行、隔離、記憶體和時間有關的部分，找出 Unbounded run configuration；判斷依據是實際生效的值，包括框架的預設值，無法確定的值視為沒有上限。"),
        ("It looks up defaults and known problems in the installed version's own files, read and never run, then the official documentation and changelog, then the official issue tracker; a query sent outside carries only the framework's name, its version and the setting's name, each conclusion names its source and version, and what it cannot find is reported as unknown.",
         "它依序查詢預設值與已知問題：先看已安裝版本自帶的檔案，只讀不執行，再看官方文件與 changelog，最後看官方 issue tracker；送到外部的查詢只帶框架名稱、版本與設定名稱，每個結論都註明來源與版本，查不到的就回報為未知。"),
        ("A speed-up that raises concurrency states the worker count it leads to and its memory effect, and a worker count that follows the machine's core count is never offered.",
         "提高並行度的加速建議會說明它造成的 worker 數量與對記憶體的影響，從不建議依機器核心數決定 worker 數量。"),
        # docs/specs/test-speedup-record.md, ticket 02: the section is named by its title, not its position.
        ("The section Run configurations with resource risk lists each flagged setting with its location, kind, whether it affects memory or time, why it is unbounded, its weighing and the direction of a fix, as information that holds nothing back; cc-feather states no cap's number.",
         "「有資源風險的執行設定」一節列出每個被標出的設定，附上位置、種類、影響記憶體還是時間、為何沒有上限、權衡結果與修正方向，只供參考，不擋任何事；cc-feather 不提供任何上限的數字。"),
        ("Then main offers to measure, stating the command, the scope and the tests it leaves out, and runs nothing until you agree; tests with resource risk are left out unless you include them, and then run inside the Runner.",
         "之後主 Agent 才提議量測，說明指令、範圍與排除的測試，經你同意才執行；有資源風險的測試預設排除，你決定納入時改在 Runner 內執行。"),
        ("When a run's configuration is flagged, the measurement bounds it with a command-line override that changes no file, its number taken as the budget rules take one or asked of you when no source states it, or runs it inside the Runner, and says that timings taken at a different concurrency are not comparable with your ordinary run.",
         "執行設定被標出時，量測會用不改任何檔案的命令列覆寫來限制它，數字依預算規則取得，沒有來源說明時就問你，或改在 Runner 內執行；並說明在不同並行度下量到的時間不能和你平常的執行相比。"),
        ("The measurement may include profiling the slowest tests the offer names, with a profiler the project's environment already has, to show where their time goes; it too runs only after you agree, and what it shows is reported as speed-ups that keep what the tests verify.",
         "量測也可以對提議中列出的最慢測試做 profiling，使用專案環境中已有的 profiler，找出時間花在哪裡；它同樣經你同意才執行，結果以加速建議回報，同樣不削弱測試驗證的內容。"),
        ("With delegation installed, analyst does the reading.",
         "裝有分派元件時，由 analyst 負責閱讀分析。"),
        # docs/specs/test-speedup-record.md, ticket 02: the record, the incremental pass and whole files, the run
        # configuration every run, the item states, Since the last run, versions and the upgrade review, the
        # measurement comparison, `show`, `prune` and `--full`.
        ("It keeps a Speed-up record for the repository under the main worktree's `.feather/test-speedup/`, or under the project directory outside Git, which Git ignores and which it writes after every run without asking; writing it needs no Checkout lease.",
         "它為儲存庫保存一份 Speed-up record，放在 main worktree 的 `.feather/test-speedup/` 下，不在 Git 中的專案則放在專案目錄下；Git 會忽略這份紀錄，它在每次執行後自動寫入，不必詢問；寫入它不需要 Checkout lease。"),
        ("A run analyses only the test files that are new, whose content changed, or whose shared fixtures, setup files, test runner configuration or test scripts changed since the record last analysed them, and the rest keep their recorded result; a change to the code under test or to a library does not by itself start a new analysis, and a test file is always analysed whole.",
         "每次執行只分析新的測試檔、內容改變的測試檔，以及自紀錄上次分析以來共用 fixture、setup 檔、test runner 設定或測試 script 改變的測試檔，其餘沿用紀錄中的結果；受測程式碼或函式庫的變更本身不會觸發重新分析，而且測試檔一律整個分析。"),
        ("The check for an Unbounded run configuration still runs on the whole scope every run.",
         "Unbounded run configuration 的檢查仍在每次執行時涵蓋整個範圍。"),
        ("Each item in the record is undecided, picked, declined, landed or obsolete: only your answer picks or declines one, a declined item comes back only when its file's content changed since you decided or when you ask, main marks one landed or obsolete only after checking the code, and one that shows up again after that is reopened as undecided with its earlier state shown.",
         "紀錄中的每個項目都處於 undecided、picked、declined、landed 或 obsolete 其中一種狀態：只有你的回答能 pick 或 decline 一個項目；declined 的項目只有在你決定之後它的檔案內容改變，或你要求時才會再提出；主 Agent 確認過程式碼後才把項目標為 landed 或 obsolete，之後若又出現，就重新開啟為 undecided，並顯示它先前的狀態。"),
        ("The report starts with a section, Since the last run, that says which files were analysed again and why, which items were found landed, obsolete or reopened or are proposed again, and which are still undecided or picked; the two resource-risk sections list every current test and setting with resource risk, whatever its state.",
         "報告以「自上次執行以來」一節開頭，說明哪些檔案重新分析及原因、哪些項目被判定為 landed、obsolete 或重新開啟，或再次提出，以及哪些仍是 undecided 或 picked；有資源風險的兩節列出目前每個有資源風險的測試與設定，不論它的狀態。"),
        ("The record keeps the versions of the test runner and its plugins, and when one changed, the report says so; when you ask, main reviews what the upgrade changed for the tests, a query sent outside carrying only the framework's name, both versions and a setting's name.",
         "紀錄保存 test runner 與其 plugin 的版本，版本改變時報告會指出；你要求時，主 Agent 會檢視這次升級對測試造成的改變，送到外部的查詢只帶框架名稱、兩個版本與設定名稱。"),
        ("Each measurement is kept with a comparison key of its command, selected tests, concurrency and overrides, Runner limits and the tests left out, and compared only with the last one under the same key: the total time, the tests that became slowest and fastest, and the timing change observed around each landed item.",
         "每次量測都連同比較鍵保存，比較鍵包括指令、選定的測試、並行度與覆寫、Runner 限制以及排除的測試；只和同一比較鍵的上一次量測相比：總時間、變得最慢與最快的測試，以及每個 landed 項目前後觀察到的時間變化。"),
        ("`/cc-feather:test-speedup show` summarises the record and lists the other forms of the command, `prune` removes old measurements and finished items after a dry run you confirm and never removes an undecided, picked or declined item, and `--full` analyses the whole scope again while keeping every item's state.",
         "`/cc-feather:test-speedup show` 摘要這份紀錄並列出指令的其他形式；`prune` 在你確認試跑結果後移除舊的量測與已完成的項目，從不移除 undecided、picked 或 declined 的項目；`--full` 重新分析整個範圍，並保留每個項目的狀態。"),
        ("See [the command](../skills/test-speedup/SKILL.md).",
         "見[指令](../skills/test-speedup/SKILL.md)。"),
    )

    def reference_text(self, name):
        text = feather_support.REFERENCE_FILES[name].read_text(encoding="utf-8")
        start, sub = self.REFERENCE_SECTIONS[name]
        section = text.split(start, 1)[1].split("\n## ", 1)[0]
        self.assertIn(sub, section)
        return section

    def test_readmes_and_references_describe_the_command_in_both_languages(self):
        for name, listing in self.README_LISTINGS.items():
            with self.subTest(listing=name):
                self.assertIn(listing + "\n", (config.ROOT / name).read_text(encoding="utf-8"))
        for english, chinese in self.REFERENCE_PAIRS:
            for name, sentence in (("reference.md", english), ("reference.zh-TW.md", chinese)):
                with self.subTest(place=name, sentence=sentence[:40]):
                    self.assert_whole_sentence(sentence, self.reference_text(name))

    def test_the_old_wording_is_gone(self):
        """docs/specs/test-speedup-record.md, ticket 02: the replaced sentences are not left beside their successors."""
        self.assertNotIn("This command only reports:", self.source("SKILL.md"))
        self.assertNotIn("a file is written only when the user asks for one", self.source("SKILL.md"))
        for name, old in (("reference.md", "A fourth section lists"), ("reference.zh-TW.md", "第四節列出"),
                          ("reference.md", "Each only reports and changes no file"),
                          ("reference.zh-TW.md", "它們只出報告、不改任何檔案")):
            with self.subTest(place=name, old=old):
                self.assertNotIn(old, self.reference_text(name))

    def test_the_skill_is_packaged_and_names_its_launcher(self):
        """docs/specs/test-speedup-record.md, ticket 02: as PackagingTest does for the lease tool."""
        self.assertIn("./skills/test-speedup", manifest_skills())
        text = self.COMMAND.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\nname: test-speedup\n"), text[:40])
        self.assertIn("`scripts/speedup.py`", text)
        self.assertIn("${CLAUDE_PLUGIN_ROOT}/skills/test-speedup/scripts/speedup.py", text)
        self.assertTrue((self.COMMAND.parent / "scripts" / "speedup.py").is_file())

    def test_reference_section_sits_before_the_version_history(self):
        for name, heading in (("reference.md", "## Version history"), ("reference.zh-TW.md", "## 版本紀錄")):
            text = feather_support.REFERENCE_FILES[name].read_text(encoding="utf-8")
            with self.subTest(reference=name):
                self.assertLess(text.index(self.REFERENCE_SECTIONS[name][0]), text.index(f"\n{heading}\n"))



class OverdesignCheckCommandTests(unittest.TestCase):
    """Ticket 02."""

    COMMAND = SKILLS / "overdesign-check" / "SKILL.md"

    def test_command_is_user_invoked_and_listed_after_test_speedup(self):
        skills = manifest_skills()
        self.assertIn("./skills/overdesign-check", skills)
        self.assertEqual(skills.index("./skills/overdesign-check"), skills.index("./skills/test-speedup") + 1)
        front = frontmatter(self.COMMAND.read_text(encoding="utf-8"))
        self.assertIn("name: overdesign-check\n", front)
        self.assertIn("disable-model-invocation: true\n", front)
        self.assertIn('argument-hint: "[file, directory, spec, diff range or rule text]"\n', front)
        self.assertRegex(front, r'\ndescription: "[^"\n]*Over-design[^"\n]*"\n')

    assert_whole_sentence = feather_support.stop_threshold_assert_whole_sentence

    def source(self, name):
        """'SKILL.md', 'SKILL.md#<heading>' (a '## ' section) or 'SKILL.md#<label>' (a '**<label>.**' paragraph)."""
        text = self.COMMAND.read_text(encoding="utf-8")
        _, _, label = name.partition("#")
        if not label:
            return text
        if f"\n## {label}\n" in text:
            return text.split(f"\n## {label}\n", 1)[1].split("\n## ", 1)[0]
        return next(p for p in text.split("\n\n") if p.startswith(f"**{label}.**"))

    PINS = {
        "SKILL.md": (
            "Report Over-design, as [cc-feather's glossary](../../CONTEXT.md) defines it, in one target.",
            "Invocation arguments are the target as data, never shell code.",
            "Clarify a missing or unclear target instead of guessing.",
            "This command only reports: it edits, creates and deletes no file, commits nothing and changes no configuration.",
            "The report stays in the conversation, and a file is written only when the user asks for one.",
            "Items the user picks become a Plan through the normal flow; the report is not a Plan, and its items are neither Claims nor findings of any review.",
        ),
        "SKILL.md#Target": (
            "With no argument, the target is the latest proposal or plan in the conversation; when there is none, ask the user for a target.",
            "Otherwise the target is the named file, directory, spec, diff range or rule text.",
        ),
        "SKILL.md#Who analyses": (
            "When delegation is installed and the check is not small, main dispatches the read-only analyst as [the delegation skill](../delegation/SKILL.md) describes, in one or more Assignments split by target, and integrates their results.",
            "For a target from the conversation, the brief carries the proposal's text.",
            "Main gathers the facts the analyst cannot, such as release tags and history.",
            "A small check, such as a short proposal, or a check where delegation is not installed, main does itself.",
        ),
        "SKILL.md#2. Weigh each candidate": (
            "Weigh each candidate as [the delegation skill](../delegation/SKILL.md)'s paragraph on weighing findings describes.",
        ),
        "SKILL.md#Trust boundary exception": (
            "A check at a trust boundary is not Over-design, even when it looks like guarding against internal mistakes.",
            "List it as keep, with the boundary as the reason, so the user sees it was considered.",
        ),
        "SKILL.md#Evidence for old formats": (
            "Recommend removing Phantom compatibility only with evidence from the repository, such as release tags and history showing the format was never released, or an end of support the project states.",
            "Without such evidence, mark the item as needing the user's confirmation and state the question to ask: whether old data still exists outside the repository is a fact only the user knows.",
        ),
        "SKILL.md#3. Report": (
            "Each item states its location, category, when it occurs, worst outcome, existing coverage, evidence and recommendation: remove, simplify, keep or needs the user's confirmation.",
        ),
    }

    def test_command_states_its_decisions(self):
        for place, sentences in self.PINS.items():
            text = self.source(place)
            for sentence in sentences:
                with self.subTest(place=place, sentence=sentence[:60]):
                    self.assert_whole_sentence(sentence, text)

    OVER_DESIGN = (
        "Code, rules or design kept for cases that neither normal use nor the applicable threat model meets: defending "
        "against states only the project's own code could produce, compatibility with formats or tokens that were never "
        "released or no longer exist anywhere, configuration or extension points with a single user, and several "
        "defences guarding the same case. A check at a trust boundary is not Over-design even when it looks like guarding "
        "against internal mistakes. Whether an old format still exists outside the repository is a fact only the user can "
        "confirm.\n_Avoid_: overengineering, gold-plating, defensive bloat"
    )
    # The 0.35.0 entry, which this feature leaves unchanged.
    UNBOUNDED_PROBE = (
        "A new or modified test or probe, whoever wrote it, any part of which, the input generator, the code under test, "
        "a reference implementation or control, callbacks, measurement, output collection or descendant processes, has no "
        "established bound on total work or retained data, or whose bound allows a peak memory or time that does not fit "
        "the run's budget or, without one, the project's resource guidance. An unknown bound counts as none, and a bounded "
        "input size, a bounded outer loop or a timeout alone is not a bound. A role does not run one and returns it to "
        "main; main runs it only after redesigning it so that every part is bounded within the budget, or inside the "
        "Runner with the budget's limits, never as it is and never with a timeout alone.\n_Avoid_: runaway test, heavy test"
    )

    def test_glossary_defines_over_design_and_keeps_unbounded_probe(self):
        entries = feather_support.glossary_entries((config.ROOT / "CONTEXT.md").read_text(encoding="utf-8"))
        self.assertEqual(entries["Over-design"].strip(), self.OVER_DESIGN)
        self.assertEqual(entries["Unbounded probe"].strip(), self.UNBOUNDED_PROBE)

    def test_categories_are_the_glossary_entrys_four(self):
        categories = self.source("SKILL.md#1. Find candidates")
        for label, meaning in (
            ("Self-made states", "defending against states only the project's own code could produce"),
            ("Phantom compatibility", "compatibility with formats or tokens that were never released or no longer exist anywhere"),
            ("Single-user generality", "configuration or extension points with a single user"),
            ("Stacked defences", "several defences guarding the same case"),
        ):
            with self.subTest(category=label):
                self.assertIn(f"- **{label}**: {meaning}.\n", categories)
                self.assertIn(meaning, self.OVER_DESIGN)

    def test_weighing_is_pointed_to_by_both_commands_and_restated_by_neither(self):
        delegation = (SKILLS / "delegation" / "SKILL.md").read_text(encoding="utf-8")
        weighing = next(p for p in delegation.split("\n\n") if p.startswith("Before proposing or adopting a requirement"))
        for command in (self.COMMAND, TestSpeedupCommandTests.COMMAND):
            text = " ".join(command.read_text(encoding="utf-8").split())
            self.assertIn("[the delegation skill](../delegation/SKILL.md)'s paragraph on weighing findings", text)
            for sentence in feather_support.sentences(weighing):
                with self.subTest(command=command.parent.name, sentence=sentence[:60]):
                    self.assertNotIn(sentence, text)

    README_LISTINGS = {
        "README.md": "- `/cc-feather:overdesign-check [file, directory, spec, diff range or rule text]`: report Over-design in the proposal just discussed, or in what you name: defences against states only the project's own code could produce, compatibility kept for formats or tokens that no longer exist, configuration with a single user and stacked defences. Only you can run it, and it changes no file; each item is weighed and gets a recommendation, and old-format compatibility is called unneeded only with evidence, otherwise you are asked; see the [reference](docs/reference.md#design-and-test-checks).",
        "README.zh-TW.md": "| `/cc-feather:overdesign-check [檔案、目錄、spec、diff 範圍或規則文字]` | 檢查剛才討論的提案，或你指定的對象，是否有過度設計：防範只有專案自己的程式碼才會造成的狀態、為已不存在的格式或 token 保留相容、只有一個使用者的設定，以及重疊的防禦。只能由你執行，不改任何檔案；每一項都附權衡與建議，舊格式相容只有在有證據時才判定為不需要，否則會問你；見[參考文件](docs/reference.zh-TW.md#設計與測試檢查) |",
    }
    REFERENCE_SECTIONS = {"reference.md": "\n### Over-design check\n", "reference.zh-TW.md": "\n### 過度設計檢查\n"}
    REFERENCE_PAIRS = (
        ("`/cc-feather:overdesign-check` checks the proposal just discussed, or the file, directory, spec, diff range or rule text you name, for Over-design: defences against states only the project's own code could produce, compatibility with formats or tokens that were never released or no longer exist, configuration or extension points with a single user, and several defences guarding the same case.",
         "`/cc-feather:overdesign-check` 檢查剛才討論的提案，或你指定的檔案、目錄、spec、diff 範圍或規則文字，是否有過度設計：防範只有專案自己的程式碼才會造成的狀態、為從未發佈或已不存在的格式或 token 保留相容、只有一個使用者的設定或擴充點，以及多層防禦擋同一個情況。"),
        ("Each item is weighed by when it occurs, its worst outcome and what already covers it, as the delegation skill's rule on weighing findings states, and ends in a recommendation: remove, simplify, keep or needs your confirmation.",
         "每一項都依何時發生、最壞結果與現有涵蓋來權衡，做法就是分派 skill 對 finding 的權衡規則，最後給出建議：刪除、簡化、保留或需你確認。"),
        ("A check at a trust boundary is kept, with its reason.",
         "信任邊界上的檢查會保留，並寫明理由。"),
        ("Compatibility with an old format is called unneeded only with evidence from the repository, such as its release history; otherwise main asks you, since only you know whether old data still exists.",
         "舊格式的相容只有在 repository 有證據時才判定為不需要，例如它的發佈紀錄；否則主 Agent 會問你，因為只有你知道舊資料是否還存在。"),
        ("With delegation installed, analyst does the reading, and for a proposal from the conversation its brief carries the proposal's text.",
         "裝有分派元件時，由 analyst 負責閱讀分析；對象是對話中的提案時，它的 brief 會附上提案原文。"),
        ("See [the command](../skills/overdesign-check/SKILL.md).",
         "見[指令](../skills/overdesign-check/SKILL.md)。"),
    )

    def test_readmes_and_references_describe_the_command_in_both_languages(self):
        for name, listing in self.README_LISTINGS.items():
            with self.subTest(listing=name):
                self.assertIn(listing + "\n", (config.ROOT / name).read_text(encoding="utf-8"))
        for english, chinese in self.REFERENCE_PAIRS:
            for name, sentence in (("reference.md", english), ("reference.zh-TW.md", chinese)):
                text = feather_support.REFERENCE_FILES[name].read_text(encoding="utf-8")
                section = text.split(self.REFERENCE_SECTIONS[name], 1)[1].split("\n## ", 1)[0]
                with self.subTest(place=name, sentence=sentence[:40]):
                    self.assert_whole_sentence(sentence, section)

    def test_over_design_section_follows_test_speedups_in_the_design_checks_section(self):
        for name in ("reference.md", "reference.zh-TW.md"):
            text = feather_support.REFERENCE_FILES[name].read_text(encoding="utf-8")
            start, speedups = TestSpeedupCommandTests.REFERENCE_SECTIONS[name]
            section = text.split(start, 1)[1].split("\n## ", 1)[0]
            with self.subTest(reference=name):
                self.assertLess(section.index(speedups), section.index(self.REFERENCE_SECTIONS[name]))


class TestDesignCommandTests(unittest.TestCase):
    """docs/specs/test-design.md, ticket 02."""

    COMMAND = SKILLS / "test-design" / "SKILL.md"
    GUIDELINES = SKILLS / "test-design" / "references" / "guidelines.md"

    def test_command_is_user_invoked_and_listed_after_overdesign_check(self):
        skills = manifest_skills()
        self.assertEqual(skills.count("./skills/test-design"), 1)
        self.assertEqual(skills.index("./skills/test-design"), skills.index("./skills/overdesign-check") + 1)
        front = frontmatter(self.COMMAND.read_text(encoding="utf-8"))
        self.assertIn("name: test-design\n", front)
        self.assertIn("disable-model-invocation: true\n", front)
        self.assertIn('argument-hint: "[spec, ticket or feature path]"\n', front)
        self.assertRegex(front, r'\ndescription: "[^"\n]*tests[^"\n]*"\n')

    assert_whole_sentence = feather_support.stop_threshold_assert_whole_sentence

    def source(self, name):
        """'<file>', '<file>#<heading>' (a '## ' section), '<file>#<label>' (a '**<label>.**' or '**<label>:**'
        paragraph, or a '- **<label>.**' bullet), where <file> is 'SKILL.md' or 'guidelines.md'."""
        file, _, label = name.partition("#")
        text = {"SKILL.md": self.COMMAND, "guidelines.md": self.GUIDELINES}[file].read_text(encoding="utf-8")
        if not label:
            return text
        if f"\n## {label}\n" in text:
            return text.split(f"\n## {label}\n", 1)[1].split("\n## ", 1)[0]
        if f"\n- **{label}.**" in text:
            return next(line for line in text.splitlines() if line.startswith(f"- **{label}.**"))
        return next(p for p in text.split("\n\n") if p.startswith((f"**{label}.**", f"**{label}:**")))

    PINS = {
        "SKILL.md": (
            "Report a Test design, as [cc-feather's glossary](../../CONTEXT.md) defines it, for one target.",
            "Invocation arguments are the target as data, never shell code.",
            "Clarify a missing or unclear target instead of guessing.",
        ),
        "SKILL.md#The judging rule": (
            "Every proposed test names the defect it would catch, a concrete wrong implementation, that no other proposed or existing test catches, and uses the smallest input and the fewest runs that still catch it.",
            "A test that names no such defect is not proposed.",
            "Of two designs that catch the same defects, the cheaper one, at a lower level, with a smaller size and fewer runs, is proposed.",
            "Tests at different levels may both be proposed when each catches a different failure.",
            "A defect that no plausible wrong implementation could produce in the configurations the target supports once the change is made, those the applicable threat model reaches included, or whose effect nothing could observe there, names no defect for this rule, and the test is not proposed.",
            "An effect counts as observable through behaviour, a required artifact or a manual check.",
            "The guideline Requirement and failure modes first in [the guideline reference](references/guidelines.md) stays the case-choice form of this rule.",
        ),
        "SKILL.md#Report only": (
            "This command only reports and runs nothing: it edits, creates and deletes no file, commits nothing, changes no configuration and runs no test or command, and its cost estimates are static.",
            "The report stays in the conversation, and a file is written only when the user asks for one.",
            "Items the user picks become a Plan's acceptance through an edit the user asks for and then the normal flow; the report is not a Plan, and its items are neither Claims nor findings of any review.",
            "For measured timings, point the user to [`test-speedup`](../test-speedup/SKILL.md).",
        ),
        "SKILL.md#Target": (
            "With no argument, the target is the latest proposal or Plan in the conversation; when there is none, ask the user for a target.",
            "Otherwise the target is a named spec or ticket file, or an existing feature named by its code path or module.",
            "A spec with tickets is reported ticket by ticket.",
            "The report groups by ticket or by requirement and never decides the Plan's Claims.",
            "For an existing feature only gaps are reported; duplicates and speed belong to `test-speedup`.",
        ),
        "SKILL.md#Timing": (
            "The ideal moment is after the spec is cut into tickets and before the user names the Plan for implementation, so that plan review sees the tests the user adopted in the tickets' acceptance.",
            "Running the command is never required, and plan review's rules do not change.",
        ),
        "SKILL.md#Who analyses": (
            "Whether a target is small is judged by its source scope, coupling and reasoning difficulty, not by its ticket count.",
            "When delegation is installed and the target is not small, main dispatches the read-only analyst as [the delegation skill](../delegation/SKILL.md) describes, in one Assignment by default, a spec with its tickets included, and integrates the results.",
            "The target is split only when it exceeds what one analyst can handle well, along distinct behaviours or invariants, and the brief then gives each shared fixture design or overlapping test obligation to one Assignment, which the others reference rather than propose again.",
            "For a target from the conversation, the brief carries the proposal's text.",
            "Main gathers what the analyst cannot, such as the repository history that error guessing reads.",
            "A small target, or a target where delegation is not installed, main does itself.",
        ),
        "SKILL.md#1. Design the tests": (
            "Choose levels, cases, doubles and data as [the guideline reference](references/guidelines.md) states, each guideline where it applies.",
            "A proposed test already avoids what [the shared test criteria](../test-speedup/references/test-criteria.md)'s Speed criteria and Further criteria list, a further criterion only where its condition holds.",
        ),
        "SKILL.md#Behaviour to code": (
            "**Behaviour to code.** Tickets name no file paths, so before the Existing related tests search the analysis, or main when it analyses the target itself, locates the source paths and test support behind each ticket's behaviour; main may give a starting scope in the brief.",
            "A behaviour it cannot map is reported as uncertainty in Existing related tests.",
        ),
        "SKILL.md#Candidates before statements": (
            "**Candidates before statements.** The cases the Runs and sizes rules and the guideline techniques give, partitions, boundaries, transitions, integration points and each case of a parametrized test included, are candidates, graded like any other, not cases every report must propose.",
            "The analysis first lists each candidate test in one line: the requirement, the concrete defect, whether it can occur and be observed as the judging rule says, the existing coverage and any overlap with another ticket's candidates.",
            "It grades each candidate as Recommended, Optional or Not proposed, and only then writes the full statement for the Recommended ones.",
            "An Optional test is one line: its defect, its level and why it is Optional, plus a mark for any obligation that still applies to it, such as a gate who runs it must be named for or a bound that is unknown, which also lists it under Resource risk.",
            "Its full statement is written when the user asks or before it enters any acceptance.",
            "This happens within one analysis, with no round-trip to the user.",
        ),
        "SKILL.md#Grades": (
            "**Grades.** Every proposed test is graded Recommended or Optional, weighed as [the delegation skill](../delegation/SKILL.md)'s paragraph on weighing findings describes: when the defect can occur in normal use or under the applicable threat model, its worst credible outcome, and whether an existing test or rule covers it.",
            "That paragraph's rule that normal-use rarity alone never discounts a security problem applies.",
            "A defect reached only by a rare downstream configuration and confirmable at a glance in code review is Optional at most, unless its outcome is a security problem or data loss, which the paragraph alone grades.",
        ),
        "SKILL.md#Runs and sizes": (
            "A deterministic behaviour gets one case per partition and boundary.",
            "A count that is itself the requirement, such as a retry limit or a quota, is tested at N-1, N and N+1.",
            "Nondeterminism is removed first with a fixed seed, a fake clock or a controllable schedule; repetition that remains states its count and why that count suffices.",
            "The input is the smallest that reaches the behaviour; a large limit is reached through an injectable setting or a lazily generated, memory-bounded input, and a change to production code for testability is marked as one for the user to decide.",
            "Real scale is used only when scale itself is the requirement, and such tests go under Resource risk.",
            "Property-based tests keep the framework's default case count unless the report states what more cases would catch; a small input space is enumerated instead.",
        ),
        "SKILL.md#Each Recommended test states": (
            "**Each Recommended test states:** the defect it catches; its expected result and where that result comes from, a spec or acceptance passage, or characterization of current behaviour with any behaviour that may be a bug listed for the user to confirm; its level; how its cases are chosen; its size and run count with why they suffice, as its estimated cost; the bound of its work; the role of any test double it uses.",
            "A guideline is cited only where the choice is not obvious.",
        ),
        "SKILL.md#Gated new tests": (
            "**Gated new tests.** A new test may be gated by an environment variable, a marker or a short mode only when the report names who runs it, a Claim's acceptance or a gate's Declared test suite with its prerequisites, and states that the run needs positive evidence that the gated tests ran; a command that succeeds is not that evidence.",
            "A gate nothing runs is never proposed.",
            "An environment-gated test's skip message names the variable.",
            "[The shared test criteria](../test-speedup/references/test-criteria.md)'s Correctness bar governs changes to existing tests, so it does not bind a gated new test, and its rule against adding a skip stays as it is for existing tests.",
        ),
        "SKILL.md#Resource risk": (
            "**Resource risk.** Every proposed test is judged against the whole [Unbounded probe entry](../../CONTEXT.md) as it stands, each part it names applied to the test, generator rejection, shrinking, the code under test, the oracle, retained output, descendant processes and work handed outside the run included.",
            "A test that would be one gets a bounded redesign, or is listed as likely needing a Resource-risk claim mark, as information for plan review.",
            "Weigh each listed test as [the delegation skill](../delegation/SKILL.md)'s paragraph on weighing findings describes.",
            "A worker count that follows the machine's core count is never proposed, and any cap's number comes from the project's or the user's resource guidance or a measured peak.",
            "The Unbounded probe and Unbounded run configuration entries and the delegation rules for them do not change.",
        ),
        "SKILL.md#Error guessing": (
            "**Error guessing.** The analysis may read the repository's own history, its log, fix commits and tickets, for past trouble areas near the target.",
            "It reads no external issue tracker, and history never overrides the current requirement.",
        ),
        "SKILL.md#Lookups": (
            "**Lookups.** Framework defaults and known problems are looked up only as [`test-speedup`'s Lookups paragraph](../test-speedup/SKILL.md) allows, with the same order and the same limit on what a query carries; the command adds no other web access at runtime.",
        ),
        "SKILL.md#2. Report": (
            "**Acceptance problems**, each place where a verification the target's existing acceptance states is invalid for the intended change: it cannot be carried out, it would pass on the old code or on a wrong implementation, such as an oracle with no ordering guarantee, or it asserts a result that differs from behaviour the target does not change, such as a status code the framework never returns.",
            "Each comes with the evidence main checked.",
            "A difference from code the target is meant to change is the change still to be implemented, not an acceptance problem, and a newly considered test that could not fail goes under Not proposed.",
            "A problem whose fix changes only how a criterion is verified goes here or under Proposed tests.",
            "**Decisions for the user**, each of: a production-code change for testability; a meaning the spec leaves unclear; a change to required behaviour, such as widening, removing or rewording a requirement or an invariant; a characterised behaviour that may be a bug; and each place where a test need may change how the tickets are cut or their blocking edges.",
            "These are never recommended as test proposals.",
            "A test that depends on an open decision names it.",
            "**Lean set**, one line for each Recommended test, its ticket, level and case count with a pointer to its statement, each Recommended manual check, and each extension or update of an existing related test that a Recommended test relies on; then the number of tests and cases at each level.",
            "It states no time figure, holds no removal, and leaves out every test that depends on an open decision.",
            "Rerunning an existing test is not listed in it.",
            "**Proposed tests**, grouped by ticket or requirement, Recommended tests with their full statement and Optional tests in one line each, and a subsection for checks that need manual verification, such as a UI's look or behaviour seen only in a real environment, each with the reason a person must check it.",
            "**Existing related tests**, each as rerun, extend or update, found by searching the tests for the target's paths and directory names as Related-test acceptance does, whether or not Related-test acceptance is on, and reported as found or not found, never as proof that none exist.",
            "Each behaviour that could not be mapped to code is listed here too.",
            "**Removals**, each existing test the proposed ones would make redundant.",
            "**Not proposed**, each test considered and left out, grouped by reason, each group naming the tests it covers.",
            "**Resource risk**, each proposed test that uses real scale or likely needs a Resource-risk claim mark, with its reason and weighing, Optional tests with an unknown bound included.",
        ),
        "SKILL.md#Main's integration": (
            "**Main's integration.** Before reporting, main re-grades every analyst item by the same weighing, merges duplicates across tickets and checks each Acceptance problem against the code; analyst grades are input.",
            "Main recommends the Lean set and never recommends adopting every proposal.",
            "When main analyses a small target itself, the same applies to its own candidates.",
        ),
        "SKILL.md#3. Removals": (
            "Removals follow [the shared test criteria](../test-speedup/references/test-criteria.md)'s removal rule in its Correctness bar, replacements included, where the test that covers exactly the same behaviour may be a proposed one.",
            "A picked removal's acceptance requires the new test to be written and passing before the old one is removed.",
            "No measurement is needed.",
        ),
        "guidelines.md": (
            "Each guideline states when it applies and when it does not, and applies only there.",
        ),
        "guidelines.md#Rules this relies on": (
            "What makes a test slower or less robust than it needs to be, and how a removal is offered, are [the shared test criteria](../../test-speedup/references/test-criteria.md).",
            "Whether a test is unbounded is decided by the Unbounded probe entry in [cc-feather's glossary](../../../CONTEXT.md), and how a finding is weighed is [the delegation skill](../../delegation/SKILL.md)'s rule.",
            "These guidelines copy none of them.",
        ),
        # One sentence per guideline group.
        "guidelines.md#Lowest level that observes": (
            "A behaviour is tested at the lowest level that can observe it: a unit test for logic, an integration test for wiring between components, a broad test for what only the assembled system shows.",
        ),
        "guidelines.md#Boundary values": (
            "cc-feather's default is two values, the boundary and its nearest neighbour across it, and three values, the boundary and one on each side, where a wrong comparison or an off-by-one is a real risk.",
        ),
        "guidelines.md#Order of preference": (
            "A real implementation is used when it is fast, deterministic and has no effect outside the test; otherwise a fake, otherwise a stub; an interaction check only when the interaction is the requirement, such as a message being sent exactly once.",
        ),
        "guidelines.md#Hermetic": (
            "Hermetic means isolated and self-contained: a test depends only on what it controls, and a controlled local dependency, such as a database or a subprocess started for the run, counts as hermetic.",
        ),
        "guidelines.md#Fixed seeds in always-run suites": (
            "A suite that runs on every change uses a fixed seed or a stored corpus, and open-ended exploration runs only in explicit, time-boxed runs.",
        ),
        "guidelines.md#Traced to a criterion": (
            "Each acceptance test traces to one acceptance criterion, its positive cases first and its negative ones after.",
        ),
        "guidelines.md#Key examples": (
            "A few key examples per rule illustrate it, and a case a technique derives is a candidate, proposed only when it catches a defect the other cases do not, at the grade it earns.",
            "Derived cases kept inside one parametrized test count as that test's cases; candidates left out are grouped under Not proposed.",
            "It applies to every rule an acceptance criterion states.",
            "The key examples are not an exhaustive list.",
        ),
        "guidelines.md#Fails on the wrong implementation": (
            "Each test states why it fails on the old code or on a wrong implementation and what guarantees the order its oracle relies on, such as a registration barrier or an event wait rather than a sleep.",
            "A newly considered test that cannot state it is redesigned or not proposed; an existing acceptance verification that cannot is listed under Acceptance problems.",
            "It applies to every proposed test and to every verification an existing acceptance states.",
            "It does not ask for an ordering guarantee where the oracle relies on no order.",
        ),
        "guidelines.md#Exact counts only where the count is the contract": (
            "An exact count is asserted where cardinality, completeness, absence or repetition is part of the required result, such as the records a query must return, no forbidden record, audit events or a message sent exactly once.",
            "It applies to every assertion on a count.",
            "It does not apply to an incidental count, such as log lines, which is asserted as at least one occurrence with the right content.",
        ),
        "guidelines.md#Code-text checks last": (
            "A check of code text or syntax trees is used only where no behaviour, required artifact or manual check can observe the effect, and is marked brittle.",
            "It applies to every proposed check that reads code rather than running it.",
            "It does not apply where the text read is itself a required artifact, such as a document or a generated file the requirement names.",
        ),
        "guidelines.md#Decision order": (
            "A test that needs a real dependency uses a disposable instance of the same engine first, such as a container or a local process created for the run; otherwise a read-only, gated smoke test that asserts no changing volumes or values.",
        ),
        "guidelines.md#Ecosystem hints": (
            "These hints apply to projects in each ecosystem and do not override a project's own established conventions.",
        ),
        # The three hard prohibitions.
        "guidelines.md#Hard prohibitions": (
            "Three things are never proposed: a fall-back to a hard-coded connection string when the environment variable is unset, a connection to production by default, and credentials in test files.",
            "They apply to every proposed test and every piece of test support, and there is no case where they do not.",
        ),
    }

    def test_command_states_its_decisions(self):
        for place, sentences in self.PINS.items():
            text = self.source(place)
            for sentence in sentences:
                with self.subTest(place=place, sentence=sentence[:60]):
                    self.assert_whole_sentence(sentence, text)

    def test_the_judging_rule_comes_first(self):
        headings = [line for line in self.source("SKILL.md").splitlines() if line.startswith("## ")]
        self.assertEqual(headings[0], "## The judging rule")

    def test_the_report_has_eight_sections_in_order(self):
        report = self.source("SKILL.md#2. Report")
        self.assertIn("The report has eight sections, in this order:\n", report)
        sections = [line.split("**")[1] for line in report.splitlines() if line.startswith("- **")]
        self.assertEqual(sections, ["Acceptance problems", "Decisions for the user", "Lean set", "Proposed tests",
                                    "Existing related tests", "Removals", "Not proposed", "Resource risk"])
        # The Ticket-shape notes section is replaced by an item under Decisions for the user.
        for name in ("SKILL.md", "guidelines.md"):
            with self.subTest(file=name):
                self.assertNotIn("Ticket-shape notes", self.source(name))

    def test_the_new_test_quality_guidelines_follow_the_existing_ones(self):
        labels = [line.split("**")[1] for line in self.source("guidelines.md#Test quality").splitlines()
                  if line.startswith("- **")]
        self.assertEqual(labels[-3:], ["Fails on the wrong implementation.",
                                       "Exact counts only where the count is the contract.", "Code-text checks last."])

    def test_the_weighing_paragraph_is_pointed_to_unrestated_and_unchanged(self):
        """Single-owner check: the grades point to the delegation skill's weighing paragraph, neither the skill nor its
        guideline reference repeats any of its sentences verbatim, and the paragraph is the one the completion-criteria
        tests pin."""
        owner = completion_criteria.WeighFindingsBeforeRulesTests
        delegation = (SKILLS / "delegation" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn(" ".join(owner.PARAGRAPH), owner.paragraphs(delegation))
        self.assertIn("[the delegation skill](../delegation/SKILL.md)'s paragraph on weighing findings",
                      self.source("SKILL.md#Grades"))
        self.assertIn("[the delegation skill](../../delegation/SKILL.md)'s rule",
                      " ".join(self.source("guidelines.md#Rules this relies on").split()))
        for name in ("SKILL.md", "guidelines.md"):
            flat = " ".join(self.source(name).split())
            for sentence in owner.PARAGRAPH:
                with self.subTest(file=name, sentence=sentence[:60]):
                    self.assertNotIn(sentence, flat)

    GROUPS = ("Levels and sizes", "Case choice", "Doubles", "Test quality", "Property-based testing and fuzzing",
              "Acceptance", "External dependencies", "Ecosystem hints")

    def test_the_guideline_groups_are_the_specs_each_guideline_with_where_it_applies(self):
        headings = [line[3:] for line in self.source("guidelines.md").splitlines() if line.startswith("## ")]
        self.assertEqual(headings, ["Rules this relies on", *self.GROUPS])
        for group in self.GROUPS[:-1]:
            bullets = [line for line in self.source(f"guidelines.md#{group}").splitlines() if line.startswith("- **")]
            self.assertGreaterEqual(len(bullets), 2, group)
            for bullet in bullets:
                with self.subTest(group=group, guideline=bullet[:40]):
                    self.assertRegex(bullet, r" (It applies|They apply) ")
        hints = self.source("guidelines.md#Ecosystem hints")
        labels = [line.split("**")[1] for line in hints.splitlines() if line.startswith("- **")]
        self.assertEqual(labels, ["Go.", "Python.", "JavaScript or TypeScript run with pnpm, Vue included."])
        for idiom in ("t.Run", "parametrize", "fake timers"):
            with self.subTest(idiom=idiom):
                self.assertIn(idiom, hints)
        self.assertIn("- **Hard prohibitions.**", self.source("guidelines.md#External dependencies"))

    def test_the_guidelines_carry_no_source_labels_citations_or_statistics(self):
        text = self.source("guidelines.md")
        for marker in ("http://", "https://", "www.", "et al", "according to", "Source", "source:", "%", "per cent", "percent"):
            with self.subTest(marker=marker):
                self.assertNotIn(marker, text)
        # No numbered citation, footnote or figure of any kind; the only links are the relative pointers.
        self.assertNotRegex(text, r"\d")
        self.assertNotRegex(text, r"\[\^")
        for target in re.findall(r"\]\(([^)]+)\)", text):
            with self.subTest(link=target):
                self.assertTrue(target.startswith("../"))

    POINTERS = {
        "SKILL.md": (("../../CONTEXT.md", config.ROOT / "CONTEXT.md"),
                     ("../delegation/SKILL.md", SKILLS / "delegation" / "SKILL.md"),
                     ("../test-speedup/SKILL.md", SKILLS / "test-speedup" / "SKILL.md"),
                     ("../test-speedup/references/test-criteria.md", TestSpeedupCommandTests.CRITERIA),
                     ("references/guidelines.md", SKILLS / "test-design" / "references" / "guidelines.md")),
        "guidelines.md": (("../../../CONTEXT.md", config.ROOT / "CONTEXT.md"),
                          ("../../delegation/SKILL.md", SKILLS / "delegation" / "SKILL.md"),
                          ("../../test-speedup/references/test-criteria.md", TestSpeedupCommandTests.CRITERIA)),
    }

    def test_pointers_resolve(self):
        for name, links in self.POINTERS.items():
            path = {"SKILL.md": self.COMMAND, "guidelines.md": self.GUIDELINES}[name]
            text = path.read_text(encoding="utf-8")
            for link, target in links:
                with self.subTest(file=name, link=link):
                    self.assertIn(f"]({link})", text)
                    self.assertTrue(target.is_file())
                    self.assertEqual((path.parent / link).resolve(), target.resolve())
            for link in re.findall(r"\]\(([^)#]+)", text):
                with self.subTest(file=name, every_link=link):
                    self.assertTrue((path.parent / link).is_file())

    def test_linked_rules_are_not_restated(self):
        entries = feather_support.glossary_entries((config.ROOT / "CONTEXT.md").read_text(encoding="utf-8"))
        delegation = (SKILLS / "delegation" / "SKILL.md").read_text(encoding="utf-8")
        weighing = next(p for p in delegation.split("\n\n") if p.startswith("Before proposing or adopting a requirement"))
        speedup = TestSpeedupCommandTests()
        owned = {"weighing": feather_support.sentences(weighing),
                 "shared criteria": [s for _, s in speedup.shared_statements()],
                 "test-speedup lookups": feather_support.sentences(speedup.source("SKILL.md#Lookups"))}
        for term in ("Unbounded probe", "Unbounded run configuration", "Declared test suite", "Related-test acceptance"):
            owned[term] = feather_support.sentences(entries[term].split("\n_Avoid_")[0])
        self.assertGreaterEqual(len(owned["shared criteria"]), 30)
        for name in ("SKILL.md", "guidelines.md"):
            flat = " ".join(self.source(name).split())
            for owner, sentences in owned.items():
                for sentence in sentences:
                    with self.subTest(file=name, owner=owner, sentence=sentence[:60]):
                        self.assertNotIn(sentence, flat)
            with self.subTest(file=name, rule="Runner"):
                self.assertNotIn("--memory-mib", flat)
                self.assertNotIn("a timeout alone is not a bound", flat)
                self.assertNotIn("An unknown bound counts as none", flat)
            for part in TestSpeedupCommandTests.SHARED_PARTS:
                with self.subTest(file=name, heading=part):
                    self.assertNotIn(f"\n## {part}\n", self.source(name))

    TEST_DESIGN = (
        "A report of the tests one target needs, the target being a spec, its tickets or an existing feature: each "
        "proposed test graded Recommended or Optional, with the defect it would catch that no other test catches, and "
        "only a Recommended test with the full statement of its expected result and where that result comes from, its "
        "level, how its cases are chosen, its size and number of runs with why they suffice, and the bound of its work, "
        "together with the checks that need manual verification, the existing tests that already verify part of the "
        "target and the existing tests the proposed ones would make redundant. The report leads with acceptance "
        "problems, decisions for the user and a Lean set of the Recommended tests. It is information, not "
        "a Plan, and its items are not Claims; what the user picks enters a Plan's acceptance only through an edit the "
        "user asks for.\n_Avoid_: test plan, test strategy"
    )

    def test_glossary_defines_test_design_in_the_design_checks_section(self):
        text = (config.ROOT / "CONTEXT.md").read_text(encoding="utf-8")
        entries = feather_support.glossary_entries(text)
        self.assertEqual(entries["Test design"].strip(), self.TEST_DESIGN)
        section = text.split("\n## Design checks\n", 1)[1].split("\n## ", 1)[0]
        self.assertIn("\n**Test design**:\n", section)
        self.assertEqual(entries["Unbounded probe"].strip(), OverdesignCheckCommandTests.UNBOUNDED_PROBE)

    README_LISTINGS = {
        "README.md": "- `/cc-feather:test-design [spec, ticket or feature path]`: report the tests the proposal just discussed, or the spec, ticket or existing feature you name, needs: each proposed test names the defect it would catch that no other test catches, uses the smallest input and fewest runs that still catch it and is graded Recommended or Optional, and the report leads with acceptance problems, decisions for you and a Lean set of the Recommended tests. Only you can run it; it changes and runs nothing, and what you pick enters a ticket's acceptance only when you ask for that edit; see the [reference](docs/reference.md#design-and-test-checks).",
        "README.zh-TW.md": "| `/cc-feather:test-design [spec、ticket 或功能路徑]` | 為剛才討論的提案，或你指定的 spec、ticket 或既有功能，提出需要的測試：每個建議的測試都指出它能抓到、而其他測試抓不到的缺陷，使用仍能抓到它的最小輸入與最少執行次數，並評為 Recommended 或 Optional；報告以驗收問題、需你決定的事項與由 Recommended 測試組成的 Lean set 開頭。只能由你執行，不改也不執行任何東西；你挑選的項目只有在你要求修改時才寫進 ticket 的驗收；見[參考文件](docs/reference.zh-TW.md#設計與測試檢查) |",
    }
    REFERENCE_SECTIONS = {"reference.md": "\n### Test design\n", "reference.zh-TW.md": "\n### 測試設計\n"}
    REFERENCE_PAIRS = (
        ("`/cc-feather:test-design` proposes the tests a target needs: the proposal or plan just discussed, a spec or ticket you name, or an existing feature named by its code path or module.",
         "`/cc-feather:test-design` 提出一個對象需要的測試：對象是剛才討論的提案或計畫、你指定的 spec 或 ticket，或以程式碼路徑或模組指定的既有功能。"),
        ("Every proposed test names the defect it would catch, a concrete wrong implementation, that no other proposed or existing test catches, and uses the smallest input and the fewest runs that still catch it; of two designs that catch the same defects, the cheaper one is proposed.",
         "每個建議的測試都指出它能抓到的缺陷，也就是一個具體的錯誤實作，而且是其他建議或既有測試都抓不到的，並使用仍能抓到它的最小輸入與最少執行次數；兩種設計抓到相同缺陷時，提出較便宜的那一種。"),
        ("A defect that no plausible wrong implementation could produce in the configurations the target supports, or whose effect nothing could observe, is not tested.",
         "在對象支援的設定中，沒有任何合理的錯誤實作會造成的缺陷，或沒有任何方式能觀察到其影響的缺陷，不會為它設計測試。"),
        ("The cases the techniques give, such as partitions and boundaries, are candidates: each is listed in one line and graded Recommended, Optional or not proposed, weighed as the delegation skill's rule on weighing findings states, and a defect reached only by a rare downstream configuration and easy to confirm in code review is Optional at most, unless its outcome is a security problem or data loss.",
         "技巧給出的案例，例如分割與邊界，都只是候選：每個候選列成一行，評為 Recommended、Optional 或不提出，權衡方式就是分派 skill 對 finding 的權衡規則；只有罕見的下游設定才會遇到、在 code review 中一眼就能確認的缺陷，最多評為 Optional，除非它的後果是安全問題或資料遺失。"),
        ("Only a Recommended test states its expected result and where that result comes from, its level, how its cases are chosen, its size and number of runs with why they suffice, and the bound of its work; an Optional test is one line, written out in full when you ask or before it enters any acceptance.",
         "只有 Recommended 測試會說明預期結果與其來源、層級、案例如何挑選、大小與執行次數以及為何足夠，還有它工作量的上限；Optional 測試只寫一行，在你要求時或寫進任何驗收之前才完整寫出。"),
        ("A deterministic behaviour gets one case per partition and boundary, a count that is the requirement is tested at its boundary rather than with a loop, and nondeterminism is removed with a fixed seed, a fake clock or a controllable schedule before any repetition is proposed.",
         "確定性的行為每個分割與邊界各一個案例；本身就是需求的次數只在邊界測試，不用迴圈；提出任何重複執行之前，先用固定 seed、fake clock 或可控制的排程消除不確定性。"),
        ("A gated new test is proposed only with who runs it, a claim's acceptance or a Declared test suite, and its run needs positive evidence that the gated tests ran.",
         "有開關控制的新測試只有在指出由誰執行時才會提出，也就是某個 claim 的驗收或某個 Declared test suite，而且它的執行必須有正面證據顯示這些測試真的跑了。"),
        ("Every proposed test is judged against the Unbounded probe entry; one that would be unbounded gets a bounded redesign or is listed as likely needing a Resource-risk claim mark, as information for plan review.",
         "每個建議的測試都以 Unbounded probe 的定義判斷；會沒有上限的測試改成有上限的設計，或列為可能需要 Resource-risk claim 標記，作為計畫審查的參考。"),
        ("The report has eight sections, in this order: acceptance problems, each verification in the existing acceptance that cannot be carried out, would pass on the old code or on a wrong implementation, or asserts a result that unchanged behaviour does not give; decisions for you, such as a production-code change for testability, a meaning the spec leaves unclear, a change to required behaviour and a test need that may change how the tickets are cut; the Lean set, one line for each Recommended test and check with the number of tests and cases at each level; proposed tests grouped by ticket or requirement, with checks that need manual verification; existing related tests to rerun, extend or update, with any behaviour that could not be mapped to code; removals; tests not proposed, grouped by reason; and resource risk.",
         "報告依序分八節：驗收問題，也就是既有驗收中無法執行、在舊程式碼或錯誤實作上也會通過，或斷言了未變更行為不會產生的結果的驗證；需你決定的事項，例如為了可測試性而改動正式程式碼、spec 沒說清楚的意義、對必要行為的變更，以及可能改變 ticket 切分方式的測試需求；Lean set，每個 Recommended 測試與檢查各一行，並附上每個層級的測試數與案例數；依 ticket 或需求分組的建議測試，連同需要人工驗證的檢查；要重跑、擴充或更新的既有相關測試，連同無法對應到程式碼的行為；刪除；依理由分組的未提出測試；以及資源風險。"),
        ("Before reporting, main re-grades every item, merges duplicates across tickets and checks each acceptance problem against the code, and it recommends the Lean set, never every proposal.",
         "提出報告之前，主 Agent 會重新評定每一項、合併各 ticket 間重複的項目，並對照程式碼檢查每個驗收問題；它建議採用 Lean set，絕不建議採用所有提議。"),
        ("A removal follows the same evidence rule as `/cc-feather:test-speedup`'s, for you to decide one by one, and a picked removal needs the new test written and passing before the old one is removed.",
         "刪除採用與 `/cc-feather:test-speedup` 相同的證據規則，由你逐條決定；被選中的刪除必須先寫好新測試並通過，才移除舊測試。"),
        ("It changes and runs nothing, and what you pick enters a ticket's acceptance only through an edit you ask for.",
         "它不改也不執行任何東西；你挑選的項目只有透過你要求的修改才會寫進 ticket 的驗收。"),
        ("The best moment to run it is after a spec is cut into tickets and before you name the plan for implementation, so that plan review sees the tests you adopted; it is never required.",
         "最適合執行的時機是 spec 切成 ticket 之後、你指定要實作的計畫之前，這樣計畫審查會看到你採用的測試；它從不是必要步驟。"),
        ("It reads the repository's own history for past trouble areas but no external issue tracker, and looks up framework defaults only as `/cc-feather:test-speedup` does.",
         "它會讀 repository 自己的歷史找出過去出問題的地方，但不讀外部 issue tracker；查詢框架預設值的方式與 `/cc-feather:test-speedup` 相同。"),
        ("Its guideline reference covers levels and sizes, case choice, test doubles, test quality, property-based testing and fuzzing, acceptance, external dependencies and hints for Go, Python and JavaScript or TypeScript.",
         "它的指引參考涵蓋層級與大小、案例挑選、test double、測試品質、property-based testing 與 fuzzing、驗收、外部相依，以及 Go、Python 與 JavaScript 或 TypeScript 的提示。"),
        ("With delegation installed and a target that is not small, judged by its source scope, coupling and reasoning difficulty rather than its ticket count, one analyst does the reading by default, and the work is split only along distinct behaviours or invariants when it is too much for one.",
         "裝有分派元件且對象不小時，對象大小依原始碼範圍、耦合程度與推理難度判斷，而不是依 ticket 數量，預設由一個 analyst 負責閱讀分析；只有在一個 analyst 處理不了時，才依不同的行為或不變條件拆分。"),
        ("See [the command](../skills/test-design/SKILL.md).",
         "見[指令](../skills/test-design/SKILL.md)。"),
    )

    def test_readmes_and_references_describe_the_command_in_both_languages(self):
        for name, listing in self.README_LISTINGS.items():
            with self.subTest(listing=name):
                self.assertIn(listing + "\n", (config.ROOT / name).read_text(encoding="utf-8"))
        for english, chinese in self.REFERENCE_PAIRS:
            for name, sentence in (("reference.md", english), ("reference.zh-TW.md", chinese)):
                text = feather_support.REFERENCE_FILES[name].read_text(encoding="utf-8")
                section = text.split(self.REFERENCE_SECTIONS[name], 1)[1].split("\n## ", 1)[0]
                with self.subTest(place=name, sentence=sentence[:40]):
                    self.assert_whole_sentence(sentence, section)

    def test_readme_listing_follows_overdesign_check(self):
        for name, listing in self.README_LISTINGS.items():
            text = (config.ROOT / name).read_text(encoding="utf-8")
            overdesign = OverdesignCheckCommandTests.README_LISTINGS[name]
            with self.subTest(readme=name):
                self.assertIn(overdesign + "\n" + listing + "\n", text)

    def test_section_follows_over_design_checks_in_the_design_checks_section(self):
        for name in ("reference.md", "reference.zh-TW.md"):
            text = feather_support.REFERENCE_FILES[name].read_text(encoding="utf-8")
            start, _ = TestSpeedupCommandTests.REFERENCE_SECTIONS[name]
            section = text.split(start, 1)[1].split("\n## ", 1)[0]
            with self.subTest(reference=name):
                over_design = section.index(OverdesignCheckCommandTests.REFERENCE_SECTIONS[name])
                self.assertLess(over_design, section.index(self.REFERENCE_SECTIONS[name]))
                # Nothing sits between Over-design check's section and this one.
                between = section[over_design + 1:section.index(self.REFERENCE_SECTIONS[name])]
                self.assertNotIn("\n### ", between)


class NotInstalledTests(unittest.TestCase):
    """Ticket 03: the commands ship with the plugin; no installed policy template or role definition names them.
    docs/specs/test-design.md, ticket 02, adds test-design."""

    def test_no_template_or_role_definition_mentions_any_of_the_commands(self):
        # templates/ holds the policy templates and, under templates/agents/, the role definitions.
        self.assertTrue((config.ROOT / "templates" / "agents" / "analyst.md").is_file())
        for path in sorted((config.ROOT / "templates").rglob("*")):
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8")
            for command in ("test-speedup", "overdesign-check", "test-design"):
                with self.subTest(template=path.relative_to(config.ROOT).as_posix(), command=command):
                    self.assertNotIn(command, text)


if __name__ == "__main__":
    unittest.main()
