# Only what a Claim's acceptance needs holds its completion, except security

Code review held completion for more than the Claim promised. Any correctness bug, and any regression a reviewer inferred, blocked, whether or not the Claim's acceptance asked for it and whether or not anything showed the regression. Each such finding started another fix and another review, and each fix could surface the next one; the 0.23.0 round was finished only by deferring findings by hand. Nothing in the product said which non-security findings hold completion and which are recorded for later.

This record is written in parts, each by the ticket that implements its rule, so that its implementation and reviews can check it against the procedures they change. This part records the completion criteria.

The user decided (2026-10-14, in a grilling and after a security analysis of a first version; the [spec](../specs/completion-criteria.md) carries the acceptance and its security invariants):

- **Completion criteria.** A Claim's reviews judge it against four conditions: its acceptance as written is met; existing behaviour is not broken; it introduces no security problem and no data loss; and it has no Deviation. A Blocking finding shows one of them unmet. Every other finding, including an issue that predates the change, a correctness problem outside what the acceptance states and a regression that is only inferred, is a Non-blocking finding.
- **Evidence for a regression.** A broken existing behaviour that is neither a security problem nor data loss blocks only when a failing test or a reproduction shows it. The existing behaviour, and any written rule or shipped spec acceptance it is judged against, are taken at the Claim's base revision, never from the reviewed commit, so a change cannot redefine what it must not break.
- **Security stays as it is.** A security problem the change introduced or made exploitable, through a new route, permission or data flow even when the vulnerable code is outside the diff, and data loss the change introduced, are Blocking findings whatever the acceptance states, on the reviewer's evidence as before: a removed or weakened security control blocks without a reproduction. BROKEN keeps its meaning, Adversarial review keeps its timing, and a pre-existing vulnerability still becomes separate work in the project's tracker.
- **Deviations.** A Deviation from the Plan still blocks, and a material one still stops main to ask the user for a revised Plan.
- **The Follow-up record.** Non-blocking findings go to one Follow-up record per piece of work: with handoff maintenance active a handoff record of its own, otherwise listed in the completion report, which names it. It is data: its next step is always the user's decision whether to start a later Plan, the findings it quotes are marked as untrusted, reading or resuming it authorizes nothing, and Accept and land never relies on it. A later Plan that fixes recorded findings is new work under the existing rules.
- **In the reviewer role.** The criteria live in the installed reviewer definition as well as in the procedures, because procedures alone could not stop a reviewer from answering CHANGES_REQUESTED for a correctness problem outside the acceptance. The verifier already stays within the Claim and refutes only on a reproduced failure, and the adversary's criteria are the security criteria kept here, so both definitions are unchanged.
- **Both modes, every user, no setting.** The criteria apply in both Review modes and to every user.

This amends [ADR 0006](0006-review-state-validity-and-completion.md): what holds a Claim's completion is now these four conditions, not every correctness problem or inferred regression a review finds. ADR 0006's state model, validity rules and Acceptance gate are unchanged.

## Considered Options

- **Block on every correctness problem in the change**: the earlier criteria; rounds widen and loop, since each fix can surface the next finding.
- **A separate list of blocking exceptions**: its items restate the four conditions and invite reviewers to widen them.
- **A setting to choose the old criteria**: adds configuration for a rule every user benefits from.
- **Let security defects outside the acceptance land through Accept and land, with deferred Adversarial reviews**: the 2026-10-14 security analysis found that the promise to show every such defect to the user could be broken in many places, mostly through repository content alone, and ADR 0009 had already rejected letting a flaw the change introduced land.
- **Per-Claim review timing with Review schedules and Review groups**: where Claims share files, as nearly all of this project's Plans do, the groups collapse to reviewing after the whole Plan, so the 0.20.0 case that motivated it is not fixed; it is deferred to separate work on retained passes.

## Consequences

Fewer findings hold a Claim, and the rest are kept in one place for a later Plan the user starts. Security findings block as before, so security edge cases can still take several rounds; those are handled by the user's existing triage, outside these rules. The installed reviewer definition changed, so existing installations need `/cc-feather:setup update` after the plugin update. The verifier, adversary, analyst and executor definitions, the installed policy, the handoff skill and the configuration tool are unchanged. These rules are instructions to the model, kept consistent by tests rather than enforced by a tool: a reviewer can still misclassify a finding, and main's rejection of a finding given as blocking still needs evidence.

## Serial reviews and the final check

This part records the serial rule and the final check. Nothing stated that main leaves a working tree alone while a review of it runs, although a gated pass judges a workspace equal to the commit its brief names, and nothing ran the Plan's overall acceptance at the final commit before landing or release, so a dependency between Claims that main missed could still slip through.

The user decided (2026-10-14, with the completion criteria above):

