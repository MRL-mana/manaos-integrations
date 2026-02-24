from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from typing import Any

import yaml


def _http_status(method: str, url: str, timeout_s: float = 6.0, headers: dict[str, str] | None = None) -> dict[str, Any]:
    m = str(method or "GET").strip().upper() or "GET"
    h = {"User-Agent": "manaos-rpg-doctor/0.1"}
    if isinstance(headers, dict):
        for k, v in headers.items():
            if k and v:
                h[str(k)] = str(v)

    req = urllib.request.Request(url, method=m, headers=h)
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

    headers: dict[str, str] = {}
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

    limit = int(os.environ.get("MANAOS_RPG_DISABLE_404_LIMIT", "800") or 800)
    timeout_s = float(os.environ.get("MANAOS_RPG_DISABLE_404_TIMEOUT", "6") or 6)

    changed = 0
    checked = 0
    skipped = 0

    for r in rules:
        if checked >= limit:
            break
        if not isinstance(r, dict):
            continue
        if r.get("enabled") is False:
            continue

        method = str(r.get("method") or "GET").upper()
        p = str(r.get("path") or "")
        # NOTE: 安全第一。
        # - probe は常に GET（副作用回避）
        # - ただし POST-only endpoint を GET すると 404 になり得るため、
        #   「無効化の対象」は GET ルールのみに限定する。
        if method != "GET":
            skipped += 1
            continue

        if not p.startswith("/"):
            continue
        if "{" in p and "}" in p:
            skipped += 1
            continue

        # probe は GET のみ（副作用回避）。404 なら無効化。

        url = unified_base + p

        probe_method = "GET"
        st = _http_status(probe_method, url, timeout_s=timeout_s, headers=headers)
        status = int(st.get("status") or 0)

        checked += 1

        # 404 のみを自動無効化
        if status == 404:
            r["enabled"] = False
            changed += 1

    # 出力
    header = (
        "# Unified API Proxy allowlist (RPG backend)\n"
        "# AUTO-GENERATED from Unified /openapi.json\n"
        "#\n"
        "# gate:\n"
        "#   - read: 実行OK\n"
        "#   - write: MANAOS_RPG_ENABLE_UNIFIED_WRITE=1 が必要\n"
        "#   - danger: write + MANAOS_RPG_ENABLE_UNIFIED_DANGEROUS=1 が必要\n"
        "#\n"
        f"# doctor: auto-disabled 404 at {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        "\n"
    )

    out = {"rules": rules}
    body = yaml.safe_dump(out, sort_keys=False, allow_unicode=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(header)
        f.write(body)

    print(json.dumps({"checked": checked, "skipped": skipped, "disabled_404": changed}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
