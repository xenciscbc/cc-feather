# Review counts are scoped to a session

Automatic review counts (plan review, code review, outcome verification) are per session: a resumed session starts a new count, because resuming requires the user. Within a session the non-reset rules stay (mode change, renamed plan, cosmetic split, different reviewer, model or wording). What crosses sessions is an unresolved verdict and the restriction it imposes, and only when an active handoff records it as plain text; the note is removed once a later call passes it or the user decides. Without such a handoff record, a resumed session carries no restriction from an earlier one.

## Considered Options

- **A fixed `審查：` segment with counts in the handoff**: carries budgets across sessions, but every update must maintain the format, the line grows, and it only protects against one extra review after a user-initiated resume.
- **No handoff record at all**: simplest, but a resumed session could commit or report a claim that was never approved.

## Consequences

A resume may run up to two more automatic calls for the same plan or claim. Restriction notes recorded in an active handoff still cross sessions, so such a claim is not committed or reported complete after a resume; an unresolved verdict that no active handoff records does not restrict a later session. The handoff runtime and record schema do not change.

(Amended by ADR 0007: the restriction now applies to landing on the default branch, release and reporting complete rather than to committing; a restricted claim may be committed before its passes.)
