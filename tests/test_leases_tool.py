"""Acquire, release and list a Checkout lease (checkout leases ticket 01).

The lease tool runs as a subprocess against temporary real Git repositories with real linked worktrees, and only its
JSON result and exit status are asserted. The fixture and its isolated Git environment are those of
tests/test_handoff_shared_store.py: a base made with mkdtemp under FEATHER_LINK_TEST_DIR when set, holding main/ with
one commit and linked worktrees wt1 and wt2 beside it (outside .claude/worktrees/), synthetic data only, removed on
cleanup. Pre-created leases and critical-section locks are synthetic files written by the tests. The concurrency case
starts two tool processes a fixed number of times, each with its own timeout."""
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess
import sys

from tests.test_handoff_shared_store import FIELDS, MARKER, ROOT, SharedBase

TOOL = ROOT / "skills/leases/scripts/leases.py"
HANDOFF_TOOL = ROOT / "skills/handoff/scripts/handoff.py"
SKILL = ROOT / "skills/leases/SKILL.md"
MAIN_KEY = ".main"
RACE_ROUNDS = 5
TIMEOUT = 60


class LeaseBase(SharedBase):
    def setUp(self):
        super().setUp()
        self.leases = self.main / ".feather" / "leases"

    def command(self, project: Path, *args, exact=False) -> list[str]:
        return [sys.executable, "-B", str(TOOL), "--project", str(project), *(["--exact-root"] if exact else []),
                *args]

    def lease(self, project: Path, *args, expected=0, exact=False, env=None) -> dict:
        result = subprocess.run(self.command(project, *args, exact=exact), capture_output=True, text=True,
                                encoding="utf-8", timeout=TIMEOUT, env=env)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def acquire(self, project: Path, checkout: Path, *, session="session-a", purpose="ticket 01", expected=0,
                exact=False) -> dict:
        return self.lease(project, "acquire", "--checkout", str(checkout), "--session", session,
                          "--purpose", purpose, expected=expected, exact=exact)

    def release(self, project: Path, checkout: Path, lease_id: str, *, expected=0) -> dict:
        return self.lease(project, "release", "--checkout", str(checkout), "--lease-id", lease_id, expected=expected)

    def listing(self, project: Path, *, exact=False) -> dict:
        return self.lease(project, "list", exact=exact)

    def entry(self, listed: dict, checkout: Path) -> dict:
        matches = [item for item in listed["checkouts"]
                   if os.path.normcase(os.path.normpath(item["path"])) == os.path.normcase(str(checkout))]
        self.assertEqual(len(matches), 1, listed)
        return matches[0]

    def status(self, checkout: Path) -> str:
        return self.git(checkout, "status", "--porcelain", "--untracked-files=all")


