#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ManaOS dashboard CLI (SSOT + Health + optional CI)."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests
import yaml  # type: ignore[import-untyped]


RESET = "\x1b[0m"
COLORS = {
    "ok": "\x1b[32m",
    "warn": "\x1b[33m",
    "fail": "\x1b[31m",
    "dim": "\x1b[2m",
}


@dataclass
class ServiceRow:
    section: str
    name: str
    enabled: bool
    port: int | None
    url: str
    depends_on: list[str]
    health: str = "SKIP"
    status: str = "SKIP"
    summary: str = "SKIP"


def eprint(*args: Any) -> None:
    print(*args, file=sys.stderr)


def colorize(text: str, tone: str, use_color: bool) -> str:
    if not use_color:
        return text
    return f"{COLORS.get(tone, '')}{text}{RESET}"


def load_ledger(path: str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as file:
        loaded = yaml.safe_load(file)
    if not isinstance(loaded, dict):
        raise ValueError("ledger root must be mapping")
    return loaded


def normalize_rows(ledger: dict[str, Any]) -> list[ServiceRow]:
    rows: list[ServiceRow] = []
    for section in ("core", "optional"):
        block = ledger.get(section, {})
        if not isinstance(block, dict):
            continue
        for name, spec in block.items():
            if not isinstance(spec, dict):
                continue
            port = spec.get("port")
            url = str(spec.get("url") or "").strip()
            if not url and isinstance(port, int):
                url = f"http://127.0.0.1:{port}"
            rows.append(
                ServiceRow(
                    section=section,
                    name=str(name),
                    enabled=bool(spec.get("enabled", False)),
                    port=port if isinstance(port, int) else None,
                    url=url,
                    depends_on=[
                        str(item)
                        for item in spec.get("depends_on", [])
                    ],
                )
            )
    return rows


def get_json(
    url: str,
    headers: dict[str, str],
    timeout: float,
) -> tuple[int, Any]:
    response = requests.get(url, headers=headers, timeout=timeout)
    content_type = (response.headers.get("content-type") or "").lower()
    if "application/json" in content_type:
        try:
            return response.status_code, response.json()
        except ValueError:
            return response.status_code, {"_raw_text": response.text[:2000]}
    return response.status_code, {
        "_raw_text": response.text[:2000],
        "_content_type": content_type,
    }


def probe_service(row: ServiceRow, timeout: float) -> ServiceRow:
    if not row.enabled:
        row.health = "DISABLED"
        row.status = "DISABLED"
        row.summary = "DISABLED"
        return row

    if not row.url:
        row.health = "NO_URL"
        row.status = "NO_URL"
        row.summary = "NO_URL"
        return row

    headers: dict[str, str] = {}
    endpoints = [
        ("health", "/health"),
        ("status", "/status"),
    ]

    health_code: int | None = None
    status_code: int | None = None
    health_payload: Any = None
    status_payload: Any = None

    for label, path in endpoints:
        target = row.url.rstrip("/") + path
        try:
            code, payload = get_json(target, headers=headers, timeout=timeout)
        except requests.Timeout:
            code, payload = -1, {"_error": "timeout"}
        except requests.RequestException as exception:
            code, payload = -2, {"_error": str(exception)}

        if label == "health":
            health_code, health_payload = code, payload
        else:
            status_code, status_payload = code, payload

    row.health = code_to_state(health_code)
    row.status = code_to_state(status_code)

    if health_code == 200 or status_code == 200:
        row.summary = "OK"
    elif health_code == -1 or status_code == -1:
        row.summary = "TIMEOUT"
    elif health_code == 404 and status_code == 404:
        row.summary = "NO_ENDPOINT"
    elif health_code == -2 and status_code == -2:
        row.summary = "DOWN"
    else:
        row.summary = "WARN"

    if status_code == 200 and isinstance(status_payload, dict):
        check = status_payload.get("check_summary")
        if isinstance(check, dict):
            row.summary = "OK"

    if health_code == 200 and isinstance(health_payload, dict):
        if row.summary not in ("OK",):
            row.summary = "OK"

    return row


def code_to_state(code: int | None) -> str:
    if code is None:
        return "UNKNOWN"
    if code == 200:
        return "OK"
    if code == 404:
        return "NO_ENDPOINT"
    if code == -1:
        return "TIMEOUT"
    if code == -2:
        return "DOWN"
    return f"HTTP_{code}"


def dependency_alerts(rows: list[ServiceRow]) -> list[str]:
    index = {row.name: row for row in rows}
    alerts: list[str] = []
    for row in rows:
        if not row.enabled:
            continue
        for dependency in row.depends_on:
            dep = index.get(dependency)
            if dep is None:
                alerts.append(f"{row.name} depends_on {dependency}: MISSING")
                continue
            if not dep.enabled:
                alerts.append(f"{row.name} depends_on {dependency}: DISABLED")
                continue
            if dep.summary in ("OK", "SKIP"):
                alerts.append(f"{row.name} depends_on {dependency}: OK")
            else:
                alerts.append(
                    f"{row.name} depends_on {dependency}: {dep.summary}"
                )
    return alerts


def _build_rev_deps(rows: list[ServiceRow]) -> dict[str, set[str]]:
    """逆依存グラフを構築: dep_name -> {dependants}"""
    rev: dict[str, set[str]] = {}
    for row in rows:
        for dep in row.depends_on:
            rev.setdefault(dep, set()).add(row.name)
    return rev


def _bfs_blast(target: str, rev_deps: dict[str, set[str]]) -> list[str]:
    """BFS でブラスト半径 (連鎖停止するサービス名リスト) を求める。"""
    visited: set[str] = set()
    queue: deque[str] = deque([target])
    while queue:
        node = queue.popleft()
        for dep in rev_deps.get(node, set()):
            if dep not in visited:
                visited.add(dep)
                queue.append(dep)
    return sorted(visited)


def print_blast_alerts(
    rows: list[ServiceRow],
    use_color: bool,
) -> None:
    """DOWN/TIMEOUT のサービスについてブラスト半径を表示する。"""
    down_rows = [
        r for r in rows
        if r.enabled and r.summary in ("DOWN", "TIMEOUT")
    ]
    if not down_rows:
        return

    rev_deps = _build_rev_deps(rows)
    print("BLAST RISK")
    for row in down_rows:
        affected = _bfs_blast(row.name, rev_deps)
        if affected:
            names = ", ".join(affected[:8])
            if len(affected) > 8:
                names += f" +{len(affected) - 8} more"
            line = f"[BLAST] {row.name} DOWN -> cascades to: {names} ({len(affected)} total)"
            print(colorize(line, "fail", use_color))
        else:
            line = f"[BLAST] {row.name} DOWN -> isolated (no cascade)"
            print(colorize(line, "warn", use_color))
    print()


def fetch_latest_validate_ledger(repo: str, token: str) -> dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    runs_url = f"https://api.github.com/repos/{repo}/actions/runs?per_page=20"
    response = requests.get(runs_url, headers=headers, timeout=8)
    response.raise_for_status()
    payload = response.json()
    runs = payload.get("workflow_runs", [])

    target = None
    for run in runs:
        if run.get("name") == "Validate Ledger":
            target = run
            break

    if not target:
        return {"status": "NOT_FOUND"}

    run_id = target.get("id")
    jobs_url = (
        f"https://api.github.com/repos/{repo}/actions/runs/{run_id}/jobs"
        "?per_page=50"
    )
    jobs_response = requests.get(jobs_url, headers=headers, timeout=8)
    jobs_response.raise_for_status()
    jobs_payload = jobs_response.json()
    jobs = jobs_payload.get("jobs", [])

    stage2 = "UNKNOWN"
    stage3 = "UNKNOWN"
    stage3_elapsed_ms: float | None = None

    for job in jobs:
        for step in job.get("steps", []):
            name = str(step.get("name") or "")
            conclusion = str(step.get("conclusion") or "")
            if name == "Stage2 contract checks":
                stage2 = conclusion.upper() or "UNKNOWN"
            if name.startswith("Stage3 lightweight E2E smoke"):
                stage3 = conclusion.upper() or "UNKNOWN"

    return {
        "status": str(target.get("conclusion") or "UNKNOWN").upper(),
        "run_id": run_id,
        "sha": str(target.get("head_sha") or "")[:7],
        "url": target.get("html_url"),
        "stage2": stage2,
        "stage3": stage3,
        "stage3_elapsed_ms": stage3_elapsed_ms,
    }


def print_table(rows: list[ServiceRow], use_color: bool) -> None:
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"ManaOS Dashboard (SSOT+Health)  {now}")
    print()

    sections = [
        ("core", "CORE"),
        ("optional", "OPTIONAL (enabled only)"),
    ]
    for section, title in sections:
        print(title)
        display_rows = [
            row
            for row in rows
            if row.section == section and (section == "core" or row.enabled)
        ]
        if not display_rows:
            print("(none)")
            print()
            continue

        for row in display_rows:
            icon = "[OK]"
            tone = "ok"
            if row.summary in ("WARN", "NO_ENDPOINT", "HTTP_401", "HTTP_403"):
                icon = "[WARN]"
                tone = "warn"
            if row.summary in ("DOWN", "TIMEOUT", "NO_URL"):
                icon = "[FAIL]"
                tone = "fail"
            if not row.enabled:
                icon = "[SKIP]"
                tone = "dim"

            deps = ",".join(row.depends_on) if row.depends_on else "-"
            port = str(row.port) if row.port is not None else "-"
            line = (
                f"{icon} {row.name:<16} :{port:<5} "
                f"deps=[{deps:<20}] health={row.health:<11} "
                f"status={row.status:<11} summary={row.summary}"
            )
            print(colorize(line, tone, use_color))
        print()


