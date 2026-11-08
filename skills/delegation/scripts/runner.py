"""cc-feather Runner: run one command with a memory limit for its whole process tree, a time limit and an output
limit, and print one JSON result (Python 3.11+, standard library only).

usage: runner.py --memory-mib N --time-seconds S --output-bytes B --cwd DIR -- COMMAND [ARGUMENT ...]

  --memory-mib N      memory limit in MiB for the target and every descendant together
  --time-seconds S    time limit in seconds for the whole run
  --output-bytes B    how many bytes of the target's combined stdout and stderr to keep: the first half and the
                      last half, so the real end is always kept
  --cwd DIR           working directory of the target
  --                  everything after the separator is the target command, passed as plain arguments

The result on stdout is one JSON object. Its "outcome" is one of:

  passed            the target exited 0, no limit was hit and every piece of evidence was read   exit status 0
  target-failed     the target exited non-zero and no limit was hit                              exit status 10
  contained         a limit stopped or constrained the run; "limit_event" says memory or time    exit status 11
  refused           the Runner did not start the target; "refusal_reason" says why               exit status 12
  evidence-missing  the Runner could not read what it needs to judge the run; never a pass       exit status 13

A limit event overrides a target exit code of 0. A usage error prints this text on stderr and exits with status 64.

The Runner refuses instead of running unprotected: when containment is not available on this platform or cannot be
set up, when an enclosing job would make its limits unreliable, or when available memory is below the memory limit.
Only processes inside the Runner's containment are limited; work handed to an already running service is not.

Windows: the target is created inside a job object before its first instruction, with a job-wide memory limit; every
member still running when the run ends is ended, and closing the Runner's handle ends them too. The target runs at
below-normal CPU priority where the job allows it; failure to lower it is reported and does not refuse the run.
Started inside any job, the Runner refuses: Windows shows only the innermost job's limits, so a job above it could
limit memory without the Runner knowing.

Linux: the target runs in a transient systemd user scope with the memory limit for every process in it, swap
disabled, OOMPolicy=continue so the scope and its evidence survive a memory kill, and the scope's own runtime limit
equal to the time limit, so a Runner killed outright does not leave the target running past it. This needs a running
systemd user manager with the cgroup v2 memory controller delegated to it, such as WSL2 with systemd enabled. The
memory limit event comes from the scope's memory.events, never from the target's exit code. The Runner refuses when
there is no user manager, the memory controller is not delegated, the scope cannot be created or does not hold its
limits, or the Runner's own cgroup or one above the scope leaves less memory than the limit. A small helper process
stays in the scope, so its memory counts toward the limit and the peak. The target runs at niceness 10 or more. A
target ended by a signal has the negative signal number as its exit code.

Git Bash: MSYS rewrites arguments that look like POSIX paths, such as /tmp/x or /c, into Windows paths before the
Runner sees them, and it can rewrite the target's own arguments the same way. Set MSYS_NO_PATHCONV=1 for the
invocation (or MSYS2_ARG_CONV_EXCL='*') when an argument must reach the target unchanged, and give the working
directory and paths as Windows paths with forward slashes, such as C:/work/project.

Set CC_FEATHER_RUNNER_FAULT=containment or CC_FEATHER_RUNNER_FAULT=monitoring to make the Runner act as though
containment or its monitoring were unavailable; it can only turn a run into refused or evidence-missing, never into
a pass. The tests use it.
"""
import json
import os
import sys
import threading
import time

sys.dont_write_bytecode = True

EXIT_STATUS = {"passed": 0, "target-failed": 10, "contained": 11, "refused": 12, "evidence-missing": 13}
USAGE_STATUS = 64
FAULT_VARIABLE = "CC_FEATHER_RUNNER_FAULT"
READ_CHUNK = 65536
MAX_TIME_SECONDS = 7 * 24 * 3600


STATE = {"target_may_have_started": False}


class UsageError(Exception):
    pass


def usage_text() -> str:
    return __doc__ or ""


def parse(argv: list[str]) -> dict:
    if any(arg in ("-h", "--help") for arg in argv[: argv.index("--") if "--" in argv else len(argv)]):
        return {"help": True}
    if "--" not in argv:
        raise UsageError("the separator -- and a target command are required")
    split = argv.index("--")
    options, command = argv[:split], argv[split + 1:]
    if not command:
        raise UsageError("no target command after --")
    if len(options) % 2:
        raise UsageError("every option takes one value")
    values = {}
    for name, value in zip(options[::2], options[1::2]):
        if name not in ("--memory-mib", "--time-seconds", "--output-bytes", "--cwd"):
            raise UsageError(f"unknown option {name}")
        if name in values:
            raise UsageError(f"{name} given twice")
        values[name] = value
    missing = [name for name in ("--memory-mib", "--time-seconds", "--output-bytes", "--cwd") if name not in values]
    if missing:
        raise UsageError("missing " + ", ".join(missing))
    try:
        memory_mib = int(values["--memory-mib"])
        time_seconds = float(values["--time-seconds"])
        output_bytes = int(values["--output-bytes"])
    except ValueError:
        raise UsageError("--memory-mib and --output-bytes take integers, --time-seconds a number") from None
    if memory_mib < 1 or not 0 < time_seconds <= MAX_TIME_SECONDS or output_bytes < 2:
        raise UsageError("limits must be positive, the time limit at most one week and the output limit at least 2")
    if not os.path.isdir(values["--cwd"]):
        raise UsageError(f"working directory does not exist: {values['--cwd']}")
    return {"help": False, "memory_bytes": memory_mib << 20, "time_seconds": time_seconds,
            "output_bytes": output_bytes, "cwd": os.path.abspath(values["--cwd"]), "command": command}


