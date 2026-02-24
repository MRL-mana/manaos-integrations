from __future__ import annotations

import json
import os
import sys
import time
from typing import Any

import yaml


CORE_READ_PATHS = {
    "/health",
    "/api/llm/health",
    "/api/llm/models-enhanced",
    "/api/images/recent",
    "/api/comfyui/queue",
    "/api/comfyui/history",
    "/api/svi/queue",
    "/api/svi/history",
    "/api/ltx2/queue",
    "/api/ltx2/history",
}


def _as_bool(v: Any) -> bool:
    if v is None:
        return False
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return bool(int(v))
    if isinstance(v, str):
        s = v.strip().lower()
        if s in {"1", "true", "yes", "on"}:
            return True
        if s in {"0", "false", "no", "off"}:
            return False
    return False


def main() -> int:
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    path = os.path.join(repo_root, "registry", "unified_proxy.yaml")
    if not os.path.exists(path):
        print(f"ERR: not found: {path}", file=sys.stderr)
        return 2

    dry_run = _as_bool(os.environ.get("MANAOS_RPG_ENABLE_CORE_READ_DRYRUN"))

    try:
        doc = yaml.safe_load(open(path, "r", encoding="utf-8").read()) or {}
    except Exception as e:
        print(f"ERR: failed to read yaml: {e}", file=sys.stderr)
        return 2

    rules = doc.get("rules") if isinstance(doc, dict) else None
    if not isinstance(rules, list):
        print("ERR: rules is not a list", file=sys.stderr)
        return 2

    changed = 0
    matched = 0
    missing = []

    # Track which core paths we found
    found_paths: set[str] = set()

    for r in rules:
        if not isinstance(r, dict):
            continue
        method = str(r.get("method") or "").upper()
        gate = str(r.get("gate") or "read").strip().lower() or "read"
        p = str(r.get("path") or "")
        if method != "GET":
            continue
        if gate != "read":
            continue
        if p not in CORE_READ_PATHS:
            continue

        matched += 1
        found_paths.add(p)

        if r.get("enabled") is False:
            r["enabled"] = True
            changed += 1

        # Make sure timeouts are not absurdly low
        try:
            t = float(r.get("timeout_s") or 12)
        except Exception:
            t = 12.0
        if t < 3.0:
            r["timeout_s"] = 6
            changed += 1

    for p in sorted(CORE_READ_PATHS):
        if p not in found_paths:
            missing.append(p)

    if dry_run:
        print(
            json.dumps(
                {
                    "dry_run": True,
                    "matched": matched,
                    "changed": changed,
                    "missing_paths": missing,
                },
                ensure_ascii=False,
            )
        )
        return 0

    header = (
        "# Unified API Proxy allowlist (RPG backend)\n"
        "# AUTO-GENERATED from Unified /openapi.json\n"
        "#\n"
        "# gate:\n"
        "#   - read: 実行OK\n"
        "#   - write: MANAOS_RPG_ENABLE_UNIFIED_WRITE=1 が必要\n"
        "#   - danger: write + MANAOS_RPG_ENABLE_UNIFIED_DANGEROUS=1 が必要\n"
        "#\n"
        f"# ops: auto-enabled core read rules at {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        "\n"
    )

    body = yaml.safe_dump({"rules": rules}, sort_keys=False, allow_unicode=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(header)
        f.write(body)

    print(
        json.dumps(
            {
                "dry_run": False,
                "matched": matched,
                "changed": changed,
                "missing_paths": missing,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
