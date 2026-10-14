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