class Output:
    """Combined stdout and stderr, drained continuously; keeps at most the first half and the last half of the limit."""

    def __init__(self, fd: int, limit: int):
        self.fd = fd
        self.head_cap = limit // 2
        self.tail_cap = limit - self.head_cap
        self.head = bytearray()
        self.tail = bytearray()
        self.total = 0
        self.thread = threading.Thread(target=self._drain, daemon=True)

    def start(self):
        self.thread.start()

    def _drain(self):
        while True:
            try:
                chunk = os.read(self.fd, READ_CHUNK)
            except OSError:
                break
            if not chunk:
                break
            self.total += len(chunk)
            room = self.head_cap - len(self.head)
            if room > 0:
                self.head += chunk[:room]
                chunk = chunk[room:]
            if chunk:
                self.tail += chunk
                if len(self.tail) > self.tail_cap:
                    del self.tail[: len(self.tail) - self.tail_cap]

    def finish(self, wait_seconds: float) -> bool:
        self.thread.join(wait_seconds)
        return not self.thread.is_alive()

    def report(self) -> dict:
        head, tail = bytes(self.head), bytes(self.tail)
        kept = len(head) + len(tail)
        truncated = self.total > kept
        if not truncated:
            head, tail = head + tail, b""
        return {"head": head.decode("utf-8", "replace"), "tail": tail.decode("utf-8", "replace"),
                "truncated": truncated, "total_bytes": self.total, "omitted_bytes": self.total - kept}


def base_result(request: dict, backend: str) -> dict:
    return {
        "outcome": None, "limit_event": "none", "refusal_reason": None, "evidence_missing_reason": None,
        "exit_code": None, "peak_memory_bytes": None, "peak_memory_measured_by": None, "duration_seconds": 0.0,
        "output": {"head": "", "tail": "", "truncated": False, "total_bytes": 0, "omitted_bytes": 0},
        "limits": {"memory_bytes": request["memory_bytes"], "time_seconds": request["time_seconds"],
                   "output_bytes": request["output_bytes"]},
        "priority": {"lowered": False, "detail": None},
        "processes": {"total": None, "ended_by_runner": 0},
        "backend": backend, "command": request["command"], "cwd": request["cwd"],
    }


def refuse(result: dict, reason: str) -> dict:
    result["outcome"] = "refused"
    result["refusal_reason"] = reason
    return result


# ---- Windows backend: a job object ---------------------------------------------------------------------------

