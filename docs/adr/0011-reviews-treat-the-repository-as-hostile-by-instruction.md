# Reviews treat the reviewed repository as hostile, by instruction

Until 0.20.0 only one bullet of the `/cc-feather:adversarial-review` command, the review of uncommitted changes, told the adversary how to read a repository without following links, without naming attacker-chosen files in shell commands and without letting Git run a Repository-chosen program. Every other review, and main's own preparation, read the repository with ordinary file tools and ordinary Git commands, so a tracked symbolic link, a configured fsmonitor or filter, or a crafted file name reached a role or main in any code review, outcome verification, plan review or security analysis.

The user decided (2026-10-11, in three grilling rounds, one Codex consultation and one Codex discussion; the [spec](../specs/repository-safety.md) carries the claims):

- **Threat model.** The reviewed repository's tracked content (files, `.gitattributes`, submodule settings) and its local Git metadata (`.git/config`, a worktree's `config.worktree`, the hooks directory, `info/attributes`, a gitfile, `commondir` and alternates) are attacker-controlled, because a repository can arrive with its `.git` directory. Concurrent modification of files while a review runs is not defended against and is recorded as residual risk, as are Claude Code's own Git commands at session start and its loading of the project's `CLAUDE.md`, imports and `.claude` settings, which happen outside these rules.
- **One set of rules for every review read.** Main and every role follow the same Git and path rules for every repository read a review makes, whatever the review kind or the claim's classification, unchanged dependencies included. Main's preparation and its commits get checks of their own, and roles without a shell read only within a scope main has checked.
- **Conservative file reads.** A role never reads content through a symbolic link, junction or reparse point of any kind, cloud-file placeholders and deduplicated files included, nor through a file with more than one hard link or a file that is not a regular file; it may still read the corresponding Git object. The handoff tool keeps its own narrower rule, because it reads only records Feather writes.
- **Incomplete coverage is a result, not a pass.** Reviewer gains INCONCLUSIVE, counted like verifier's.
- **Assurance level.** The rules are instructions to the model, kept consistent by tests, plus the handoff tool's own code. They are not enforced by permission rules, hooks or a sandbox, and the guarantee covers reads of reviewed source content, not every file Git itself consults; the spec lists the indirect reads it does constrain.

## Considered Options

- **Keep the rules in the one bullet, or apply them only to Security-critical claims**: untrusted code is untrusted whatever the claim's classification, and the gaps 0.19.0 recorded are outside that bullet.
- **Treat non-alias reparse points as ordinary content, as the handoff tool does**: opening a cloud-file placeholder can make the sync provider download it, a network effect roles may not cause; deciding by file attributes is platform-dependent and error-prone.
- **Read hard-linked files**: from one name a role cannot tell whether another name lies outside the project; package-manager stores that use hard links pay with INCONCLUSIVE coverage.
- **Defend against concurrent modification, or enforce the rules**: both need handle-based reads, isolation or a sandbox that native Windows lacks; 0.19.0 already excluded enforcement.

## Consequences

This extends ADR 0009's isolation rule: main, reviewer, verifier and adversary execute repository code for a review only when the user has said the repository is trusted to run on this machine and the change was written by the user or in the session, and otherwise only in an isolated environment the user names, because running a change runs the whole repository with it. Repositories kept in synced folders or built with hard-linking package managers get INCONCLUSIVE coverage for the affected files. A live model can still break an instruction; tests show only that the shipped texts and the handoff tool are consistent with this decision.
