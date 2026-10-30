"""Secret-safe, dependency-free host resource diagnostics."""
from __future__ import annotations

import os
import platform
import shutil
import sys
from pathlib import Path


def _memory_bytes() -> tuple[int | None, int | None]:
    """Return (total, available) RAM where the platform exposes it safely."""
    if sys.platform == "win32":
        try:
            import ctypes

            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            status = MEMORYSTATUSEX()
            status.dwLength = ctypes.sizeof(status)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                return int(status.ullTotalPhys), int(status.ullAvailPhys)
        except (AttributeError, OSError, TypeError, ValueError):
            return None, None
    elif sys.platform.startswith("linux"):
        try:
            values = {}
            for line in Path("/proc/meminfo").read_text(encoding="ascii").splitlines():
                key, raw = line.split(":", 1)
                if key in {"MemTotal", "MemAvailable"}:
                    values[key] = int(raw.strip().split()[0]) * 1024
            return values.get("MemTotal"), values.get("MemAvailable")
        except (OSError, ValueError, IndexError):
            return None, None
    return None, None


def collect_resource_snapshot(storage_path: str | os.PathLike[str]) -> dict:
    """Collect a small host snapshot without returning paths, usernames or secrets."""
    total, available = _memory_bytes()
    try:
        disk = shutil.disk_usage(Path(storage_path).expanduser().resolve().parent)
        disk_free = int(disk.free)
        disk_total = int(disk.total)
    except OSError:
        disk_free = None
        disk_total = None

    return {
        "platform": platform.system(),
        "platform_release": platform.release(),
        "python_version": platform.python_version(),
        "cpu_logical_count": os.cpu_count(),
        "memory_total_bytes": total,
        "memory_available_bytes": available,
        "storage_free_bytes": disk_free,
        "storage_total_bytes": disk_total,
        "diagnostics_scope": "host_resources_only",
    }