def run_windows(request: dict, fault: str) -> dict:
    import ctypes
    import msvcrt
    import subprocess
    from ctypes import wintypes as w

    result = base_result(request, "windows-job-object")
    if fault == "containment":
        return refuse(result, "containment is unavailable: job object creation was disabled by " + FAULT_VARIABLE)

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)

    class BasicLimit(ctypes.Structure):
        _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64), ("PerJobUserTimeLimit", ctypes.c_int64),
                    ("LimitFlags", w.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
                    ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", w.DWORD),
                    ("Affinity", ctypes.c_size_t), ("PriorityClass", w.DWORD), ("SchedulingClass", w.DWORD)]

    class IoCounters(ctypes.Structure):
        _fields_ = [(name, ctypes.c_uint64) for name in
                    ("ReadOperationCount", "WriteOperationCount", "OtherOperationCount", "ReadTransferCount",
                     "WriteTransferCount", "OtherTransferCount")]

    class ExtendedLimit(ctypes.Structure):
        _fields_ = [("Basic", BasicLimit), ("Io", IoCounters), ("ProcessMemoryLimit", ctypes.c_size_t),
                    ("JobMemoryLimit", ctypes.c_size_t), ("PeakProcessMemoryUsed", ctypes.c_size_t),
                    ("PeakJobMemoryUsed", ctypes.c_size_t)]

    class Accounting(ctypes.Structure):
        _fields_ = [("TotalUserTime", ctypes.c_int64), ("TotalKernelTime", ctypes.c_int64),
                    ("ThisPeriodTotalUserTime", ctypes.c_int64), ("ThisPeriodTotalKernelTime", ctypes.c_int64),
                    ("TotalPageFaultCount", w.DWORD), ("TotalProcesses", w.DWORD), ("ActiveProcesses", w.DWORD),
                    ("TotalTerminatedProcesses", w.DWORD)]

    class CompletionPort(ctypes.Structure):
        _fields_ = [("CompletionKey", ctypes.c_void_p), ("CompletionPort", w.HANDLE)]

    class MemoryStatus(ctypes.Structure):
        _fields_ = [("dwLength", w.DWORD), ("dwMemoryLoad", w.DWORD), ("ullTotalPhys", ctypes.c_uint64),
                    ("ullAvailPhys", ctypes.c_uint64), ("ullTotalPageFile", ctypes.c_uint64),
                    ("ullAvailPageFile", ctypes.c_uint64), ("ullTotalVirtual", ctypes.c_uint64),
                    ("ullAvailVirtual", ctypes.c_uint64), ("ullAvailExtendedVirtual", ctypes.c_uint64)]

    class StartupInfo(ctypes.Structure):
        _fields_ = [("cb", w.DWORD), ("lpReserved", w.LPWSTR), ("lpDesktop", w.LPWSTR), ("lpTitle", w.LPWSTR),
                    ("dwX", w.DWORD), ("dwY", w.DWORD), ("dwXSize", w.DWORD), ("dwYSize", w.DWORD),
                    ("dwXCountChars", w.DWORD), ("dwYCountChars", w.DWORD), ("dwFillAttribute", w.DWORD),
                    ("dwFlags", w.DWORD), ("wShowWindow", w.WORD), ("cbReserved2", w.WORD),
                    ("lpReserved2", ctypes.c_void_p), ("hStdInput", w.HANDLE), ("hStdOutput", w.HANDLE),
                    ("hStdError", w.HANDLE)]

    class StartupInfoEx(ctypes.Structure):
        _fields_ = [("StartupInfo", StartupInfo), ("lpAttributeList", ctypes.c_void_p)]

    class ProcessInformation(ctypes.Structure):
        _fields_ = [("hProcess", w.HANDLE), ("hThread", w.HANDLE), ("dwProcessId", w.DWORD),
                    ("dwThreadId", w.DWORD)]

    k32.GetCurrentProcess.restype = w.HANDLE
    k32.IsProcessInJob.argtypes = [w.HANDLE, w.HANDLE, ctypes.POINTER(w.BOOL)]
    k32.GlobalMemoryStatusEx.argtypes = [ctypes.POINTER(MemoryStatus)]
    k32.CreateJobObjectW.restype = w.HANDLE
    k32.CreateJobObjectW.argtypes = [ctypes.c_void_p, w.LPCWSTR]
    k32.SetInformationJobObject.argtypes = [w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD]
    k32.QueryInformationJobObject.argtypes = [w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD, ctypes.c_void_p]
    k32.CreateIoCompletionPort.restype = w.HANDLE
    k32.CreateIoCompletionPort.argtypes = [w.HANDLE, w.HANDLE, ctypes.c_size_t, w.DWORD]
    k32.GetQueuedCompletionStatus.argtypes = [w.HANDLE, ctypes.POINTER(w.DWORD), ctypes.POINTER(ctypes.c_size_t),
                                              ctypes.POINTER(ctypes.c_void_p), w.DWORD]
    k32.InitializeProcThreadAttributeList.argtypes = [ctypes.c_void_p, w.DWORD, w.DWORD,
                                                      ctypes.POINTER(ctypes.c_size_t)]
    k32.UpdateProcThreadAttribute.argtypes = [ctypes.c_void_p, w.DWORD, ctypes.c_size_t, ctypes.c_void_p,
                                              ctypes.c_size_t, ctypes.c_void_p, ctypes.c_void_p]
    k32.DeleteProcThreadAttributeList.argtypes = [ctypes.c_void_p]
    k32.CreateProcessW.argtypes = [w.LPCWSTR, w.LPWSTR, ctypes.c_void_p, ctypes.c_void_p, w.BOOL, w.DWORD,
                                   ctypes.c_void_p, w.LPCWSTR, ctypes.c_void_p, ctypes.POINTER(ProcessInformation)]
    k32.ResumeThread.argtypes = [w.HANDLE]
    k32.ResumeThread.restype = w.DWORD
    k32.TerminateProcess.argtypes = [w.HANDLE, w.UINT]
    k32.WaitForSingleObject.argtypes = [w.HANDLE, w.DWORD]
    k32.WaitForSingleObject.restype = w.DWORD
    k32.GetExitCodeProcess.argtypes = [w.HANDLE, ctypes.POINTER(w.DWORD)]
    k32.TerminateJobObject.argtypes = [w.HANDLE, w.UINT]
    k32.CloseHandle.argtypes = [w.HANDLE]

    extended_limit_class, accounting_class, port_class = 9, 1, 7
    limit_process_time, limit_job_time, limit_priority_class = 0x2, 0x4, 0x20
    limit_process_memory, limit_job_memory = 0x100, 0x200
    limit_die_on_unhandled_exception, limit_breakaway_ok, limit_silent_breakaway_ok = 0x400, 0x800, 0x1000
    limit_kill_on_job_close = 0x2000
    below_normal_priority_class = 0x4000
    message_process_memory, message_job_memory = 9, 10
    attribute_handle_list, attribute_job_list = 0x20002, 0x2000D
    create_suspended, create_unicode_environment = 0x4, 0x400
    extended_startupinfo_present, create_no_window = 0x80000, 0x08000000
    startf_usestdhandles = 0x100
    ended_by_runner_code = 0xFEA7
    launch_errors = {2: "file not found", 3: "path not found", 5: "access denied", 193: "not a valid program"}

    def failure(what: str) -> str:
        return f"{what} failed (Windows error {ctypes.get_last_error()})"

    # 1. An enclosing job can impose its own limits, which would stop the target before the Runner's limits do.
    # Windows shows a process only the limits of its innermost job, never those of the jobs above it, so inside any
    # job the Runner cannot establish that no enclosing limit applies, and it refuses.
    in_job = w.BOOL()
    if not k32.IsProcessInJob(k32.GetCurrentProcess(), None, ctypes.byref(in_job)):
        return refuse(result, "cannot tell whether an enclosing job limits the Runner: " + failure("IsProcessInJob"))
    if in_job.value:
        detail = "the limits of any job above it cannot be read"
        outer = ExtendedLimit()
        if k32.QueryInformationJobObject(None, extended_limit_class, ctypes.byref(outer), ctypes.sizeof(outer), None):
            flags = outer.Basic.LimitFlags
            if flags & limit_job_memory:
                detail = (f"it limits memory for all its processes ({outer.JobMemoryLimit} bytes), and the limits "
                          "of any job above it cannot be read")
            elif flags & limit_process_memory:
                detail = (f"it limits each process's memory to {outer.ProcessMemoryLimit} bytes, and the limits of "
                          "any job above it cannot be read")
            elif flags & (limit_process_time | limit_job_time):
                detail = "it limits CPU time, and the limits of any job above it cannot be read"
        else:
            detail = "its limits cannot be read: " + failure("QueryInformationJobObject")
        return refuse(result, "the Runner is inside an enclosing job and cannot establish that no enclosing limit "
                      f"would stop the target before its own limits do: {detail}")

    # 2. Available memory must cover the memory limit.
    status = MemoryStatus()
    status.dwLength = ctypes.sizeof(status)
    if not k32.GlobalMemoryStatusEx(ctypes.byref(status)):
        return refuse(result, "cannot read available memory: " + failure("GlobalMemoryStatusEx"))
    result["available_memory"] = {"physical_bytes": status.ullAvailPhys, "commit_bytes": status.ullAvailPageFile}
    if status.ullAvailPhys < request["memory_bytes"] or status.ullAvailPageFile < request["memory_bytes"]:
        return refuse(result, f"available memory (physical {status.ullAvailPhys} bytes, commit "
                      f"{status.ullAvailPageFile} bytes) is below the memory limit ({request['memory_bytes']} bytes)")

    # 3. The job object: whole-tree memory limit, every member ended when its last handle closes, no breakaway.
    job = k32.CreateJobObjectW(None, None)
    if not job:
        return refuse(result, "containment is unavailable: " + failure("CreateJobObject"))
    limits = ExtendedLimit()
    limits.Basic.LimitFlags = limit_job_memory | limit_kill_on_job_close | limit_die_on_unhandled_exception
    limits.JobMemoryLimit = request["memory_bytes"]
    if not k32.SetInformationJobObject(job, extended_limit_class, ctypes.byref(limits), ctypes.sizeof(limits)):
        k32.CloseHandle(job)
        return refuse(result, "containment is unavailable: " + failure("setting the job's memory limit"))
    limits.Basic.LimitFlags |= limit_priority_class
    limits.Basic.PriorityClass = below_normal_priority_class
    if k32.SetInformationJobObject(job, extended_limit_class, ctypes.byref(limits), ctypes.sizeof(limits)):
        result["priority"] = {"lowered": True, "detail": "below-normal priority class for every job member"}
    else:
        result["priority"] = {"lowered": False, "detail": failure("setting the job's priority class")}
    applied = ExtendedLimit()
    if not k32.QueryInformationJobObject(job, extended_limit_class, ctypes.byref(applied), ctypes.sizeof(applied),
                                         None):
        k32.CloseHandle(job)
        return refuse(result, "cannot confirm the job's limits: " + failure("QueryInformationJobObject"))
    flags = applied.Basic.LimitFlags
    if (applied.JobMemoryLimit != request["memory_bytes"] or not flags & limit_job_memory
            or not flags & limit_kill_on_job_close or flags & (limit_breakaway_ok | limit_silent_breakaway_ok)):
        k32.CloseHandle(job)
        return refuse(result, "the job does not hold the requested memory limit and kill-on-close")

    # Memory-limit notifications arrive on a completion port; without it a memory event cannot be seen.
    port = None
    monitoring_problem = None
    if fault == "monitoring":
        monitoring_problem = "memory-limit monitoring was disabled by " + FAULT_VARIABLE
    else:
        port = k32.CreateIoCompletionPort(w.HANDLE(-1), None, 0, 1)
        if not port:
            monitoring_problem = failure("CreateIoCompletionPort")
        else:
            association = CompletionPort(None, port)
            if not k32.SetInformationJobObject(job, port_class, ctypes.byref(association),
                                               ctypes.sizeof(association)):
                monitoring_problem = failure("associating the completion port with the job")
                k32.CloseHandle(port)
                port = None

    # 4. Output: one pipe for stdout and stderr, so the order and the real end are kept; stdin is the null device.
    read_fd, write_fd = os.pipe()
    null_fd = os.open(os.devnull, os.O_RDONLY)
    for fd in (write_fd, null_fd):
        os.set_inheritable(fd, True)
    write_handle, null_handle = msvcrt.get_osfhandle(write_fd), msvcrt.get_osfhandle(null_fd)

    # 5. The target is created suspended, already inside the job through the job-list attribute, and resumed only
    # after the Runner confirms the assignment, so its first instruction and every descendant run inside the job.
    size = ctypes.c_size_t()
    k32.InitializeProcThreadAttributeList(None, 2, 0, ctypes.byref(size))
    attributes = ctypes.create_string_buffer(size.value)

    def close_launch_handles():
        for fd in (write_fd, null_fd):
            os.close(fd)

    if not k32.InitializeProcThreadAttributeList(attributes, 2, 0, ctypes.byref(size)):
        close_launch_handles()
        os.close(read_fd)
        k32.CloseHandle(job)
        return refuse(result, "containment is unavailable: " + failure("InitializeProcThreadAttributeList"))
    jobs = (w.HANDLE * 1)(job)
    handles = (w.HANDLE * 2)(null_handle, write_handle)
    if not (k32.UpdateProcThreadAttribute(attributes, 0, attribute_job_list, jobs, ctypes.sizeof(jobs), None, None)
            and k32.UpdateProcThreadAttribute(attributes, 0, attribute_handle_list, handles, ctypes.sizeof(handles),
                                              None, None)):
        problem = failure("UpdateProcThreadAttribute")
        k32.DeleteProcThreadAttributeList(attributes)
        close_launch_handles()
        os.close(read_fd)
        k32.CloseHandle(job)
        return refuse(result, "containment is unavailable: assigning the job at creation " + problem)
    startup = StartupInfoEx()
    startup.StartupInfo.cb = ctypes.sizeof(startup)
    startup.StartupInfo.dwFlags = startf_usestdhandles
    startup.StartupInfo.hStdInput = null_handle
    startup.StartupInfo.hStdOutput = write_handle
    startup.StartupInfo.hStdError = write_handle
    startup.lpAttributeList = ctypes.cast(attributes, ctypes.c_void_p)
    process = ProcessInformation()
    command = list(request["command"])
    command_line = ctypes.create_unicode_buffer(subprocess.list2cmdline(command))
    started_at = time.monotonic()
    STATE["target_may_have_started"] = True
    created = k32.CreateProcessW(None, command_line, None, None, True,
                                 create_suspended | create_unicode_environment | extended_startupinfo_present
                                 | create_no_window, None, request["cwd"], ctypes.byref(startup),
                                 ctypes.byref(process))
    launch_error = ctypes.get_last_error()
    k32.DeleteProcThreadAttributeList(attributes)
    close_launch_handles()
    if not created:
        os.close(read_fd)
        k32.CloseHandle(job)
        if launch_error in launch_errors:
            result["outcome"] = "target-failed"
            result["launch_error"] = f"the target could not start: {launch_errors[launch_error]}"
            return result
        return refuse(result, f"containment is unavailable: creating the target inside the job failed "
                      f"(Windows error {launch_error})")
    member = w.BOOL()
    if not k32.IsProcessInJob(process.hProcess, job, ctypes.byref(member)) or not member.value:
        k32.TerminateProcess(process.hProcess, ended_by_runner_code)
        k32.CloseHandle(process.hThread)
        k32.CloseHandle(process.hProcess)
        os.close(read_fd)
        k32.CloseHandle(job)
        return refuse(result, "the target was not inside the job before its first instruction")
    output = Output(read_fd, request["output_bytes"])
    output.start()
    k32.ResumeThread(process.hThread)
    k32.CloseHandle(process.hThread)

    # 6. Supervise: wait for the target while reading job messages; end the job at the time limit.
    events: list[str] = []
    message, key, overlapped = w.DWORD(), ctypes.c_size_t(), ctypes.c_void_p()

    def read_messages(wait_ms: int, budget: int = 256):
        if port is None:
            return
        for _ in range(budget):
            if not k32.GetQueuedCompletionStatus(port, ctypes.byref(message), ctypes.byref(key),
                                                 ctypes.byref(overlapped), wait_ms):
                return
            wait_ms = 0
            if message.value in (message_job_memory, message_process_memory) and "memory" not in events:
                events.append("memory")

    def accounting():
        info = Accounting()
        ok = k32.QueryInformationJobObject(job, accounting_class, ctypes.byref(info), ctypes.sizeof(info), None)
        return info if ok else None

    deadline = started_at + request["time_seconds"]
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            events.append("time")
            break
        if k32.WaitForSingleObject(process.hProcess, int(min(remaining, 0.1) * 1000)) == 0:
            break
        read_messages(0)
    target_ended = k32.WaitForSingleObject(process.hProcess, 0) == 0

    # 7. End every remaining member. After a normal exit, give the target's console host a moment to leave.
    evidence_problems = []
    if target_ended:
        for _ in range(10):
            info = accounting()
            if info is None or info.ActiveProcesses == 0:
                break
            time.sleep(0.1)
    info = accounting()
    if info is None:
        evidence_problems.append(failure("reading the job's process accounting"))
    elif info.ActiveProcesses:
        result["processes"]["ended_by_runner"] = info.ActiveProcesses - (0 if target_ended else 1)
    if info is None or info.ActiveProcesses:
        k32.TerminateJobObject(job, ended_by_runner_code)
    for _ in range(50):
        info = accounting()
        if info is not None and info.ActiveProcesses == 0:
            break
        time.sleep(0.1)
    else:
        evidence_problems.append("job members were still running after the Runner ended them")
    read_messages(0, budget=4096)
    k32.WaitForSingleObject(process.hProcess, 5000)
    code = w.DWORD()
    if k32.GetExitCodeProcess(process.hProcess, ctypes.byref(code)) and code.value != 259:
        result["exit_code"] = code.value
    else:
        evidence_problems.append("the target's exit code could not be read")
    if not output.finish(5):
        evidence_problems.append("the target's output did not close")
    result["output"] = output.report()
    final = ExtendedLimit()
    if k32.QueryInformationJobObject(job, extended_limit_class, ctypes.byref(final), ctypes.sizeof(final), None):
        result["peak_memory_bytes"] = final.PeakJobMemoryUsed
        result["peak_memory_measured_by"] = "job object peak committed memory of the whole process tree"
    else:
        evidence_problems.append(failure("reading the job's peak memory"))
    info = accounting()
    if info is not None:
        result["processes"]["total"] = info.TotalProcesses
    result["duration_seconds"] = round(time.monotonic() - started_at, 3)
    k32.CloseHandle(process.hProcess)
    if port is not None:
        k32.CloseHandle(port)
    k32.CloseHandle(job)

    # 8. Judge: a limit event decides first; then missing evidence; only then the target's exit code.
    if monitoring_problem:
        evidence_problems.append("memory-limit events could not be observed: " + monitoring_problem)
    elif ("memory" not in events and result["peak_memory_bytes"] is not None
          and result["peak_memory_bytes"] >= request["memory_bytes"] * 0.95):
        evidence_problems.append("peak memory reached the limit without a memory-limit notification")
    if events:
        result["outcome"], result["limit_event"] = "contained", events[0]
    elif evidence_problems:
        result["outcome"], result["limit_event"] = "evidence-missing", "unknown"
    elif result["exit_code"] == 0:
        result["outcome"] = "passed"
    else:
        result["outcome"] = "target-failed"
    if evidence_problems:
        result["evidence_missing_reason"] = "; ".join(evidence_problems)
    return result


