"""Checkout lease rule text (checkout-leases ticket 06): the main Agent's rules in the leases skill, the
`/cc-feather:worktrees` command, the setup component's rule block and the delegation skill's pointer."""

from __future__ import annotations

import json
import re
import unittest

from tests.feather_support import config


def read(*parts: str) -> str:
    return config.ROOT.joinpath(*parts).read_text(encoding="utf-8")


def section(text: str, heading: str) -> str:
    """The text under a Markdown heading, up to the next heading of the same or a higher level."""
    level = heading.split(" ", 1)[0]
    start = text.index("\n" + heading + "\n") + len(heading) + 2
    following = re.search(rf"\n#{{1,{len(level)}}} ", text[start:])
    return text[start:start + following.start()] if following else text[start:]


class LeaseRulesTextTests(unittest.TestCase):
    SKILL = ("skills", "leases", "SKILL.md")
    RULES = "## Main Agent rules"

    # Each heading of the rules section with the whole sentences it must carry.
    PINNED = {
        "## Main Agent rules": (
            "These rules apply while the installed guidance or the user asks the main Agent to keep Checkout leases.",
            "Only the main Agent takes, renews, takes over and returns leases.",
        ),
        "### Taking a lease": (
            "The main Agent takes a lease on a checkout when it starts implementing the first Claim of a Plan there, at the first change of Unplanned work there, and before it runs a writing test or a review that needs a stable checkout there.",
            "Reading a checkout takes no lease.",
            "Opening or entering a worktree (`EnterWorktree` by name or path, `claude --worktree`) is not taking its lease, and neither is starting a session in the main worktree's directory.",
            "Writing cc-feather's own records under the main worktree's `.feather/` (leases, handoff records, Dispatch records) is not changing a checkout and needs no lease.",
            "Merging into a branch inside the main worktree changes it, so the main Agent takes the main worktree's lease for the merge and returns it afterwards; landing by a push or a pull request does not touch the main worktree and needs none.",
            "Taking a lease never authorises changing, resetting or removing what the checkout already holds.",
        ),
        "### Locks": (
            "A held lease on a linked worktree is protected by its own lock or by the session lock of a worktree the session itself created.",
            "Right after creating a worktree itself (`EnterWorktree` by name, or `claude --worktree` with a new name), the main Agent reads that worktree's lock reason from `git worktree list --porcelain -z` and passes exactly that reason with `--accept-session-lock`; without `-z` Git quotes a reason with special characters and the reason no longer matches.",
            "A lock found on a worktree the session only entered or reused (`EnterWorktree` by path, `claude --worktree` with an existing name) counts as another holder's: the main Agent never attests it, and acquire returns `locked`.",
            "A lockless held lease is locked again with its own lock by `list` and `acquire`.",
            "Only the lease's own lock is ever removed: an accepted session lock and every other lock stay.",
            "After a takeover, a Claude Code session lock the old lease had accepted stays and counts as another holder's lock.",
        ),
        "### Serial and parallel work": (
            "A serial Plan holds one lease in its checkout, and its purpose follows the ticket being worked on: the main Agent renews it with `--purpose` when the ticket changes.",
            "Parallel Claims hold one lease per worktree.",
            "Once a parallel worktree's work is merged back and the worktree is no longer used, the main Agent returns its lease after parking: `release --park`, with `--continue-in` naming the checkout the work continues in when the branch was merged there rather than into the default branch.",
            "Subagents never take, renew or return leases.",
            "Delegated work runs under the main Agent's lease, and the main Agent decides which checkout each Assignment uses.",
            "A subagent's isolated worktree needs no lease while the subagent runs under Claude Code's agent lock; when it is kept with changes, the main Agent takes a lease on it, with the lease's own lock, until the changes are integrated.",
        ),
        "### Renewing and returning": (
            "The main Agent renews its lease at milestones, at blockers, before stopping to wait for the user and at completion, whether or not a handoff is active.",
            "It returns a lease when it stops using the checkout; completing a handoff record does not return it.",
            "Returning a lease never resets, cleans or switches the checkout.",
            "Parking detaches a linked worktree's HEAD only when the worktree is clean (no uncommitted or untracked changes) and its branch is contained in the local default branch, or in the branch of the checkout `--continue-in` names; otherwise the worktree stays as it is, the reason is reported and the lease is still returned.",
            "Parking never applies to the main worktree and never deletes a branch or a worktree.",
        ),
        "### When a lease cannot be taken": (
            "When acquire returns `held` or `locked`, the main Agent stops and shows the holder, purpose, start time, last reported activity and age, or the lock and its reason, and the user chooses: work in the main worktree, use an idle worktree, open a new worktree, or take over a lease the user judges left behind.",
            "No lease is taken over automatically: the main Agent runs `take-over` only on the user's choice, with the `version` the user was shown.",
            "Last reported activity is the activity the holder reported, not proof that the holder is still running, and no age makes a lease left behind.",
            "On `refused`, `busy` or `unknown` the main Agent acquires nothing, reports the result and does not change that checkout until it holds the lease or the user decides otherwise.",
            "A session that finds on renew or release that its lease changed hands (`changed-hands`) stops using that checkout and reports.",
        ),
        "### Reusing a parked worktree": (
            "A parked commit can be far behind, so the main Agent starts new work in a reused parked worktree on a new branch from the latest default branch (the remote's default branch when one exists), never from the parked commit itself, unless the user names another base.",
            "The listing (`/cc-feather:worktrees`) reports facts and never calls a checkout usable; which idle worktree to use is the user's choice.",
        ),
        "### Cooperative limits": (
            "A lease is cooperative: it binds only sessions that follow these rules.",
            "It does not stop, detect or manage another session's processes, and it does not keep a person or a tool that ignores leases out of a checkout.",
            "A Git worktree lock only keeps `git worktree prune`, a plain `git worktree remove` and Claude Code's cleanup away from a leased worktree.",
            "One checkout shared between Windows and WSL, or between machines, is not covered.",
        ),
    }

    def test_rules_carry_each_decision_under_its_heading(self):
        text = read(*self.SKILL)
        rules = section(text, self.RULES)
        for heading, sentences in self.PINNED.items():
            body = rules if heading == self.RULES else section(rules, heading)
            for sentence in sentences:
                with self.subTest(heading=heading, sentence=sentence[:60]):
                    self.assertIn(sentence, body)

    def test_rules_name_only_real_tool_commands_and_statuses(self):
        rules = section(read(*self.SKILL), self.RULES)
        cli = read("skills", "leases", "scripts", "feather_leases", "cli.py")
        for option in re.findall(r"`(--[a-z-]+)", rules):
            with self.subTest(option=option):
                self.assertIn(f'"{option}"', cli)
        for command in ("acquire", "renew", "release", "take-over", "list"):
            with self.subTest(command=command):
                self.assertIn(f'"{command}"', cli)


