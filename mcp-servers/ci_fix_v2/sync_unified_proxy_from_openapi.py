from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.request
from typing import Any

try:
    import yaml  # type: ignore
except Exception:
    yaml = None  # type: ignore


def _fetch_json(url: str, timeout_s: float = 12.0) -> dict[str, Any]:
    req = urllib.request.Request(url, method="GET", headers={"User-Agent": "manaos-rpg-sync/0.1"})
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        body = resp.read(20 * 1024 * 1024)
        return json.loads(body.decode("utf-8", errors="replace"))


def _slugify(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "rule"


def _timeout_for(path: str) -> int:
    p = path.lower()
    if "generate" in p or "organize" in p:
        return 180
    if "upload" in p:
        return 120
    if "pdf" in p:
        return 300
    if "history" in p or "queue" in p:
        return 20
    return 12


def _gate_for(method: str, path: str) -> str:
    m = method.upper()
    p = path.lower()
    if "execute" in p or p.endswith("/exec") or "/ops/exec" in p:
        return "danger"
    if p.startswith("/api/dev/") and ("patch" in p or "deploy" in p):
        return "danger"
    if m == "GET":
        return "read"
    # POST
    if p in {"/api/memory/search", "/memory/search"}:
        return "read"  # 検索（非破壊）
    if p in {"/api/memory/write", "/memory/write"}:
        return "write"
    if p in {"/api/ops/notify", "/ops/notify"}:
        return "write"
    if p == "/api/llm/analyze":
        return "read"  # 非破壊
    return "write"


def _label_from_openapi_method_spec(method: str, path: str, method_spec: Any) -> str:
    # openapi 生成側の事情で dict ではなく文字列が入っていることがある
    # 例: "@{description=...; operationId=...; ...; summary=...}"
    default = f"{method.upper()} {path}"
    if isinstance(method_spec, dict):
        summary = method_spec.get("summary")
        if isinstance(summary, str) and summary.strip():
            return summary.strip()
        return default

    if isinstance(method_spec, str):
        m = re.search(r"summary=([^;}]*)", method_spec)
        if m:
            s = m.group(1).strip()
            if s:
                return s
        return default

    return default


def _extract_rules(openapi: dict[str, Any]) -> list[dict[str, Any]]:
    paths = openapi.get("paths")
    if not isinstance(paths, dict):
        return []

    rules: list[dict[str, Any]] = []

    for path, methods in paths.items():
        if not isinstance(path, str) or not path.startswith("/"):
            continue
        if not isinstance(methods, dict):
            continue

        for method_key, method_spec in methods.items():
            method = str(method_key).upper()
            if method not in {"GET", "POST"}:
                continue
            rid = _slugify(f"{method}_{path}")
            label = _label_from_openapi_method_spec(method, path, method_spec)
            gate = _gate_for(method, path)
            timeout_s = _timeout_for(path)
            enabled_default = False if gate == "danger" else True
            rules.append(
                {
                    "id": rid,
                    "label": label,
                    "method": method,
                    "path": path,
                    "gate": gate,
                    "enabled": enabled_default,
                    "timeout_s": timeout_s,
                }
            )

    # 安定ソート: path -> method
    rules.sort(key=lambda r: (str(r.get("path")), str(r.get("method"))))

    # id重複があれば連番
    seen: dict[str, int] = {}
    for r in rules:
        rid = str(r.get("id") or "rule")
        if rid not in seen:
            seen[rid] = 1
            continue
        seen[rid] += 1
        r["id"] = f"{rid}_{seen[rid]}"

    return rules


def _load_existing_rules(path: str) -> dict[tuple[str, str], dict[str, Any]]:
    if yaml is None:
        return {}
    if not os.path.exists(path):
        return {}
    try:
        data = yaml.safe_load(open(path, "r", encoding="utf-8").read()) or {}
    except Exception:
        return {}

    raw = data.get("rules") if isinstance(data, dict) else None
    if not isinstance(raw, list):
        return {}

    out: dict[tuple[str, str], dict[str, Any]] = {}
    for r in raw:
        if not isinstance(r, dict):
            continue
        method = str(r.get("method") or "").upper()
        p = str(r.get("path") or "")
        if method in {"GET", "POST"} and p.startswith("/"):
            out[(method, p)] = r
    return out


def _merge_rules(new_rules: list[dict[str, Any]], existing_by_key: dict[tuple[str, str], dict[str, Any]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    for r in new_rules:
        method = str(r.get("method") or "").upper()
        path = str(r.get("path") or "")
        ex = existing_by_key.get((method, path))
        if isinstance(ex, dict):
            # 手編集優先: id/label/gate/timeout_s を保持
            r = dict(r)

            # id/gate/enabled/timeout は常に既存優先
            for k in ("id", "gate", "enabled", "timeout_s"):
                if ex.get(k) is not None:
                    r[k] = ex.get(k)

            # label は「既存がデフォルト表示のまま」なら OpenAPI summary を優先
            default_label = f"{method} {path}".strip()
            ex_label = ex.get("label")
            if isinstance(ex_label, str) and ex_label.strip() and ex_label.strip() != default_label:
                r["label"] = ex_label
        merged.append(r)
    return merged


def main() -> int:
    if yaml is None:
        print("ERR: pyyaml is required", file=sys.stderr)
        return 2

    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    out_path = os.path.join(repo_root, "registry", "unified_proxy.yaml")

    unified_base = os.environ.get("MANAOS_UNIFIED_API_BASE", "http://127.0.0.1:9502").rstrip("/")
    openapi_url = f"{unified_base}/openapi.json"

    try:
        timeout_s = float(os.environ.get("MANAOS_RPG_PROXY_SYNC_TIMEOUT_S", "30") or 30)
    except Exception:
        timeout_s = 30.0
    timeout_s = float(max(5.0, min(timeout_s, 120.0)))

    print(f"[sync] fetching openapi: {openapi_url}")
    last_err: Exception | None = None
    spec: dict[str, Any] | None = None
    for attempt in range(1, 4):
        try:
            spec = _fetch_json(openapi_url, timeout_s=timeout_s)
            last_err = None
            break
        except Exception as e:
            last_err = e
            wait_s = min(2 * attempt, 6)
            print(f"[sync] WARN: openapi fetch failed (attempt={attempt}/3): {e} (sleep {wait_s}s)")
            time.sleep(wait_s)

    if spec is None:
        print(f"ERR: failed to fetch openapi.json after retries: {last_err}", file=sys.stderr)
        return 2

    new_rules = _extract_rules(spec)

    mode = str(os.environ.get("MANAOS_RPG_PROXY_SYNC_MODE", "merge")).strip().lower() or "merge"
    if mode not in {"merge", "overwrite"}:
        mode = "merge"

    if mode == "merge":
        existing = _load_existing_rules(out_path)
        rules = _merge_rules(new_rules, existing)
    else:
        rules = new_rules
    doc = {
        "rules": rules,
    }

    header = (
        "# Unified API Proxy allowlist (RPG backend)\n"
        "# AUTO-GENERATED from Unified /openapi.json\n"
        "#\n"
        "# gate:\n"
        "#   - read: 実行OK\n"
        "#   - write: MANAOS_RPG_ENABLE_UNIFIED_WRITE=1 が必要\n"
        "#   - danger: write + MANAOS_RPG_ENABLE_UNIFIED_DANGEROUS=1 が必要\n"
        "\n"
    )

    body = yaml.safe_dump(doc, sort_keys=False, allow_unicode=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(header)
        f.write(body)

    print(f"[sync] wrote {len(rules)} rules -> {out_path} (mode={mode})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
