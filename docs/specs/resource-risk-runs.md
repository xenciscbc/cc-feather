# Resource-risk runs

Label: `ready-for-agent`

Vocabulary follows [CONTEXT.md](../../CONTEXT.md), which defines Claim, Plan, Plan review, Dispatch record, Active handoff and Security-critical claim; this spec adds Resource-risk claim, Execution method, Unbounded probe, Observed resource risk and Runner. Execution permission stays as review state's Execution defines it; every item below adds to it and never replaces it.

## Problem Statement

On 2026-11-06, in another project (cbc-go), a verifier wrote its own differential probe after plan review. The probe ran 300000 random error graphs in the test process and, on cyclic graphs, handed each graph to a reference implementation of `errors.Is` that had no step limit. On a single-Unwrap cycle the reference looped forever while the probe's measuring type appended a string per call, and the test process grew to about 21 GB. The machine later failed to boot and C: was restored from backup; whether the memory exhaustion caused the boot failure is not established.

The risk was visible in the spec: the Claim's acceptance already required cyclic cases to run in a subprocess with limits. What ran away was a probe the verifier invented during verification. Nothing in the verifier's definition or brief said anything about resources, the verifier's definition states that main-session instructions in CLAUDE.md do not apply to it, and nothing on the machine limited what the probe could take. The outer loop was bounded; the unbounded part was the reference used for comparison, so a rule about iteration counts or timeouts alone would not have stopped it, and a timeout limits time, not memory.

cbc-go's later field notes over one Plan of about 22 runs show the same shape: the risky runs were foreseeable from the spec and its tickets, about a third of the runs deliberately used heavy resources, and the one limit actually hit was main's own build, which a runner contained.

The user wants tests to use resources reasonably unless the test needs more: never crash the machine or make it unusable. The user wants the risk caught where it is foreseeable, at plan review, contained by a real limit where it runs, and a cheap safety floor everywhere else, without putting every ordinary test through a runner and without numbers fixed by cc-feather.

## Solution

Four layers, from soft to hard and back:

1. **Plan review marks the risk.** Plan review judges each Claim's resource risk. For a risky Claim it marks it a Resource-risk claim, estimates the peak with its basis, and proposes an Execution method for the risky part: a small-scale simulation, a counting witness, bounds on every part, and the limits to run under.
2. **Main approves and the Runner contains.** Main approves the Execution method and writes it, with its budget, into the Claim's execution conditions. A role runs the risky part only as approved and only inside the Runner, cc-feather's launcher that puts a hard memory and time limit on the whole process tree. The role still judges whether the Claim holds and whether the approved method can establish it; if not, it returns INCONCLUSIVE with its own proposed method and main decides.
3. **A floor for every run.** Any new or modified test or probe whose bounds are unknown or do not fit the budget is an Unbounded probe: it is not run and goes back to main. This covers unmarked Claims, off mode and main's own reruns.
4. **What happened is recorded.** Returned probes and runs stopped by a limit become an Observed resource risk on the Claim. Main tells the user, carries the record into later briefs of that Claim, and lists it at the end of the Plan.

Budgets come from the user, the Plan or guidance the user wrote, never from cc-feather. A user may preset a default budget in project or user guidance; main asks only when the need exceeds it, or when there is no budget at all.

## Acceptance

1. **Plan review judges resource risk.** The plan-review checklist gains one item: for each Claim, whether executing its implementation checks, acceptance checks or verification foreseeably risks exhausting memory, time or the machine. For a Claim where it does, the analyst:
   - marks it a Resource-risk claim with the reason;
   - estimates its peak memory and time with the basis of the estimate;
   - proposes an Execution method for the risky part.

   The kinds of risk the item names, such as unbounded recursion or graph walks, reference implementations without step limits, exhaustive or combinatorial generation, heavy parallel builds or race detectors, and whole-repository scanners, are examples and the item says the list is not exhaustive. A missing mark is not a statement that a Claim is safe. The item runs wherever plan review runs, so in off an explicit plan-review request also judges it. No separate command or skill for resource-risk analysis is added.
