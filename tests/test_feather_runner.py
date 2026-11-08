"""Runner seam: run skills/delegation/scripts/runner.py as a subprocess and judge its JSON result and exit status.

Every target is a self-limiting payload from runner_payloads.py: memory payloads take at most twice the run's memory
limit and then stop, sleeps have a fixed length and output a fixed size. Every Runner run has its own timeout, and
the Runner's job object, or on Linux its scope's runtime limit, ends the target when a timed-out Runner is killed, so
a broken Runner cannot exhaust the test machine.
"""
import ctypes
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "skills/delegation/scripts/runner.py"
PAYLOADS = Path(__file__).resolve().parent / "runner_payloads.py"
FAULT = "CC_FEATHER_RUNNER_FAULT"
EXIT = {"passed": 0, "target-failed": 10, "contained": 11, "refused": 12, "evidence-missing": 13}
WINDOWS = sys.platform == "win32"
LINUX = sys.platform.startswith("linux")


def linux_scope_problem() -> str | None:
    """None when a transient systemd user scope with a working memory limit can be created here; otherwise why not.

    Checked without the Runner, so a broken Runner cannot turn its own tests into skips."""
    if not LINUX:
        return "not Linux"
    if not shutil.which("systemd-run"):
        return "systemd-run is not installed"
    try:
        completed = subprocess.run(
            ["systemd-run", "--user", "--scope", "--quiet", "--collect", "-p", "MemoryMax=64M",
             "-p", "MemorySwapMax=0", "--", "sh", "-c",
             'cat "/sys/fs/cgroup$(cut -d: -f3 /proc/self/cgroup)/memory.max"'],
            capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError) as problem:
        return f"no user scope: {problem}"
    if completed.returncode != 0 or completed.stdout.strip() != str(64 << 20):
        return f"no user scope with a memory limit: {completed.stdout.strip()} {completed.stderr.strip()}"[:300]
    return None


LINUX_PROBLEM = linux_scope_problem() if LINUX else "not Linux"


def payload(*args: str) -> list[str]:
    return [sys.executable, "-B", str(PAYLOADS), *args]


def process_gone(pid: int, wait_seconds: float) -> bool:
    """True when the process with this id has exited or no longer exists, waiting at most wait_seconds."""
    if not WINDOWS:
        deadline = time.monotonic() + wait_seconds
        while True:
            try:
                state = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8").rsplit(")", 1)[1].split()[0]
            except (OSError, IndexError):
                return True
            if state in ("Z", "X"):
                return True
            if time.monotonic() >= deadline:
                return False
            time.sleep(0.1)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.restype = ctypes.c_void_p
    kernel32.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
    kernel32.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    handle = kernel32.OpenProcess(0x00100000, False, pid)  # SYNCHRONIZE
    if not handle:
        return True
    try:
        return kernel32.WaitForSingleObject(handle, int(wait_seconds * 1000)) == 0
    finally:
        kernel32.CloseHandle(handle)


class RunnerCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.work = Path(os.path.realpath(self.temp.name))

    def run_runner(self, target, *, memory_mib=128, time_seconds=30, output_bytes=65536, timeout=60, env=None,
                   runner_args=None):
        args = runner_args if runner_args is not None else [
            "--memory-mib", str(memory_mib), "--time-seconds", str(time_seconds),
            "--output-bytes", str(output_bytes), "--cwd", str(self.work)]
        environment = {key: value for key, value in os.environ.items() if key != FAULT}
        environment.update(env or {})
        completed = subprocess.run([sys.executable, "-B", str(RUNNER), *args, "--", *target], capture_output=True,
                                   text=True, encoding="utf-8", timeout=timeout, env=environment)
        try:
            result = json.loads(completed.stdout)
        except json.JSONDecodeError:
            self.fail(f"no JSON result (exit {completed.returncode}): {completed.stdout!r} {completed.stderr!r}")
        return completed.returncode, result

    def assertOutcome(self, code, result, outcome):
        self.assertEqual(result["outcome"], outcome, json.dumps(result, indent=1))
        self.assertEqual(code, EXIT[outcome], json.dumps(result, indent=1))


