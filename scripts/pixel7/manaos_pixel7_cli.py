#!/usr/bin/env python3
import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any, Dict, Optional


def _request_json(
    method: str,
    url: str,
    token: Optional[str],
    payload: Optional[Dict[str, Any]] = None,
    timeout: int = 10,
) -> Dict[str, Any]:
    data = None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    req = urllib.request.Request(url, method=method.upper(), data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8")
        if not body.strip():
            return {"ok": True}
        return json.loads(body)


def _print_json(obj: Dict[str, Any]) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def cmd_health(args: argparse.Namespace) -> int:
    url = args.base.rstrip("/") + "/health"
    try:
        data = _request_json("GET", url, token=None, timeout=args.timeout)
        _print_json(data)
        return 0
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}: {e.reason}", file=sys.stderr)
    except urllib.error.URLError as e:
        print(f"URL error: {e}", file=sys.stderr)
    return 1


def cmd_status(args: argparse.Namespace) -> int:
    token = args.token or os.getenv("PIXEL7_API_TOKEN", "").strip()
    if not token:
        print("PIXEL7_API_TOKEN が未設定です（--token か環境変数を指定）", file=sys.stderr)
        return 2

    url = args.base.rstrip("/") + "/api/status"
    try:
        data = _request_json("GET", url, token=token, timeout=args.timeout)
        _print_json(data)
        return 0
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore") if hasattr(e, "read") else ""
        print(f"HTTP {e.code}: {body or e.reason}", file=sys.stderr)
    except urllib.error.URLError as e:
        print(f"URL error: {e}", file=sys.stderr)
    return 1


def cmd_open_url(args: argparse.Namespace) -> int:
    token = args.token or os.getenv("PIXEL7_API_TOKEN", "").strip()
    if not token:
        print("PIXEL7_API_TOKEN が未設定です（--token か環境変数を指定）", file=sys.stderr)
        return 2

    url = args.base.rstrip("/") + "/api/open/url"
    try:
        data = _request_json(
            "POST",
            url,
            token=token,
            payload={"url": args.url},
            timeout=args.timeout,
        )
        _print_json(data)
        return 0 if data.get("ok", False) else 1
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore") if hasattr(e, "read") else ""
        print(f"HTTP {e.code}: {body or e.reason}", file=sys.stderr)
    except urllib.error.URLError as e:
        print(f"URL error: {e}", file=sys.stderr)
    return 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="ManaOS Pixel7 minimal CLI")
    p.add_argument(
        "--base",
        default=os.getenv("PIXEL7_API_BASE", "http://127.0.0.1:5122"),
        help="Pixel7 API base URL",
    )
    p.add_argument("--token", default=None, help="Bearer token (or use PIXEL7_API_TOKEN)")
    p.add_argument("--timeout", type=int, default=10, help="HTTP timeout seconds")

    sub = p.add_subparsers(dest="command", required=True)

    s_health = sub.add_parser("health", help="GET /health")
    s_health.set_defaults(func=cmd_health)

    s_status = sub.add_parser("status", help="GET /api/status (auth required)")
    s_status.set_defaults(func=cmd_status)

    s_open = sub.add_parser("open-url", help="POST /api/open/url (full profile required)")
    s_open.add_argument("url", help="URL to open on Pixel7")
    s_open.set_defaults(func=cmd_open_url)

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
