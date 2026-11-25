# Test suites

This reference owns the Test suite catalogue: where it is, the format of its entries, what counts as a pass, the results that are not a pass, the gates and when main reads it. [Review state](review-state.md)'s Final check states what the final check runs with it, and this reference adds to review state's Execution and never replaces it: a catalogue allows no run that Execution does not. Before any decision of this reference that depends on a rule review state owns, in off and in auto, main reads [review state](review-state.md) in full; review state's Reading it says when an earlier full read still serves.

## The catalogue

- **Location.** A project may keep a Test suite catalogue at `.feather/test-suites.md` in the Working checkout, tracked in Git with the code it tests. Main reads it from the checkout at the commit it works on, not from the main worktree as with the Handoff store. Writing it is a change to the checkout: where Checkout leases are kept, it needs a lease like any other change, and the exemption for cc-feather's own records does not cover it.
- **Tracked at the commit.** Main uses the catalogue only when Git tracks it at the commit it works on. Main establishes this with `git cat-file -e <commit>:.feather/test-suites.md`, which shows it only by exiting 0; review state's Final check already requires the workspace to equal the commit to be landed or tagged, so the file main reads there is that commit's. When the file exists but is untracked or ignored, main reports that, does not use it and points the user to the setup document's Test suite catalogue section. A project without a tracked catalogue is not affected by this reference.

## Entries

- **Entry format.** The catalogue is markdown with one `## <suite name>` section for each Declared test suite. Each section has four required labelled lines: `Command:`, with its working directory, flags and environment variables; `Prerequisites:`; `Passes when:`; and `Gates:`. It may also have the optional lines `Budget:`, `Conflicts:` and `Affected part:`. Main reads the file as text, and no tool parses it.
- **Passes when.** `Passes when:` states positive evidence that main can see in the run's output that the required selection ran, such as a marker line or a count above zero for a named group. An allowed-skip rule, such as no SKIP for a named pattern, may be added to that evidence but never replaces it. A narrowed run used as a Claim's acceptance states evidence for its own selection.
- **Gates.** `Gates:` lists any of `landing`, `full` and `release`, or `none`. `landing` runs the suite at every final check, whatever its Final check scope; `full` makes the suite part of the project's full run, which the overall acceptance names and the final check runs at scope `full`; `release` runs it before a release or tag. A suite whose gates include `landing` is a Landing-required suite, and one whose gates include `release` is a Release-required suite. A suite with `none` runs only when some acceptance names it.
- **Optional lines.** `Budget:` states the project's resource guidance for the suite, as the [resource-risk runs reference](resource-risk-runs.md)'s The budget states. `Conflicts:` names what the suite must not run alongside, such as another suite or a shared resource. `Affected part:` states how its command is narrowed to the part a change affects.
- **An unclear entry.** When main cannot read an entry unambiguously, it reports the entry to the user. Until the entry is corrected or the user decides Accept and land naming it, every final check and release whose requirements the entry could affect counts as not run at the scope it needs. Main never guesses a gate and never treats an unclear entry as absent.

## Results

- **A pass.** A Declared test suite passes only when its command succeeds and its output shows the evidence its `Passes when:` line states.
- **Results that are not a pass.** A run whose assertions failed is a failure. A run whose prerequisites are missing, or whose output does not show its pass condition, has not run. A run stopped from outside has not completed, and is judged as the [resource-risk runs reference](resource-risk-runs.md)'s Main's floor states. Main keeps these three results apart, in its reports and in any record, and retries none of them automatically.
- **Failure first.** A run whose assertions failed is a failure even when its output also lacks the pass condition. A failure in one suite is not hidden by another suite that did not run, and a commit that has failed stays failed, as review state's Final check states.
- **A suite nothing requires.** A suite that no gate and no acceptance requires satisfies nothing when it is not run, and blocks nothing.

## When main reads it

- **Occasions.** Main reads the catalogue at the commit it works on before writing acceptance while Related-test acceptance is on, before every final check and before the release question.
- **Which version counts.** Which suites are Landing-required suites and Release-required suites is resolved from the catalogue at the commit to be landed or tagged. A change to the catalogue during a Plan is a change to a tracked file, which its Claim's code review sees in the diff like any other; the decision at the end of the Plan lists its gate changes, as review state's Accept and land at the end of the plan states.
