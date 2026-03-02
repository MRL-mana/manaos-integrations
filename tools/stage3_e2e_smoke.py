#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage3 lightweight E2E smoke (non-blocking by usage)."""

from __future__ import annotations

import argparse
import sys
import time
from typing import Any

import requests


def eprint(*args: Any) -> None:
    print(*args, file=sys.stderr)


def build_headers(api_key: str | None) -> dict[str, str]:
    if not api_key:
        return {}
    return {
        "X-API-Key": api_key,
        "Authorization": f"Bearer {api_key}",
    }


def get_json(
    base_url: str,
    path: str,
    headers: dict[str, str],
    timeout: float,
) -> tuple[int, Any]:
    response = requests.get(
        base_url.rstrip("/") + path,
        headers=headers,
        timeout=timeout,
    )
    content_type = (response.headers.get("content-type") or "").lower()
    if "application/json" not in content_type:
        return response.status_code, {
            "_raw_text": response.text[:2000],
            "_content_type": content_type,
        }
    try:
        return response.status_code, response.json()
    except ValueError:
        return response.status_code, {"_raw_text": response.text[:2000]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:9502")
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--timeout", type=float, default=5.0)
    args = parser.parse_args()

    headers = build_headers(args.api_key)

    checks: list[tuple[str, str, list[str]]] = [
        ("Unified health", "/health", ["status"]),
        ("Unified status", "/status", ["check_summary"]),
        ("OpenAPI", "/openapi.json", ["paths"]),
    ]

    warnings: list[str] = []
    started = time.perf_counter()

    for name, path, required_keys in checks:
        try:
            status, payload = get_json(
                args.base_url,
                path,
                headers,
                args.timeout,
            )
        except requests.RequestException as exception:
            warnings.append(f"{name}: request failed: {exception}")
            continue

        if status != 200:
            warnings.append(f"{name}: expected 200, got {status}")
            continue

        if not isinstance(payload, dict):
            warnings.append(
                f"{name}: expected JSON object, got {type(payload).__name__}"
            )
            continue

        for key in required_keys:
            if key not in payload:
                warnings.append(f"{name}: missing key '{key}'")

    elapsed_ms = (time.perf_counter() - started) * 1000
    print("Stage3 lightweight E2E summary:")
    print(f"elapsed_ms={elapsed_ms:.1f}")

    if warnings:
        print(f"⚠️ warnings: {len(warnings)}")
        for warning in warnings:
            print(" -", warning)
    else:
        print("✅ no warnings")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
