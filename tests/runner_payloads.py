"""Self-limiting payloads the Runner tests run as targets (Python 3.11+, standard library only).

Every mode is bounded on its own, so a broken Runner cannot let a payload exhaust the machine: memory is taken in
1 MiB chunks up to the cap the test passes (at most twice the run's memory limit) and then released, every sleep
has a fixed length, and output has a fixed size.

    python runner_payloads.py <mode> [arguments]
"""
import os
from pathlib import Path
import subprocess
import sys
import time

CHUNK = 1 << 20
CAP_LIMIT_MIB = 512  # no mode ever holds more than this, whatever argument it is given


def allocate(cap_mib: int) -> int:
    """Take memory in 1 MiB chunks up to cap_mib, then stop; 3 when an allocation failed, 0 when the cap was reached."""
    cap_mib = min(int(cap_mib), CAP_LIMIT_MIB)
    held = []
    try:
        for _ in range(cap_mib):
            held.append(bytearray(CHUNK))
    except MemoryError:
        taken = len(held)
        held.clear()
        print(f"memory-error after {taken} MiB", flush=True)
        return 3
    held.clear()
    print(f"allocated {cap_mib} MiB without a failure", flush=True)
    return 0


def main(argv: list[str]) -> int:
    mode, args = argv[0], argv[1:]
    if mode == "print":
        print("payload-ok", flush=True)
        return 0
    if mode == "fail":
        print("payload-failing", flush=True)
        return int(args[0]) if args else 7
    if mode == "alloc":
        return allocate(int(args[0]))
    if mode == "alloc-child":
        # The child takes memory past the limit; the parent ignores the child's outcome and exits 0.
        child = subprocess.run([sys.executable, "-B", __file__, "alloc", args[0]], timeout=50)
        print(f"child exited {child.returncode}; parent exits 0", flush=True)
        return 0
    if mode == "sleep":
        time.sleep(min(float(args[0]), 30.0))
        return 0
    if mode == "pid-sleep":
        # Write this process's id where the test can see it, then sleep a fixed time.
        Path(args[0]).write_text(str(os.getpid()), encoding="utf-8")
        time.sleep(min(float(args[1]), 30.0))
        return 0
    if mode == "spawn-sleeper":
        # Start a sleeping child that outlives this process, record its id, and exit 0 at once.
        child = subprocess.Popen([sys.executable, "-B", __file__, "sleep", "30"])
        Path(args[0]).write_text(str(child.pid), encoding="utf-8")
        print(f"left child {child.pid}", flush=True)
        return 0
    if mode == "flood":
        # A fixed number of numbered lines, then a final marker line.
        lines = min(int(args[0]), 200000)
        out = sys.stdout.buffer
        for index in range(lines):
            out.write(b"flood line %06d\n" % index)
        out.write(b"FLOOD-END-MARKER\n")
        out.flush()
        return 0
    if mode == "priority":
        import ctypes
        kernel32 = ctypes.WinDLL("kernel32")
        kernel32.GetCurrentProcess.restype = ctypes.c_void_p
        kernel32.GetPriorityClass.argtypes = [ctypes.c_void_p]
        print(f"priority-class {kernel32.GetPriorityClass(kernel32.GetCurrentProcess()):#x}", flush=True)
        return 0
    if mode == "marker":
        Path(args[0]).write_text("ran", encoding="utf-8")
        return 0
    if mode == "in-plain-job":
        # Put this process into a job that sets no memory, time or process limit (only kill-on-close), then run
        # the given command inside it with a fixed timeout and relay its output and exit code.
        import ctypes
        from ctypes import wintypes
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateJobObjectW.restype = wintypes.HANDLE
        kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        kernel32.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
        kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]

        class Basic(ctypes.Structure):
            _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64), ("PerJobUserTimeLimit", ctypes.c_int64),
                        ("LimitFlags", wintypes.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
                        ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD),
                        ("Affinity", ctypes.c_size_t), ("PriorityClass", wintypes.DWORD),
                        ("SchedulingClass", wintypes.DWORD)]

        class Extended(ctypes.Structure):
            _fields_ = [("Basic", Basic), ("IoInfo", ctypes.c_uint64 * 6), ("ProcessMemoryLimit", ctypes.c_size_t),
                        ("JobMemoryLimit", ctypes.c_size_t), ("PeakProcessMemoryUsed", ctypes.c_size_t),
                        ("PeakJobMemoryUsed", ctypes.c_size_t)]

        job = kernel32.CreateJobObjectW(None, None)
        limits = Extended()
        limits.Basic.LimitFlags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not job or not kernel32.SetInformationJobObject(job, 9, ctypes.byref(limits), ctypes.sizeof(limits)) \
                or not kernel32.AssignProcessToJobObject(job, kernel32.GetCurrentProcess()):
            print(f"job setup failed (Windows error {ctypes.get_last_error()})", file=sys.stderr)
            return 65
        inner = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", timeout=60)
        sys.stdout.write(inner.stdout)
        sys.stdout.flush()
        return inner.returncode
    print(f"unknown mode {mode}", file=sys.stderr)
    return 64


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