2. **Main approves the Execution method.** Main reviews the proposed Execution method and approves it, changes it, or asks the user. An approved Execution method names the experiment for the risky part, its bounds, the memory and time limits, that it runs inside the Runner, and the source of the budget. The budget comes, in order, from the user's own statement in this session, the Plan's execution conditions, the project's resource guidance, then the user's resource guidance; guidance may state a default budget. When the needed budget exceeds that default or no source states one, main asks the user. cc-feather states no numbers.
3. **Approval stays bound to what it approved.** An approved Execution method is bound to its Claim, the Claim's recorded reading set, the experiment it describes, its budget and the budget's source. It stops being valid when the Claim's reading set changes, when the Plan gets a new plan review, or when its record is missing or does not match what it was recorded for; main then approves it again before the Claim's next run, asking the user where the budget's source requires it. In auto it is recorded in the Plan's Dispatch record; in off in the Active handoff when one exists, and otherwise in the session's state. It is never written into the Claim's text.
4. **Execution conditions reach every run.** Main carries a Claim's execution conditions verbatim into every brief of a role that may execute code for it: its implementation, outcome verification and Adversarial review, including reopened calls and later sessions, and applies them to its own runs for the Claim, such as reruns, reproductions and the final check's rerun of its primary acceptance. A review's run, and main's own run, needs both the Execution determination and its execution conditions; for an implementation by executor or security-executor, which get no Execution determination, the execution conditions add limits to what the Assignment allows and add no Execution determination. An approved Execution method never lifts a restriction the user stated, and the Runner is never the isolated environment the user named.
5. **Role rule.** The verifier, adversary, executor and security-executor definitions each carry one paragraph, identical apart from role-specific outcome words, that states:
   - that for a Resource-risk claim the role runs the risky part only as the approved Execution method in its brief describes and only inside the Runner with the brief's limits, and never changes it: no raised limit, no larger or different experiment;
   - that the role still judges whether the Claim holds, ordinary acceptance checks and counterexample probes included, and whether the approved Execution method can establish the Claim;
   - that when it judges the method insufficient or wrong, it does not work around it but reports INCONCLUSIVE with its proposed method and the reason;
   - which new or modified test or probe is an Unbounded probe: any part of it, the input generator, the code under test, a reference implementation or control, callbacks, measurement, output collection and descendant processes, has no established bound on total work or retained data, or the peak memory and time that the bound allows do not fit the budget the brief carries or, without one, the project's resource guidance; an unknown bound counts as none; a bounded input size, a bounded outer loop or a timeout alone is not a bound; a check the Plan lists that the role changes counts as modified;
   - that the role does not run an Unbounded probe and returns it to main, and returns a probe it cannot judge against any budget or guidance;
   - that the role states the estimated peak and its basis for each bounded probe it writes that it runs against a budget;
   - that the role never raises a limit and reruns;
   - that a run the Runner reports as contained, timed out or refused, or whose evidence is missing, is inconclusive evidence judged from the Runner's result, not from the target's exit code; a non-zero exit with no limit event is a failure; results established independently of it stand;
   - that the report names every probe it returned and every run a limit stopped, with the reason.

   The verifier and adversary report the inconclusive part as INCONCLUSIVE or within their coverage; the executor and security-executor report it as partial or blocked. The paragraph sits beside each role's Execution paragraph or, for the executor and security-executor, which have none, beside their scope instructions, and it never widens what Execution or the Assignment allows.
