#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ManaOS 人格思想チェック（RPG監視 + 9502運用向け）。"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    print("Missing dependency: pyyaml. Install with: pip install pyyaml", file=sys.stderr)
    raise SystemExit(1)

try:
    import requests
except ImportError:
    requests = None


@dataclass
class CheckResult:
    principle_id: str
    check_id: str
    title: str
    automated: bool
    required: bool
    status: str  # pass/fail/manual/skipped
    detail: str


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _get_nested(obj: Any, dotted_key: str) -> Any:
    cur = obj
    for token in dotted_key.split("."):
        if isinstance(cur, dict) and token in cur:
            cur = cur[token]
        else:
            raise KeyError(dotted_key)
    return cur


def _fetch_json(
    url: str,
    timeout: float,
    cache: dict[str, tuple[int, Any]],
    headers: dict[str, str],
) -> tuple[int, Any]:
    cache_key = f"{url}|{headers.get('X-API-Key','')}"
    if cache_key in cache:
        return cache[cache_key]
    if requests is None:
        raise RuntimeError("requests module is not installed")
    response = requests.get(url, timeout=timeout, headers=headers)
    try:
        body = response.json()
    except Exception:
        body = {"_raw_text": response.text[:1000]}
    data = (response.status_code, body)
    cache[cache_key] = data
    return data


def _check_file_exists(check: dict[str, Any], repo_root: Path) -> tuple[bool, str]:
    rel = str(check.get("path") or "").strip()
    target = repo_root / rel
    ok = target.exists()
    return ok, f"path={rel} exists={ok}"


def _check_http_status(
    check: dict[str, Any],
    timeout: float,
    cache: dict[str, tuple[int, Any]],
    headers: dict[str, str],
) -> tuple[bool, str]:
    url = str(check.get("url") or "").strip()
    expected = int(check.get("expect_status", 200))
    status, _body = _fetch_json(url, timeout, cache, headers)
    ok = status == expected
    return ok, f"url={url} status={status} expect={expected}"


def _check_http_json_key_exists(
    check: dict[str, Any],
    timeout: float,
    cache: dict[str, tuple[int, Any]],
    headers: dict[str, str],
) -> tuple[bool, str]:
    url = str(check.get("url") or "").strip()
    key = str(check.get("key") or "").strip()
    status, body = _fetch_json(url, timeout, cache, headers)
    try:
        _value = _get_nested(body, key)
        return True, f"url={url} status={status} key={key} found"
    except KeyError:
        return False, f"url={url} status={status} key={key} missing"


def _check_http_json_equals(
    check: dict[str, Any],
    timeout: float,
    cache: dict[str, tuple[int, Any]],
    headers: dict[str, str],
) -> tuple[bool, str]:
    url = str(check.get("url") or "").strip()
    key = str(check.get("key") or "").strip()
    expected = check.get("expect")
    status, body = _fetch_json(url, timeout, cache, headers)
    try:
        value = _get_nested(body, key)
    except KeyError:
        return False, f"url={url} status={status} key={key} missing"
    ok = value == expected
    return ok, f"url={url} status={status} key={key} value={value!r} expect={expected!r}"


def _check_yaml_keys_present(check: dict[str, Any], repo_root: Path) -> tuple[bool, str]:
    rel = str(check.get("path") or "").strip()
    keys = check.get("keys") or []
    target = repo_root / rel
    if not target.exists():
        return False, f"path={rel} not found"
    data = _load_yaml(target)

    missing: list[str] = []
    for dotted in keys:
        try:
            _ = _get_nested(data, str(dotted))
        except KeyError:
            missing.append(str(dotted))
    ok = len(missing) == 0
    return ok, f"path={rel} missing={missing}"


def _check_yaml_optional_all_disabled(check: dict[str, Any], repo_root: Path) -> tuple[bool, str]:
    rel = str(check.get("path") or "").strip()
    target = repo_root / rel
    if not target.exists():
        return False, f"path={rel} not found"
    data = _load_yaml(target)
    optional = data.get("optional")
    if not isinstance(optional, dict):
        return False, "optional section missing or invalid"

    enabled_services: list[str] = []
    for name, config in optional.items():
        if isinstance(config, dict) and bool(config.get("enabled", False)):
            enabled_services.append(str(name))

    ok = len(enabled_services) == 0
    return ok, f"optional_enabled={enabled_services}"