# ---- Linux backend: a transient systemd user scope -----------------------------------------------------------

CGROUP_ROOT = "/sys/fs/cgroup"
SMALL_READ = 65536

# The helper runs inside the scope. It reports its cgroup, waits for the Runner's go byte, then starts the target as
# its child at a lower priority with the output pipe as stdout and stderr, reports the exit code, and stays in the
# scope so the scope and its memory evidence outlive the target until the Runner has read them. If the Runner goes
# away, the control pipe reaches end of file and the helper ends every process in the scope.
LINUX_HELPER = r"""
import os, select, sys
report, control, out = (int(value) for value in sys.argv[1:4])
cwd, command = sys.argv[4], sys.argv[5:]
def say(text):
    os.write(report, (text + "\n").encode("utf-8", "replace"))
def end_scope():
    try:
        with open(path + "/cgroup.kill", "w") as handle:
            handle.write("1")
    finally:
        os._exit(0)
relative = ""
with open("/proc/self/cgroup", "rb") as handle:
    for line in handle.read(65536).decode("utf-8", "replace").splitlines():
        if line.startswith("0::"):
            relative = line[3:]
path = "/sys/fs/cgroup" + relative
say("cgroup " + relative)
if os.read(control, 1) != b"g":
    os._exit(0)
status_read, status_write = os.pipe()
child = os.fork()
if child == 0:
    try:
        os.close(status_read)
        os.close(report)
        os.close(control)
        try:
            os.setpriority(os.PRIO_PROCESS, 0, max(10, os.getpriority(os.PRIO_PROCESS, 0)))
            os.write(status_write, b"priority lowered\n")
        except OSError as problem:
            os.write(status_write, ("priority failed " + str(problem) + "\n").encode("utf-8", "replace"))
        os.chdir(cwd)
        os.dup2(out, 1)
        os.dup2(out, 2)
        os.close(out)
        os.execvp(command[0], command)
    except OSError as problem:
        os.write(status_write, ("launch " + str(problem.errno) + " " + str(problem.strerror) + "\n").encode())
    os._exit(127)
os.close(status_write)
os.close(out)
status = b""
while len(status) < 65536:
    chunk = os.read(status_read, 4096)
    if not chunk:
        break
    status += chunk
os.close(status_read)
for line in status.decode("utf-8", "replace").splitlines():
    say(line)
while True:
    if select.select([control], [], [], 0.1)[0]:
        end_scope()
    done, wait_status = os.waitpid(child, os.WNOHANG)
    if done:
        say("exit " + str(os.waitstatus_to_exitcode(wait_status)))
        break
while True:
    select.select([control], [], [])
    end_scope()
"""