def print_ci(ci_data: dict[str, Any], use_color: bool) -> None:
    print("CI (latest)")
    status = str(ci_data.get("status") or "UNKNOWN")
    if status in ("SUCCESS", "COMPLETED"):
        tone = "ok"
    elif status in ("SKIP", "NOT_FOUND"):
        tone = "dim"
    else:
        tone = "warn"

    stage2 = ci_data.get("stage2", "UNKNOWN")
    stage3 = ci_data.get("stage3", "UNKNOWN")
    sha = ci_data.get("sha", "-")
    line = (
        f"Validate Ledger={status} sha={sha} "
        f"Stage2={stage2} Stage3={stage3}"
    )
    print(colorize(line, tone, use_color))
    if ci_data.get("url"):
        print(ci_data["url"])
    print()


def load_file_secretary_summary(audit_log: str) -> dict[str, Any]:
    path = Path(audit_log)
    if not path.exists():
        return {
            "last_run": None,
            "processed": 0,
            "errors": 0,
            "total": 0,
        }

    processed = 0
    errors = 0
    total = 0
    last_run: str | None = None

    with path.open("r", encoding="utf-8") as file:
        for line in file:
            text = line.strip()
            if not text:
                continue
            total += 1
            try:
                record = json.loads(text)
            except ValueError:
                errors += 1
                continue

            timestamp = record.get("timestamp")
            if isinstance(timestamp, str):
                if last_run is None or timestamp > last_run:
                    last_run = timestamp

            result = str(record.get("result") or "")
            if result == "OK":
                processed += 1
            if result.startswith("FAIL"):
                errors += 1

    return {
        "last_run": last_run,
        "processed": processed,
        "errors": errors,
        "total": total,
    }