6. **Main after an INCONCLUSIVE about the method.** When a role reports the approved Execution method insufficient, main either approves the role's proposed method, or another, and dispatches a new, fresh, normally counted call, asking the user where the new budget requires it; or keeps the method only together with new evidence or a changed condition that addresses the named gap. Without either, the Claim is reported unverified and the user decides. A call stopped by a limit closes as a completed call without a pass; a larger budget means a new call. Counting, the Stop threshold and what counts as a call are unchanged.
7. **Main's own floor.** The role rule's floor applies to main when main runs a test or probe a role returned or reproduces a failure a role reported. Main runs a returned Unbounded probe only after redesigning it so every part is bounded within the budget, or inside the Runner with the budget's limits, and never as it is and never with a timeout alone. Main's own runs for a Resource-risk claim use the Runner.
8. **Observed resource risk.** When a role returns a probe, or a run stops on a limit, main records an Observed resource risk on that Claim, naming the run and its test or probe, the reason, how it was handled (returned, redesigned, run within a budget, stopped by a limit), the budget and any peak the Runner observed, and tells the user in its next reply. The record does not assume that plan review missed the risk: a probe invented during execution or a run in off had no plan review to miss it. It is recorded where an approved Execution method is recorded, is carried as an execution condition into every later brief of that Claim that may execute code, stays until the Plan ends, and is listed in the decision or completion report at the end of the Plan. Writing it into the Plan or a ticket needs the user's agreement.
9. **Runner contract.** cc-feather ships a Runner that main and roles invoke with a memory limit for the whole process tree, a time limit, an output limit, a working directory and the target command as plain arguments. The Runner:
   - places the target under containment before the target's first instruction, so every descendant is inside it, and ends every remaining member when the run ends;
   - lowers the target's CPU priority where the platform allows it;
   - refuses to start when containment is not available, when an enclosing limit would make its own limits unreliable, or when available memory is below the memory limit;
   - keeps the beginning and the real end of the output within the output limit and says whether it truncated, and bounds every read of its own evidence;
   - reports a JSON result with one outcome: passed, target failed, contained (with the limit event: memory or time), refused (with the reason), or evidence missing; plus the target's exit code, observed peak memory and duration. A limit event overrides a target exit code of 0, and missing evidence is never passed;
   - exits 0 only when the outcome is passed, and with distinct codes for the other outcomes.

   Supported environments are decided by whether containment actually works: Windows through a job object, Linux through a transient systemd user scope with the cgroup v2 memory controller delegated, swap disabled for the scope and memory events read from the cgroup. Any other environment, or a supported one where the capability check fails, is refused, and a Resource-risk claim then stops for the user to decide: provide a tool that meets this contract, or accept that Claim's run without a hard limit in their own words. The Linux path ships only if it is validated on a Linux host with a systemd user manager, such as WSL2 with systemd enabled; otherwise the Runner refuses on Linux in this release.
10. **What the Runner does not cover.** The documentation names the boundary of the guarantee: only processes inside the Runner's containment are limited. Work handed to an already running service, such as a daemon, a container runtime, WSL, a build server, a database or a remote service, and tools that execute code outside the shell, such as an MCP server, are outside it. Two runs started at the same time each check available memory on their own, so their total is not limited; that is a known limitation of this release.
11. **Permissions.** A Runner invocation goes through the host's normal permission handling like any other command. cc-feather adds no permission rule. Because the target command is plain text in the invocation, whatever decides the permission sees what will run. The documentation advises against a rule that allows every Runner invocation, because such a rule allows any command through the Runner, and notes that a rule written for the target alone no longer matches once it is wrapped.
12. **Reviewer text.** The reviewer definition's Execution paragraph gives a lint and a type check, not a test or a probe, as its examples of what it may execute, matching its instruction to run only the lint and type-check commands its brief names. The code-review procedure is unchanged.
13. **Glossary and ADR.** `CONTEXT.md` defines Resource-risk claim, Execution method, Unbounded probe, Observed resource risk and Runner. The Resource-risk claim entry says that plan review marks it and that an unmarked Claim is not thereby safe. A new ADR 0019 records the layered decision, with the rejected alternatives and reasons: judging risk only at each run, which leaves the role that misjudged as the only judge; a two-phase run in which the role proposes its method mid-call and continues after approval, which needs a new paused state in review counting; a separate resource-analysis command; enforcing Runner use with a hook now; and a watchdog.
14. **Live rehearsal.** One live rehearsal in a scratch clone of cc-feather's repository, with the candidate commit loaded through `--plugin-dir`, the installed plugin disabled and the user's own installation left unchanged, runs a small Plan with one Resource-risk claim built on a self-limiting cc-feather probe: plan review marks it and proposes an Execution method, main approves it, outcome verification runs the risky part inside the Runner, and one deliberately limited run is contained and reported as inconclusive and recorded as an Observed resource risk. The cbc-go incident probe is never used.
15. **Reference documents.** Both reference documents, in English and Traditional Chinese, describe the four layers, the Runner and its boundary in a short section beside their description of the roles' execution.
16. **Release.** The version is 0.32.0.
    - Both READMEs carry a 0.32.0 update note saying what changed, that role definitions changed so existing installations run `/cc-feather:setup update` and start a fresh session, that the Runner's hard limit covers only commands run through it, and that going back means reinstalling the 0.31.0 plugin and running setup update again.
    - The `docs/setup-validation.md` entry for 0.32.0 records the validation: the test runs, a setup update that brings an existing 0.31.0 installation's roles to the new templates, the Runner's validation on each supported environment with the hosts used (or that Linux was not validated and is refused), the live rehearsal and its outcome, that the tests and one rehearsal cannot show that a model always follows the rules, the review round, and that no `v0.32.0` tag exists when the entry is written.