def read_small(path: str, cap: int = SMALL_READ) -> str | None:
    """At most cap bytes of a small file, or None when it cannot be read."""
    try:
        fd = os.open(path, os.O_RDONLY)
    except OSError:
        return None
    try:
        return os.read(fd, cap).decode("utf-8", "replace")
    except OSError:
        return None
    finally:
        os.close(fd)


def small_command(args: list[str], timeout: float = 15, env: dict | None = None) -> tuple[int | None, str]:
    """Run a short command; keep at most 8 KiB of its combined output; None as the code when it did not finish."""
    import subprocess
    read_fd, write_fd = os.pipe()
    try:
        process = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=write_fd, stderr=write_fd, env=env)
    except OSError as problem:
        os.close(read_fd)
        os.close(write_fd)
        return None, str(problem)
    os.close(write_fd)
    output = Output(read_fd, 8192)
    output.start()
    try:
        code = process.wait(timeout)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(5)
        code = None
    output.finish(5)
    report = output.report()
    os.close(read_fd)
    return code, (report["head"] + report["tail"]).strip()


def memory_events(cgroup_dir: str) -> dict | None:
    text = read_small(cgroup_dir + "/memory.events")
    if text is None:
        return None
    events = {}
    for line in text.splitlines():
        name, _, value = line.partition(" ")
        if value.strip().isdigit():
            events[name] = int(value)
    return events if "oom_kill" in events else None


