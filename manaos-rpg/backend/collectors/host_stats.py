from __future__ import annotations

import os
import platform
import shutil
import time
from pathlib import Path

import psutil

from collectors.gpu_stats import get_nvidia_compute_apps, get_nvidia_gpus


def _collect_windows_disks() -> list[dict]:
    disks: list[dict] = []
    for code in range(ord("A"), ord("Z") + 1):
        drive = f"{chr(code)}:\\"
        if not Path(drive).exists():
            continue
        try:
            usage = shutil.disk_usage(drive)
        except Exception:
            continue
        total_gb = round(usage.total / 1e9, 2)
        if total_gb <= 0:
            continue
        free_gb = round(usage.free / 1e9, 2)
        used_gb = round(max(0.0, total_gb - free_gb), 2)
        used_pct = round((used_gb / total_gb) * 100.0, 1) if total_gb > 0 else None
        disks.append(
            {
                "root": drive,
                "free_gb": free_gb,
                "total_gb": total_gb,
                "used_gb": used_gb,
                "used_percent": used_pct,
            }
        )
    disks.sort(key=lambda x: str(x.get("root") or ""))
    return disks


def get_host_stats() -> dict:
    ts = int(time.time())
    cpu_percent = psutil.cpu_percent(interval=0.25)
    mem = psutil.virtual_memory()

    system_drive = os.environ.get("SystemDrive", "C:")
    disk_root = f"{system_drive}\\"
    disk = shutil.disk_usage(disk_root)
    disks = _collect_windows_disks()

    net = psutil.net_io_counters(pernic=False)
    gpus = get_nvidia_gpus()
    gpu_apps = get_nvidia_compute_apps()

    boot_ts = int(psutil.boot_time())
    uptime_s = max(0, ts - boot_ts)

    return {
        "ts": ts,
        "host": {
            "os": platform.platform(),
            "hostname": platform.node(),
            "disk_root": disk_root,
            "boot_ts": boot_ts,
            "uptime_sec": int(uptime_s),
        },
        "cpu": {"percent": cpu_percent},
        "mem": {
            "percent": mem.percent,
            "used_gb": round(mem.used / 1e9, 2),
            "total_gb": round(mem.total / 1e9, 2),
        },
        "disk": {
            "free_gb": round(disk.free / 1e9, 2),
            "total_gb": round(disk.total / 1e9, 2),
        },
        "disks": disks,
        "net": {
            "bytes_sent": int(net.bytes_sent),
            "bytes_recv": int(net.bytes_recv),
        },
        "gpu": {
            "nvidia": gpus,
            "apps": gpu_apps,
        },
    }