17. **Unchanged.** Nothing changes in review counting, the Stop threshold, what counts as a call, the plan-review checklist's other items, the Security-critical definition, the handoff skill, the handoff tool, the setup program's code or the handoff-tidy command.

## User Stories

1. As a user, I want plan review to tell me which Claims carry resource risk, so that the risk is caught where it is foreseeable.
2. As a user, I want plan review to estimate the peak and say how, so that I can judge whether the budget is sensible.
3. As a user, I want plan review to propose how to run the risky part, so that someone who read the Plan designs the safe experiment before anything runs.
4. As a user, I want the kinds of risk given as examples only, so that a risk outside the list is still judged.
5. As a user, I want an unmarked Claim not treated as safe, so that the floor still applies to it.
6. As a user, I want an explicit plan review in off to judge resource risk too, so that off mode has a way in without a new command.
7. As a user, I want main to approve the Execution method before any run, so that no risky experiment starts without a second look.
8. As a user, I want to preset a default budget in my guidance, so that main asks me only when a Claim needs more.
9. As a user, I want main to ask me when no budget exists, so that no one invents one.
10. As a user, I want cc-feather to state no numbers, so that each project sets budgets that fit its machine and language.
11. As a user, I want an approval tied to the Claim, its reading set, the experiment and the budget, so that a changed Claim cannot run under an old approval.
12. As a user, I want a lost or mismatched approval to count as none, so that state loss never widens what runs.
13. As a user, I want the approval kept out of the Claim's text, so that recording it does not reopen reviews.
14. As a user, I want execution conditions carried into every brief that may execute code for the Claim, so that the role that runs it knows the limits.
15. As a user, I want main's own reruns and the final check to follow the same conditions, so that the risky part is not run unsafely by a different hand.
16. As a user, I want execution conditions to add to execution permission and never replace it, so that a budget never permits execution I restricted.
17. As a user, I want the Runner never to count as the isolated environment I named, so that only my own words name one.
18. As a user, I want a role to run the risky part only as approved and only inside the Runner, so that a real limit protects the machine.
19. As a user, I want a role never to raise a limit or enlarge the experiment, so that a small overrun cannot grow step by step.
20. As a user, I want the role still to judge whether the Claim holds, so that an approved method does not turn verification into rubber-stamping.
21. As a user, I want the role to say when the approved method cannot establish the Claim, so that a weak method is not mistaken for evidence.
22. As a user, I want that disagreement returned with the role's proposed method, so that its knowledge of the code is not lost.
23. As a user, I want main to decide on that proposal, so that the role never changes its own limits.
24. As a user, I want main to keep the old method only with new evidence, so that the same insufficient run is not repeated.
25. As a user, I want the Claim reported unverified when nothing changes, so that I decide instead of a loop.
26. As a user, I want a probe whose bound is unknown to count as unbounded, so that a guess never decides on its own.
27. As a user, I want a bounded outer loop or a timeout not to count as a bound, so that the incident's exact pattern is caught.
28. As a user, I want a bound that allows more than the budget to count as unbounded, so that a theoretical bound too large for the machine does not pass.
29. As a user, I want a role to state its estimated peak and basis, so that the estimate can be checked.
30. As a user, I want an Unbounded probe returned to main instead of being run, so that someone other than its author looks at it first.
31. As a user, I want the floor to cover modified Plan checks, so that changing a listed check does not bypass it.
32. As a user, I want main never to run a returned probe as it is or with a timeout alone, so that returning it is not just a delay.
33. As a user, I want a run stopped by a limit treated as inconclusive, so that containment is never mistaken for a refutation or a pass.
34. As a user, I want that judgement based on the Runner's limit event, so that a parent exiting 0 does not hide a child killed for memory.
35. As a user, I want a non-zero exit with no limit event treated as a failure, so that real failures are not excused as containment.
36. As a user, I want results established independently to stand, so that one stopped run does not erase other evidence.
37. As a user, I want a stopped call to close as a non-pass and a larger budget to need a new call, so that review counting stays as it is.
38. As a user, I want every returned probe and stopped run recorded on the Claim and told to me, so that I know it happened.
39. As a user, I want that record not to assume plan review missed it, so that invented probes and off-mode runs are described honestly.
40. As a user, I want the record carried into later briefs and listed at the end of the Plan, so that later runs start from it and I can decide whether to write it into the Plan.
41. As a user, I want the Runner to limit memory and time for the whole process tree, so that a child process cannot escape the limit.
42. As a user, I want the Runner to start its target at lower CPU priority, so that the machine stays usable.
43. As a user, I want the Runner to refuse when memory is short or containment is not available, so that a run never starts unprotected.
44. As a user, I want support decided by whether containment works, so that an environment that only looks supported is refused.
45. As a user, I want a Resource-risk claim to stop on an unsupported environment for me to decide, so that I can bring my own tool or accept the risk in my own words.
46. As a user, I want the Runner's output to keep the real end and say when it truncated, so that a failure line is never cut off.
47. As a user, I want the Runner's exit code to reflect the outcome, so that a failure cannot look like success.
48. As a user, I want the documentation to say what the Runner does not cover, so that I do not over-trust it.
49. As a user, I want Runner invocations to go through my normal permission handling with the target in plain text, so that I can see what will run.
50. As a user, I want to be warned against allowing every Runner invocation, so that I do not open a hole in my permission rules.
51. As a user, I want the reviewer's text to stop suggesting tests and probes, so that reviewer and verifier do not both run them.
52. As a user, I want one live rehearsal before release, so that the flow is seen working with a real model and a real limit.
53. As a user, I want the update note to tell me to run setup update and start a fresh session, so that installed roles get the new rules.
54. As a user, I want to know how to go back to 0.31.0, so that I can undo the change.
55. As a maintainer, I want the rules in each role definition, so that a role follows them even though CLAUDE.md does not apply to it.
56. As a maintainer, I want main's side written once with pointers elsewhere, so that ADR 0017 holds.
57. As a maintainer, I want the glossary to define the new terms, so that later rules use them consistently.
58. As a maintainer, I want an ADR for the layered decision and its rejected alternatives, so that a later reader knows why the earlier per-run design was replaced.
59. As a maintainer, I want tests that fail when a rule, the carry, the approval binding or the record is removed, so that they do not regress.
60. As a maintainer, I want Runner tests whose payloads limit themselves, so that a broken Runner cannot exhaust the test machine.
61. As a maintainer, I want the validation entry to say what the tests and the rehearsal cannot show, so that the release record is honest.

