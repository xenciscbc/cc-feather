"""Repository safety tests: the shared reference that states how main and every role read a repository for a review
(docs/specs/repository-safety.md, Claim C1), the documents that point to it, and a behaviour check that its Git forms
run no Repository-chosen program."""

from __future__ import annotations

import os
import re
import shlex
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests import feather_support
from tests.feather_support import config

REFERENCES = config.ROOT / "skills" / "delegation" / "references"
REFERENCE = REFERENCES / "repository-safety.md"
ADR_0011 = "0011-reviews-treat-the-repository-as-hostile-by-instruction.md"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class RepositorySafetyTests(unittest.TestCase):
    """C1: one shared reference states the rules of items 2 to 6 once, and every procedure, the command, the delegation
    skill, review state, the automatic-review guidance, the glossary, ADR 0009 and both READMEs point to it."""

    FILES = {
        "reference": REFERENCE,
        "plan-review.md": REFERENCES / "plan-review.md",
        "code-review.md": REFERENCES / "code-review.md",
        "outcome-verification.md": REFERENCES / "outcome-verification.md",
        "adversarial-review.md": REFERENCES / "adversarial-review.md",
        "review-state.md": REFERENCES / "review-state.md",
        "delegation SKILL.md": config.ROOT / "skills" / "delegation" / "SKILL.md",
        "command": config.ROOT / "skills" / "adversarial-review" / "SKILL.md",
        "review-auto.md": config.ROOT / "templates" / "review-auto.md",
        "CONTEXT.md": config.ROOT / "CONTEXT.md",
        "ADR 0009": config.ROOT / "docs" / "adr" / "0009-security-critical-claims-get-an-adversarial-review.md",
        "ADR 0011": config.ROOT / "docs" / "adr" / ADR_0011,
        "README.md": config.ROOT / "README.md",
        "README.zh-TW.md": config.ROOT / "README.zh-TW.md",
    }
    README_SECTIONS = {"README.md": "### Repository safety", "README.zh-TW.md": "### 儲存庫安全"}

    @classmethod
    def source(cls, name: str) -> str:
        """Text of one place: '<file>'; 'reference#<heading>' (a '## ' section of the reference);
        '<procedure>#<step number>'; '<procedure>#after' (the paragraph that compares the workspace after a call);
        'plan-review.md#after' likewise; 'delegation SKILL.md#security analysis' (that paragraph);
        'delegation SKILL.md#<heading>'; 'command#intro', 'command#gated' and 'command#<bullet label>';
        'review-state.md#<bullet label>'; '<README>#section' (the Repository safety section) or '<README>#<rule label>'."""
        path, _, part = name.partition("#")
        text = read(cls.FILES[path])
        if not part:
            return text
        if path == "reference":
            return text.split(f"\n## {part}\n", 1)[1].split("\n## ", 1)[0]
        if path in ("plan-review.md", "code-review.md", "outcome-verification.md", "adversarial-review.md"):
            if part.isdigit():
                return next(line for line in text.splitlines() if line.startswith(f"{part}. "))
            if part == "after":
                return next(p for p in text.split("\n\n") if "compares the workspace with the pre-dispatch state" in p
                            or "Compare the workspace with the pre-dispatch state" in p)
        if path == "delegation SKILL.md":
            if part == "security analysis":
                return next(line for line in text.splitlines() if line.startswith("For requested security analysis"))
            return text.split(f"\n## {part}\n", 1)[1].split("\n## ", 1)[0]
        if path == "command":
            if part == "intro":
                return text.split("\n# adversarial-review\n", 1)[1].split("\n## ", 1)[0]
            if part == "gated":
                return next(p for p in text.split("\n\n") if p.startswith("Before any call on a claim the gate covers"))
            return next(line for line in text.splitlines() if line.startswith(f"- **{part}.**"))
        if path in cls.README_SECTIONS:
            if part == "section":
                return text.split(f"\n{cls.README_SECTIONS[path]}\n", 1)[1].split("\n### ", 1)[0]
            return feather_support.review_rules_source(name)
        return feather_support.review_rules_source(name)

    assert_whole_sentence = feather_support.adversarial_retries_assert_whole_sentence
    assert_pinned = feather_support.adversarial_retries_assert_pinned
    sentences = staticmethod(feather_support.sentences)

    PREFIX = ("git --no-pager --no-optional-locks -c core.fsmonitor= -c core.quotePath=true -c log.showSignature=false "
              "-c mailmap.file= -c mailmap.blob= -c blame.ignoreRevsFile= -c diff.orderFile=/dev/null "
              "-c submodule.recurse=false")

    # Item 1 and D1–D4, D6: scope, threat model, the glossary term, the assurance level and residual risk.
    SCOPE = (
        "These rules apply to every repository read that main or a role makes for a plan review, code review, outcome "
        "verification, Adversarial review or security analysis, to main's preparation for them and to main's comparison "
        "of the workspace after each call, whatever the claim's classification, unchanged dependencies included.",
        "Searches by scout or Explore that main dispatches outside such a review are not covered.",
        "The reviewed repository's tracked content (files, `.gitattributes`, submodule settings) and its local Git "
        "metadata (`.git/config`, a worktree's `config.worktree`, the hooks directory, `info/attributes`, a gitfile, "
        "`commondir` and alternates) are attacker-controlled.",
        "User- and system-level Git configuration and the user's own environment are trusted.",
        "A Repository-chosen program is a program that the reviewed repository's configuration, attributes or hooks "
        "select and Git may run, such as an fsmonitor, a textconv or external diff, a filter, a signing program or a "
        "hook; running one counts as executing the code under review.",
        "These rules are instructions to the model, kept consistent by tests, plus the handoff tool's own code.",
        "No permission rule, hook or sandbox enforces them, so a live model can still break one.",
        "The path rules guarantee how main and the roles read reviewed source content with the file tools and shell "
        "tools; files Git itself consults are outside that guarantee, except the indirect reads that Safe Git "
        "invocation, Paths and names and Main's preparation constrain.",
        "Concurrent modification of a file between a check and a read is not defended against and is residual risk.",
        "Claude Code itself runs Git in the project when a session starts and loads the project's `CLAUDE.md`, its "
        "imports and its `.claude` settings, all before and outside these rules; that is residual risk too.",
        "The handoff tool keeps its own link rule, under which only name-surrogate or unidentified reparse points are "
        "links and hard links are rejected, because it reads only records Feather writes.",
    )
    # Item 2 (G1–G7, C12, R2-Q5, S19): the common prefix and its rules.
    GIT = (
        "Every Git command main or a role runs to read a repository for a review starts with this common prefix, and the "
        "forms below write it as `<prefix>`:",
        "The command disables fsmonitor with an empty value, `-c core.fsmonitor=`, which disables it whether the "
        "installed Git reads the setting as a boolean or as a hook path.",
        "The command runs with `--no-optional-locks` and `--no-pager`, so no index refresh is written and no configured "
        "pager runs.",
        "The command writes no index, object, ref, configuration or working-tree file, contacts no remote and runs no "
        "Repository-chosen program; only main's operations under Before add, commit, tag or push write, and Git's own "
        "index refresh is not an exception.",
        "History and differences are read only between commits or objects, with `--no-ext-diff --no-textconv`; `blame` "
        "always names a commit and uses `--no-textconv`; `cat-file` and `show` are never given `--filters` or "
        "`--textconv`.",
        "Working-tree content is read under Paths and names, never through a working-tree diff or `git status`.",
        "No signature is verified: the prefix sets `-c log.showSignature=false`, and every `log` or `show` that prints "
        "commits names an explicit format containing no signature placeholder, so a format the repository configures is "
        "never used.",
        "No mailmap file the configuration names is read, `-c mailmap.file= -c mailmap.blob=`, and no other file a "
        "setting names for these commands, `-c blame.ignoreRevsFile= -c diff.orderFile=/dev/null`; a tracked "
        "`.mailmap` is repository content like any other.",
        "The order file is cancelled with `/dev/null`, as Git documents, because an empty value makes `git diff` fail.",
        "In a checkout with a promisor remote, `--no-lazy-fetch` follows `git` only on Git 2.45.0 or later; on an older "
        "Git the reader reads no missing object, does not probe object existence to find one, and reports what it could "
        "not examine.",
        "The command never recurses into a submodule, `-c submodule.recurse=false` and `--submodule=short` where a "
        "command accepts it; content under a submodule's path is reported as not examined.",
        "`git status`, working-tree diffs (`git diff` without two commits, `diff-files`, and `diff-index` without "
        "`--cached`) and the `--filters` and `--textconv` options are not used for a review.",
        "An object read from the index always names its stage, `:0:'<path>'`, so that a path is never read as another "
        "stage.",
        "Names a listing prints reach another Git command only as NUL-separated data on standard input, such as "
        "`check-attr -z --stdin`, never on its command line.",
    )
    # The per-operation forms (Implementation Decisions), each run by the behaviour check below.
    FORMS = (
        "git <prefix> ls-files -z --stage",
        "git <prefix> ls-files -z --others --exclude-standard",
        "git <prefix> ls-files -z --cached --ignored --exclude-standard",
        "git <prefix> ls-tree -r -z --full-tree <commit>",
        "git <prefix> cat-file blob <commit>:'<path>'",
        "git <prefix> cat-file blob :0:'<path>'",
        "git <prefix> diff --no-ext-diff --no-textconv --submodule=short <commit> <commit> -- '<path>'",
        "git <prefix> diff-tree -r -z --no-ext-diff --no-textconv <commit> <commit>",
        "git <prefix> log --no-ext-diff --no-textconv --submodule=short --format='%H %an %ad %s' <commit>",
        "git <prefix> blame --no-textconv <commit> -- '<path>'",
        "git <prefix> check-attr -z <attribute> -- '<path>'",
        "git <prefix> rev-parse --show-toplevel --git-dir --git-common-dir --is-bare-repository",
        "git <prefix> hash-object -- '<path>'",
    )
    # Item 3 (P1–P6, R1-Q3–Q10, S4, S17, B8, C3).
    PATHS = (
        "Before reading a path's content with the file tools or a shell tool, the reader establishes with file-system "
        "metadata that does not follow links, not with Git:",
        "that no component of the path is a symbolic link, junction or reparse point of any kind, cloud-file placeholders "
        "and deduplicated files included, and that its canonical path lies inside the project, comparing case-sensitively "
        "unless the file system is known to be case-insensitive;",
        "that it is a regular file, not a directory read as content, FIFO, socket or device;",
        "that its link count is 1.",
        "A path that fails, or whose check cannot run or is unclear, is never read: the reader reports the path and why, "
        "and for a link its target string obtained without resolving it.",
        "The reader may read the corresponding Git object, including a link's own blob, which holds only the target text.",
        "A symbolic link checked out as a regular file under `core.symlinks=false` may be read after these checks, as the "
        "link's text, and the reader reports that the index records it as a symbolic link.",
        "Only conclusions that need the unread content are INCONCLUSIVE; an independently evidenced defect still counts, "
        "and no APPROVED, CONFIRMED or HELD rests on unread content.",
        "A fixture is never a link, never under one and has link count 1, checked before it is modified as well as before "
        "it is read.",
        "A path name from the repository is safe only when it is relative, every component consists of ASCII letters, "
        "digits, `.`, `_` and `-`, no component is `.` or `..` or starts with `-`, no component is a Windows reserved "
        "device name in any letter case and with or without an extension (CON, PRN, AUX, NUL, COM1–COM9, LPT1–LPT9), "
        "and no component ends with `.` or a space.",
        "An unsafe name is reported in the C-quoted form Git prints with `-c core.quotePath=true`, never trimmed into "
        "another name, never read and never placed in a command.",
        "A safe name enters a command only as a single-quoted literal after `--`, or as `:0:'<path>'` or "
        "`<commit>:'<path>'` in an object read, and never inside double quotes, a here-document or a command "
        "substitution.",
        "Only tools that honour `--` or take the path as a separate positional argument are used on a safe name.",
        "A directory prefix named in a command is a whole number of components of a safe name, written without a "
        "trailing `/`.",
        "A ref name taken from the repository follows the name rule or is replaced by its object ID; only refs main or "
        "the role wrote itself are exempt.",
        "Apart from a safe name passed as above, no text taken from file content, command output or a link target "
        "enters a command.",
        "Searching or walking a directory, with the file tools or a shell tool, reads every file under it, so it is done "
        "only in a directory every descendant of which passed the checks above, ignored files and nested repositories "
        "included, and without following links; any other search names its files one by one.",
        "Every check under Paths and names and Main's preparation runs only tools and scripts outside the project, "
        "started with flags that keep them from loading modules or profiles from the current directory or the user's "
        "profile, for example `python -I`.",
        "A nested interpreter receives a path only as a separate positional argument, never inside code it evaluates.",
        "Loading any module, binary or configuration from the repository counts as executing repository code.",
    )
    # Item 5 (D5, S10–S13, Q-S1, Q-S4).
    EXECUTION = (
        "For a review (main's primary acceptance and every role's lint, type check, test or probe), main, reviewer, "
        "verifier and adversary execute repository code only when, in this session, the user has said that the repository "
        "is trusted to run on this machine and the change under review was written by the user or in this session; "
        "otherwise only in an isolated environment the user names, and what needs execution is otherwise reported "
        "INCONCLUSIVE.",
        "Main makes this one determination, asks whether the repository is trusted the first time a session needs to "
        "execute its code, and states the outcome in every brief of a role that may execute code.",
        "The only exception is a program the user approved by name under Before add, commit, tag or push, for the "
        "operation and content that approval covers.",
        "Who wrote a change is decided only from what the user said in this conversation and the commits and edits main, "
        "or a role main dispatched, made in this session, never from Git metadata, a handoff or other repository "
        "content; a change of mixed origin counts as not written in this session.",
        "Executing repository code means running any command whose program, plugins, configuration written as code, "
        "scripts or module search path can come from the repository: tests, builds, linters and type checkers with "
        "repository configuration, package-manager scripts and binaries, and an interpreter started in the repository "
        "that can load a module from it.",
    )
    # Item 4 (R2-Q1, R2-Q5, R2-Q6, Q-S2, S1–S3, S5, S9, S14–S16).
    PREPARATION = (
        "Before the first Git command it runs in a session for a repository, whether for a review or under Before add, "
        "commit, tag or push, main checks with `git --version` that Git is 2.32 or later, since older Git follows a "
        "symbolic link when it reads `.gitattributes`, `.gitignore` or `.mailmap`; otherwise it reports it and runs no "
        "such command and dispatches nothing.",
        "confirms that the version check has run;",
        "reads the repository's configuration with origins and scopes and without following includes, covering its local "
        "and worktree scopes, and reports and asks the user before dispatching when `include.path` or an `includeIf` "
        "path, `core.attributesFile` or `core.excludesFile` points outside the project, when `core.worktree` or "
        "`core.bare` is set, when the Git directory is a gitfile or has a `commondir` pointing outside the project, when "
        "alternates are configured, or when Git's top-level directory differs from the project;",
        "lists changes and establishes that the workspace equals the reviewed commit only with commands that read the "
        "index, objects and attributes and with reads under Paths and names, never with `git status`, a working-tree "
        "diff or another command that compares or refreshes the working tree;",
        "records a snapshot of what item 2 read, the list of hooks under Before add, commit, tag or push and "
        "`info/attributes`, and before every later dispatch and in every comparison of the workspace after a call reads "
        "them again; a difference is reported and asked about before the next dispatch;",
        "compares the workspace after each call under the same restrictions as item 3.",
        "Before comparing any path under item 3, main checks the `filter` attribute of every path it will compare and, "
        "after the user has answered any question from item 2, reads the effective configuration with its includes to "
        "find which drivers are defined.",
        "When any compared path's filter names a defined driver, main stops and asks the user for that call; until the "
        "user decides, the call is not dispatched and the claim is reported blocked.",
        "Each path passes Paths and names before its content is hashed, the hash applies only built-in conversions such "
        "as end-of-line handling, and no hash is written to the object database.",
        "A tracked symbolic link is compared by its target text, read from metadata without following it; any other "
        "compared path that fails Paths and names means equality cannot be established, so main reports the claim "
        "blocked and asks the user.",
        "For a review assignment of a role without a shell, main gives an allowlist: the files that passed Paths and "
        "names and the directories every descendant of which, ignored files and nested repositories included, passed it.",
        "The role reads only listed files and searches only listed directories.",
        "Main also lists the tracked files that ignore rules match, since a search skips them, and the brief says an empty "
        "search result does not show that something is absent.",
        "Main's brief carries this paragraph for roles without a shell word for word, so a role installed by the user, "
        "such as the user's own Explore, receives it too:",
    )
    # Item 4 (S14–S16): the paragraph C2 item 4 copies into analyst, scout and Explore, kept whole.
    NO_SHELL_PARAGRAPH = (
        "In a review assignment, read only the files your brief lists and search only the directories it lists, and "
        "never follow a symbolic link, junction or other reparse point. An empty search result does not show that "
        "something is absent, because a search skips ignored files; report what your reads and searches leave "
        "unexamined. When a review assignment's brief gives no allowlist, report it as a missing requirement instead of "
        "reading the repository."
    )
    # Item 6 (R2-Q2, S6–S8, Q-S3, Q-S4, B7, plan review call 2's R2).
    WRITING = (
        "This rule adds a condition to main's existing authority under [review state](review-state.md)'s Commits before "
        "the passes and Repository authority; it grants no authority, and a tag still needs the user's authority for "
        "tagging.",
        "Before each `git add`, commit, tag or push, main runs it only in its fixed form and first lists what the "
        "repository's local Git metadata lets it run or use:",
        "| `git add` | the claim's files only, as safe names after `--` | hooks; filter drivers on every tracked path and on "
        "each untracked path being added | `-c core.hooksPath=` a directory outside the project with nothing in it, and "
        "each configured `hook.<name>` disabled |",
        "| commit | message by `-m` or `-F`, no editor, no `--trailer` | hooks; filter drivers on every tracked path; "
        "signing: `commit.gpgSign`, `gpg.program`, `gpg.<format>.program`, `gpg.ssh.defaultKeyCommand` | as for `git "
        "add`, plus `--no-verify`, `--no-gpg-sign` and `-c commit.gpgSign=false` |",
        "| tag | annotated message by `-m` or `-F`, no editor | hooks; signing: `tag.gpgSign`, `tag.forceSignAnnotated` "
        "and the signing programs above | as for `git add`, plus `--no-sign` and `-c tag.gpgSign=false -c "
        "tag.forceSignAnnotated=false` |",
        "| push | one remote named by main and an explicit refspec for each ref, with `--no-follow-tags` and "
        "`--recurse-submodules=no` | hooks; the effective push URL of that remote and each ref it updates; every setting "
        "in the local or worktree scope under `remote.<name>.*`, `url.*`, `http.*`, `credential.*`, `ssh.*`, "
        "`protocol.*` and `push.*`, and `core.sshCommand`, `core.askPass` and `core.gitProxy` | as for `git add`, plus "
        "`--no-verify`, `--no-signed` and `-c push.gpgSign=false` |",
        "Hooks are files in the effective hooks directory that do not end in `.sample`, including one `core.hooksPath` "
        "names in the local configuration, and hooks the configuration defines under `hook.<name>`; filters run during "
        "the operation's index refresh even for paths it does not commit.",
        "Main reads every list of this rule from the effective configuration with its includes followed, with each "
        "setting's origin and scope, and a setting an include brings into the local or worktree scope counts as that "
        "scope, so a setting a tracked file supplies through an include is listed like any other.",
        "The push settings are listed by namespace, not by key, because any of them can change where content and "
        "credentials go or which program runs while the URL stays the same.",
        "Every operation also disables fsmonitor with `-c core.fsmonitor=`.",
        "A claim file whose name is unsafe under Paths and names is not added; main reports it and does not perform the "
        "operation.",
        "When the list is not empty, main names each program with the SHA-256 of its content, read under Paths and names "
        "(a hook file, or the repository file a configured command names; for a configured command naming no repository "
        "file, its command string), and for a push the destination URL and refs, and asks the user to choose one of "
        "three answers:",
        "This is the user's approval of those programs under the exception in Execution.",
        "This is the user's explicit permission to skip hooks, and main offers it only when every listed hook can be "
        "disabled on the installed Git as the table shows.",
        "This leaves the claim blocked as for a user instruction not to commit or push.",
        "Filters, transport settings and the destination cannot be skipped, because skipping would change what is "
        "written or where it is sent, so for them the choices are only run or not perform.",
        "When main cannot establish a program, its content or the effective destination, it does not perform the "
        "operation and reports why.",
        "The answer covers exactly the programs, contents and destination main named, for the rest of the session; when "
        "a later operation's list, a content hash or the destination differs, main asks again.",
        "The answer does not cross sessions and is not written into a handoff.",
    )

    def test_the_reference_states_its_scope_threat_model_and_assurance(self):
        self.assertTrue(read(REFERENCE).startswith("# Repository safety\n"))
        self.assert_pinned({"reference#Scope and assurance": self.SCOPE})

    def test_the_reference_gives_the_common_prefix_once_with_its_rules(self):
        section = self.source("reference#Safe Git invocation")
        self.assertIn(f"```text\n{self.PREFIX}\n```", section)
        self.assertEqual(read(REFERENCE).count(self.PREFIX), 1)
        self.assert_pinned({"reference#Safe Git invocation": self.GIT})
        for form in self.FORMS:
            with self.subTest(form=form):
                self.assertIn(f"`{form}`", section)

    def test_every_git_form_carries_the_prefix_and_no_option_that_runs_a_program(self):
        # Item 8: a form that dropped the prefix, compared the working tree or verified a signature would run a
        # Repository-chosen program.
        section = self.source("reference#Safe Git invocation")
        rows = [line for line in section.splitlines() if line.startswith("| ") and not line.startswith("| ---")][1:]
        spans = [span for row in rows for span in re.findall(r"`(git [^`]*)`", row)]
        self.assertGreaterEqual(len(spans), len(self.FORMS))
        for span in spans:
            with self.subTest(span=span):
                self.assertTrue(span.startswith("git <prefix> "))
                self.assertNotRegex(span, r"--(?:filters|textconv|show-signature|ext-diff)\b|\s-w\b|%G")
                subcommand = span.split()[2]
                if subcommand in ("diff", "diff-tree", "log", "show"):
                    self.assertIn("--no-ext-diff --no-textconv", span)
                if subcommand in ("log", "show"):
                    self.assertIn("--format=", span)
                if subcommand == "blame":
                    self.assertRegex(span, r"blame --no-textconv <commit> -- ")
                if subcommand in ("diff", "diff-tree"):
                    self.assertRegex(span, r"<commit> <commit>")
        # Every sentence of the reference that names `git status` or a working-tree diff forbids it.
        for sentence in self.sentences(read(REFERENCE)):
            if "`git status`" in sentence:
                with self.subTest(sentence=sentence[:60]):
                    self.assertRegex(sentence, r"\bnever\b|not used")

    def test_every_path_placeholder_is_a_single_quoted_literal(self):
        text = read(REFERENCE)
        placeholders = list(re.finditer(r"<path>", text))
        self.assertGreaterEqual(len(placeholders), 8)
        for match in placeholders:
            context = text[max(0, match.start() - 10):match.end() + 1]
            with self.subTest(context=context):
                self.assertRegex(context, r"(?:-- |:0:|<commit>:)'<path>'$")
        for span in re.findall(r"`([^`]*<path>[^`]*)`", text):
            with self.subTest(span=span):
                self.assertNotRegex(span, r"[\"$\\]|<<")

    def test_the_reference_states_the_path_and_name_rules(self):
        self.assert_pinned({"reference#Paths and names": self.PATHS})

    def test_the_safe_name_rule_leaves_nothing_for_a_shell_to_interpret(self):
        """Moved from the command's Uncommitted changes bullet (0.19.0 C5 item 9.10, Q24, N1) and tightened by C1 item 3
        (P3, R1-Q9): a component holds only ASCII letters, digits, `.`, `_` and `-`, so a safe name read through a
        quoted form is one word; a crafted name that breaks out of the quotes fails the rule, and so do `..`, a leading
        `-`, a reserved device name and a trailing dot or space."""
        sentence = self.PATHS[9]
        self.assertIn("every component consists of ASCII letters, digits, `.`, `_` and `-`,", sentence)
        allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._-")
        reserved = {"CON", "PRN", "AUX", "NUL", *(f"COM{n}" for n in range(1, 10)), *(f"LPT{n}" for n in range(1, 10))}

        def safe(name):
            if not name or name.startswith("/"):
                return False
            for component in name.split("/"):
                if (not component or component in (".", "..") or component.startswith("-")
                        or not set(component) <= allowed or component.endswith((".", " "))
                        or component.split(".", 1)[0].upper() in reserved):
                    return False
            return True

        for character in sorted(allowed):
            with self.subTest(character=character):
                self.assertEqual(shlex.quote(character), character, "the shell would interpret an allowed character")
        for character in "'\"\\$`!*?[]{}~#&|;<>() \t\n\r:%=@,+^":
            with self.subTest(character=repr(character)):
                self.assertFalse(safe(f"a{character}b"))
        for name in ("skills/adversarial-review/SKILL.md", "sub/a_b.9", "Z9", "con1/x.txt"):
            with self.subTest(name=name):
                self.assertTrue(safe(name))
                for form in ("cat-file blob :0:'<path>'", "blame --no-textconv HEAD -- '<path>'"):
                    expected = [word.replace("<path>", name) for word in shlex.split(form)]
                    self.assertEqual(shlex.split(form.replace("<path>", name)), expected)
        for name in ("-n", "sub/-a_b.9", "..", "a/../b", "./a", "/etc/x", "aux.txt", "CON", "Lpt9.md", "a.", "a/b ",
                     "a//b", "a'$(id)'b", "a' 'b", "x'`id`'y"):
            with self.subTest(name=name):
                self.assertFalse(safe(name))
        # The rule names each of those exclusions.
        for phrase in ("no component is `.` or `..` or starts with `-`", "(CON, PRN, AUX, NUL, COM1–COM9, LPT1–LPT9)",
                       "in any letter case and with or without an extension", "no component ends with `.` or a space"):
            self.assertIn(phrase, sentence)

    def test_the_reference_states_the_execution_rule(self):
        self.assert_pinned({"reference#Execution": self.EXECUTION})

    def test_the_reference_states_mains_preparation_and_the_allowlist(self):
        self.assert_pinned({"reference#Main's preparation": self.PREPARATION})

    def test_the_paragraph_for_roles_without_a_shell_stands_whole_once(self):
        # C2 item 4 copies this paragraph word for word into analyst, scout and Explore.
        paragraphs = read(REFERENCE).split("\n\n")
        self.assertEqual(paragraphs.count(self.NO_SHELL_PARAGRAPH), 1)
        index = paragraphs.index(self.NO_SHELL_PARAGRAPH)
        self.assertTrue(paragraphs[index - 1].endswith("receives it too:"))
        self.assertIn(self.NO_SHELL_PARAGRAPH, self.source("reference#Main's preparation"))

    def test_the_reference_states_mains_checks_before_add_commit_tag_or_push(self):
        self.assert_pinned({"reference#Before add, commit, tag or push": self.WRITING})
        section = self.source("reference#Before add, commit, tag or push")
        for label in ("Run them as configured.", "Skip hooks and signing.", "Do not perform the operation."):
            self.assertIn(f"- **{label}**", section)

    # Item 1: the glossary entry, which ADR 0011 and the reference use.
    GLOSSARY = ("A program that the reviewed repository's configuration, attributes or hooks select and Git may run, such "
                "as an fsmonitor, a textconv or external diff, a filter, a signing program or a hook. The reviewed "
                "repository's tracked content and its local Git metadata are both treated as attacker-controlled, so "
                "running one counts as executing the code under review.\n_Avoid_: git hook, safe git")

    def test_the_glossary_defines_repository_chosen_program_before_blocking_finding(self):
        text = self.source("CONTEXT.md")
        self.assertEqual(feather_support.glossary_entries(text)["Repository-chosen program"], self.GLOSSARY)
        review = text.split("\n## Review\n", 1)[1]
        self.assertLess(review.index("**Repository-chosen program**:"), review.index("**Blocking finding**:"))
        self.assertGreater(review.index("**Repository-chosen program**:"), review.index("**Adversarial review**:"))
        for place in ("reference", "ADR 0011"):
            with self.subTest(place=place):
                self.assertIn("Repository-chosen program", self.source(place))

    # Item 1: each procedure points to the reference where it dispatches or prepares a call and where it compares the
    # workspace after one; so do the command and the delegation skill's security-analysis paragraph.
    POINTERS = {
        "plan-review.md#2": (
            "Main and analyst follow [repository safety](repository-safety.md) for every repository read the review "
            "makes: main prepares the call as its Main's preparation describes and gives analyst, which has no shell, the "
            "allowlist and paragraph it describes.",
        ),
        "plan-review.md#after": (
            "Analyst has no shell, but main still compares the workspace with the pre-dispatch state after each call, "
            "under [repository safety](repository-safety.md)'s Main's preparation, and preserves or reports any change.",
        ),
        "code-review.md#2": (
            "Main and reviewer follow [repository safety](repository-safety.md) for every repository read the review "
            "makes, and main prepares the call as its Main's preparation describes.",
        ),
        "code-review.md#after": (
            "Main makes that comparison, like every repository read of the review, under [repository "
            "safety](repository-safety.md)'s Main's preparation, never with `git status` or a working-tree diff.",
        ),
        "outcome-verification.md#2": (
            "Main and verifier follow [repository safety](repository-safety.md) for every repository read the "
            "verification makes, and main prepares the call as its Main's preparation describes.",
        ),
        "outcome-verification.md#after": (
            "Main makes that comparison, like every repository read of the verification, under [repository "
            "safety](repository-safety.md)'s Main's preparation, never with `git status` or a working-tree diff.",
        ),
        "adversarial-review.md#2": (
            "Main and adversary follow [repository safety](repository-safety.md) for every repository read the call "
            "makes, and main prepares the call as its Main's preparation describes.",
        ),
        "adversarial-review.md#after": (
            "Main makes that comparison, like every repository read of the call, under [repository "
            "safety](repository-safety.md)'s Main's preparation, never with `git status` or a working-tree diff.",
        ),
        "command#intro": (
            "Main and adversary follow [repository safety](../delegation/references/repository-safety.md) for every "
            "repository read the call makes, in main's preparation of the call and in its comparison of the workspace "
            "after it.",
        ),
        "command#gated": (
            "Main makes these checks under [repository safety](../delegation/references/repository-safety.md)'s Main's "
            "preparation, and makes a commit only as its Before add, commit, tag or push allows.",
        ),
        "delegation SKILL.md#security analysis": (
            "Main and analyst follow [repository safety](references/repository-safety.md) for every repository read a "
            "security analysis makes, and main prepares the brief, including analyst's allowlist, as it describes.",
        ),
        "delegation SKILL.md#Repository safety": (
            "For every repository read that a plan review, code review, outcome verification, Adversarial review or "
            "security analysis makes, for main's preparation of each call and its comparison of the workspace after it, "
            "and before main adds, commits, tags or pushes, read and follow [repository "
            "safety](references/repository-safety.md).",
        ),
        "delegation SKILL.md#Code review": (
            "When the installed policy, a session preference that turns automatic review on or an explicit user request "
            "requires code review, read and follow [the code-review procedure](references/code-review.md) after the "
            "primary acceptance passes, or is recorded as not run under [repository "
            "safety](references/repository-safety.md)'s Execution, and before outcome verification.",
        ),
    }

    def test_every_procedure_points_to_the_reference_where_it_dispatches_and_compares(self):
        self.assert_pinned(self.POINTERS)
        self.assertTrue((REFERENCES / "repository-safety.md").is_file())
        # The delegation skill lists the reference beside the procedures, after Adversarial review.
        skill = self.source("delegation SKILL.md")
        self.assertLess(skill.index("\n## Adversarial review\n"), skill.index("\n## Repository safety\n"))

    # Item 5: the primary acceptance under D5, and Adversarial review's dynamic-probing condition replaced.
    EXECUTION_POINTERS = {
        "code-review.md#1": (
            "Run the primary acceptance first.",
            "Main runs it only as [repository safety](repository-safety.md)'s Execution allows; when main may not run it, "
            "main records the acceptance as not run with the reason, and code review proceeds on the code.",
        ),
        "outcome-verification.md#1": (
            "Main runs the primary acceptance only as [repository safety](repository-safety.md)'s Execution allows; when "
            "main may not run it, main records the acceptance as not run with the reason and still dispatches the "
            "verifier, whose brief says the acceptance was not run, so the verifier reports what needs execution "
            "INCONCLUSIVE and the call counts as for any INCONCLUSIVE.",
        ),
        "adversarial-review.md#3": (
            "Dynamic probing follows [repository safety](repository-safety.md)'s Execution: it runs on this machine only "
            "when, in this session, the user has said that the repository is trusted to run on this machine and the "
            "change under attack was written by the user or in this session, and otherwise only in an isolated "
            "environment the user names; without either, the role analyses statically and reports INCONCLUSIVE for what "
            "needs execution.",
            "The brief states the outcome of that determination.",
        ),
        "command#intro": (
            "Targets named in the arguments enter the brief only as step 3 of the procedure describes, including its rule "
            "that dynamic probing follows [repository safety](../delegation/references/repository-safety.md)'s "
            "Execution, so it runs on this machine only for a repository the user has said is trusted and a change "
            "written by the user or in this session, and otherwise only in an isolated environment the user names.",
        ),
    }
    # The replaced condition: code not written by the user or in this session alone decided dynamic probing.
    EXECUTION_REMOVED = {
        "adversarial-review.md#3": ("When the code under attack was not written by the user or in this session, dynamic "
                                    "probing runs only in an isolated environment the user names;",),
        "command#intro": ("code not written by the user or in this session is probed dynamically only in an isolated "
                          "environment the user names.",),
    }

    def test_execution_follows_the_reference_in_steps_1_and_in_adversarial_review(self):
        self.assert_pinned(self.EXECUTION_POINTERS)
        for place, phrases in self.EXECUTION_REMOVED.items():
            for phrase in phrases:
                with self.subTest(place=place, removed=phrase[:50]):
                    self.assertNotIn(phrase, self.source(place))

    # Item 6: review state's repository authority and the automatic-review guidance point to the rule.
    AUTHORITY_POINTERS = {
        "review-state.md#Commits before the passes": (
            "Before each `git add`, commit or push this authority allows, main meets [repository "
            "safety](repository-safety.md)'s Before add, commit, tag or push.",
        ),
        "review-state.md#Repository authority": (
            "Every commit, tag and push, and every `git add` before a commit, also meets [repository "
            "safety](repository-safety.md)'s Before add, commit, tag or push, which adds a condition to this authority "
            "and grants none.",
        ),
        "review-auto.md": (
            "Before any `git add`, commit, tag or push, main lists the hooks, filters, signing and transport settings the "
            "repository's Git configuration would use and asks the user when that list is not empty, as "
            "cc-feather:delegation's repository safety describes.",
        ),
    }

    def test_repository_authority_and_auto_guidance_point_to_the_writing_checks(self):
        self.assert_pinned(self.AUTHORITY_POINTERS)
        for scope in ("user", "project"):
            with self.subTest(scope=scope):
                self.assertIn(self.AUTHORITY_POINTERS["review-auto.md"][0], config._policy("auto", scope=scope))

    # Item 3: the command keeps only its listing, marking and tighter search rule, and the hard-link sentence is gone.
    COMMAND_KEPT = (
        "Main lists untracked paths file by file and never lists a collapsed directory; an untracked directory Git cannot "
        "list file by file, such as a nested repository, is named in the brief and reported INCONCLUSIVE.",
        "Main marks each listed path that is, or lies under, a symbolic link, junction or other reparse point.",
        "The role reads only the listed files themselves and searches or walks no directory under this bullet, a "
        "submodule directory included; what that leaves unexamined it reports as INCONCLUSIVE.",
        "Every other rule for reading these paths, naming them in commands and reading staged and HEAD content is "
        "[repository safety](../delegation/references/repository-safety.md)'s Safe Git invocation and Paths and names.",
    )
    HARD_LINK = "A hard link is project content like any other file."

    def test_the_command_keeps_only_what_is_specific_to_it(self):
        self.assert_pinned({"command#Uncommitted changes": self.COMMAND_KEPT})
        for place in ("command", "reference", "adversarial-review.md", "README.md"):
            with self.subTest(place=place):
                self.assertNotIn(self.HARD_LINK, self.source(place))
        self.assertNotIn("hard link is project content", self.source("command").casefold())

    # Item 5 (B12): ADR 0009's amendment note points to ADR 0011.
    AMENDMENT = (
        "[ADR 0011](0011-reviews-treat-the-repository-as-hostile-by-instruction.md) extends the isolation rule above to "
        "every review: main, reviewer, verifier and adversary execute repository code for a review only when the user "
        "has said in the session that the repository is trusted to run on this machine and the change was written by "
        "the user or in the session, and otherwise only in an isolated environment the user names.",
    )

    def test_adr_0009_gains_an_amendment_note_pointing_to_adr_0011(self):
        text = self.source("ADR 0009")
        note = text.split("\n## Amendment note for 0.21.0\n", 1)[1]
        for sentence in self.AMENDMENT:
            self.assert_whole_sentence(sentence, note)
        self.assertTrue((config.ROOT / "docs" / "adr" / ADR_0011).is_file())
        # ADR 0011 already states D6 as residual risk.
        self.assertIn("are Claude Code's own Git commands at session start and its loading of the project's "
                      "`CLAUDE.md`, imports and `.claude` settings, which happen outside these rules.",
                      self.source("ADR 0011"))

    # Item 7: both READMEs summarise items 1 to 6 and D1 to D6, paired, keeping the "instructions to the model" words.
    README = (
        ("Every review reads your repository under one set of rules, the [repository safety "
         "reference](skills/delegation/references/repository-safety.md): main and every role follow it for every "
         "repository read a plan review, code review, outcome verification, Adversarial review or security analysis "
         "makes, for main's preparation of each call and its comparison of the workspace afterwards, whatever the "
         "claim's classification and including unchanged dependencies.",
         "每次審查都依同一套規則讀取你的儲存庫，也就是[儲存庫安全參考](skills/delegation/references/repository-safety.md)："
         "計畫審查、程式碼審查、結果驗證、對抗式審查或安全分析對儲存庫的每一次讀取、主 Agent 為每次呼叫所做的準備，以及呼叫後"
         "對工作區的比對，主 Agent 與每個角色都遵守它，不論 claim 如何分類，也包括沒有變更的相依項目。"),
        ("The reviewed repository's tracked content and its local Git metadata, such as `.git/config`, its hooks and "
         "`info/attributes`, count as attacker-controlled; your user- and system-level Git configuration and your "
         "environment are trusted.",
         "受審儲存庫追蹤的內容與它本機的 Git 中繼資料（例如 `.git/config`、hooks 與 `info/attributes`）都視為攻擊者可控制；"
         "你的使用者與系統層級 Git 設定以及你自己的環境則視為可信。"),
        ("every Git command a review runs disables fsmonitor, optional locks and the pager, writes nothing, contacts no "
         "remote and runs no program the repository chose, such as an fsmonitor, a textconv or external diff, a filter, "
         "a signing program or a hook.",
         "**Git 指令：**審查執行的每個 Git 指令都會停用 fsmonitor、選用鎖定與分頁程式，不寫入任何東西、不連線遠端，也不執行儲存庫選定的程式，"
         "例如 fsmonitor、textconv 或外部 diff、filter、簽章程式或 hook。"),
        ("It compares commits rather than the working tree, never runs `git status` or a working-tree diff, verifies no "
         "signature, ignores configured mailmap and order files, fetches no missing object and does not recurse into "
         "submodules.",
         "它比對 commit 而不是工作樹，絕不執行 `git status` 或工作樹 diff，不驗證簽章，忽略設定指定的 mailmap 與排序檔，"
         "不抓取缺少的物件，也不遞迴進入 submodule。"),
        ("before a file is read, main or the role checks without following links that no part of its path is a symbolic "
         "link, junction or other reparse point, cloud-file placeholders included, that it lies inside the project, is a "
         "regular file and has a single hard link; a file that fails is reported and not read, and only what needs its "
         "content is INCONCLUSIVE.",
         "**讀取檔案：**讀取檔案前，主 Agent 或角色會在不跟隨連結的情況下檢查：路徑的每一段都不是符號連結、junction 或其他 reparse point"
         "（包括雲端檔案的預留位置），檔案位於專案內、是一般檔案，而且只有一個硬連結；不符合的檔案只回報、不讀取，只有需要它"
         "內容的結論才算 INCONCLUSIVE。"),
        ("A directory is searched only when everything under it passed these checks.",
         "只有底下所有東西都通過檢查的目錄才會被搜尋。"),
        ("A file name from the repository enters a command only when it passes a strict name rule, and then only as a "
         "quoted literal; text from file content, command output or a link target never does.",
         "來自儲存庫的檔名必須通過嚴格的命名規則，才會以加上引號的字面值放進指令；來自檔案內容、指令輸出或連結目標的文字絕不"
         "放進指令。"),
        ("main, reviewer, verifier and adversary run repository code for a review, such as tests, builds, linters, type "
         "checkers and probes, only when you have said in this session that the repository is trusted to run on this "
         "machine and the change was written by you or in this session; otherwise only in an isolated environment you "
         "name, and what needs execution is INCONCLUSIVE.",
         "**執行儲存庫程式碼：**主 Agent、reviewer、verifier 與 adversary 只有在你於這個 session 說過這個儲存庫可以在這台機器上執行，而且變更是"
         "你寫的或在這個 session 寫的時，才會為審查執行儲存庫程式碼，例如測試、建置、linter、型別檢查與探測；否則只在你指定"
         "的隔離環境中執行，需要執行的部分回報 INCONCLUSIVE。"),
        ("Main asks you about trust the first time a session needs it.",
         "session 第一次需要時，主 Agent 會問你是否信任這個儲存庫。"),
        ("When main may not run the primary acceptance itself, it records it as not run, code review proceeds on the code "
         "and verification is still dispatched.",
         "主 Agent 不能自己執行主要驗收時，會記為未執行，程式碼審查仍就程式碼進行，結果驗證也照樣派出。"),
        ("main checks once per session that Git is 2.32 or later, reads the repository's configuration without "
         "following includes and asks you before dispatching when it points outside the project or moves the work tree, "
         "asks you before a call whose comparison would run a filter, and asks again when the repository's Git metadata "
         "changes between dispatches.",
         "**審查之前：**主 Agent 每個 session 檢查一次 Git 是否為 2.32 或更新版本，在不跟隨 include 的情況下讀取儲存庫設定，設定指向專案"
         "外或移動了工作樹時，會在派出前先問你；比對工作區會執行 filter 時，該次呼叫前也會問你；派出之間儲存庫的 Git 中繼資料"
         "有變化時，會再問你。"),
        ("A role without a shell, such as analyst, scout or Explore, reads and searches only the checked files and "
         "directories main lists for it.",
         "沒有 shell 的角色，例如 analyst、scout 與 Explore，只讀取與搜尋主 Agent 為它列出、已檢查過的檔案與目錄。"),
        ("main names the hooks, filters and signing programs the repository's Git configuration would run, each with "
         "the SHA-256 of its content, and for a push the destination and its transport settings, and asks you whether to "
         "run them as configured, skip hooks and signing, or not perform the operation; filters, transport settings and "
         "the destination can only be run or declined.",
         "**add、commit、tag 或 push 之前：**主 Agent 會列出儲存庫的 Git 設定會執行的 hook、filter 與簽章程式，每一個附上內容的 SHA-256，push 時還有目的地與"
         "傳輸設定，並問你要照設定執行、略過 hook 與簽章，還是不執行這個操作；filter、傳輸設定與目的地只能執行或拒絕。"),
        ("Your answer covers exactly what main named, for the rest of the session.",
         "你的回答只涵蓋主 Agent 列出的項目，在這個 session 剩下的時間有效。"),
        ("These rules are instructions to the model, not a sandbox: no permission rule, hook or sandbox enforces them, "
         "and tests only keep the texts consistent.",
         "這些規則是給模型的指示，不是 sandbox：沒有任何權限規則、hook 或 sandbox 強制它們，測試只確保文字前後一致。"),
        ("They cover how main and the roles read reviewed source content, not every file Git itself consults.",
         "它們涵蓋主 Agent 與角色如何讀取受審的原始碼內容，而不是 Git 本身讀取的每個檔案。"),
        ("Concurrent modification of files during a review is not defended against, and Claude Code itself runs Git in "
         "the project when a session starts and loads the project's `CLAUDE.md`, its imports and its `.claude` settings "
         "before and outside these rules; both are residual risk.",
         "審查期間檔案被同時修改的情況不在防護範圍內，而 Claude Code 本身在 session 開始時會在專案中執行 Git，並載入專案的 "
         "`CLAUDE.md`、它匯入的檔案與 `.claude` 設定，這些都發生在這些規則之前、之外；兩者都是剩餘風險。"),
    )
    # The bullets of the README section, by label, each pinned in both languages.
    README_LABELS = (("Git commands", "Git 指令"), ("File reads", "讀取檔案"),
                     ("Running repository code", "執行儲存庫程式碼"), ("Before a review", "審查之前"),
                     ("Before add, commit, tag or push", "add、commit、tag 或 push 之前"))
    # The Commit rule, the code-review row and the dynamic-probing sentence point to the section.
    README_POINTERS = (
        ("Before each `git add`, commit or push of these claims, main also checks what the repository's Git "
         "configuration would run, as under [Repository safety](#repository-safety).",
         "對這些 claim 做 `git add`、commit 或 push 之前，主 Agent 也會檢查儲存庫的 Git 設定會執行什麼，見[儲存庫安全](#儲存庫安全)。"),
        ("| Code review | After main's primary acceptance passes, or is recorded as not run under [Repository "
         "safety](#repository-safety) | reviewer, reading the diff itself | APPROVED |",
         "| 程式碼審查 | 主 Agent 的主要驗收通過後，或依[儲存庫安全](#儲存庫安全)記為未執行時 | reviewer，自行取得 diff | APPROVED |"),
        ("Dynamic probing follows the rule for running repository code under [Repository safety](#repository-safety): it "
         "runs on your machine only when you have said in this session that the repository is trusted there and the "
         "change was written by you or in this session, and otherwise only in an isolated environment you name; without "
         "one the attack stays static.",
         "動態探測依[儲存庫安全](#儲存庫安全)中執行儲存庫程式碼的規則：只有你在這個 session 說過這個儲存庫可以在你的機器上執"
         "行，而且變更是你寫的或在這個 session 寫的，才會在你的機器上進行，否則只在你指定的隔離環境中進行；沒有的話只做靜態攻擊。"),
    )

    def test_readmes_summarise_the_rules_in_both_languages(self):
        for english, chinese in self.README:
            with self.subTest(sentence=english[:60]):
                self.assert_pinned({"README.md#section": (english,), "README.zh-TW.md#section": (chinese,)})
        for english, chinese in self.README_LABELS:
            with self.subTest(label=english):
                self.assertIn(f"\n- **{english}:** ", self.source("README.md#section"))
                self.assertIn(f"\n- **{chinese}：**", self.source("README.zh-TW.md#section"))
        # The section sits after Security-critical work and before the automatic review switch in each README.
        for name, (before, section, after) in {
                "README.md": ("### Security-critical work", "### Repository safety", "### Automatic review switch"),
                "README.zh-TW.md": ("### 安全關鍵工作", "### 儲存庫安全", "### 自動審查開關")}.items():
            text = self.source(name)
            with self.subTest(readme=name):
                self.assertLess(text.index(f"\n{before}\n"), text.index(f"\n{section}\n"))
                self.assertLess(text.index(f"\n{section}\n"), text.index(f"\n{after}\n"))

    def test_readmes_point_to_the_section_from_the_commit_rule_table_and_probing(self):
        for english, chinese in self.README_POINTERS:
            with self.subTest(sentence=english[:60]):
                self.assertIn(english, self.source("README.md"))
                self.assertIn(chinese, self.source("README.zh-TW.md"))
        self.assertIn(self.README_POINTERS[0][0], self.source("README.md#Commit"))
        self.assertIn(self.README_POINTERS[0][1], self.source("README.zh-TW.md#Commit 條件"))

    def test_no_sentence_lets_a_role_read_through_a_link_or_an_unchecked_directory(self):
        # Item 8, abuse check: every sentence of the reference's Paths and names that mentions following links,
        # searching a directory or placing a name in a command is one of the pinned rules.
        risky = re.compile(r"\bfollow|search|walk|enters a command|in a command|placed in a command", re.I)
        pinned = {" ".join(sentence.split()) for sentence in self.PATHS}
        for sentence in self.sentences(self.source("reference#Paths and names")):
            if risky.search(sentence):
                with self.subTest(sentence=sentence[:60]):
                    self.assertTrue(any(sentence in rule or rule in sentence for rule in pinned), sentence)