class AcquireTest(LeaseBase):
    def test_acquire_on_a_free_checkout_records_the_lease(self):
        before = datetime.now().astimezone()
        acquired = self.acquire(self.wt1, self.wt1, session="alpha", purpose="implement ticket 01")
        self.assertEqual((acquired["status"], acquired["acquired"]), ("ok", True), acquired)
        lease = acquired["lease"]
        self.assertEqual(lease["schema_version"], 1)
        self.assertEqual(lease["checkout"]["key"], "wt1")
        self.assertEqual(os.path.normcase(os.path.normpath(lease["checkout"]["path"])), os.path.normcase(str(self.wt1)))
        self.assertRegex(lease["lease_id"], r"^[0-9a-f]{32}$")
        self.assertEqual((lease["session"], lease["purpose"]), ("alpha", "implement ticket 01"))
        self.assertTrue(lease["host"] and lease["runtime"], lease)
        for field in ("started", "last_activity"):
            moment = datetime.fromisoformat(lease[field])
            self.assertIsNotNone(moment.utcoffset(), lease)
            self.assertGreaterEqual(moment, before - timedelta(seconds=5))
        self.assertIsInstance(lease["diagnostic_pid"], int)
        self.assertNotIn("pid", lease)
        self.assertEqual(os.path.normcase(acquired["location"]), os.path.normcase(str(self.leases)))

    def test_the_main_worktree_has_the_reserved_key(self):
        acquired = self.acquire(self.wt2, self.main)
        self.assertEqual((acquired["status"], acquired["lease"]["checkout"]["key"]), ("ok", MAIN_KEY), acquired)

    def test_the_checkout_defaults_to_the_project(self):
        acquired = self.lease(self.wt2, "acquire", "--session", "s", "--purpose", "p")
        self.assertEqual((acquired["status"], acquired["lease"]["checkout"]["key"]), ("ok", "wt2"), acquired)

    def test_a_second_acquire_returns_the_holder_and_acquires_nothing(self):
        first = self.acquire(self.wt1, self.wt1, session="alpha", purpose="first purpose")
        second = self.acquire(self.main, self.wt1, session="beta", purpose="second purpose")
        self.assertEqual((second["status"], second["acquired"]), ("held", False), second)
        self.assertEqual(second["lease"], first["lease"])
        self.assertEqual(second["lease"]["purpose"], "first purpose")
        self.assertGreaterEqual(second["age_seconds"], 0)
        self.assertIn("started", second["lease"])
        self.assertIn("last_activity", second["lease"])
        listed = self.entry(self.listing(self.wt2), self.wt1)
        self.assertEqual(listed["lease"]["lease"]["lease_id"], first["lease"]["lease_id"])

    def test_every_acquisition_has_a_new_lease_id(self):
        first = self.acquire(self.wt1, self.wt1)["lease"]["lease_id"]
        self.assertEqual(self.release(self.wt1, self.wt1, first)["status"], "ok")
        second = self.acquire(self.wt1, self.wt1)["lease"]["lease_id"]
        self.assertNotEqual(first, second)

    def test_different_checkouts_are_acquired_independently(self):
        results = [self.acquire(self.main, checkout) for checkout in (self.main, self.wt1, self.wt2)]
        self.assertEqual([item["status"] for item in results], ["ok"] * 3, results)
        self.assertEqual(len({item["lease"]["lease_id"] for item in results}), 3)
        self.assertEqual([item["lease"]["checkout"]["key"] for item in results], [MAIN_KEY, "wt1", "wt2"])

    def test_a_path_that_is_not_a_checkout_is_refused(self):
        inner = self.wt1 / "inner"
        inner.mkdir()
        refused = self.acquire(self.wt1, inner, expected=2)
        self.assertEqual((refused["status"], refused["code"]), ("error", "not-a-checkout"), refused)
        refused = self.acquire(self.wt1, self.outside, expected=2)
        self.assertEqual(refused["code"], "not-a-checkout", refused)

    def test_two_concurrent_acquires_of_one_checkout_produce_exactly_one_success(self):
        for round_number in range(RACE_ROUNDS):
            with self.subTest(round=round_number):
                command = self.command(self.main, "acquire", "--checkout", str(self.wt1), "--session",
                                       "racer", "--purpose", f"round {round_number}")
                processes = [subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                              encoding="utf-8") for _ in range(2)]
                results = []
                for process in processes:
                    try:
                        out, err = process.communicate(timeout=TIMEOUT)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.communicate()
                        self.fail("a racing acquire did not finish in time")
                    self.assertEqual(process.returncode, 0, out + err)
                    results.append(json.loads(out))
                statuses = [item["status"] for item in results]
                self.assertEqual(statuses.count("ok"), 1, results)
                self.assertIn(next(status for status in statuses if status != "ok"), {"busy", "held"}, results)
                self.assertEqual([item["acquired"] for item in results].count(True), 1, results)
                winner = next(item for item in results if item["status"] == "ok")
                listed = self.entry(self.listing(self.main), self.wt1)
                self.assertEqual(listed["lease"]["lease"]["lease_id"], winner["lease"]["lease_id"])
                self.assertEqual(self.release(self.main, self.wt1, winner["lease"]["lease_id"])["status"], "ok")