## Implementation Decisions

- **Plan review owns the judgement.** Resource risk is one checklist item in plan review, beside the existing items, not a separate review step, command or skill. It is not counted separately and adds no verdict of its own: a missing or weak Execution method is a plan-review finding like any other. The Security-critical classification and its security analysis are unchanged and unrelated.
- **One fresh call per run.** The approved Execution method travels in the brief of one fresh, normally counted call. There is no paused state and no continuation of a call after approval: the role's disagreement is an INCONCLUSIVE, which the existing rule for a call after INCONCLUSIVE already governs.
- **Role placement.** The operative rule lives in each role definition, because a role reads its definition on every call and main-session instructions do not apply to it. A CONTEXT.md entry alone would not reach an installed role.
- **One owner on main's side.** Main's side, approval, budget sources, the approval binding, the carry, main's floor, decisions after INCONCLUSIVE and the Observed resource risk record, has one owner among the delegation references: a new short reference for resource-risk runs. Review state's Execution and Dispatch record, plan review, the outcome-verification and Adversarial review procedures and the delegation skill's dispatch steps keep pointers to it, as ADR 0017 sets. Review state's Dispatch record gains the approved Execution methods and Observed resource risks among its contents.
- **Execution, not authorship.** The floor follows execution, not authorship: it covers a new or modified test or probe whoever wrote it, including main's reruns and reproductions.
- **Runner form.** The Runner is a standard-library Python script inside the delegation skill, resolved from the loaded skill like the handoff tool, with a Windows backend through a job object and a Linux backend through a transient systemd user scope. Main gives the resolved Runner path and the limits in the brief. The target command is passed as plain arguments after a separator, never encoded.
- **Runner result shape.** The JSON result carries at least: outcome (passed, target-failed, contained, refused, evidence-missing), limit event (memory, time, none, unknown), refusal reason, target exit code, peak memory with how it was measured, duration, output head and tail with truncation flags, and the limits it applied. Exit status is 0 only for passed, with one distinct code per other outcome.
- **Prototype findings the Runner keeps.** From cbc-go's prototypes: a parent can exit 0 while a child is killed for memory, so the limit event decides; systemd's default OOM policy stops the scope and loses evidence, so the scope keeps running and memory events are read from the cgroup; swap must be disabled for the scope; an enclosing job object can impose stricter limits, so the Runner checks for one; a target that hits the limit can hang until the time limit; a Linux supervisor killed outright leaves the scope running until its runtime limit, so the scope's own runtime limit equals the time limit; Git Bash rewrites path-like arguments before the Runner sees them, which the usage notes cover. The prototypes' known defects are not carried over: a runner exit status that ignores the target's outcome, an unbounded read of checkpoint evidence, and output that keeps only its beginning.
- **CPU priority.** The Runner lowers priority where the platform allows it; failure to lower it is reported in the result and does not refuse the run.
- **Version.** The release is 0.32.0, a minor version because role behaviour changes and a new tool ships. It also completes the `reviewer-execution-scope` handoff record.

