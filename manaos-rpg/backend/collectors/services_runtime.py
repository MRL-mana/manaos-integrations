from __future__ import annotations

from typing import Any

from collectors.docker_inspect import get_docker_container_runtime
from collectors.http_probe import http_probe
from collectors.pm2_runtime import get_pm2_runtime_by_name
from collectors.ports_probe import is_port_open


def compute_services_status(
    services: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for s in services:
        runtime = _compute_one(s)
        out.append({**s, **runtime})
    return out


def _compute_one(service: dict[str, Any]) -> dict[str, Any]:
    kind = str(service.get("kind") or "port").lower()
    port = service.get("port")
    health_url = service.get("health_url")

    alive_by_http = False
    http_status = None
    if health_url:
        pr = http_probe(str(health_url), timeout_s=0.8)
        alive_by_http = bool(pr.get("ok"))
        http_status = pr.get("status")
    alive_by_port = False
    if port:
        alive_by_port = is_port_open("127.0.0.1", int(port))

    degraded = False
    restart_count = None

    if kind == "docker":
        container = service.get("container")
        docker_rt = (
            get_docker_container_runtime(str(container))
            if container
            else None
        )
        if isinstance(docker_rt, dict):
            docker_status = docker_rt.get("docker_status")
            docker_health = docker_rt.get("docker_health")
            restart_count = docker_rt.get("restart_count")
            started_at = docker_rt.get("started_at")
            finished_at = docker_rt.get("finished_at")
        else:
            docker_status = None
            docker_health = None
            restart_count = None
            started_at = None
            finished_at = None

        alive_by_docker = False
        alive_by_docker_health = False

        if docker_status == "running":
            alive_by_docker = True

        if docker_health in ("unhealthy", "starting"):
            degraded = True
        if docker_health == "healthy":
            alive_by_docker_health = True

        alive = (
            alive_by_docker
            or alive_by_docker_health
            or alive_by_http
            or alive_by_port
        )

        alive_by = (
            "docker_health"
            if alive_by_docker_health
            else (
                "docker"
                if alive_by_docker
                else (
                    "http"
                    if alive_by_http
                    else ("port" if alive_by_port else "none")
                )
            )
        )
        return {
            "alive": bool(alive),
            "alive_by": alive_by,
            "http_status": http_status,
            "degraded": bool(degraded),
            "restart_count": restart_count,
            "docker_status": docker_status,
            "docker_health": docker_health,
            "started_at": started_at,
            "finished_at": finished_at,
        }

    if kind == "pm2":
        pm2_name = (
            service.get("pm2")
            or service.get("pm2_name")
            or service.get("name")
        )
        rt = get_pm2_runtime_by_name(str(pm2_name)) if pm2_name else None
        pm2_status = rt.get("pm2_status") if isinstance(rt, dict) else None
        restart_count = (
            rt.get("restart_count") if isinstance(rt, dict) else None
        )
        pm_uptime = rt.get("pm_uptime") if isinstance(rt, dict) else None
        pm2_found = rt.get("pm2_found") if isinstance(rt, dict) else None

        alive_by_pm2 = pm2_status == "online"
        if pm2_status in ("stopped", "errored"):
            degraded = True

        alive = alive_by_pm2 or alive_by_http or alive_by_port
        alive_by = (
            "pm2"
            if alive_by_pm2
            else (
                "http"
                if alive_by_http
                else ("port" if alive_by_port else "none")
            )
        )
        return {
            "alive": bool(alive),
            "alive_by": alive_by,
            "http_status": http_status,
            "degraded": bool(degraded),
            "restart_count": restart_count,
            "pm2_found": pm2_found,
            "pm2_status": pm2_status,
            "pm_uptime": pm_uptime,
        }

    alive = alive_by_http or alive_by_port
    return {
        "alive": bool(alive),
        "alive_by": (
            "http" if alive_by_http else ("port" if alive_by_port else "none")
        ),
        "http_status": http_status,
        "degraded": False,
        "restart_count": None,
    }
