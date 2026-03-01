#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stage2 response contract validation (minimal).

Current checks:
- GET /status must return JSON object with required keys (status 200)

Exit code:
0 = OK
1 = Validation failed
"""

from __future__ import annotations

import argparse
import sys
from typing import Any

import requests


def eprint(*args: Any) -> None:
    print(*args, file=sys.stderr)


def check_status_contract(base_url: str, api_key: str | None, timeout: float) -> list[str]:
    errors: list[str] = []
    url = f"{base_url.rstrip('/')}/status"
    headers = {"X-API-Key": api_key} if api_key else {}

    try:
        response = requests.get(url, headers=headers, timeout=timeout)
    except Exception as exception:
        return [f"request failed: {url}: {exception}"]

    if response.status_code != 200:
        return [f"unexpected status for {url}: {response.status_code}"]

    content_type = response.headers.get("content-type", "")
    if "application/json" not in content_type:
        errors.append(f"unexpected content-type for {url}: {content_type}")
        return errors

    try:
        payload = response.json()
    except Exception as exception:
        return [f"invalid json for {url}: {exception}"]

    if not isinstance(payload, dict):
        errors.append(f"contract mismatch for {url}: expected JSON object, got {type(payload).__name__}")
        return errors

    required_keys = ["status", "ready", "check_summary"]
    for key in required_keys:
        if key not in payload:
            errors.append(f"contract mismatch for {url}: missing key '{key}'")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:9502")
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--timeout", type=float, default=10.0)
    args = parser.parse_args()

    errors = check_status_contract(args.base_url, args.api_key, args.timeout)

    if errors:
        eprint("❌ Contract validation failed:")
        for error in errors:
            eprint(" -", error)
        return 1

    print("✅ Contract validation OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