## Testing Decisions

- **What a good test is.** Good tests check external behaviour: the shipped text a model reads, the templates setup deploys, the release documents, and the Runner's result and exit status for a given run. They do not pin wording that carries no decision or the Runner's internals.
- **Rule text seam.** A new test class pins the decision-carrying sentences: the plan-review item, its non-exhaustive examples and that a missing mark is not safety; main's approval, budget order, default budget and asking the user; the approval binding and what invalidates it; the carry into every brief and main's own runs; that conditions add to Execution and the Runner is not a named isolated environment; the role paragraph in each of the four roles, and its absence from the reviewer, analyst, scout, mech-executor and Explore definitions; main's decisions after INCONCLUSIVE; main's floor; the Observed resource risk record and its place; the Runner boundary and permission notes; and the pointers ADR 0017 requires. Prior art: the existing text-contract test modules for delegation rules, which read the references and templates.
- **Glossary and ADR.** Tests pin the five CONTEXT.md entries and ADR 0019's decision and rejected alternatives, following the existing tests that read CONTEXT.md and docs/adr.
- **Reviewer test.** The existing test that pins the reviewer's Execution paragraph is updated so its examples are a lint and a type check.
- **Runner seam.** A new test module invokes the Runner as a subprocess with small payloads and asserts its JSON result and exit status: a passing target; a failing target; a child that exceeds the memory limit while its parent exits 0; a target that exceeds the time limit; a descendant left running at the end; an output flood that keeps the real end and flags truncation; refusal when memory headroom is short and when containment is unavailable; and missing evidence. Every payload limits itself, for example by allocating at most twice the run's memory limit and then stopping, and every test has its own timeout, so a broken Runner cannot exhaust the test machine. Windows tests run on Windows; Linux tests run where a systemd user manager with a delegated memory controller exists and are skipped otherwise, while the refusal on an unavailable capability is tested everywhere. Prior art: the handoff tool's tests, which run the tool as a subprocess and assert its JSON output.
- **Setup tests.** The existing tests that show a changed role template is stale until setup update keep passing; no new setup test.
- **Release tests.** The existing release tests pin the version, the 0.32.0 update notes and the validation entry, following their conventions for the previous release.
- **Live rehearsal.** The rehearsal in Acceptance item 14 is run once and recorded in the validation entry; it is not automated.
- **Not shown.** Neither the tests nor one rehearsal show that a model always follows the rules.

