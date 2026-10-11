#!/usr/bin/env python3
"""Read-only, no-network profile of THE MACHINE EXECUTING THIS SCRIPT.

Do not interpret container/CI results as the owner's device. No identifiers,
serial numbers, private filesystem names, environment variables or IPs printed.
"""
import json
import os
import platform
import shutil
import subprocess
from pathlib import Path


def _read_positive_int(path):
    try:
        raw = Path(path).read_text(encoding="ascii").strip()
        n = int(raw)
        return n if 0 < n < 2**60 else None
    except (ValueError, OSError):
        return None


def read_memory():
    total = None
    available = None
    try:
        for row in Path("/proc/meminfo").read_text(encoding="ascii").splitlines():
            if row.startswith("MemTotal:"):
                total = int(row.split()[1]) * 1024
            if row.startswith("MemAvailable:"):
                available = int(row.split()[1]) * 1024
    except (OSError, ValueError, IndexError):
        pass
    # A container may report host physical memory despite stricter cgroup caps.
    limits = [_read_positive_int("/sys/fs/cgroup/memory.max"),
              _read_positive_int("/sys/fs/cgroup/memory/memory.limit_in_bytes")]
    limits = [x for x in limits if x is not None]
    cap = min(limits) if limits else None
    effective = min(total, cap) if total is not None and cap is not None else (cap or total)
    return {"host_visible_total_bytes": total, "host_visible_available_bytes": available,
            "cgroup_limit_bytes": cap, "effective_limit_bytes": effective}


def read_nvidia():
    if not shutil.which("nvidia-smi"):
        return {"status": "NOT_DETECTED_BY_NVIDIA_SMI", "gpu_count": None}
    try:
        completed = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=3, check=True)
        devices = []
        for line in completed.stdout.splitlines():
            name, mib = line.rsplit(",", 1)
            devices.append({"model": name.strip()[:100], "total_vram_mib": int(mib.strip())})
        return {"status": "REPORTED_BY_NVIDIA_SMI", "gpu_count": len(devices), "devices": devices}
    except (subprocess.SubprocessError, ValueError, OSError):
        return {"status": "GPU_INFO_UNAVAILABLE", "gpu_count": None}


def profile_now():
    return {"evidence_scope": "EXECUTION_ENVIRONMENT_ONLY_NOT_OWNER_DEVICE",
            "os": platform.system(), "architecture": platform.machine(),
            "cpu_logical_count": os.cpu_count(), "memory": read_memory(),
            "nvidia_gpu": read_nvidia(),
            "other_gpu_types": "NOT_PROBED", "inference_measured": False}


if __name__ == "__main__":
    print(json.dumps(profile_now(), ensure_ascii=False, sort_keys=True))
