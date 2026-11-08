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
    in_job = w.BOOL()
    if not k32.IsProcessInJob(k32.GetCurrentProcess(), None, ctypes.byref(in_job)):
        return refuse(result, "cannot tell whether an enclosing job limits the Runner: " + failure("IsProcessInJob"))
    if in_job.value:
        outer = ExtendedLimit()
        if not k32.QueryInformationJobObject(None, extended_limit_class, ctypes.byref(outer), ctypes.sizeof(outer),
                                             None):
            return refuse(result, "the Runner is inside an enclosing job whose limits cannot be read: "
                          + failure("QueryInformationJobObject"))
        flags = outer.Basic.LimitFlags
        if flags & limit_job_memory:
            return refuse(result, "an enclosing job limits memory for all its processes "
                          f"({outer.JobMemoryLimit} bytes), so its limit could stop the target before the Runner's")
        if flags & limit_process_memory and outer.ProcessMemoryLimit < request["memory_bytes"]:
            return refuse(result, "an enclosing job limits each process's memory to "
                          f"{outer.ProcessMemoryLimit} bytes, below the Runner's memory limit")
        if flags & (limit_process_time | limit_job_time):
            return refuse(result, "an enclosing job limits CPU time, so its limit could stop the target first")

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


# ---- Entry ---------------------------------------------------------------------------------------------------

def run(request: dict) -> dict:
    fault = os.environ.get(FAULT_VARIABLE, "")
    if sys.platform == "win32":
        return run_windows(request, fault)
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