def enclosing_memory_limit(relative: str, memory_bytes: int, include_self: bool) -> str | None:
    """The first cgroup on the path to the root whose memory.max or memory.high leaves less than memory_bytes free."""
    parts = [part for part in relative.split("/") if part]
    levels = ["/" + "/".join(parts[:count]) for count in range(len(parts), 0, -1)]
    if not include_self:
        levels = levels[1:]
    for level in levels:
        current = read_small(CGROUP_ROOT + level + "/memory.current")
        in_use = int(current) if current and current.strip().isdigit() else 0
        for name in ("memory.max", "memory.high"):
            value = read_small(CGROUP_ROOT + level + "/" + name)
            if value is None or not value.strip().isdigit():
                continue
            if int(value) - in_use < memory_bytes:
                return (f"the enclosing cgroup {level} sets {name} to {value.strip()} bytes with {in_use} bytes in "
                        f"use, which leaves less than the memory limit ({memory_bytes} bytes)")
    return None


def run_linux(request: dict, fault: str) -> dict:
    import shutil
    import select
    import subprocess

    result = base_result(request, "linux-systemd-user-scope")
    if fault == "containment":
        return refuse(result, "containment is unavailable: transient scope creation was disabled by " + FAULT_VARIABLE)
    systemd_run, systemctl = shutil.which("systemd-run"), shutil.which("systemctl")
    if not systemd_run or not systemctl:
        return refuse(result, "containment is unavailable: systemd-run or systemctl is not installed, so there is "
                      "no systemd user manager to create a scope")

    # 1. A running systemd user manager with the cgroup v2 memory controller delegated to it.
    code, text = small_command([systemctl, "--user", "show", "-p", "SystemState", "-p", "ControlGroup",
                                "-p", "Version"])
    manager = dict(line.partition("=")[::2] for line in text.splitlines() if "=" in line) if code == 0 else {}
    if code != 0 or manager.get("SystemState") not in ("running", "degraded"):
        return refuse(result, "containment is unavailable: no running systemd user manager answered ("
                      + (text or f"systemctl exit {code}")[:500] + ")")
    result["containment"] = {"systemd_version": manager.get("Version"), "unit": None, "cgroup": None}
    if read_small(CGROUP_ROOT + "/cgroup.controllers") is None:
        return refuse(result, "containment is unavailable: the cgroup v2 hierarchy is not mounted at " + CGROUP_ROOT)
    delegated = (read_small(CGROUP_ROOT + manager.get("ControlGroup", "/-") + "/cgroup.subtree_control") or "").split()
    if "memory" not in delegated:
        return refuse(result, "containment is unavailable: the memory controller is not delegated to the systemd "
                      f"user manager (its cgroup enables: {' '.join(delegated) or 'nothing readable'})")

    # 2. The Runner's own cgroup must not be limited below the run, or the Runner itself could be stopped first.
    own = ""
    for line in (read_small("/proc/self/cgroup") or "").splitlines():
        if line.startswith("0::"):
            own = line[3:]
    if not own:
        return refuse(result, "containment is unavailable: the Runner's own cgroup v2 path cannot be read")
    limit = enclosing_memory_limit(own, request["memory_bytes"], include_self=True)
    if limit:
        return refuse(result, "an enclosing limit would make the Runner's limits unreliable: " + limit)

    # 3. Available memory must cover the memory limit.
    available = None
    for line in (read_small("/proc/meminfo") or "").splitlines():
        if line.startswith("MemAvailable:") and line.split()[1].isdigit():
            available = int(line.split()[1]) * 1024
    if available is None:
        return refuse(result, "cannot read available memory from /proc/meminfo")
    result["available_memory"] = {"physical_bytes": available, "commit_bytes": None}
    if available < request["memory_bytes"]:
        return refuse(result, f"available memory ({available} bytes, MemAvailable) is below the memory limit "
                      f"({request['memory_bytes']} bytes)")

    # 4. The scope: the memory limit for every process in it, no swap, an OOM policy that keeps the scope running so
    # its memory events survive, and the scope's own runtime limit equal to the time limit, so a Runner killed
    # outright does not leave the target running past it.
    unit = f"cc-feather-runner-{os.getpid()}-{time.time_ns()}"
    result["containment"]["unit"] = unit + ".scope"
    runtime_us = max(1, int(-(-request["time_seconds"] * 1_000_000 // 1)))
    report_read, report_write = os.pipe()
    control_read, control_write = os.pipe()
    out_read, out_write = os.pipe()
    setup_read, setup_write = os.pipe()
    started_at = time.monotonic()
    try:
        helper = subprocess.Popen(
            [systemd_run, "--user", "--scope", "--quiet", "--collect", "--unit", unit,
             "--description", "cc-feather Runner target: " + " ".join(request["command"])[:200],
             "-p", f"MemoryMax={request['memory_bytes']}", "-p", "MemorySwapMax=0", "-p", "OOMPolicy=continue",
             "-p", f"RuntimeMaxSec={runtime_us}us", "-p", "KillSignal=SIGKILL", "--",
             sys.executable, "-I", "-S", "-B", "-c", LINUX_HELPER, str(report_write), str(control_read),
             str(out_write), request["cwd"], *request["command"]],
            stdin=subprocess.DEVNULL, stdout=setup_write, stderr=setup_write,
            pass_fds=(report_write, control_read, out_write))
    except OSError as problem:
        for fd in (report_read, report_write, control_read, control_write, out_read, out_write, setup_read,
                   setup_write):
            os.close(fd)
        return refuse(result, f"containment is unavailable: systemd-run could not start: {problem}")
    for fd in (report_write, control_read, out_write, setup_write):
        os.close(fd)
    setup = Output(setup_read, 8192)
    setup.start()
    output = Output(out_read, request["output_bytes"])
    output.start()

    reports: list[str] = []
    pending = bytearray()
    report_bytes = [0]

    def read_reports(wait_seconds: float) -> bool:
        """Read complete report lines, at most 64 KiB in all; False at end of file."""
        if not select.select([report_read], [], [], max(0.0, wait_seconds))[0]:
            return True
        chunk = os.read(report_read, 4096)
        if not chunk:
            return False
        report_bytes[0] += len(chunk)
        if report_bytes[0] <= SMALL_READ:
            pending.extend(chunk)
            while b"\n" in pending:
                line, _, rest = bytes(pending).partition(b"\n")
                pending[:] = rest
                reports.append(line.decode("utf-8", "replace"))
        return True

    def report(prefix: str) -> str | None:
        return next((line[len(prefix):] for line in reports if line.startswith(prefix)), None)

    scope_dir = None

    def end_scope():
        if scope_dir is not None:
            try:
                with open(scope_dir + "/cgroup.kill", "w") as handle:
                    handle.write("1")
            except OSError:
                pass

    def close_down(wait_seconds: float) -> bool:
        """End every process in the scope and wait until the helper and the scope are gone."""
        end_scope()
        os.close(control_write)
        try:
            helper.wait(wait_seconds)
        except subprocess.TimeoutExpired:
            helper.kill()
            helper.wait(5)
        gone_by = time.monotonic() + wait_seconds
        while scope_dir is not None and os.path.isdir(scope_dir) and time.monotonic() < gone_by:
            end_scope()
            time.sleep(0.05)
        return scope_dir is None or not os.path.isdir(scope_dir)

    def finish_refusal(reason: str) -> dict:
        close_down(10)
        setup.finish(5)
        output.finish(5)
        os.close(report_read)
        os.close(setup_read)
        os.close(out_read)
        return refuse(result, reason)

    # 5. Confirm the scope before the target exists: the helper is in it and the limits hold.
    open_report = True
    created_by = time.monotonic() + 30
    while report("cgroup ") is None and open_report and time.monotonic() < created_by:
        open_report = read_reports(0.1)
        if helper.poll() is not None and not select.select([report_read], [], [], 0)[0]:
            break
    relative = report("cgroup ")
    if relative is None:
        setup.finish(5)
        problem = setup.report()
        return finish_refusal("containment is unavailable: the scope could not be created ("
                              + ((problem["head"] + problem["tail"]).strip()[:500]
                                 or f"systemd-run exit {helper.poll()}") + ")")
    if not relative.endswith("/" + unit + ".scope"):
        return finish_refusal(f"the Runner's helper is not inside the scope it created (it is in {relative})")
    scope_dir = CGROUP_ROOT + relative
    result["containment"]["cgroup"] = relative
    members = (read_small(scope_dir + "/cgroup.procs") or "").split()
    applied = (read_small(scope_dir + "/memory.max") or "").strip()
    swap = (read_small(scope_dir + "/memory.swap.max") or "").strip()
    group = (read_small(scope_dir + "/memory.oom.group") or "").strip()
    if str(helper.pid) not in members:
        return finish_refusal("the Runner's helper is not a member of the scope it created")
    if applied != str(request["memory_bytes"]):
        return finish_refusal("the scope does not hold the requested memory limit (memory.max reads "
                              f"{applied or 'nothing'}); the memory controller may not be delegated")
    if swap != "0":
        return finish_refusal(f"swap is not disabled for the scope (memory.swap.max reads {swap or 'nothing'})")
    if group not in ("0", ""):
        return finish_refusal("the scope would end all its processes together at the first memory kill")
    code, text = small_command([systemctl, "--user", "show", unit + ".scope", "-p", "OOMPolicy",
                                "-p", "RuntimeMaxUSec"])
    properties = dict(line.partition("=")[::2] for line in text.splitlines() if "=" in line)
    if code != 0 or properties.get("OOMPolicy") != "continue" or properties.get("RuntimeMaxUSec") in (None, "",
                                                                                                      "infinity"):
        return finish_refusal("the scope does not hold the OOM policy and runtime limit the Runner set ("
                              + text[:300] + ")")
    limit = enclosing_memory_limit(relative, request["memory_bytes"], include_self=False)
    if limit:
        return finish_refusal("an enclosing limit would make the scope's limits unreliable: " + limit)
    monitoring_problem = None
    baseline = None
    if fault == "monitoring":
        monitoring_problem = "memory-limit monitoring was disabled by " + FAULT_VARIABLE
    else:
        baseline = memory_events(scope_dir)
        if baseline is None:
            monitoring_problem = "the scope's memory.events cannot be read"

    # 6. Start the target and supervise: read memory events while it runs; end the scope at the time limit.
    events: list[str] = []
    evidence_problems: list[str] = []

    def check_memory():
        if baseline is None or "memory" in events:
            return
        now = memory_events(scope_dir)
        if now is not None and (now.get("oom_kill", 0) > baseline.get("oom_kill", 0)
                                or now.get("oom", 0) > baseline.get("oom", 0)):
            events.append("memory")

    STATE["target_may_have_started"] = True
    os.write(control_write, b"g")
    deadline = started_at + request["time_seconds"]
    while report("exit ") is None and report("launch ") is None:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            events.append("time")
            break
        if not open_report:
            break
        open_report = read_reports(min(remaining, 0.1))
        check_memory()
    end_reported = report("exit ") is not None
    if not end_reported and "time" not in events and time.monotonic() - started_at >= request["time_seconds"]:
        events.append("time")  # the scope's own runtime limit ended it first
    exit_by = time.monotonic() + 5
    while open_report and report("exit ") is None and report("launch ") is not None and time.monotonic() < exit_by:
        open_report = read_reports(0.1)
    check_memory()

    priority = report("priority ")
    if priority == "lowered":
        result["priority"] = {"lowered": True, "detail": "niceness at least 10 for the target and its descendants"}
    elif priority is not None:
        result["priority"] = {"lowered": False, "detail": "lowering the target's priority " + priority}
    launch = report("launch ")
    if launch is not None:
        number, _, message = launch.partition(" ")
        result["launch_error"] = f"the target could not start: {message} (errno {number})"

    # 7. End every remaining process. After a normal exit, give descendants a moment to leave on their own.
    def others() -> list[str]:
        return [pid for pid in (read_small(scope_dir + "/cgroup.procs") or "").split() if pid != str(helper.pid)]

    if end_reported or launch is not None:
        for _ in range(10):
            if not others():
                break
            time.sleep(0.1)
    left = others()
    result["processes"]["ended_by_runner"] = max(0, len(left) - (0 if end_reported or launch is not None else 1))
    peak = read_small(scope_dir + "/memory.peak")
    if peak is not None and peak.strip().isdigit():
        result["peak_memory_bytes"] = int(peak)
        result["peak_memory_measured_by"] = ("cgroup v2 memory.peak of the scope: the whole process tree, the "
                                             "Runner's small helper and page cache charged to the scope")
    else:
        evidence_problems.append("the scope's memory.peak cannot be read")
    check_memory()
    if not close_down(10):
        evidence_problems.append("processes in the scope were still running after the Runner ended them")
    exit_text = report("exit ")
    if exit_text is not None and exit_text.lstrip("-").isdigit():
        result["exit_code"] = int(exit_text)
    elif launch is None and "time" not in events and "memory" not in events:
        evidence_problems.append("the target's exit code could not be read")
    if not output.finish(5):
        evidence_problems.append("the target's output did not close")
    result["output"] = output.report()
    setup.finish(1)
    os.close(report_read)
    os.close(setup_read)
    os.close(out_read)
    result["duration_seconds"] = round(time.monotonic() - started_at, 3)

    # 8. Judge: a limit event decides first; then missing evidence; only then the target's exit code.
    if monitoring_problem:
        evidence_problems.append("memory-limit events could not be observed: " + monitoring_problem)
    if launch is not None and not events:
        result["outcome"] = "target-failed"
    elif events:
        result["outcome"], result["limit_event"] = "contained", events[0]
    elif evidence_problems:
        result["outcome"], result["limit_event"] = "evidence-missing", "unknown"
    elif result["exit_code"] == 0:
        result["outcome"] = "passed"
    else:
        result["outcome"] = "target-failed"
    if evidence_problems:
        result["evidence_missing_reason"] = "; ".join(evidence_problems)
    return result


# ---- Entry ---------------------------------------------------------------------------------------------------

def run(request: dict) -> dict:
    fault = os.environ.get(FAULT_VARIABLE, "")
    if sys.platform == "win32":
        return run_windows(request, fault)
    if sys.platform.startswith("linux"):
        return run_linux(request, fault)
    result = base_result(request, "none")
    return refuse(result, f"containment is unavailable: this release has no containment backend for {sys.platform}")


def main(argv: list[str]) -> int:
    if sys.version_info < (3, 11):
        print("runner.py requires Python 3.11+", file=sys.stderr)
        return USAGE_STATUS
    try:
        request = parse(argv)
    except UsageError as problem:
        print(f"runner.py: {problem}\n\n{usage_text()}", file=sys.stderr)
        return USAGE_STATUS
    if request["help"]:
        print(usage_text())
        return 0
    try:
        result = run(request)
    except Exception as problem:  # the Runner's own failure is never reported as the target's outcome
        result = base_result(request, "unknown")
        result["outcome"] = "evidence-missing" if STATE["target_may_have_started"] else "refused"
        reason = f"the Runner failed: {type(problem).__name__}: {problem}"
        result["refusal_reason" if result["outcome"] == "refused" else "evidence_missing_reason"] = reason
        result["limit_event"] = "unknown"
    print(json.dumps(result, ensure_ascii=True, indent=1))
    return EXIT_STATUS[result["outcome"]]


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
