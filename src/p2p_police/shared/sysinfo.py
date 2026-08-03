"""Hardware disclosure for the step-0 declaration (rulebook ch. 5.5, rule 24).

Computational fairness rests on honest, best-effort hardware reporting; absent
sensors report 'unknown' rather than guessing. Probes are cached per process:
the spec is embedded in every negotiate message and repushed until the rival
answers, and hardware does not change mid-run.
"""

import os
import platform
import subprocess
from functools import lru_cache


def hardware_spec() -> dict:
    """Best-effort host description for the sealed pre-game declaration."""
    gpu_model, vram_gb = _gpu()
    return {
        "os": f"{platform.system()} {platform.release()}",
        "cpu_type": platform.processor() or platform.machine() or "unknown",
        "cpu_cores": os.cpu_count() or 0,
        "cpu_freq_mhz": _cpu_freq_mhz(),
        "ram_gb": _ram_gb(),
        "gpu_model": gpu_model,
        "vram_gb": vram_gb,
        "python": platform.python_version(),
    }


@lru_cache(maxsize=1)
def _cpu_freq_mhz() -> int:
    try:  # Windows: the registry publishes the base clock; no extra deps
        import winreg

        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                            r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as key:
            return int(winreg.QueryValueEx(key, "~MHz")[0])
    except Exception:
        return 0


@lru_cache(maxsize=1)
def _gpu() -> tuple[str, int]:
    """(gpu_model, vram_gb): nvidia-smi when present (exact VRAM), else the
    Windows video-controller name (VRAM stays 0: Win32 AdapterRAM saturates
    at 4 GB, and a wrong number is worse than a missing one)."""
    try:
        lines = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5).stdout.strip().splitlines()
        if lines:
            name, _, mib = lines[0].partition(",")
            if name.strip():
                return name.strip(), round(float(mib) / 1024)
    except Exception:
        pass
    try:
        lines = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "(Get-CimInstance Win32_VideoController).Name"],
            capture_output=True, text=True, timeout=15).stdout.strip().splitlines()
        if lines and lines[0].strip():
            return lines[0].strip(), _vram_gb_registry()
    except Exception:
        pass
    return "unknown", _vram_gb_registry()


@lru_cache(maxsize=1)
def _vram_gb_registry() -> int:
    """Driver-reported VRAM (HardwareInformation.qwMemorySize, a QWORD — no
    Win32 AdapterRAM 4-GB saturation); 0 when no display key exposes it."""
    try:
        import winreg

        base = (r"SYSTEM\CurrentControlSet\Control\Class"
                r"\{4d36e968-e325-11ce-bfc1-08002be10318}")
        best = 0
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, base) as root:
            for i in range(32):
                try:
                    sub = winreg.EnumKey(root, i)
                except OSError:
                    break
                if not sub.isdigit():
                    continue
                try:
                    with winreg.OpenKey(root, sub) as key:
                        raw = winreg.QueryValueEx(
                            key, "HardwareInformation.qwMemorySize")[0]
                        best = max(best, round(int(raw) / 1024 ** 3))
                except OSError:
                    continue
        return best
    except Exception:
        return 0


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
