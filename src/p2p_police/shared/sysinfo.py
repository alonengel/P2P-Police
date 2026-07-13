"""Hardware disclosure for the step-0 declaration (rulebook ch. 5.5, rule 24).

Computational fairness rests on honest, best-effort hardware reporting; absent
sensors report 'unknown' rather than guessing.
"""

import os
import platform


def hardware_spec() -> dict:
    """Best-effort host description for the sealed pre-game declaration."""
    return {
        "os": f"{platform.system()} {platform.release()}",
        "cpu_type": platform.processor() or platform.machine() or "unknown",
        "cpu_cores": os.cpu_count() or 0,
        "cpu_freq_mhz": 0,      # not exposed portably without extra deps
        "ram_gb": _ram_gb(),
        "gpu_model": "unknown",  # no GPU is used by the agent
        "vram_gb": 0,
        "python": platform.python_version(),
    }


def _ram_gb() -> int:
    try:  # Windows: query total physical memory via ctypes (stdlib only)
        import ctypes

        class MemoryStatus(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_uint64),
                ("ullAvailPhys", ctypes.c_uint64),
                ("ullTotalPageFile", ctypes.c_uint64),
                ("ullAvailPageFile", ctypes.c_uint64),
                ("ullTotalVirtual", ctypes.c_uint64),
                ("ullAvailVirtual", ctypes.c_uint64),
                ("ullAvailExtendedVirtual", ctypes.c_uint64),
            ]

        status = MemoryStatus(dwLength=ctypes.sizeof(MemoryStatus))
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return round(status.ullTotalPhys / (1024**3))
    except Exception:
        pass
    return 0
