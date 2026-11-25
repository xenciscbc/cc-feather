# Test criteria

The criteria in this reference say what makes a test slower or less robust than it needs to be, and its correctness bar says what a change to an existing test keeps. A skill that writes, reviews or changes tests points to this reference and does not restate it.

## Rules this relies on

Whether a test or a test run is unbounded is decided by the Unbounded probe and Unbounded run configuration entries in [cc-feather's glossary](../../../CONTEXT.md), and which suites a check runs by its Test suite catalogue and Related-test acceptance entries. How a finding is weighed, how a test with resource risk is run and how work is reviewed are [the delegation skill](../../delegation/SKILL.md)'s rules. This reference copies none of them.

## Speed criteria

A test is slower than it needs to be where it has:

- per-test setup that can be shared per module or session;
- fixed sleeps that can wait on an event or a condition;
- real I/O, such as network, disk, processes or databases, that a fake can replace;
- tests that can run in parallel;
- inputs, data sets, iteration counts and fixtures larger than the behaviour needs, which a smaller one can verify;
- behaviour tested again at several levels.

## Further criteria

Each criterion applies under the condition it states, and only there.

- **No DOM where none is needed.** A frontend test that needs no DOM runs without a DOM environment, such as jsdom or happy-dom. It applies to a frontend test whose code under test renders no component and uses no DOM or browser API.
- **Port 0.** A test server binds port 0 rather than a fixed port, and the test reads the port it was given. It applies to every test that starts a listening server, unless the fixed port is what the test verifies.
- **Waits with a timeout.** A wait on a channel, promise or condition has a timeout, so that a missing event fails the test instead of hanging it. It applies to every such wait in a test or its setup that blocks until another goroutine, thread, process or callback acts.
- **Limited output.** Collected output has a limit. It applies wherever a test or its setup keeps output it collects, such as a child process's output, logs or captured events, whose size nothing else bounds.
- **Cleanup on failure paths.** Failure paths clean up goroutines, connections and transactions, as the success path does. It applies to every test or fixture that starts a goroutine, opens a connection or begins a transaction, and is met by cleanup that runs however the test ends, such as `t.Cleanup`, `defer`, a `finally` block or a fixture's teardown.
- **Fixed sleeps.** A fixed sleep becomes an event or condition wait, or a fake clock where it verifies the same logic, with real elapsed time kept only when real scheduling or clock integration is the property. It applies to every fixed sleep in a test or its setup.

## Correctness bar

The correctness bar governs changes to existing tests, speed-ups and removals alike: weakening an assertion, adding a skip, loosening a timeout and reducing generated cases are never offered there. Each speed-up names the test or assertion that keeps verifying the behaviour it touches. A speed-up keeps every assertion, test and timeout at least as strict as it is now: weakening an assertion, adding a skip or loosening a timeout is never offered. A smaller input is offered only when size is not what the test verifies. A test of performance, of a limit or boundary of size, of a race or concurrency that needs many iterations, or one that generates property-based or fuzz cases keeps its size; reducing the number of generated cases counts as weakening and is never offered. A smaller-input speed-up names the test that keeps verifying every boundary value the larger input reached. Removing a test is offered only in the Removals section, each removal either naming the test that covers exactly the same behaviour as evidence or being a replacement, for the user to decide one by one, replacements included. A replacement describes a smaller test that verifies the same fact and states that fact, then lists everything else the removed test verifies, such as wiring between components, routing or configuration loading, each item with the existing test that keeps verifying it. A replacement with any item lacking such a test is not offered. The smaller test is described in the report, not written; a picked replacement's Plan writes it before the heavy test is removed.
