from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from typing import Any

import yaml


def _http_status(url: str, timeout_s: float, headers: dict[str, str]) -> dict[str, Any]:
    req = urllib.request.Request(url, method="GET", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            return {"ok": 200 <= int(resp.status) < 400, "status": int(resp.status)}
    except urllib.error.HTTPError as e:
        return {"ok": False, "status": int(getattr(e, "code", 0) or 0)}
    except Exception as e:
        return {"ok": False, "status": 0, "error": str(e)}


def main() -> int:
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    path = os.path.join(repo_root, "registry", "unified_proxy.yaml")

    unified_base = os.environ.get("MANAOS_UNIFIED_API_BASE", "http://127.0.0.1:9502").rstrip("/")
    api_key = (
        os.environ.get("MANAOS_UNIFIED_API_KEY")
        or os.environ.get("MANAOS_INTEGRATION_READONLY_API_KEY")
        or os.environ.get("MANAOS_INTEGRATION_OPS_API_KEY")
        or os.environ.get("MANAOS_INTEGRATION_API_KEY")
        or os.environ.get("API_KEY")
        or ""
    ).strip()

    headers: dict[str, str] = {"User-Agent": "manaos-rpg-enable/0.1"}
    if api_key:
        headers["X-API-Key"] = api_key

    if not os.path.exists(path):
        print(f"ERR: not found: {path}", file=sys.stderr)
        return 2

    doc = yaml.safe_load(open(path, "r", encoding="utf-8").read()) or {}
    rules = doc.get("rules") if isinstance(doc, dict) else None
    if not isinstance(rules, list):
        print("ERR: rules is not a list", file=sys.stderr)
        return 2

    limit = int(os.environ.get("MANAOS_RPG_ENABLE_READ_EXISTS_LIMIT", "400") or 400)
    timeout_s = float(os.environ.get("MANAOS_RPG_ENABLE_READ_EXISTS_TIMEOUT", "2.0") or 2.0)
    max_enable = int(os.environ.get("MANAOS_RPG_ENABLE_READ_EXISTS_MAX", "60") or 60)

    limit = max(1, min(limit, 2000))
    timeout_s = float(max(0.2, min(timeout_s, 8.0)))
    max_enable = max(1, min(max_enable, 500))

    checked = 0
    enabled = 0
    skipped = 0

    for r in rules:
        if checked >= limit or enabled >= max_enable:
            break
        if not isinstance(r, dict):
            continue

        if r.get("enabled") is not False:
            continue

        method = str(r.get("method") or "").upper()
        gate = str(r.get("gate") or "read").strip().lower() or "read"
        p = str(r.get("path") or "")

        if method != "GET" or gate != "read":
            skipped += 1
            continue
        if not p.startswith("/"):
            skipped += 1
            continue
        if "{" in p and "}" in p:
            skipped += 1
            continue

        url = unified_base + p
        st = _http_status(url, timeout_s=timeout_s, headers=headers)
        status = int(st.get("status") or 0)
        checked += 1

        # "exists" とみなすステータス（認証/405/422でも存在はする）
        if status in {200, 201, 202, 204, 400, 401, 403, 405, 422}:
            r["enabled"] = True
            enabled += 1

    header = (
        "# Unified API Proxy allowlist (RPG backend)\n"
        "# AUTO-GENERATED from Unified /openapi.json\n"
        "#\n"
        "# gate:\n"
        "#   - read: 実行OK\n"
        "#   - write: MANAOS_RPG_ENABLE_UNIFIED_WRITE=1 が必要\n"
        "#   - danger: write + MANAOS_RPG_ENABLE_UNIFIED_DANGEROUS=1 が必要\n"
        "#\n"
        f"# ops: auto-enabled read rules that exist at {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        "\n"
    )

    body = yaml.safe_dump({"rules": rules}, sort_keys=False, allow_unicode=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(header)
        f.write(body)

    print(json.dumps({"checked": checked, "skipped": skipped, "enabled": enabled}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
