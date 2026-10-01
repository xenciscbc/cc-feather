# Code review gets a dedicated reviewer role

Code review in the automatic flow needs the diff, the history behind it (to tell a regression from an issue that predates the change) and cheap static checks, and it must see the whole change rather than what the implementing main agent chooses to show. We added a `reviewer` native role with Read, Glob, Grep and Bash instead of giving the job to an existing role.

## Considered Options

- **analyst with the diff pasted in by main**: keeps analyst read-only, but the implementer chooses what the reviewer sees, large diffs consume main's context, and without git history the reviewer cannot tell whether an issue predates the change.
- **analyst with Bash**: removes the tool-enforced read-only guarantee that security analysis and plan review rely on.
- **verifier doing code review too**: it already has Bash, but one role would judge both whether a Claim holds and whether its code is sound, and the two could not be given different models.

## Consequences

The installed role set grows to eight and `reviewer` is recorded in state. An existing installation picks it up through setup update, the same added-role path verifier used; until then, required code review is blocked rather than skipped. A plugin version without `reviewer` rejects a state that records it, so downgrading needs remove with the newer plugin first or a restore from the update backup.