class WorktreesCommandTests(unittest.TestCase):
    COMMAND = ("skills", "worktrees", "SKILL.md")

    PINNED = (
        "List the checkouts of the current repository with [the lease tool](../leases/SKILL.md#tool)'s `list` command; this command adds no rules of its own.",
        "The listing is not read-only: it locks a held lease's linked worktree again when that worktree has no lock, and it removes orphan leases, whose checkout Git no longer registers.",
        "Report each worktree it locked again (`relocked`) and each orphan lease it removed or kept.",
        "It takes, renews, returns and takes over no lease, and it never parks, resets, cleans, switches or removes a checkout.",
        "The listing reports facts and never calls a checkout usable, free or reusable; a checkout without a lease has no registered use.",
        "Last reported activity is reported activity, not liveness.",
    )

    def test_command_is_user_invoked_and_states_what_the_listing_changes(self):
        text = read(*self.COMMAND)
        self.assertTrue(text.startswith("---\n"))
        frontmatter = text.split("---")[1]
        self.assertIn("name: worktrees\n", frontmatter)
        self.assertIn("disable-model-invocation: true\n", frontmatter)
        self.assertRegex(frontmatter, r'\ndescription: "[^"\n]*locks a lockless held lease again[^"\n]*'
                                      r'removes orphan leases[^"\n]*"\n')
        for sentence in self.PINNED:
            with self.subTest(sentence=sentence[:60]):
                self.assertIn(sentence, text)

    def test_command_is_packaged_after_the_leases_skill(self):
        skills = json.loads(read(".claude-plugin", "plugin.json"))["skills"]
        self.assertIn("./skills/worktrees", skills)
        self.assertEqual(skills.index("./skills/worktrees"), skills.index("./skills/leases") + 1)
        self.assertIn("The plugin packages fifteen skills.", read("docs", "setup.md"))


