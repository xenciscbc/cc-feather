# A user-invoked command drafts and checks the Test suite catalogue, and new tests must show they ran

[The declared test suites spec](../specs/declared-test-suites.md) made the Test suite catalogue data the project writes: cc-feather never created, edited or proposed edits to it on its own, and its Out of Scope excluded any tool that parses, validates or generates it. Its rules for acceptance applied only while Related-test acceptance was on, which is off by default. In use, writing an entry well proved hard, since a pass condition on the exit code, a missed build tag or an omitted prerequisite lets a gated suite pass without running what it should, and the catalogue went stale as work added tests that no suite selects.

The user decided (2026-11-27, in a design interview with a second opinion from Codex):

- **A command the user invokes**, `/cc-feather:test-suites`, drafts a catalogue when the project has none and checks it when it has one. It writes only the suites, gates and ignore change the user confirms, after reading both files again, under a Checkout lease, and commits nothing. Every gate is the user's choice; the command recommends one with a reason.
- **"Never creates, edits or proposes edits on its own" becomes "never creates or edits on its own".** cc-feather now reports gaps without being asked: main lists new tests a Claim adds that no suite selects, or that need a prerequisite no entry names, and `test-design` names the suite expected to select each Recommended test, listing an Uncatalogued one for the user to decide. It proposes edits when the user runs the command, or when a suite's command cannot show that a Claim's new tests ran.
- **New tests show they ran.** A Claim that adds tests to a suite gets primary acceptance whose output shows those tests executed and passed; a listing, a skip line, cached output or an exit code alone is not that evidence.
- **The catalogue rules are read before any acceptance.** In a project whose checkout tracks the catalogue, the installed delegation guidance has main read the test-suites reference before writing any acceptance, whether or not Related-test acceptance is on; only the narrowing rules stay tied to that setting. Because this changes installed guidance, existing installations need a setup update.

This supersedes the declared test suites spec's exclusion of a generating tool and its "proposes edits" clause; that spec as shipped is not rewritten.

## Considered Options

- **No command; users write the catalogue by hand**, as before: every project would rediscover how to write a pass condition and which tests its commands miss.
- **A parser or validator tool, or a check at every final check**: a tool would decide what "selects" means across frameworks that only reading the configuration can judge, and a check at every landing adds an analysis to work that the new acceptance rule already covers at the Claim.
- **The acceptance rules only while Related-test acceptance is on**: no setup update, but the default setting is off, so most projects would get no check.
- **Main edits the catalogue when a Claim adds tests**: the gates and pass conditions are the project's decisions, so main reports the gap and the user decides.

## Consequences

The command is not an automatic editor, a parser or a configuration setting: it runs only when the user invokes it, reads files unless the user agrees to a listing command, and writes nothing the user did not confirm. Until setup update, an installation keeps the old behaviour while Related-test acceptance is off, and `review` refuses to change a saved setting in that scope. Unplanned edits and acceptance the user writes get no check; running the command shows that the catalogue and the tests agree, not that any test ran. A dependency the command cannot settle statically is reported as not established, never as clean.
