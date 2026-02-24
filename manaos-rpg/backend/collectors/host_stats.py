from __future__ import annotations

import os
import platform
import shutil
import time

import psutil

from .gpu_stats import get_nvidia_compute_apps, get_nvidia_gpus


def get_host_stats() -> dict:
    ts = int(time.time())
    cpu_percent = psutil.cpu_percent(interval=0.25)
    mem = psutil.virtual_memory()

    system_drive = os.environ.get("SystemDrive", "C:")
    disk_root = f"{system_drive}\\"
    disk = shutil.disk_usage(disk_root)

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
        "net": {
            "bytes_sent": int(net.bytes_sent),
            "bytes_recv": int(net.bytes_recv),
        },
        "gpu": {
            "nvidia": gpus,
            "apps": gpu_apps,
        },
    }