class RunnerEveryPlatformTests(RunnerCase):
    def test_refuses_when_containment_is_unavailable_and_never_starts_the_target(self):
        marker = self.work / "ran.txt"
        code, result = self.run_runner(payload("marker", str(marker)), env={FAULT: "containment"}, timeout=30)
        self.assertOutcome(code, result, "refused")
        self.assertIn("containment", result["refusal_reason"])
        self.assertIsNone(result["exit_code"])
        self.assertFalse(marker.exists())

    def test_a_usage_error_has_its_own_exit_status(self):
        completed = subprocess.run([sys.executable, "-B", str(RUNNER), "--memory-mib", "64"], capture_output=True,
                                   text=True, encoding="utf-8", timeout=30)
        self.assertNotIn(completed.returncode, EXIT.values())
        self.assertIn("usage", completed.stderr.lower())

    def test_usage_text_covers_git_bash_path_rewriting(self):
        completed = subprocess.run([sys.executable, "-B", str(RUNNER), "--help"], capture_output=True, text=True,
                                   encoding="utf-8", timeout=30)
        self.assertEqual(completed.returncode, 0)
        self.assertIn("Git Bash", completed.stdout)
        self.assertIn("MSYS_NO_PATHCONV=1", completed.stdout)


@unittest.skipUnless(WINDOWS, "the Windows backend runs on Windows")
class RunnerWindowsTests(RunnerCase):
    def test_a_passing_target_passes_with_its_whole_output_and_the_applied_limits(self):
        code, result = self.run_runner(payload("print"), memory_mib=128, time_seconds=30, output_bytes=4096)
        self.assertOutcome(code, result, "passed")
        self.assertEqual(result["limit_event"], "none")
        self.assertIsNone(result["refusal_reason"])
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(result["output"]["head"].strip(), "payload-ok")
        self.assertEqual(result["output"]["tail"], "")
        self.assertFalse(result["output"]["truncated"])
        self.assertEqual(result["limits"], {"memory_bytes": 128 << 20, "time_seconds": 30.0, "output_bytes": 4096})
        self.assertIsInstance(result["peak_memory_bytes"], int)
        self.assertGreater(result["peak_memory_bytes"], 0)
        self.assertTrue(result["peak_memory_measured_by"])
        self.assertGreaterEqual(result["duration_seconds"], 0)

    def test_a_failing_target_is_target_failed_with_its_exit_code(self):
        code, result = self.run_runner(payload("fail", "7"))
        self.assertOutcome(code, result, "target-failed")
        self.assertEqual(result["limit_event"], "none")
        self.assertEqual(result["exit_code"], 7)
        self.assertIn("payload-failing", result["output"]["head"])

    def test_a_child_over_the_memory_limit_is_contained_although_the_parent_exits_0(self):
        # Limit 128 MiB; the child takes at most 256 MiB in 1 MiB chunks and then stops.
        code, result = self.run_runner(payload("alloc-child", "256"), memory_mib=128, time_seconds=60, timeout=90)
        self.assertOutcome(code, result, "contained")
        self.assertEqual(result["limit_event"], "memory")
        self.assertEqual(result["exit_code"], 0)
        self.assertIn("parent exits 0", result["output"]["head"] + result["output"]["tail"])
        # The kernel enforces the limit at allocation granularity, so the peak may pass it by a little.
        self.assertLessEqual(result["peak_memory_bytes"], (128 << 20) * 1.05)

    def test_a_target_over_the_time_limit_is_contained_and_ended(self):
        pid_file = self.work / "pid.txt"
        started = time.monotonic()
        code, result = self.run_runner(payload("pid-sleep", str(pid_file), "30"), time_seconds=2, timeout=45)
        self.assertLess(time.monotonic() - started, 25)
        self.assertOutcome(code, result, "contained")
        self.assertEqual(result["limit_event"], "time")
        self.assertTrue(process_gone(int(pid_file.read_text(encoding="utf-8")), 5))

    def test_a_descendant_left_running_is_ended_when_the_run_ends(self):
        pid_file = self.work / "child.txt"
        code, result = self.run_runner(payload("spawn-sleeper", str(pid_file)), timeout=45)
        self.assertOutcome(code, result, "passed")
        self.assertGreaterEqual(result["processes"]["ended_by_runner"], 1)
        self.assertTrue(process_gone(int(pid_file.read_text(encoding="utf-8")), 5))

    def test_killing_the_runner_ends_the_target(self):
        pid_file = self.work / "pid.txt"
        runner = subprocess.Popen(
            [sys.executable, "-B", str(RUNNER), "--memory-mib", "128", "--time-seconds", "40", "--output-bytes",
             "4096", "--cwd", str(self.work), "--", *payload("pid-sleep", str(pid_file), "30")],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            deadline = time.monotonic() + 20
            while not pid_file.exists() or not pid_file.read_text(encoding="utf-8"):
                self.assertLess(time.monotonic(), deadline, "the target never started")
                self.assertIsNone(runner.poll())
                time.sleep(0.1)
            target = int(pid_file.read_text(encoding="utf-8"))
            self.assertFalse(process_gone(target, 0))
        finally:
            runner.kill()
            runner.wait(timeout=15)
        self.assertTrue(process_gone(target, 5))

    def test_an_output_flood_keeps_the_beginning_and_the_real_end(self):
        code, result = self.run_runner(payload("flood", "100000"), output_bytes=4096)
        self.assertOutcome(code, result, "passed")
        output = result["output"]
        self.assertTrue(output["truncated"])
        self.assertGreater(output["total_bytes"], 1_000_000)
        self.assertTrue(output["head"].startswith("flood line 000000\n"))
        self.assertTrue(output["tail"].rstrip().endswith("FLOOD-END-MARKER"))
        self.assertLessEqual(len(output["head"].encode()) + len(output["tail"].encode()), 4096)

    def test_the_target_runs_at_lower_cpu_priority(self):
        code, result = self.run_runner(payload("priority"))
        self.assertOutcome(code, result, "passed")
        self.assertTrue(result["priority"]["lowered"])
        self.assertIn("priority-class 0x4000", result["output"]["head"])

    def test_refuses_when_available_memory_is_below_the_memory_limit(self):
        marker = self.work / "ran.txt"
        code, result = self.run_runner(payload("marker", str(marker)), memory_mib=1 << 30, timeout=30)
        self.assertOutcome(code, result, "refused")
        self.assertIn("available memory", result["refusal_reason"])
        self.assertFalse(marker.exists())

    def test_refuses_inside_an_enclosing_job_with_a_memory_limit(self):
        # The outer Runner's job limits memory, so a Runner started inside it refuses.
        marker = self.work / "ran.txt"
        inner = [sys.executable, "-B", str(RUNNER), "--memory-mib", "64", "--time-seconds", "20", "--output-bytes",
                 "4096", "--cwd", str(self.work), "--", *payload("marker", str(marker))]
        code, result = self.run_runner(inner, memory_mib=256, time_seconds=40, timeout=60)
        self.assertOutcome(code, result, "target-failed")
        self.assertEqual(result["exit_code"], EXIT["refused"])
        inner_result = json.loads(result["output"]["head"])
        self.assertEqual(inner_result["outcome"], "refused")
        self.assertIn("enclosing job", inner_result["refusal_reason"])
        self.assertFalse(marker.exists())

    def test_refuses_inside_any_enclosing_job_because_jobs_above_it_cannot_be_read(self):
        # A job with no memory, time or process limit encloses the Runner. Windows shows a process only the limits of
        # its innermost job, so a job above that one could still limit memory; the Runner refuses rather than trust
        # limits it cannot establish.
        marker = self.work / "ran.txt"
        inner = [sys.executable, "-B", str(RUNNER), "--memory-mib", "64", "--time-seconds", "20", "--output-bytes",
                 "4096", "--cwd", str(self.work), "--", *payload("marker", str(marker))]
        completed = subprocess.run(payload("in-plain-job", *inner), capture_output=True, text=True, encoding="utf-8",
                                   timeout=90)
        self.assertEqual(completed.returncode, EXIT["refused"], completed.stdout + completed.stderr)
        inner_result = json.loads(completed.stdout)
        self.assertEqual(inner_result["outcome"], "refused")
        self.assertIn("enclosing job", inner_result["refusal_reason"])
        self.assertFalse(marker.exists())

    def test_missing_evidence_is_never_passed(self):
        code, result = self.run_runner(payload("print"), env={FAULT: "monitoring"})
        self.assertOutcome(code, result, "evidence-missing")
        self.assertEqual(result["limit_event"], "unknown")
        self.assertEqual(result["exit_code"], 0)
        self.assertTrue(result["evidence_missing_reason"])


def scope_of(pid: int) -> str:
    """The name of the systemd unit whose cgroup holds this process."""
    line = next(line for line in Path(f"/proc/{pid}/cgroup").read_text(encoding="utf-8").splitlines()
                if line.startswith("0::"))
    return line.rsplit("/", 1)[1]


def parent_of(pid: int) -> int:
    return int(Path(f"/proc/{pid}/stat").read_text(encoding="utf-8").rsplit(")", 1)[1].split()[1])


def wait_for_pid(test: unittest.TestCase, pid_file: Path, runner: subprocess.Popen) -> int:
    deadline = time.monotonic() + 20
    while not pid_file.exists() or not pid_file.read_text(encoding="utf-8"):
        test.assertLess(time.monotonic(), deadline, "the target never started")
        test.assertIsNone(runner.poll())
        time.sleep(0.1)
    return int(pid_file.read_text(encoding="utf-8"))


@unittest.skipIf(LINUX_PROBLEM, f"the Linux backend needs a systemd user scope with a memory limit: {LINUX_PROBLEM}")
class RunnerLinuxTests(RunnerCase):
    def assertScopeGone(self, result):
        unit = result["containment"]["unit"]
        state = subprocess.run(["systemctl", "--user", "is-active", unit], capture_output=True, text=True,
                               timeout=30).stdout.strip()
        self.assertNotIn(state, ("active", "activating", "deactivating"), unit)

    def test_a_passing_target_passes_with_its_whole_output_and_the_applied_limits(self):
        code, result = self.run_runner(payload("print"), memory_mib=128, time_seconds=30, output_bytes=4096)
        self.assertOutcome(code, result, "passed")
        self.assertEqual(result["backend"], "linux-systemd-user-scope")
        self.assertEqual(result["limit_event"], "none")
        self.assertIsNone(result["refusal_reason"])
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(result["output"]["head"].strip(), "payload-ok")
        self.assertEqual(result["output"]["tail"], "")
        self.assertFalse(result["output"]["truncated"])
        self.assertEqual(result["limits"], {"memory_bytes": 128 << 20, "time_seconds": 30.0, "output_bytes": 4096})
        self.assertIsInstance(result["peak_memory_bytes"], int)
        self.assertGreater(result["peak_memory_bytes"], 0)
        self.assertIn("memory.peak", result["peak_memory_measured_by"])
        self.assertGreaterEqual(result["duration_seconds"], 0)
        self.assertScopeGone(result)

    def test_a_failing_target_is_target_failed_with_its_exit_code(self):
        code, result = self.run_runner(payload("fail", "7"))
        self.assertOutcome(code, result, "target-failed")
        self.assertEqual(result["limit_event"], "none")
        self.assertEqual(result["exit_code"], 7)
        self.assertIn("payload-failing", result["output"]["head"])

    def test_a_target_that_cannot_start_is_target_failed(self):
        code, result = self.run_runner([str(self.work / "no-such-program")])
        self.assertOutcome(code, result, "target-failed")
        self.assertEqual(result["limit_event"], "none")
        self.assertIn("could not start", result["launch_error"])

    def test_a_child_over_the_memory_limit_is_contained_although_the_parent_exits_0(self):
        # Limit 128 MiB; the child takes at most 256 MiB in 1 MiB chunks and then stops.
        code, result = self.run_runner(payload("alloc-child", "256"), memory_mib=128, time_seconds=60, timeout=90)
        self.assertOutcome(code, result, "contained")
        self.assertEqual(result["limit_event"], "memory")
        self.assertEqual(result["exit_code"], 0)
        self.assertIn("parent exits 0", result["output"]["head"] + result["output"]["tail"])
        self.assertLessEqual(result["peak_memory_bytes"], (128 << 20) * 1.05)
        self.assertScopeGone(result)

    def test_a_target_over_the_memory_limit_is_contained_with_its_signal(self):
        # Limit 64 MiB; the target takes at most 128 MiB in 1 MiB chunks and then stops.
        code, result = self.run_runner(payload("alloc", "128"), memory_mib=64, time_seconds=60, timeout=90)
        self.assertOutcome(code, result, "contained")
        self.assertEqual(result["limit_event"], "memory")
        self.assertEqual(result["exit_code"], -signal.SIGKILL)

    def test_a_target_over_the_time_limit_is_contained_and_ended(self):
        pid_file = self.work / "pid.txt"
        started = time.monotonic()
        code, result = self.run_runner(payload("pid-sleep", str(pid_file), "30"), time_seconds=2, timeout=45)
        self.assertLess(time.monotonic() - started, 25)
        self.assertOutcome(code, result, "contained")
        self.assertEqual(result["limit_event"], "time")
        self.assertTrue(process_gone(int(pid_file.read_text(encoding="utf-8")), 5))
        self.assertScopeGone(result)

    def test_a_descendant_left_running_is_ended_when_the_run_ends(self):
        pid_file = self.work / "child.txt"
        code, result = self.run_runner(payload("spawn-sleeper", str(pid_file)), timeout=45)
        self.assertOutcome(code, result, "passed")
        self.assertGreaterEqual(result["processes"]["ended_by_runner"], 1)
        self.assertTrue(process_gone(int(pid_file.read_text(encoding="utf-8")), 5))
        self.assertScopeGone(result)

    def test_killing_the_runner_ends_the_target(self):
        pid_file = self.work / "pid.txt"
        runner = subprocess.Popen(
            [sys.executable, "-B", str(RUNNER), "--memory-mib", "128", "--time-seconds", "40", "--output-bytes",
             "4096", "--cwd", str(self.work), "--", *payload("pid-sleep", str(pid_file), "30")],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            target = wait_for_pid(self, pid_file, runner)
            self.assertFalse(process_gone(target, 0))
        finally:
            runner.kill()
            runner.wait(timeout=15)
        self.assertTrue(process_gone(target, 5))

    def test_the_scope_runtime_limit_equals_the_time_limit_and_ends_the_target_without_the_runner(self):
        # Kill the Runner and its helper in the scope outright: only the scope's own runtime limit is left.
        pid_file = self.work / "pid.txt"
        started = time.monotonic()
        runner = subprocess.Popen(
            [sys.executable, "-B", str(RUNNER), "--memory-mib", "128", "--time-seconds", "6", "--output-bytes",
             "4096", "--cwd", str(self.work), "--", *payload("pid-sleep", str(pid_file), "30")],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            target = wait_for_pid(self, pid_file, runner)
            unit = scope_of(target)
            self.assertTrue(unit.startswith("cc-feather-runner-") and unit.endswith(".scope"), unit)
            limit = subprocess.run(["systemctl", "--user", "show", unit, "-p", "RuntimeMaxUSec", "--value"],
                                   capture_output=True, text=True, timeout=30).stdout.strip()
            self.assertEqual(limit, "6s")
            os.kill(parent_of(target), signal.SIGKILL)
        finally:
            runner.kill()
            runner.wait(timeout=15)
        self.assertFalse(process_gone(target, 0.5))
        self.assertTrue(process_gone(target, 15))
        self.assertLess(time.monotonic() - started, 6 + 8)

    def test_an_output_flood_keeps_the_beginning_and_the_real_end(self):
        code, result = self.run_runner(payload("flood", "100000"), output_bytes=4096)
        self.assertOutcome(code, result, "passed")
        output = result["output"]
        self.assertTrue(output["truncated"])
        self.assertGreater(output["total_bytes"], 1_000_000)
        self.assertTrue(output["head"].startswith("flood line 000000\n"))
        self.assertTrue(output["tail"].rstrip().endswith("FLOOD-END-MARKER"))
        self.assertLessEqual(len(output["head"].encode()) + len(output["tail"].encode()), 4096)

    def test_the_target_runs_at_lower_cpu_priority(self):
        code, result = self.run_runner(payload("priority"))
        self.assertOutcome(code, result, "passed")
        self.assertTrue(result["priority"]["lowered"])
        niceness = int(result["output"]["head"].split()[1])
        self.assertGreaterEqual(niceness, 10)

    def test_refuses_when_available_memory_is_below_the_memory_limit(self):
        marker = self.work / "ran.txt"
        code, result = self.run_runner(payload("marker", str(marker)), memory_mib=1 << 30, timeout=30)
        self.assertOutcome(code, result, "refused")
        self.assertIn("available memory", result["refusal_reason"])
        self.assertFalse(marker.exists())

    def test_refuses_inside_an_enclosing_cgroup_whose_limit_is_below_the_run(self):
        # The outer Runner's scope limits memory to 128 MiB, so a Runner inside it asking for 256 MiB refuses.
        marker = self.work / "ran.txt"
        inner = [sys.executable, "-B", str(RUNNER), "--memory-mib", "256", "--time-seconds", "20", "--output-bytes",
                 "4096", "--cwd", str(self.work), "--", *payload("marker", str(marker))]
        code, result = self.run_runner(inner, memory_mib=128, time_seconds=40, timeout=60)
        self.assertOutcome(code, result, "target-failed")
        self.assertEqual(result["exit_code"], EXIT["refused"])
        inner_result = json.loads(result["output"]["head"])
        self.assertEqual(inner_result["outcome"], "refused")
        self.assertIn("enclosing", inner_result["refusal_reason"])
        self.assertFalse(marker.exists())

    def test_refuses_without_a_user_manager(self):
        marker = self.work / "ran.txt"
        environment = {key: value for key, value in os.environ.items()
                       if key not in ("XDG_RUNTIME_DIR", "DBUS_SESSION_BUS_ADDRESS", FAULT)}
        completed = subprocess.run(
            [sys.executable, "-B", str(RUNNER), "--memory-mib", "64", "--time-seconds", "20", "--output-bytes",
             "4096", "--cwd", str(self.work), "--", *payload("marker", str(marker))],
            capture_output=True, text=True, encoding="utf-8", timeout=60, env=environment)
        result = json.loads(completed.stdout)
        self.assertOutcome(completed.returncode, result, "refused")
        self.assertIn("user manager", result["refusal_reason"])
        self.assertFalse(marker.exists())

    def test_refuses_when_the_scope_cannot_be_created(self):
        # A systemd-run earlier on PATH that always fails stands in for a manager that cannot create the scope.
        tools = self.work / "tools"
        tools.mkdir()
        fake = tools / "systemd-run"
        fake.write_text("#!/bin/sh\necho 'scope creation failed for the test' >&2\nexit 1\n", encoding="utf-8")
        fake.chmod(0o755)
        marker = self.work / "ran.txt"
        code, result = self.run_runner(payload("marker", str(marker)), timeout=60,
                                       env={"PATH": f"{tools}{os.pathsep}{os.environ.get('PATH', '')}"})
        self.assertOutcome(code, result, "refused")
        self.assertIn("scope could not be created", result["refusal_reason"])
        self.assertIn("scope creation failed for the test", result["refusal_reason"])
        self.assertFalse(marker.exists())

    def test_missing_evidence_is_never_passed(self):
        code, result = self.run_runner(payload("print"), env={FAULT: "monitoring"})
        self.assertOutcome(code, result, "evidence-missing")
        self.assertEqual(result["limit_event"], "unknown")
        self.assertEqual(result["exit_code"], 0)
        self.assertTrue(result["evidence_missing_reason"])


if __name__ == "__main__":
    unittest.main()