class ReleaseTest(LeaseBase):
    def test_release_with_the_holders_lease_id_returns_the_lease(self):
        acquired = self.acquire(self.wt1, self.wt1)
        released = self.release(self.wt2, self.wt1, acquired["lease"]["lease_id"])
        self.assertEqual((released["status"], released["released"]), ("ok", True), released)
        self.assertEqual(released["lease"], acquired["lease"])
        self.assertEqual(self.entry(self.listing(self.main), self.wt1)["lease"]["state"], "absent")

    def test_release_with_another_lease_id_reports_changed_hands_and_changes_nothing(self):
        acquired = self.acquire(self.wt1, self.wt1)
        refused = self.release(self.wt1, self.wt1, "0" * 32)
        self.assertEqual((refused["status"], refused["released"]), ("changed-hands", False), refused)
        self.assertEqual(refused["lease"], acquired["lease"])
        listed = self.entry(self.listing(self.main), self.wt1)["lease"]
        self.assertEqual((listed["state"], listed["lease"]), ("held", acquired["lease"]))

    def test_release_of_an_absent_lease_reports_changed_hands(self):
        old = self.acquire(self.wt1, self.wt1)["lease"]["lease_id"]
        self.release(self.wt1, self.wt1, old)
        again = self.release(self.wt1, self.wt1, old)
        self.assertEqual((again["status"], again["released"], again["lease"]), ("changed-hands", False, None), again)


class CriticalSectionTest(LeaseBase):
    def write_lock(self, key: str, age: timedelta) -> bytes:
        self.leases.mkdir(parents=True, exist_ok=True)
        (self.leases / ".gitignore").write_text("*\n", encoding="utf-8")
        created = (datetime.now(timezone.utc) - age).astimezone().isoformat(timespec="microseconds")
        data = (json.dumps({"created": created, "host": "fixture-host", "pid": 4242, "operation": "acquire",
                            "checkout": key}) + "\n").encode("utf-8")
        (self.leases / f"{key}.lock").write_bytes(data)
        return data

    def assert_busy(self, result: dict, minimum_age: int):
        self.assertEqual(result["status"], "busy", result)
        section = result["critical_section"]
        self.assertTrue(section["readable"], section)
        self.assertEqual(section["holder"], {"host": "fixture-host", "pid": 4242, "operation": "acquire"})
        self.assertGreaterEqual(section["age_seconds"], minimum_age)
        self.assertIsNotNone(datetime.fromisoformat(section["created"]).utcoffset())

    def test_a_held_critical_section_is_reported_at_once_and_never_broken(self):
        data = self.write_lock("wt1", timedelta(hours=3))
        started = datetime.now()
        busy = self.acquire(self.main, self.wt1)
        self.assertLess((datetime.now() - started).total_seconds(), TIMEOUT / 2)
        self.assert_busy(busy, 3 * 3600 - 5)
        self.assertFalse(busy["acquired"])
        self.assertEqual(self.entry(self.listing(self.main), self.wt1)["lease"]["state"], "absent")
        self.assertEqual((self.leases / "wt1.lock").read_bytes(), data)
        self.assertEqual(self.acquire(self.main, self.wt2)["status"], "ok")

    def test_release_meets_a_held_critical_section_and_changes_nothing(self):
        acquired = self.acquire(self.main, self.wt1)
        self.write_lock("wt1", timedelta(seconds=30))
        busy = self.release(self.main, self.wt1, acquired["lease"]["lease_id"])
        self.assert_busy(busy, 25)
        self.assertFalse(busy["released"])
        self.assertEqual(self.entry(self.listing(self.main), self.wt1)["lease"]["lease"], acquired["lease"])