class LeasesSetupBlockTests(unittest.TestCase):
    BLOCK = """<!-- cc-feather:leases:begin -->
# Feather checkout leases

Before changing a checkout of a Git repository, take a Checkout lease on it, then renew and return it, following cc-feather:leases. If unavailable, report the limitation.

Take the lease when starting to implement the first Claim of a Plan in a checkout, at the first change of Unplanned work, and before a writing test or a review that needs a stable checkout. Reading a checkout, opening or entering a worktree, and writing cc-feather's own records under `.feather/` take none. Renew it at milestones, blockers, before stopping to wait for the user and at completion, whether or not a handoff is active, and return it when the session stops using the checkout. When a lease cannot be taken, stop and let the user choose; never take a lease over automatically.

Only the main Agent takes, renews and returns leases. Subagents never do; delegated work runs under the main Agent's lease.
<!-- cc-feather:leases:end -->
"""

    def test_template_is_the_pinned_rule_block(self):
        self.assertEqual(read("templates", "leases.md").replace("\r\n", "\n"), self.BLOCK)
        self.assertEqual(config._leases_policy(), self.BLOCK.rstrip("\n"))

    def test_setup_skill_and_document_describe_the_component(self):
        setup = read("skills", "setup", "SKILL.md")
        for sentence in (
                "- `leases`: the persistent Checkout lease rules in a marked block of the scope's instruction file, telling the main Agent to take, renew and return leases as cc-feather:leases describes. It is not installed by default and is installed only when selected by name.",
                "- `both`: operate on handoff and delegation in one preview/apply transaction; it never includes `leases`.",
        ):
            with self.subTest(sentence=sentence[:60]):
                self.assertIn(sentence, setup)
        document = read("docs", "setup.md")
        for sentence in (
                "Leases installs templates/leases.md under `cc-feather:leases` markers; it is off by default, `both` never includes it, and installing, updating or removing it leaves the handoff and delegation components untouched.",
                "Check/show report all three components by default, so a scope without it shows `leases` as not installed; the top-level `installed` flag is true while any component, `leases` included, is installed, and `update` or `remove` with `both` in a scope that holds only `leases` refuses and changes nothing.",
        ):
            with self.subTest(sentence=sentence[:60]):
                self.assertIn(sentence, document)


class DelegationPointerTests(unittest.TestCase):
    POINTER = ("When main keeps Checkout leases, it decides which checkout each Assignment uses and holds that "
               "checkout's lease itself, as [the lease rules](../leases/SKILL.md#main-agent-rules) describe; "
               "children never take, renew or return leases.")

    def test_dispatch_section_points_at_the_lease_rules_where_it_assigns_checkouts(self):
        dispatch = section(read("skills", "delegation", "SKILL.md"), "## Dispatch")
        self.assertIn(self.POINTER, dispatch)
        paragraph = next(part for part in dispatch.split("\n\n") if self.POINTER in part)
        self.assertIn("Isolate overlapping checkout risks in separate worktrees or serialize writers.", paragraph)


if __name__ == "__main__":
    unittest.main()
