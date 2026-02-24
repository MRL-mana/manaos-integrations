from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class NvidiaGpuSample:
    name: str
    utilization_gpu: int | None
    mem_used_mb: int | None
    mem_total_mb: int | None
    temperature_c: int | None
    power_draw_w: int | None


def _try_run(cmd: list[str], timeout_s: float = 1.5) -> str | None:
    try:
        completed = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        out = (completed.stdout or "").strip()
        return out if out else None
    except Exception:
        return None


def get_nvidia_gpus() -> list[dict]:
    if not shutil.which("nvidia-smi"):
        return []

    q = "name,utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw"
    out = _try_run(["nvidia-smi", f"--query-gpu={q}", "--format=csv,noheader,nounits"], timeout_s=2.0)
    if not out:
        return []

    gpus: list[dict] = []
    for line in out.splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 6:
            continue
        name = parts[0]
        util = _to_int(parts[1])
        mem_used = _to_int(parts[2])
        mem_total = _to_int(parts[3])
        temp = _to_int(parts[4])
        power = _to_int(parts[5])
        gpus.append(
            {
                "name": name,
                "utilization_gpu": util,
                "mem_used_mb": mem_used,
                "mem_total_mb": mem_total,
                "temperature_c": temp,
                "power_draw_w": power,
            }
        )
    return gpus


def get_nvidia_compute_apps() -> list[dict]:
    if not shutil.which("nvidia-smi"):
        return []

    # compute apps first (more common for AI workloads). Fallback to query-apps.
    out = _try_run(
        [
            "nvidia-smi",
            "--query-compute-apps=pid,process_name,used_gpu_memory",
            "--format=csv,noheader,nounits",
        ],
        timeout_s=2.0,
    )
    if not out:
        out = _try_run(
            [
                "nvidia-smi",
                "--query-apps=pid,process_name,used_gpu_memory",
                "--format=csv,noheader,nounits",
            ],
            timeout_s=2.0,
        )
    if not out:
        # may require accounting mode; best-effort
        out = _try_run(
            [
                "nvidia-smi",
                "--query-accounted-apps=pid,process_name,gpu_memory_usage",
                "--format=csv,noheader,nounits",
            ],
            timeout_s=2.0,
        )
    if not out:
        return []

    apps: list[dict] = []
    for line in out.splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 3:
            continue
        pid = _to_int(parts[0])
        name = parts[1]
        used_mb = _to_int(parts[2])
        # nvidia-smi sometimes emits N/A for memory; skip those for "犯人"用途
        if used_mb is None:
            continue
        apps.append({"pid": pid, "process_name": name, "used_gpu_memory_mb": used_mb})

    # sort by VRAM used desc
    apps.sort(key=lambda x: int(x.get("used_gpu_memory_mb") or 0), reverse=True)
    return apps


def _to_int(v: str) -> int | None:
    try:
        return int(float(v))
    except Exception:
        return None
