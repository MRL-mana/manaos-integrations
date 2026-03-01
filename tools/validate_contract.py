#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage2 response contract validation (non-blocking by default)."""

from __future__ import annotations

import argparse
import sys
import time
from typing import Any

import requests


def eprint(*args: Any) -> None:
    print(*args, file=sys.stderr)


def get_json(
    url: str,
    headers: dict[str, str],
    timeout: float,
) -> tuple[int, Any]:
    response = requests.get(url, headers=headers, timeout=timeout)
    status = response.status_code
    content_type = (response.headers.get("content-type") or "").lower()

    if "application/json" in content_type:
        try:
            return status, response.json()
        except ValueError:
            return status, {"_raw_text": response.text[:2000]}

    return status, {
        "_raw_text": response.text[:2000],
        "_content_type": content_type,
    }


def has_keys(
    obj: Any,
    keys: list[str],
    name: str,
    warnings: list[str],
) -> None:
    if not isinstance(obj, dict):
        warnings.append(
            f"{name}: expected object with keys {keys}, "
            f"got {type(obj).__name__}"
        )
        return
    for key in keys:
        if key not in obj:
            warnings.append(f"{name}: missing key '{key}'")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:9502")
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--timeout", type=float, default=3.0)
    parser.add_argument("--retries", type=int, default=10)
    parser.add_argument("--retry-wait", type=float, default=1.0)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="warningsを失敗扱いにする",
    )
    args = parser.parse_args()

    headers: dict[str, str] = (
        {"X-API-Key": args.api_key} if args.api_key else {}
    )

    checks: list[dict[str, Any]] = [
        {
            "name": "LLM models list",
            "path": "/api/llm/models",
            "expect_status": 200,
            "expect_type": list,
        },
        {
            "name": "Mothership resources",
            "path": "/api/mothership/resources",
            "expect_status": 200,
            "expect_type": (dict, list),
        },
        {
            "name": "File secretary inbox status",
            "path": "/api/file-secretary/inbox/status",
            "expect_status": 200,
            "expect_type": dict,
            "expect_keys": ["status"],
        },
    ]

    warnings: list[str] = []

    for check in checks:
        url = args.base_url.rstrip("/") + check["path"]
        passed_status = False
        last_status: int | None = None
        last_body: Any = None

        for _ in range(args.retries):
            try:
                status, body = get_json(
                    url,
                    headers=headers,
                    timeout=args.timeout,
                )
                last_status, last_body = status, body
                if status == check["expect_status"]:
                    passed_status = True
                    break
            except requests.RequestException as exception:
                last_status, last_body = None, {"_error": str(exception)}
            time.sleep(args.retry_wait)

        if not passed_status:
            warnings.append(
                f"{check['name']}: expected {check['expect_status']} "
                f"from {check['path']}, got {last_status}. "
                f"body={last_body}"
            )
            continue

        expected_type = check.get("expect_type")
        if expected_type:
            if isinstance(expected_type, tuple):
                if not isinstance(last_body, expected_type):
                    type_names = ", ".join(
                        type_item.__name__
                        for type_item in expected_type
                    )
                    warnings.append(
                        f"{check['name']}: expected type {type_names} "
                        f"got {type(last_body).__name__}"
                    )
            else:
                if not isinstance(last_body, expected_type):
                    warnings.append(
                        f"{check['name']}: expected type "
                        f"{expected_type.__name__} got "
                        f"{type(last_body).__name__}"
                    )

        if "expect_keys" in check:
            has_keys(last_body, check["expect_keys"], check["name"], warnings)

    print("Stage2 contract checks summary:")
    if warnings:
        print(f"⚠️ warnings: {len(warnings)}")
        for warning in warnings:
            print(" -", warning)
    else:
        print("✅ no warnings")

    if args.strict and warnings:
        eprint("❌ Strict mode: warnings found")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