class ListingTest(LeaseBase):
    def test_the_listing_covers_every_registered_worktree_with_its_lease_state(self):
        detached = self.base / "elsewhere" / "wt3"
        self.git(self.main, "worktree", "add", "--quiet", "--detach", str(detached))
        claude = self.main / ".claude" / "worktrees" / "agent"
        self.git(self.main, "worktree", "add", "--quiet", "-b", "agent-branch", str(claude))
        held = self.acquire(self.wt1, self.wt1, purpose="held purpose")
        (self.leases / "wt2.json").write_text("{not json", encoding="utf-8")
        head = self.git(self.main, "rev-parse", "HEAD")

        listed = self.listing(self.wt2)
        self.assertEqual(listed["status"], "ok", listed)
        self.assertEqual(len(listed["checkouts"]), 5, listed)
        main = self.entry(listed, self.main)
        self.assertEqual((main["main"], main["key"], main["branch"], main["detached"]), (True, MAIN_KEY, "main", False))
        self.assertEqual(main["lease"], {"state": "absent", "description": "no registered use"})
        first = self.entry(listed, self.wt1)
        self.assertEqual((first["main"], first["key"], first["branch"]), (False, "wt1", "wt1"))
        self.assertEqual(first["lease"]["state"], "held")
        self.assertEqual(first["lease"]["lease"], held["lease"])
        self.assertGreaterEqual(first["lease"]["age_seconds"], 0)
        second = self.entry(listed, self.wt2)
        self.assertEqual(second["lease"]["state"], "unknown", second)
        self.assertTrue(second["lease"]["reason"])
        outside = self.entry(listed, detached)
        self.assertEqual((outside["detached"], outside["branch"], outside["head"]), (True, None, head))
        self.assertEqual(outside["lease"]["state"], "absent")
        agent = self.entry(listed, claude)
        self.assertEqual((agent["branch"], agent["lease"]["state"]), ("agent-branch", "absent"))
        self.assertEqual(listed["checkouts"][0]["key"], MAIN_KEY)

    def test_an_unreadable_lease_is_unknown_and_blocks_acquire(self):
        self.leases.mkdir(parents=True)
        (self.leases / ".gitignore").write_text("*\n", encoding="utf-8")
        (self.leases / "wt1.json").write_text(json.dumps({"schema_version": 99}), encoding="utf-8")
        self.assertEqual(self.entry(self.listing(self.main), self.wt1)["lease"]["state"], "unknown")
        blocked = self.acquire(self.main, self.wt1)
        self.assertEqual((blocked["status"], blocked["acquired"]), ("unknown", False), blocked)
        self.assertEqual((self.leases / "wt1.json").read_text(encoding="utf-8"), json.dumps({"schema_version": 99}))

    def test_a_failed_worktree_query_is_unknown(self):
        environment = {**os.environ, "PATH": str(self.outside)}
        listed = self.lease(self.wt1, "list", env=environment)
        self.assertEqual((listed["status"], listed["checkouts"]), ("unknown", []), listed)
        self.assertTrue(listed["reason"])
        acquired = self.lease(self.wt1, "acquire", "--session", "s", "--purpose", "p", env=environment)
        self.assertEqual((acquired["status"], acquired["acquired"]), ("unknown", False), acquired)
        self.assertFalse((self.wt1 / ".feather").exists())
        self.assertFalse(self.leases.exists())