class RepositorySafetyGitFormsTests(unittest.TestCase):
    """C1 item 2, regression and abuse check: in a throwaway repository whose local configuration and attributes name an
    fsmonitor, a textconv driver and an external diff that each leave a marker, every Git form the reference gives runs
    none of them, while the same reads without the reference's options run them (positive controls)."""

    def test_the_reference_forms_run_no_repository_chosen_program(self):
        reference = read(REFERENCE)
        prefix = reference.split("```text\n", 1)[1].split("\n```", 1)[0]
        self.assertEqual(prefix, RepositorySafetyTests.PREFIX)
        for form in RepositorySafetyTests.FORMS:
            self.assertIn(f"`{form}`", reference)
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp:
            root = Path(os.path.realpath(temp))
            repo, marker, empty = root / "repo", root / "marker", root / "gitconfig"
            repo.mkdir()
            empty.write_bytes(b"")
            scripts = {}
            for name, body in (("monitor", "exit 1"), ("textconv", 'cat "$1"'), ("extdiff", "exit 0")):
                script = root / f"{name}.sh"
                script.write_text(f'#!/bin/sh\necho {name} >> "{marker.as_posix()}"\n{body}\n', encoding="utf-8",
                                  newline="\n")
                script.chmod(0o755)
                scripts[name] = script.as_posix()
            # No inherited GIT_* variable reaches the throwaway repository, and the user's configuration is not read.
            env = {key: value for key, value in os.environ.items() if not key.upper().startswith("GIT_")}
            env.update({"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": str(empty)})

            def git(*args):
                try:
                    return subprocess.run(["git", *args], cwd=repo, env=env, stdin=subprocess.DEVNULL,
                                          capture_output=True, timeout=60)
                except (OSError, subprocess.TimeoutExpired) as error:
                    self.skipTest(f"Git cannot be run: {error}")

            def ran():
                found = marker.read_text(encoding="utf-8").split() if marker.exists() else []
                if marker.exists():
                    marker.unlink()
                return set(found)

            identity = ("-c", "user.name=t", "-c", "user.email=t@example.invalid", "-c", "core.fsmonitor=",
                        "-c", "commit.gpgSign=false")
            self.assertEqual(git("init", "-q", ".").returncode, 0)
            self.assertEqual(git("config", "core.autocrlf", "false").returncode, 0)
            (repo / ".gitattributes").write_bytes(b"*.txt diff=marker\n")
            (repo / "a.txt").write_bytes(b"one\n")
            self.assertEqual(git(*identity, "add", "--", ".gitattributes", "a.txt").returncode, 0)
            self.assertEqual(git(*identity, "commit", "-q", "--no-verify", "-m", "one").returncode, 0)
            (repo / "a.txt").write_bytes(b"one\ntwo\n")
            self.assertEqual(git(*identity, "commit", "-q", "--no-verify", "-am", "two").returncode, 0)
            for key, value in (("core.fsmonitor", scripts["monitor"]), ("diff.marker.textconv", scripts["textconv"]),
                               ("diff.external", scripts["extdiff"])):
                self.assertEqual(git("config", key, value).returncode, 0)
            ran()

            # Positive controls: the same reads without the reference's options run each configured program.
            git("cat-file", "blob", ":0:a.txt")
            git("diff", "HEAD~1", "HEAD")
            git("diff", "--no-ext-diff", "HEAD~1", "HEAD")
            controls = ran()
            if not controls:
                self.skipTest("this Git ran no configured program in the control reads")

            substitutions = {"<prefix>": " ".join(shlex.split(prefix)[1:]), "<commit> <commit>": "HEAD~1 HEAD",
                             "<commit>": "HEAD", "<path>": "a.txt", "<attribute>": "diff"}
            for form in RepositorySafetyTests.FORMS:
                command = form
                for placeholder, value in substitutions.items():
                    command = command.replace(placeholder, value)
                with self.subTest(form=form):
                    result = git(*shlex.split(command)[1:])
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(ran(), set(), f"{command} ran a configured program")
            # Each control that ran is one this check covered, so a form that dropped its option would be caught.
            self.assertTrue(controls <= {"monitor", "textconv", "extdiff"}, controls)


if __name__ == "__main__":
    unittest.main()