def print_file_secretary(summary: dict[str, Any], use_color: bool) -> None:
    print("FILE SECRETARY")
    line = (
        "last_run={last_run} processed={processed} "
        "errors={errors} total={total}"
    ).format(
        last_run=summary.get("last_run") or "-",
        processed=summary.get("processed", 0),
        errors=summary.get("errors", 0),
        total=summary.get("total", 0),
    )
    tone = "ok" if int(summary.get("errors", 0)) == 0 else "warn"
    print(colorize(line, tone, use_color))
    print()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--ledger",
        default="config/services_ledger.yaml",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="enabled service に対して /health と /status を確認",
    )
    parser.add_argument(
        "--ci",
        action="store_true",
        help="GITHUB_TOKEN がある場合に CI 最新結果を表示",
    )
    parser.add_argument(
        "--repo",
        default=os.getenv("GITHUB_REPOSITORY", "MRL-mana/manaos-integrations"),
    )
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--timeout", type=float, default=2.5)
    parser.add_argument("--no-color", action="store_true")
    parser.add_argument(
        "--blast",
        action="store_true",
        help="--check と組み合わせ: DOWN サービスのブラスト半径を表示",
    )
    parser.add_argument(
        "--file-secretary-audit",
        default="logs/file_secretary_audit.jsonl",
    )
    args = parser.parse_args()

    try:
        ledger = load_ledger(args.ledger)
    except (OSError, ValueError, yaml.YAMLError) as exception:
        eprint(f"failed to load ledger: {exception}")
        return 1

    rows = normalize_rows(ledger)
    if args.check:
        rows = [probe_service(row, args.timeout) for row in rows]

    alerts = dependency_alerts(rows)

    ci_data: dict[str, Any] = {"status": "SKIP"}
    if args.ci:
        token = (os.getenv("GITHUB_TOKEN") or "").strip()
        if not token:
            ci_data = {"status": "SKIP", "reason": "GITHUB_TOKEN not set"}
        else:
            try:
                ci_data = fetch_latest_validate_ledger(args.repo, token)
            except (requests.RequestException, ValueError) as exception:
                ci_data = {"status": "ERROR", "reason": str(exception)}

    file_secretary_summary = load_file_secretary_summary(
        args.file_secretary_audit
    )

    payload = {
        "timestamp": dt.datetime.now().isoformat(timespec="seconds"),
        "ledger_version": ledger.get("version"),
        "rows": [row.__dict__ for row in rows],
        "dependency_alerts": alerts,
        "ci": ci_data,
        "file_secretary": file_secretary_summary,
    }

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    use_color = (not args.no_color) and sys.stdout.isatty()
    print_table(rows, use_color)

    print("DEPENDENCY ALERTS")
    if alerts:
        for alert in alerts:
            tone = "ok" if alert.endswith(": OK") else "warn"
            print(colorize(f"- {alert}", tone, use_color))
    else:
        print("(none)")
    print()

    if args.blast and args.check:
        print_blast_alerts(rows, use_color)
    elif args.blast and not args.check:
        use_color_local = (not args.no_color) and sys.stdout.isatty()
        print(colorize("[NOTE] --blast requires --check to be enabled (no probe = no blast data)", "warn", use_color_local))
        print()

    if args.ci:
        print_ci(ci_data, use_color)

    print_file_secretary(file_secretary_summary, use_color)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