class LocationTest(LeaseBase):
    def test_a_tracked_checkout_and_an_explicit_root_use_the_same_leases(self):
        (self.wt1 / ".gitignore").write_text(MARKER + "\n", encoding="utf-8")
        tracked = subprocess.run([sys.executable, "-B", str(HANDOFF_TOOL), "--project", str(self.wt1), "list"],
                                 capture_output=True, text=True, encoding="utf-8", timeout=TIMEOUT)
        self.assertEqual(json.loads(tracked.stdout)["root"]["tracking"], "tracked", tracked.stdout)
        acquired = self.acquire(self.wt1, self.wt2)
        self.assertEqual(acquired["status"], "ok", acquired)
        explicit = self.acquire(self.wt2, self.wt1, exact=True)
        self.assertEqual(explicit["status"], "ok", explicit)
        views = [self.listing(self.main), self.listing(self.wt1), self.listing(self.wt2),
                 self.listing(self.wt1, exact=True), self.listing(self.wt2, exact=True)]
        for view in views:
            with self.subTest(view=view.get("project")):
                self.assertEqual(os.path.normcase(view["location"]), os.path.normcase(str(self.leases)))
                self.assertEqual(self.entry(view, self.wt2)["lease"]["lease"], acquired["lease"])
                self.assertEqual(self.entry(view, self.wt1)["lease"]["lease"], explicit["lease"])
        self.assertFalse((self.wt1 / ".feather" / "leases").exists())
        self.assertFalse((self.wt2 / ".feather").exists())

    def test_an_unestablished_location_fails_without_writing_elsewhere(self):
        (self.main / ".feather").mkdir()
        (self.main / ".feather" / "leases").write_text("not a directory", encoding="utf-8")
        failed = self.acquire(self.wt1, self.wt1, expected=2)
        self.assertEqual(failed["status"], "error", failed)
        self.assertFalse((self.wt1 / ".feather").exists())
        listed = self.listing(self.wt1)
        self.assertEqual(self.entry(listed, self.wt1)["lease"]["state"], "unknown", listed)
        self.assertEqual((self.main / ".feather" / "leases").read_text(encoding="utf-8"), "not a directory")

    def test_the_directory_ignores_itself(self):
        self.acquire(self.wt1, self.wt1)
        self.assertEqual((self.leases / ".gitignore").read_text(encoding="utf-8"), "*\n")

    def assert_status_unchanged(self):
        before = (self.status(self.main), self.status(self.wt1))
        acquired = self.acquire(self.wt1, self.wt1)
        self.assertEqual(acquired["status"], "ok", acquired)
        main = self.acquire(self.wt1, self.main)
        self.assertEqual(main["status"], "ok", main)
        self.assertEqual((self.status(self.main), self.status(self.wt1)), before)
        self.release(self.wt1, self.wt1, acquired["lease"]["lease_id"])
        self.release(self.wt1, self.main, main["lease"]["lease_id"])
        self.assertEqual((self.status(self.main), self.status(self.wt1)), before)

    def test_leases_change_no_status_with_untracked_handoff_records(self):
        created = subprocess.run([sys.executable, "-B", str(HANDOFF_TOOL), "--project", str(self.wt1), "create",
                                  "--work", "w.md"], input=json.dumps({"title": "w", "fields": FIELDS}),
                                 capture_output=True, text=True, encoding="utf-8", timeout=TIMEOUT)
        self.assertEqual(created.returncode, 0, created.stdout + created.stderr)
        self.assertTrue((self.main / ".feather" / "handoffs" / "w.md").exists())
        self.assert_status_unchanged()

    def test_leases_change_no_status_with_tracked_handoff_records(self):
        (self.main / ".gitignore").write_text(MARKER + "\n", encoding="utf-8")
        store = self.main / ".feather" / "handoffs"
        store.mkdir(parents=True)
        (store / "w.md").write_text("# w\n", encoding="utf-8")
        self.commit(self.main, "track handoffs")
        self.assertIn(".feather/handoffs/w.md", self.git(self.main, "ls-files"))
        self.assert_status_unchanged()


class PackagingTest(LeaseBase):
    def test_the_skill_is_packaged_and_names_its_launcher(self):
        manifest = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        self.assertIn("./skills/leases", manifest["skills"])
        text = SKILL.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\nname: leases\n"), text[:40])
        self.assertIn("`scripts/leases.py`", text)
        self.assertIn("${CLAUDE_PLUGIN_ROOT}/skills/leases/scripts/leases.py", text)

    def test_a_usage_error_is_json(self):
        refused = self.lease(self.main, "acquire", "--session", "s", expected=2)
        self.assertEqual((refused["status"], refused["code"]), ("error", "usage"), refused)