- **Serial within a working tree.** While a code review, outcome verification or Adversarial review call runs, main does not change the working tree it judges, its own handoff records inside the project included, which it updates only between calls, and implementation in that working tree waits until the call ends. Before dispatching such a call, main confirms that no Assignment or background process it started that may write the working tree is still running, and at most one gated call that executes code runs in a working tree at a time. When main's comparison after a call finds a change to a file the Claim depends on, that call's pass is not used. This follows from the existing rule that a gated pass judges a workspace equal to the commit its brief names and unchanged during the call; it makes main's behaviour explicit.
- **No review worktrees.** Main does not create a worktree for a review on its own. Work the user runs in separate worktrees may proceed in parallel, each worktree its own workspace and serial in itself. The worktree exception extends no trust: each worktree still gets repository safety's preparation and checks. Shared test resources stay governed by each brief's target start and reset.
- **Final check.** Before landing or release, main runs the Plan's overall acceptance checks once at the final commit, within repository safety's Execution rules. It is main's own run, not a review step: it is not a counted step and adds no verdict. It runs only when the workspace equals the commit to be landed or tagged, established as for a gated pass, so an untracked or changed file cannot take part in it. When Execution does not allow it, it is recorded as not run, and that is stated before landing and in any Accept and land decision. A failure reopens the Claims it affects under the existing rules, and landing and release wait for their passes again; a failure that cannot be attributed with evidence reopens every Claim the check covers. It runs again at the new final commit after any fix.

Considered options for this part:

- **Main creates a worktree for each review**: it would let implementation continue while a review runs, but setting up a worktree can mean reinstalling dependencies or rebuilding in other projects, and each new worktree would need repository safety's preparation and checks again.
- **Parallel review calls in one working tree**: two calls that execute code in the same working tree can disturb what each other judges; parallel review calls are left to separate work on retained passes.
- **No final check, relying on each Claim's passes**: each pass judges one Claim, so a dependency between Claims that main missed could land unchecked.
- **A counted final review step with its own verdict**: it would stop the flow by itself at the Stop threshold and add a verdict, while its failure already reopens Claims under the existing rules.

Consequences of this part: a review call holds implementation in the working tree it judges until it ends, so work in one working tree takes longer than it would with a separate worktree per review, which the user can still set up. The final check adds one run of the Plan's acceptance checks before landing or release; it is the only safeguard this record adds for work merged from separate worktrees, and how passes carry over across such a merge is left to separate work.

## A single Accept and land decision

This part records the single Accept and land decision. When several Claims of a Plan needed an Accept and land decision, main could stop the user after each one, and nothing said how the list the user decides on is built.

The user decided (2026-10-14, with the completion criteria above):

- **Several Claims in one decision.** One Accept and land decision may name several Claims, stating for each the commit it accepts, the missing passes, the known vulnerabilities and the remaining risk, and, when the final check is recorded as not run, that it has not run.
- **Asked once, at the end of the Plan.** Main asks once, after every Claim of the Plan has finished its reviews and the final check has passed or is recorded as not run, before landing or release. Until then a Claim that needs the decision stays under the Acceptance gate as it stands, and its ticket stays unfinished.
- **Landing earlier.** Main asks earlier only when the user asks to land a Claim earlier. Landing a Claim before the end of the Plan lands every Claim on that branch, so main's list covers every gated Claim on the branch, and the decision states that the final check has not run.
- **The list comes from main's own observations.** Main builds the list from the review results it received in this session, not by reading a record in the working tree, and reports any difference from such a record. Each missing pass names the step and the call that left it missing, and the known vulnerabilities appear as the reporting role stated them, never merged or downgraded. Where main cannot establish a Claim's verdicts or missing passes, as after a context compaction, Unknown state applies and main stops and asks. Accept and land never relies on the Follow-up record.
- **What counts as the decision.** The user may confirm part of the list, the rest staying pending; "continue", silence or turning automatic review off is not a confirmation, and the decision covers only what was listed.

This amends [ADR 0008](0008-repository-authority-acceptance-and-gate-lifetime.md): an Accept and land decision may name several Claims, and main asks for it once at the end of the Plan, or earlier only for the whole branch when the user asks to land a Claim earlier, with a list built from its own observations in this session. ADR 0008's rule that Accept and land is the only way past the Acceptance gate without the passes, its recording and visibility, and the gate's conditions are unchanged.

Considered options for this part:

- **Ask after every Claim that needs the decision**: it stops the user once per Claim, while the decision can wait for the end of the Plan, when the whole list is known.
- **Build the list from a record in the working tree**, such as a handoff or the Follow-up record: anyone who can edit the working tree, repository content included, could drop a finding or a missing pass from what the user decides on; main reports a difference from such a record instead.
- **Merge or summarise known vulnerabilities across Claims**: a merged or downgraded entry hides what the user accepts.
- **Take "continue" or silence as a confirmation of the whole list**: the user would accept Claims they never chose.

Consequences of this part: the user is asked once per Plan for the Claims that need it, and a Claim waiting for the decision keeps its ticket unfinished until then. After a context compaction main may have to stop and ask instead of listing a Claim. A forged Accept and land note in a handoff is an existing weakness this part does not change.