def run_check(
    principle_id: str,
    check: dict[str, Any],
    repo_root: Path,
    timeout: float,
    cache: dict[str, tuple[int, Any]],
    headers: dict[str, str],
) -> CheckResult:
    check_id = str(check.get("id") or "unknown")
    title = str(check.get("title") or check_id)
    automated = bool(check.get("automated", False))
    required = bool(check.get("required", False))

    if not automated:
        return CheckResult(principle_id, check_id, title, automated, required, "manual", "manual check")

    check_type = str(check.get("type") or "").strip()
    try:
        if check_type == "file_exists":
            ok, detail = _check_file_exists(check, repo_root)
        elif check_type == "http_status":
            ok, detail = _check_http_status(check, timeout, cache, headers)
        elif check_type == "http_json_key_exists":
            ok, detail = _check_http_json_key_exists(check, timeout, cache, headers)
        elif check_type == "http_json_equals":
            ok, detail = _check_http_json_equals(check, timeout, cache, headers)
        elif check_type == "yaml_keys_present":
            ok, detail = _check_yaml_keys_present(check, repo_root)
        elif check_type == "yaml_optional_all_disabled":
            ok, detail = _check_yaml_optional_all_disabled(check, repo_root)
        else:
            return CheckResult(principle_id, check_id, title, automated, required, "skipped", f"unknown type: {check_type}")
    except Exception as ex:
        return CheckResult(principle_id, check_id, title, automated, required, "fail", f"exception: {ex}")

    return CheckResult(principle_id, check_id, title, automated, required, "pass" if ok else "fail", detail)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/personality_principles.yaml")
    parser.add_argument("--output", default="logs/personality_self_check.latest.json")
    parser.add_argument("--timeout", type=float, default=3.0)
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--strict", action="store_true", help="required の fail を終了コード1にする")
    parser.add_argument("--as-json", action="store_true")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    config_path = repo_root / args.config

    if not config_path.exists():
        print(f"config not found: {config_path}", file=sys.stderr)
        return 1

    config = _load_yaml(config_path)
    principles = config.get("principles") or []
    if not isinstance(principles, list):
        print("invalid config: principles must be list", file=sys.stderr)
        return 1

    cache: dict[str, tuple[int, Any]] = {}
    results: list[CheckResult] = []
    api_key = args.api_key or os.environ.get("MANAOS_API_KEY") or os.environ.get("UNIFIED_API_KEY")
    headers: dict[str, str] = {}
    if api_key:
        headers["X-API-Key"] = api_key
        headers["Authorization"] = f"Bearer {api_key}"

    for principle in principles:
        if not isinstance(principle, dict):
            continue
        pid = str(principle.get("id") or "unknown")
        checks = principle.get("checks") or []
        if not isinstance(checks, list):
            continue
        for check in checks:
            if not isinstance(check, dict):
                continue
            results.append(run_check(pid, check, repo_root, args.timeout, cache, headers))

    summary = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "profile": config.get("profile"),
        "mode": (config.get("modes") or {}).get("default", "safe"),
        "total": len(results),
        "pass": sum(1 for r in results if r.status == "pass"),
        "fail": sum(1 for r in results if r.status == "fail"),
        "manual": sum(1 for r in results if r.status == "manual"),
        "skipped": sum(1 for r in results if r.status == "skipped"),
    }

    report = {
        "summary": summary,
        "results": [
            {
                "principle_id": r.principle_id,
                "check_id": r.check_id,
                "title": r.title,
                "automated": r.automated,
                "required": r.required,
                "status": r.status,
                "detail": r.detail,
            }
            for r in results
        ],
    }

    out_path = repo_root / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.as_json:
        print(json.dumps(report, ensure_ascii=False))
    else:
        print("ManaOS Personality Self Check")
        print(f" profile: {summary['profile']} / mode: {summary['mode']}")
        print(
            f" total={summary['total']} pass={summary['pass']} fail={summary['fail']} "
            f"manual={summary['manual']} skipped={summary['skipped']}"
        )
        if summary["fail"] > 0:
            print(" failed checks:")
            for row in report["results"]:
                if row["status"] == "fail":
                    print(f"  - [{row['principle_id']}] {row['check_id']}: {row['detail']}")
        print(f" report: {out_path}")

    if args.strict:
        required_failed = any(r.status == "fail" and r.required for r in results)
        if required_failed:
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
