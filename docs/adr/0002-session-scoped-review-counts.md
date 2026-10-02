# Review counts are scoped to a session

Automatic review counts (plan review, code review, outcome verification) are per session: a resumed session starts a new count, because resuming requires the user. Within a session the non-reset rules stay (mode change, renamed plan, cosmetic split, different reviewer, model or wording). What crosses sessions is an unresolved verdict and the restriction it imposes, recorded as plain text in an active handoff and removed once a later call passes it or the user decides.

## Considered Options

- **A fixed `審查：` segment with counts in the handoff**: carries budgets across sessions, but every update must maintain the format, the line grows, and it only protects against one extra review after a user-initiated resume.
- **No handoff record at all**: simplest, but a resumed session could commit or report a claim that was never approved.

## Consequences

A resume may run up to two more automatic calls for the same plan or claim. Restriction notes still cross sessions, so an unresolved claim is not committed or reported complete after a resume. The handoff runtime and record schema do not change.