## Out of Scope

- A hook that enforces Runner use. A probe on Claude Code 2.1.319 showed it is feasible, but binding a call to its Claim, failing closed, permission preservation and shell equivalence need their own validation; it is a later, separately gated release.
- Limiting the total of several runs started at the same time, across sessions or worktrees.
- A watchdog for the session's processes.
- A separate command or skill for resource-risk analysis.
- A paused, two-phase call or any change to review counting, the Stop threshold or what counts as a call.
- Runner support beyond Windows and Linux, such as macOS.
- Concrete budgets, priorities or parallelism values, and language-specific settings such as `GOMEMLIMIT`, `-p` or `-parallel`, which belong in project guidance.
- Containing work done through already running services, containers, WSL, remote services or MCP tools.

## Further Notes

- Origin: a proposal, its first addendum, Windows and Linux runner prototypes and field notes from the cbc-go session, kept outside the repository at `J:\gotmp\runner-proto-2026-11-07\`, and the incident probe at `J:\gotmp\verify-adminerr-01\`. They belong to that session and may be removed; the handoff record `resource-risk-proposal` summarises what this spec relies on. The incident probe must not be run.
- Measurements: the addendum measured about 0.5 to 0.6 GiB per Go package test, up to 1.5 GiB with `-race`, and about 12 MB per idle Go child process, and showed that an acyclic graph with shared subtrees makes an unbounded reference walk an exponential number of nodes; the field notes saw peaks of about 2.1 GiB for a single-package `-race` test and 2.3 GiB for a whole-repository govulncheck; the one limit hit was main's own build without limited parallelism, contained by a runner; a watchdog stopped nothing; and a runner output cap that kept only the beginning cut off a FAIL line. cc-feather's own suite on 2026-11-07: 1031 tests in 454 seconds wall, about 43 seconds of CPU, Python peak private memory about 37 MiB, at most one child process at a time.
- Hook probe, 2026-11-08, Claude Code 2.1.319 on Windows 11: PreToolUse hooks from settings and from a plugin fire inside subagents with `agent_id` and `agent_type`; rewriting the command works for Bash, PowerShell and background Bash; permission is checked against the rewritten command; SubagentStart carries no brief; continuing an agent fires SubagentStart again with the same `agent_id`; hooks in an agent definition's frontmatter did not fire; each hook call cost about 40 ms. These inform the deferred hook.
- This design replaces the per-run design of 2026-11-07, which judged risk only at each run and excluded the runner and planning-time marking. Codex second opinions (gpt-6-astra, effort high) shaped it: the floor must follow execution rather than authorship, cover security-executor and bound collection; an approved method before one fresh call is simpler than a paused call; a stopped call closes as a non-pass; approval needs a validity rule; a broad allow rule for the Runner defeats command-level permissions; and support must be decided by working containment.
- This spec also completes the `reviewer-execution-scope` handoff record.
- For codex-feather: not affected; the rules live in cc-feather's role templates and delegation references, and the Runner ships in cc-feather's delegation skill.
