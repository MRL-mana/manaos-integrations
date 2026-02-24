from __future__ import annotations

import hmac
import json
import os
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import yaml
from fastapi import FastAPI, Header, Depends
from fastapi import HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from collectors.events import append_event, tail_events
from collectors.host_stats import get_host_stats
from collectors.items_collector import resolve_item_roots, safe_resolve_under_root, scan_items
from collectors.ollama_runtime import get_ollama_ps_models
from collectors.services_runtime import compute_services_status

BASE = Path(__file__).resolve().parent
REG = BASE.parent / "registry"
REPO_ROOT = BASE.parent.parent
STORE = BASE / "storage"
STORE.mkdir(parents=True, exist_ok=True)

STATE_FILE = STORE / "state.json"
EVENTS_FILE = STORE / "events.log"

ACTION_LAST_FILE = STORE / "last_action.json"

UNIFIED_DOCTOR_CACHE_FILE = STORE / "unified_doctor_cache.json"
UNIFIED_DOCTOR_CACHE_TTL_S = 60

DEFAULT_UNIFIED_API_BASE = os.environ.get("MANAOS_UNIFIED_API_BASE", "http://127.0.0.1:9502").rstrip("/")
DEFAULT_OLLAMA_BASE = os.environ.get("MANAOS_OLLAMA_BASE", "http://127.0.0.1:11434").rstrip("/")

# --- Bearer token auth for write/action endpoints ---
_RPG_API_TOKEN = os.environ.get("MANAOS_RPG_API_TOKEN", "").strip()


def _require_token(authorization: str | None = Header(None)) -> None:
    """Validate Bearer token for dangerous endpoints.
    If MANAOS_RPG_API_TOKEN is unset, auth is skipped (localhost-only use)."""
    if not _RPG_API_TOKEN:
        return  # token not configured – skip auth (dev/localhost)
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Bearer token required")
    if not hmac.compare_digest(token, _RPG_API_TOKEN):
        raise HTTPException(status_code=403, detail="invalid token")


app = FastAPI(title="ManaOS RPG API", version="0.1")

_CORS_ORIGINS = [
    o.strip()
    for o in os.environ.get("MANAOS_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _unified_dangerous_enabled() -> bool:
    v = str(os.environ.get("MANAOS_RPG_ENABLE_UNIFIED_DANGEROUS", "0")).strip().lower()
    return v in {"1", "true", "yes", "on"}


def _load_unified_proxy_rules() -> list[dict[str, Any]]:
    y = load_yaml(REG / "unified_proxy.yaml")
    raw = y.get("rules") or []
    if not isinstance(raw, list):
        return []

    out: list[dict[str, Any]] = []
    for r in raw:
        if not isinstance(r, dict):
            continue
        rid = str(r.get("id") or "").strip()
        method = str(r.get("method") or "").strip().upper()
        path = str(r.get("path") or "").strip()
        if not rid or method not in {"GET", "POST"} or not path.startswith("/"):
            continue
        gate = str(r.get("gate") or "read").strip().lower() or "read"
        if gate not in {"read", "write", "danger"}:
            gate = "read"

        enabled_raw = r.get("enabled")
        if enabled_raw is None:
            enabled = True
        elif isinstance(enabled_raw, bool):
            enabled = enabled_raw
        elif isinstance(enabled_raw, (int, float)):
            enabled = bool(int(enabled_raw))
        elif isinstance(enabled_raw, str):
            v = enabled_raw.strip().lower()
            if v in {"0", "false", "no", "off"}:
                enabled = False
            elif v in {"1", "true", "yes", "on"}:
                enabled = True
            else:
                enabled = True
        else:
            enabled = True

        label = str(r.get("label") or rid).strip() or rid
        try:
            timeout_s = float(r.get("timeout_s") or 12)
        except Exception:
            timeout_s = 12.0
        timeout_s = float(max(1.0, min(timeout_s, 300.0)))

        out.append(
            {
                "id": rid,
                "label": label,
                "method": method,
                "path": path,
                "gate": gate,
                "enabled": enabled,
                "timeout_s": timeout_s,
            }
        )
    return out


def _actions_enabled() -> bool:
    v = str(os.environ.get("MANAOS_RPG_ENABLE_ACTIONS", "0")).strip().lower()
    return v in {"1", "true", "yes", "on"}


def _unified_write_enabled() -> bool:
    v = str(os.environ.get("MANAOS_RPG_ENABLE_UNIFIED_WRITE", "0")).strip().lower()
    return v in {"1", "true", "yes", "on"}


def _load_actions() -> list[dict[str, Any]]:
    actions_yaml = load_yaml(REG / "actions.yaml")
    raw = actions_yaml.get("actions") or []
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for a in raw:
        if isinstance(a, dict) and a.get("id"):
            out.append(a)
    return out


def _run_action(action: dict[str, Any]) -> dict[str, Any]:
    kind = str(action.get("kind") or "").strip()
    if kind != "pwsh_file":
        return {"ok": False, "error": f"unsupported kind: {kind}"}

    rel = str(action.get("path") or "").strip()
    if not rel:
        return {"ok": False, "error": "missing path"}

    # path は repo root 配下のみ許可
    script = safe_resolve_under_root(REPO_ROOT, rel)
    if script is None or (not script.exists()) or (not script.is_file()):
        return {"ok": False, "error": "script not found/forbidden"}

    timeout_sec = int(action.get("timeout_sec") or 60)
    timeout_sec = max(1, min(timeout_sec, 600))

    cwd_raw = str(action.get("cwd") or ".").strip() or "."
    cwd_path = safe_resolve_under_root(REPO_ROOT, cwd_raw) or REPO_ROOT

    cmd = [
        "pwsh",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script),
    ]

    args = action.get("args")
    if isinstance(args, list):
        for a in args:
            if a is None:
                continue
            cmd.append(str(a))

    try:
        completed = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            timeout=float(timeout_sec),
            cwd=str(cwd_path),
        )

        stdout = (completed.stdout or "").strip()[-20000:]
        stderr = (completed.stderr or "").strip()[-20000:]
        return {
            "ok": completed.returncode == 0,
            "exit_code": int(completed.returncode),
            "stdout": stdout,
            "stderr": stderr,
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _http_json_get(url: str, timeout_s: float = 5.0, headers: dict[str, str] | None = None) -> dict[str, Any]:
    h = {"User-Agent": "manaos-rpg/0.1"}
    if isinstance(headers, dict):
        for k, v in headers.items():
            if k and v:
                h[str(k)] = str(v)

    req = urllib.request.Request(url, method="GET", headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            body = resp.read(2 * 1024 * 1024)
            data = json.loads(body.decode("utf-8", errors="replace"))
            return {"ok": 200 <= int(resp.status) < 400, "status": int(resp.status), "data": data}
    except urllib.error.HTTPError as e:
        try:
            body = e.read(64 * 1024)
            text = body.decode("utf-8", errors="replace")
        except Exception:
            text = ""
        return {"ok": False, "status": int(getattr(e, "code", 0) or 0), "error": text[:2000]}
    except Exception as e:
        return {"ok": False, "status": 0, "error": str(e)}


def _unified_api_key() -> str:
    # 優先度: RPG専用 → 統合APIのread-only → ops → admin → 旧キー
    keys = [
        os.environ.get("MANAOS_UNIFIED_API_KEY"),
        os.environ.get("MANAOS_INTEGRATION_READONLY_API_KEY"),
        os.environ.get("MANAOS_INTEGRATION_OPS_API_KEY"),
        os.environ.get("MANAOS_INTEGRATION_API_KEY"),
        os.environ.get("API_KEY"),
    ]
    for k in keys:
        if k and str(k).strip():
            return str(k).strip()
    return ""


def get_unified_integrations_status() -> dict[str, Any]:
    # NOTE: Unified(9502) は MCP API Server として稼働しており、
    # /api/integrations/status は存在しない（404）。
    # ここでは「到達性/自己申告/公開OpenAPI」を使って状態を返す。

    api_key = _unified_api_key()
    headers: dict[str, str] = {}
    if api_key:
        headers["X-API-Key"] = api_key

    health_url = f"{DEFAULT_UNIFIED_API_BASE}/health"
    openapi_url = f"{DEFAULT_UNIFIED_API_BASE}/openapi.json"

    h = _http_json_get(health_url, timeout_s=8.0, headers=headers)
    o = _http_json_get(openapi_url, timeout_s=8.0, headers=headers)

    # openapi.json が取れているなら基盤としてはALIVE扱い（healthが遅い/一時失敗でも落とさない）
    ok = bool(o.get("ok"))

    openapi_summary: dict[str, Any] = {
        "ok": bool(o.get("ok")),
        "status": o.get("status"),
    }
    if o.get("ok") and isinstance(o.get("data"), dict):
        spec = o.get("data") or {}
        paths = spec.get("paths") if isinstance(spec.get("paths"), dict) else {}
        path_names = list(paths.keys()) if isinstance(paths, dict) else []

        # method summary（全量specをsnapshotに持たないため、カウントだけ計算）
        get_paths = []
        post_paths = []
        for p, ops in (paths or {}).items():
            if not isinstance(ops, dict):
                continue
            if isinstance(ops.get("get"), dict):
                get_paths.append(str(p))
            if isinstance(ops.get("post"), dict):
                post_paths.append(str(p))

        get_no_params = [p for p in get_paths if ("{" not in p and "}" not in p)]
        openapi_summary.update(
            {
                "title": spec.get("info", {}).get("title") if isinstance(spec.get("info"), dict) else None,
                "version": spec.get("info", {}).get("version") if isinstance(spec.get("info"), dict) else None,
                "paths_count": len(path_names),
                "paths_sample": sorted([str(p) for p in path_names])[:20],
                "get_paths_count": len(get_paths),
                "get_paths_no_params_count": len(get_no_params),
                "post_paths_count": len(post_paths),
            }
        )

    return {
        "ok": ok,
        "url": health_url,
        "status": h.get("status"),
        "auth_configured": bool(api_key),
        "data": {
            "health": h.get("data") if h.get("ok") else None,
            "openapi": openapi_summary,
        },
        "checks": {
            "health": {"url": health_url, "status": h.get("status"), "ok": bool(h.get("ok")), "error": h.get("error")},
            "openapi": {"url": openapi_url, "status": o.get("status"), "ok": bool(o.get("ok")), "error": o.get("error")},
        },
    }


def _unified_headers() -> dict[str, str]:
    api_key = _unified_api_key()
    if not api_key:
        return {}
    return {"X-API-Key": api_key}


def _load_unified_doctor_cache() -> dict[str, Any]:
    if not UNIFIED_DOCTOR_CACHE_FILE.exists():
        return {}
    try:
        return json.loads(UNIFIED_DOCTOR_CACHE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_unified_doctor_cache(data: dict[str, Any]) -> None:
    try:
        UNIFIED_DOCTOR_CACHE_FILE.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception:
        return


def _probe_unified_proxy_rules(
    *,
    limit: int = 60,
    include_disabled: bool = False,
    probe_timeout_s: float = 1.2,
    max_total_s: float = 3.0,
) -> dict[str, Any]:
    limit_i = max(1, min(int(limit), 500))
    rules_all = _load_unified_proxy_rules()
    rules = [r for r in rules_all if include_disabled or bool(r.get("enabled", True))][:limit_i]

    try:
        probe_timeout_s_f = float(probe_timeout_s)
    except Exception:
        probe_timeout_s_f = 1.2
    probe_timeout_s_f = float(max(0.2, min(probe_timeout_s_f, 6.0)))

    try:
        max_total_s_f = float(max_total_s)
    except Exception:
        max_total_s_f = 3.0
    max_total_s_f = float(max(0.5, min(max_total_s_f, 60.0)))

    started = time.monotonic()
    out: list[dict[str, Any]] = []

    counts = {
        "total": 0,
        "skipped": 0,
        "skipped_post": 0,
        "conn_error": 0,
        "auth": 0,
        "not_found_get": 0,
        "post_probe_unknown": 0,
    }

    for r in rules:
        if (time.monotonic() - started) > max_total_s_f:
            break

        rid = str(r.get("id"))
        enabled = bool(r.get("enabled", True))
        method = str(r.get("method") or "GET").upper()
        path = str(r.get("path") or "")
        gate = str(r.get("gate") or "read")

        counts["total"] += 1

        if method == "POST":
            # POST は副作用があり得るので probe しない。
            counts["skipped_post"] += 1
            counts["skipped"] += 1
            out.append(
                {
                    "id": rid,
                    "enabled": enabled,
                    "method": method,
                    "path": path,
                    "gate": gate,
                    "probe_method": None,
                    "status": None,
                    "exists": None,
                    "note": "post_probe_skipped",
                }
            )
            continue

        if "{" in path and "}" in path:
            counts["skipped"] += 1
            out.append(
                {
                    "id": rid,
                    "enabled": enabled,
                    "method": method,
                    "path": path,
                    "gate": gate,
                    "probe_method": "GET",
                    "status": None,
                    "exists": None,
                    "note": "needs_path_param",
                }
            )
            continue

        url = f"{DEFAULT_UNIFIED_API_BASE}{path}"
        st = _http_status("GET", url, timeout_s=probe_timeout_s_f, headers=_unified_headers())
        status = int(st.get("status") or 0)

        note = None
        exists: bool | None
        if status in {200, 201, 202, 204, 400, 401, 403, 405, 422}:
            exists = True
        elif status == 404 and method == "POST":
            exists = None
        else:
            exists = False

        if status == 0:
            note = "conn_error"
            counts["conn_error"] += 1
        elif status in {401, 403}:
            note = "auth"
            counts["auth"] += 1
        elif status == 404 and method == "GET":
            note = "not_found"
            counts["not_found_get"] += 1
        elif status == 404 and method == "POST":
            note = "probe_get_404_for_post (unknown)"
            counts["post_probe_unknown"] += 1
        elif status == 405:
            note = "method_not_allowed (exists)"

        recommend_action_id = None
        if enabled and status == 404 and method == "GET":
            recommend_action_id = "unified_proxy_disable_404"

        out.append(
            {
                "id": rid,
                "enabled": enabled,
                "method": method,
                "path": path,
                "gate": gate,
                "probe_method": "GET",
                "status": status,
                "exists": exists,
                "note": note,
                "recommend_action_id": recommend_action_id,
                "auth_configured": bool(_unified_api_key()),
            }
        )

    return {
        "ok": True,
        "ts": int(time.time()),
        "base": DEFAULT_UNIFIED_API_BASE,
        "probe_timeout_s": probe_timeout_s_f,
        "max_total_s": max_total_s_f,
        "count": len(out),
        "counts": counts,
        "results": out,
    }


def _maybe_refresh_unified_doctor_cache() -> dict[str, Any]:
    cache = _load_unified_doctor_cache()
    ts = int(cache.get("ts") or 0)
    if ts > 0 and (int(time.time()) - ts) < UNIFIED_DOCTOR_CACHE_TTL_S:
        return cache

    try:
        fresh = _probe_unified_proxy_rules(
            limit=60,
            include_disabled=False,
            probe_timeout_s=1.2,
            max_total_s=3.0,
        )
        _save_unified_doctor_cache(fresh)
        return fresh
    except Exception as e:
        # 失敗しても snapshot を落とさない（最後のキャッシュがあればそれを返す）
        cache["ok"] = False
        cache["error"] = str(e)
        return cache


def _append_next_action(next_actions: list[str], msg: str) -> None:
    m = str(msg or "").strip()
    if not m:
        return
    if m in next_actions:
        return
    next_actions.append(m)


def _append_next_action_hint(
    hints: list[dict[str, Any]],
    *,
    label: str,
    action_id: str | None = None,
) -> None:
    lab = str(label or "").strip()
    if not lab:
        return
    aid = str(action_id or "").strip() or None
    key = (lab, aid)
    for h in hints:
        if not isinstance(h, dict):
            continue
        if (str(h.get("label") or "").strip(), str(h.get("action_id") or "").strip() or None) == key:
            return
    payload: dict[str, Any] = {"label": lab}
    if aid:
        payload["action_id"] = aid
    hints.append(payload)


def _unified_get(path: str, timeout_s: float = 8.0) -> dict[str, Any]:
    path = str(path or "").strip()
    if not path.startswith("/"):
        path = "/" + path
    url = f"{DEFAULT_UNIFIED_API_BASE}{path}"
    r = _http_json_get(url, timeout_s=timeout_s, headers=_unified_headers())
    if not r.get("ok"):
        return {
            "ok": False,
            "url": url,
            "status": r.get("status"),
            "error": r.get("error"),
            "auth_configured": bool(_unified_api_key()),
        }
    return {
        "ok": True,
        "url": url,
        "status": r.get("status"),
        "auth_configured": bool(_unified_api_key()),
        "data": r.get("data"),
    }


def _unified_post(path: str, payload: dict[str, Any], timeout_s: float = 30.0) -> dict[str, Any]:
    path = str(path or "").strip()
    if not path.startswith("/"):
        path = "/" + path
    url = f"{DEFAULT_UNIFIED_API_BASE}{path}"
    r = _http_json_post(url, payload=payload, timeout_s=timeout_s, headers=_unified_headers())
    if not r.get("ok"):
        return {
            "ok": False,
            "url": url,
            "status": r.get("status"),
            "error": r.get("error"),
            "auth_configured": bool(_unified_api_key()),
        }
    return {
        "ok": True,
        "url": url,
        "status": r.get("status"),
        "auth_configured": bool(_unified_api_key()),
        "data": r.get("data"),
    }


def _http_json_post(
    url: str,
    payload: dict[str, Any],
    timeout_s: float = 30.0,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    h = {
        "Content-Type": "application/json; charset=utf-8",
        "User-Agent": "manaos-rpg/0.1",
    }
    if isinstance(headers, dict):
        for k, v in headers.items():
            if k and v:
                h[str(k)] = str(v)

    req = urllib.request.Request(url, method="POST", data=raw, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            body = resp.read(8 * 1024 * 1024)
            data = json.loads(body.decode("utf-8", errors="replace"))
            return {"ok": 200 <= int(resp.status) < 400, "status": int(resp.status), "data": data}
    except urllib.error.HTTPError as e:
        try:
            body = e.read(128 * 1024)
            text = body.decode("utf-8", errors="replace")
        except Exception:
            text = ""
        return {"ok": False, "status": int(getattr(e, "code", 0) or 0), "error": text[:4000]}
    except Exception as e:
        return {"ok": False, "status": 0, "error": str(e)}


def _http_status(method: str, url: str, timeout_s: float = 6.0, headers: dict[str, str] | None = None) -> dict[str, Any]:
    m = str(method or "GET").strip().upper() or "GET"
    h = {"User-Agent": "manaos-rpg/0.1"}
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


def _http_status_post_json(url: str, timeout_s: float = 6.0, headers: dict[str, str] | None = None) -> dict[str, Any]:
    raw = json.dumps({}, ensure_ascii=False).encode("utf-8")
    h = {
        "Content-Type": "application/json; charset=utf-8",
        "User-Agent": "manaos-rpg/0.1",
    }
    if isinstance(headers, dict):
        for k, v in headers.items():
            if k and v:
                h[str(k)] = str(v)

    req = urllib.request.Request(url, method="POST", headers=h, data=raw)
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            _ = resp.read(1024)
            return {"ok": 200 <= int(resp.status) < 400, "status": int(resp.status)}
    except urllib.error.HTTPError as e:
        return {"ok": False, "status": int(getattr(e, "code", 0) or 0)}
    except Exception as e:
        return {"ok": False, "status": 0, "error": str(e)}


def compute_danger(host: dict, services: list[dict]) -> int:
    danger = 0
    cpu = float(host.get("cpu", {}).get("percent") or 0)
    mem = float(host.get("mem", {}).get("percent") or 0)
    disk_free = float(host.get("disk", {}).get("free_gb") or 0)

    if cpu > 90:
        danger += 2
    if mem > 90:
        danger += 2
    if disk_free < 20:
        danger += 2

    nvidia = host.get("gpu", {}).get("nvidia") or []
    try:
        for g in nvidia:
            t = g.get("temperature_c")
            u = g.get("utilization_gpu")
            used = g.get("mem_used_mb")
            total = g.get("mem_total_mb")
            if t is not None and int(t) >= 85:
                danger += 2
            if u is not None and int(u) >= 95:
                danger += 1
            if used is not None and total is not None and int(total) > 0:
                vram_pct = int(round((int(used) / int(total)) * 100))
                if vram_pct >= 95:
                    danger += 2
                elif vram_pct >= 90:
                    danger += 1
    except Exception:
        pass

    always_on_down = any((not s.get("alive")) and ("always_on" in (s.get("tags") or [])) for s in services)
    if always_on_down:
        danger += 3

    # degraded / restart loop は運用的に危険度を上げる
    try:
        for s in services:
            tags = s.get("tags") or []
            if "always_on" not in tags:
                continue
            if s.get("degraded"):
                danger += 1
            if s.get("docker_health") == "unhealthy":
                danger += 2
            rc = s.get("restart_count")
            if isinstance(rc, int) and rc >= 5:
                danger += 1
            if isinstance(rc, int) and rc >= 10:
                danger += 1
    except Exception:
        pass

    return int(danger)


def snapshot() -> dict[str, Any]:
    services_yaml = load_yaml(REG / "services.yaml")
    models_yaml = load_yaml(REG / "models.yaml")
    menu_yaml = load_yaml(REG / "features.yaml")
    devices_yaml = load_yaml(REG / "devices.yaml")
    quests_yaml = load_yaml(REG / "quests.yaml")
    skills_yaml = load_yaml(REG / "skills.yaml")
    items_yaml = load_yaml(REG / "items.yaml")
    prompts_yaml = load_yaml(REG / "prompts.yaml")
    actions = _load_actions()

    services = list(services_yaml.get("services") or [])
    models = list(models_yaml.get("models") or [])
    menu = list(menu_yaml.get("menu") or [])
    devices = list(devices_yaml.get("devices") or [])
    quests = list(quests_yaml.get("quests") or [])
    skills = list(skills_yaml.get("skills") or [])

    prompts = prompts_yaml.get("prompts") or {}
    if not isinstance(prompts, dict):
        prompts = {}

    unified_proxy_rules = _load_unified_proxy_rules()

    item_roots = resolve_item_roots(REPO_ROOT, items_yaml)
    items_recent = scan_items(item_roots)

    host = get_host_stats()
    services_status = compute_services_status(services)
    danger = compute_danger(host, services_status)

    # Unified API の統合ステータスは、基盤がALIVEのときだけ取りに行く（落ちてる時は待たない）
    unified_alive = any(str(s.get("id")) == "unified_api_server" and bool(s.get("alive")) for s in services_status)
    if unified_alive:
        unified_integrations = get_unified_integrations_status()
    else:
        unified_integrations = {
            "ok": False,
            "url": f"{DEFAULT_UNIFIED_API_BASE}/api/integrations/status",
            "status": 0,
            "error": "unified_api_down",
            "auth_configured": bool(_unified_api_key()),
        }

    prev_state: dict[str, Any] = {}
    if STATE_FILE.exists():
        try:
            prev_state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            prev_state = {}

    prev_services = prev_state.get("services") or []
    prev_by_id: dict[str, dict[str, Any]] = {}
    if isinstance(prev_services, list):
        for ps in prev_services:
            sid = ps.get("id")
            if sid:
                prev_by_id[str(sid)] = ps

    alive_map = {str(s.get("id")): bool(s.get("alive")) for s in services_status}
    for s in services_status:
        sid = str(s.get("id"))
        deps = list(s.get("depends_on") or [])
        deps_down = [d for d in deps if not alive_map.get(str(d), False)]
        s["deps_down"] = deps_down
        s["blocked"] = len(deps_down) > 0

        # blocked 状態変化イベント
        prev_blocked = bool((prev_by_id.get(sid) or {}).get("blocked"))
        now_blocked = bool(s.get("blocked"))
        if now_blocked and not prev_blocked:
            append_event(EVENTS_FILE, "blocked", "依存関係によりブロックされました", {"service": sid, "deps_down": deps_down})
        if (not now_blocked) and prev_blocked:
            append_event(EVENTS_FILE, "unblocked", "ブロックが解除されました", {"service": sid})

        # docker health 変化イベント
        prev_health = (prev_by_id.get(sid) or {}).get("docker_health")
        now_health = s.get("docker_health")
        if now_health and now_health != prev_health:
            if now_health == "unhealthy":
                append_event(EVENTS_FILE, "unhealthy", "Docker health が UNHEALTHY になりました", {"service": sid})
            if prev_health == "unhealthy" and now_health == "healthy":
                append_event(EVENTS_FILE, "healthy", "Docker health が HEALTHY に復帰しました", {"service": sid})

        # restart_count 増加イベント（docker/pm2共通）
        prev_rc = (prev_by_id.get(sid) or {}).get("restart_count")
        now_rc = s.get("restart_count")
        if isinstance(now_rc, int):
            try:
                prev_rc_int = int(prev_rc) if prev_rc is not None else None
            except Exception:
                prev_rc_int = None

            if prev_rc_int is not None and now_rc > prev_rc_int:
                delta = now_rc - prev_rc_int
                append_event(
                    EVENTS_FILE,
                    "restart_increase",
                    "再起動回数が増加しました（ループ兆候）",
                    {"service": sid, "restart_count": now_rc, "delta": delta},
                )

    # モデル: Ollamaのロード状況（指定があれば）
    ollama_loaded = set(get_ollama_ps_models())
    models_enriched: list[dict[str, Any]] = []
    for m in models:
        m2 = dict(m)
        key = None
        if isinstance(m.get("ollama"), str):
            key = m.get("ollama")
        runtime = m.get("runtime")
        if key is None and isinstance(runtime, dict) and isinstance(runtime.get("ollama"), str):
            key = runtime.get("ollama")
        if key:
            m2["loaded"] = key in ollama_loaded
        models_enriched.append(m2)

    next_actions: list[str] = []
    disk_free = float(host.get("disk", {}).get("free_gb") or 0)
    if disk_free and disk_free < 50:
        next_actions.append("空き容量が少なめ：古いログ/モデル/生成物の退避や削除")
    cpu = float(host.get("cpu", {}).get("percent") or 0)
    if cpu > 90:
        next_actions.append("CPU高負荷：重い処理を止める/再起動/並列数を下げる")
    mem = float(host.get("mem", {}).get("percent") or 0)
    if mem > 90:
        next_actions.append("RAM逼迫：常駐を減らす/キャッシュを削る/再起動")
    try:
        for g in (host.get("gpu", {}).get("nvidia") or []):
            t = g.get("temperature_c")
            u = g.get("utilization_gpu")
            used = g.get("mem_used_mb")
            total = g.get("mem_total_mb")
            power = g.get("power_draw_w")
            if t is not None and int(t) >= 85:
                next_actions.append("GPU温度高い：生成を止める/冷却強化/ファン確認")
                break
            if u is not None and int(u) >= 98:
                next_actions.append("GPU使用率ほぼ100%：キュー詰まりなら停止/再起動を検討")
                # 継続してVRAMも見る
            if used is not None and total is not None and int(total) > 0:
                vram_pct = int(round((int(used) / int(total)) * 100))
                if vram_pct >= 95:
                    next_actions.append("VRAM逼迫（95%+）：モデル/生成を止める、不要プロセス終了")
                    break
                if vram_pct >= 90:
                    next_actions.append("VRAM高め（90%+）：キューや常駐を整理")
            if power is not None and int(power) >= 300:
                next_actions.append("GPU電力高め：負荷が常時高いなら生成/学習の見直し")
                break
    except Exception:
        pass

    # GPU犯人リスト（上位）
    apps = host.get("gpu", {}).get("apps") or []
    if isinstance(apps, list) and apps:
        top = apps[:5]
        offenders = []
        for a in top:
            nm = a.get("process_name")
            pid = a.get("pid")
            mb = a.get("used_gpu_memory_mb")
            if mb is None:
                continue
            offenders.append(f"{nm}(pid={pid})={mb}MB")
        if offenders:
            next_actions.append("VRAM犯人: " + "; ".join(offenders))

    always_on_down = [s.get("id") for s in services_status if (not s.get("alive")) and ("always_on" in (s.get("tags") or []))]
    if always_on_down:
        next_actions.append(f"常駐が落ちてる：{', '.join([str(x) for x in always_on_down])} を復旧")

    next_action_hints: list[dict[str, Any]] = []

    # always_on の degraded / unhealthy / restart loop
    unhealthy = [
        str(s.get("id"))
        for s in services_status
        if ("always_on" in (s.get("tags") or [])) and (s.get("docker_health") == "unhealthy")
    ]
    if unhealthy:
        next_actions.append(f"UNHEALTHY：{', '.join(unhealthy)} の依存先/ヘルスURL/ログ確認")

    restart_loop = [
        str(s.get("id"))
        for s in services_status
        if ("always_on" in (s.get("tags") or [])) and isinstance(s.get("restart_count"), int) and int(s.get("restart_count")) >= 5
    ]
    if restart_loop:
        next_actions.append(f"再起動多い：{', '.join(restart_loop)}（設定変更/依存/ログを確認）")

    blocked_svcs = [str(s.get("id")) for s in services_status if bool(s.get("blocked"))]
    if blocked_svcs:
        next_actions.append(f"blocked解除：依存サービスを先に復旧 → {', '.join(blocked_svcs)} を再確認")

    # Unified Doctor (cached): 可視化→提案（ワンクリック実行の前段）
    if unified_alive:
        d = _maybe_refresh_unified_doctor_cache()
        counts = d.get("counts") if isinstance(d, dict) else None
        d_results = d.get("results") if isinstance(d, dict) else None
        if not isinstance(d_results, list):
            d_results = []

        has_enabled_get_rule = any(
            isinstance(r, dict)
            and bool(r.get("enabled", True))
            and str(r.get("method") or "GET").upper() == "GET"
            and isinstance(r.get("path"), str)
            and ("{" not in str(r.get("path")))
            for r in unified_proxy_rules
        )

        # recommend から action hint を作る（counts頼みの誤提案を減らす）
        if any(
            isinstance(r, dict) and str(r.get("recommend_action_id") or "") == "unified_proxy_disable_404"
            for r in d_results
        ):
            _append_next_action_hint(
                next_action_hints,
                label="実行：Unified allowlist 404自動無効化（台帳掃除 / GETのみ）",
                action_id="unified_proxy_disable_404",
            )

        if isinstance(counts, dict):
            try:
                total = int(counts.get("total") or 0)
            except Exception:
                total = 0
            try:
                skipped = int(counts.get("skipped") or 0)
            except Exception:
                skipped = 0
            try:
                not_found_get = int(counts.get("not_found_get") or 0)
            except Exception:
                not_found_get = 0
            try:
                conn_err = int(counts.get("conn_error") or 0)
            except Exception:
                conn_err = 0
            try:
                auth_cnt = int(counts.get("auth") or 0)
            except Exception:
                auth_cnt = 0

            # conn_error（到達不能）時は実行系を出しても効かないので、まず到達性の提案に寄せる
            can_act_on_unified = conn_err == 0

            openapi_paths_count = None
            if isinstance(unified_integrations, dict):
                od = unified_integrations.get("data") if isinstance(unified_integrations.get("data"), dict) else {}
                oo = od.get("openapi") if isinstance(od.get("openapi"), dict) else {}
                pc = oo.get("paths_count")
                if isinstance(pc, int):
                    openapi_paths_count = pc
                else:
                    try:
                        openapi_paths_count = int(pc) if pc is not None else None
                    except Exception:
                        openapi_paths_count = None

            rules_count = len(unified_proxy_rules)
            sync_likely_useful = (
                total == 0
                or not_found_get >= 1
                or (isinstance(openapi_paths_count, int) and openapi_paths_count >= 1 and rules_count < openapi_paths_count)
            )

            # 同期ボタンは「同期が効きそう」なときだけ出す（OpenAPIと台帳が揃っているなら不要）
            if can_act_on_unified and sync_likely_useful:
                _append_next_action_hint(
                    next_action_hints,
                    label="実行：Unified allowlist 同期（OpenAPI→unified_proxy.yaml）",
                    action_id="unified_proxy_sync",
                )

            # 到達性
            if conn_err >= 8:
                _append_next_action(
                    next_actions,
                    "Unified API到達エラー多数：unified_api_server(9502) の起動/復旧を確認",
                )

            # 有効ルールが probe 不可（POST-only/パスパラメータ必須）だけだと、自動提案材料が取れない
            if total >= 1 and skipped >= total:
                if int(counts.get("skipped_post") or 0) >= 1:
                    _append_next_action(
                        next_actions,
                        "Unified allowlist が POST中心のため安全probeができない：OpenAPI/実行結果ベースで運用（必要ならinclude_disabledで一覧確認）",
                    )
                    if can_act_on_unified and (not has_enabled_get_rule):
                        # OpenAPI上に「GET（パスパラメータ無し）」が1つも無い場合、このアクションは効かないので提案しない
                        get_no_params_cnt = None
                        if isinstance(unified_integrations, dict):
                            od2 = unified_integrations.get("data") if isinstance(unified_integrations.get("data"), dict) else {}
                            oo2 = od2.get("openapi") if isinstance(od2.get("openapi"), dict) else {}
                            get_no_params_cnt = oo2.get("get_paths_no_params_count")
                        try:
                            get_no_params_cnt_i = int(get_no_params_cnt) if get_no_params_cnt is not None else 0
                        except Exception:
                            get_no_params_cnt_i = 0

                        if get_no_params_cnt_i >= 1:
                            _append_next_action_hint(
                                next_action_hints,
                                label="実行：Unified allowlist コアread有効化（安全なGETのみ）",
                                action_id="unified_proxy_enable_core_read",
                            )
                else:
                    _append_next_action(
                        next_actions,
                        "Unified allowlistの有効ルールが少ない/パスパラメータ必須のみ：『Proxy Doctor（include_disabled=true）』で確認→同期/有効化を検討",
                    )

            # 認証
            if auth_cnt >= 1 and not bool(_unified_api_key()):
                _append_next_action(
                    next_actions,
                    "Unified API認証が必要：環境変数 MANAOS_UNIFIED_API_KEY（read-only可）を設定",
                )

            # GET 404 のみを「台帳掃除」対象にする（POST-only 誤爆を避ける）
            if not_found_get >= 1:
                _append_next_action(
                    next_actions,
                    "Unified allowlistにGET 404が残存：クエスト『Unified allowlist 404自動無効化（台帳掃除）』を実行",
                )

    # 戦闘ログ: always_on の DOWN/RECOVER を「変化時だけ」記録
    down_now = [
        str(s.get("id"))
        for s in services_status
        if (not s.get("alive")) and ("always_on" in (s.get("tags") or []))
    ]
    down_prev: list[str] = list(prev_state.get("always_on_down") or [])

    newly_down = sorted(list(set(down_now) - set(down_prev)))
    recovered = sorted(list(set(down_prev) - set(down_now)))
    if newly_down:
        append_event(EVENTS_FILE, "service_down", "always_on が停止しました", {"services": newly_down})
    if recovered:
        append_event(EVENTS_FILE, "service_recovered", "always_on が復旧しました", {"services": recovered})

    return {
        "ts": int(time.time()),
        "menu": menu,
        "host": host,
        "services": services_status,
        "unified": {
            "base": DEFAULT_UNIFIED_API_BASE,
            "integrations": unified_integrations,
            "proxy": {
                "enabled": True,
                "rules": unified_proxy_rules,
                "write_enabled": _unified_write_enabled(),
                "dangerous_enabled": _unified_dangerous_enabled(),
            },
        },
        "models": models_enriched,
        "devices": devices,
        "quests": quests,
        "skills": skills,
        "prompts": prompts,
        "items": {
            "roots": [{"id": r.id, "label": r.label} for r in item_roots],
            "recent": items_recent,
        },
        "actions": [{"id": a.get("id"), "label": a.get("label"), "tags": a.get("tags") or []} for a in actions],
        "actions_enabled": _actions_enabled(),
        "danger": danger,
        "next_actions": next_actions,
        "next_action_hints": next_action_hints,
        "always_on_down": down_now,
    }


@app.get("/health")
def health() -> dict[str, Any]:
    return {"ok": True, "ts": int(time.time())}


@app.get("/api/snapshot")
def api_snapshot() -> dict[str, Any]:
    data = snapshot()
    STATE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data


@app.get("/api/state")
def api_state() -> dict[str, Any]:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"error": "no state yet. call /api/snapshot first."}


@app.get("/api/events")
def api_events(limit: int = 100) -> dict[str, Any]:
    limit = max(1, min(int(limit), 1000))
    return {"events": tail_events(EVENTS_FILE, limit=limit)}


@app.get("/api/registry")
def api_registry() -> dict[str, Any]:
    return {
        "services": load_yaml(REG / "services.yaml").get("services") or [],
        "models": load_yaml(REG / "models.yaml").get("models") or [],
        "menu": load_yaml(REG / "features.yaml").get("menu") or [],
        "devices": load_yaml(REG / "devices.yaml").get("devices") or [],
        "quests": load_yaml(REG / "quests.yaml").get("quests") or [],
        "skills": load_yaml(REG / "skills.yaml").get("skills") or [],
        "items": load_yaml(REG / "items.yaml").get("items") or [],
        "prompts": load_yaml(REG / "prompts.yaml").get("prompts") or {},
        "actions": load_yaml(REG / "actions.yaml").get("actions") or [],
        "unified_proxy": load_yaml(REG / "unified_proxy.yaml").get("rules") or [],
    }


@app.post("/api/unified/proxy/run", dependencies=[Depends(_require_token)])
def api_unified_proxy_run(body: dict[str, Any]) -> dict[str, Any]:
    payload = _validate_proxy_body(body)
    rid = str(payload.get("id") or "").strip()
    if not rid:
        raise HTTPException(status_code=400, detail="id is required")

    rules = _load_unified_proxy_rules()
    rule = next((r for r in rules if str(r.get("id")) == rid), None)
    if rule is None:
        raise HTTPException(status_code=404, detail="unknown proxy id")

    if not bool(rule.get("enabled", True)):
        raise HTTPException(status_code=403, detail="proxy rule disabled")

    gate = str(rule.get("gate") or "read")
    if gate == "write":
        _require_unified_write()
    if gate == "danger":
        _require_unified_write()
        if not _unified_dangerous_enabled():
            raise HTTPException(
                status_code=403,
                detail="dangerous unified ops disabled. set MANAOS_RPG_ENABLE_UNIFIED_DANGEROUS=1",
            )

    method = str(rule.get("method") or "GET").upper()
    path = str(rule.get("path") or "").strip()
    timeout_s = float(rule.get("timeout_s") or 12.0)

    q = payload.get("query")
    if q is None:
        q = {}
    if not isinstance(q, dict):
        raise HTTPException(status_code=400, detail="query must be an object")

    # {job_id} などの path param を埋める（queryから取って消す）
    if "{" in path and "}" in path:
        for k, v in list(q.items()):
            token = "{" + str(k) + "}"
            if token in path:
                path = path.replace(token, urllib.parse.quote(str(v), safe=""))
                q.pop(k, None)

    if q:
        qs = urllib.parse.urlencode({str(k): str(v) for k, v in q.items()})
        if "?" in path:
            path = path + "&" + qs
        else:
            path = path + "?" + qs

    if method == "GET":
        return _unified_get(path, timeout_s=timeout_s)

    if method == "POST":
        b = payload.get("body")
        if b is None:
            b = {}
        if not isinstance(b, dict):
            raise HTTPException(status_code=400, detail="body must be an object")
        b2 = _expand_item_uris(b)
        return _unified_post(path, payload=b2, timeout_s=timeout_s)

    raise HTTPException(status_code=400, detail="unsupported method")


@app.get("/api/unified/proxy/doctor")
def api_unified_proxy_doctor(
    limit: int = 80,
    include_disabled: bool = True,
    probe_timeout_s: float = 1.5,
    max_total_s: float = 8.0,
) -> dict[str, Any]:
    # allowlist の死活を軽量に確認する
    # - 副作用防止のため、probe は常に GET（405 を「存在」とみなす）
    # - path param が必要なものはスキップ
    limit_i = max(1, min(int(limit), 500))
    rules_all = _load_unified_proxy_rules()
    rules = [r for r in rules_all if include_disabled or bool(r.get("enabled", True))][:limit_i]

    try:
        probe_timeout_s_f = float(probe_timeout_s)
    except Exception:
        probe_timeout_s_f = 1.5
    probe_timeout_s_f = float(max(0.2, min(probe_timeout_s_f, 6.0)))

    try:
        max_total_s_f = float(max_total_s)
    except Exception:
        max_total_s_f = 8.0
    max_total_s_f = float(max(1.0, min(max_total_s_f, 60.0)))

    started = time.monotonic()

    out: list[dict[str, Any]] = []
    for r in rules:
        if (time.monotonic() - started) > max_total_s_f:
            break

        rid = str(r.get("id"))
        enabled = bool(r.get("enabled", True))
        method = str(r.get("method") or "GET").upper()
        path = str(r.get("path") or "")
        gate = str(r.get("gate") or "read")
        timeout_s = probe_timeout_s_f

        if "{" in path and "}" in path:
            out.append(
                {
                    "id": rid,
                    "enabled": enabled,
                    "method": method,
                    "path": path,
                    "gate": gate,
                    "probe_method": "GET",
                    "status": None,
                    "ok": False,
                    "note": "needs_path_param",
                }
            )
            continue

        url = f"{DEFAULT_UNIFIED_API_BASE}{path}"
        probe_method = "GET"
        st = _http_status(probe_method, url, timeout_s=timeout_s, headers=_unified_headers())

        status = int(st.get("status") or 0)
        err_raw = st.get("error")
        err_s = None
        if isinstance(err_raw, str) and err_raw.strip():
            err_s = err_raw.strip()[:300]
        note = None
        if status == 405:
            note = "method_not_allowed (exists)"
        if status in {401, 403}:
            note = "auth"
        if status == 404:
            if method == "POST":
                # POST-only endpoint を GET で probe すると 404 になり得る。
                # ここでは「存在しない」と断定しない。
                note = "probe_get_404_for_post (unknown)"
            else:
                note = "not_found"
        if status == 0 and err_s:
            note = "conn_error"

        recommend = None
        recommend_action_id = None
        if enabled and status == 404 and method != "POST":
            # 典型: Unified側に未実装/廃止されたパスが allowlist に残っている
            # 対処は「allowlist再同期」または「404を無効化」
            recommend = "run_unified_proxy_disable_404"
            recommend_action_id = "unified_proxy_disable_404"

        # 404 以外は「存在している可能性が高い」とみなす（認証やmethod違いでもOK）
        exists: bool | None
        if status in {200, 201, 202, 204, 400, 401, 403, 405, 422}:
            exists = True
        elif status == 404 and method == "POST":
            exists = None
        else:
            exists = False

        out.append(
            {
                "id": rid,
                "enabled": enabled,
                "method": method,
                "path": path,
                "gate": gate,
                "probe_method": probe_method,
                "status": status,
                "ok": bool(st.get("ok")) or status in {400, 401, 403, 405, 422},
                "exists": exists,
                "note": note,
                "error": err_s,
                "recommend": recommend,
                "recommend_action_id": recommend_action_id,
                "auth_configured": bool(_unified_api_key()),
            }
        )

    return {
        "ok": True,
        "base": DEFAULT_UNIFIED_API_BASE,
        "truncated": len(out) < len(rules),
        "max_total_s": max_total_s_f,
        "probe_timeout_s": probe_timeout_s_f,
        "count": len(out),
        "results": out,
    }


@app.get("/api/actions")
def api_actions() -> dict[str, Any]:
    actions = _load_actions()
    return {
        "enabled": _actions_enabled(),
        "actions": [
            {"id": a.get("id"), "label": a.get("label"), "kind": a.get("kind"), "tags": a.get("tags") or []}
            for a in actions
        ],
    }


@app.post("/api/actions/{action_id}/run", dependencies=[Depends(_require_token)])
def api_run_action(action_id: str) -> dict[str, Any]:
    if not _actions_enabled():
        raise HTTPException(status_code=403, detail="actions disabled. set MANAOS_RPG_ENABLE_ACTIONS=1")

    actions = _load_actions()
    action = next((a for a in actions if str(a.get("id")) == action_id), None)
    if action is None:
        raise HTTPException(status_code=404, detail="unknown action")

    started = int(time.time())
    result = _run_action(action)
    ended = int(time.time())

    payload = {
        "ts": ended,
        "action_id": action_id,
        "label": action.get("label"),
        "result": result,
        "duration_sec": max(0, ended - started),
    }
    ACTION_LAST_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    append_event(
        EVENTS_FILE,
        "action_run",
        f"action {action_id} {'OK' if result.get('ok') else 'NG'}",
        {"action_id": action_id, "ok": bool(result.get('ok')), "exit_code": result.get('exit_code')},
    )
    return payload


@app.get("/api/actions/last")
def api_last_action() -> dict[str, Any]:
    if ACTION_LAST_FILE.exists():
        return json.loads(ACTION_LAST_FILE.read_text(encoding="utf-8"))
    return {"error": "no action run yet"}


@app.get("/api/ollama/tags")
def api_ollama_tags() -> dict[str, Any]:
    url = f"{DEFAULT_OLLAMA_BASE}/api/tags"
    r = _http_json_get(url, timeout_s=5.0)
    if not r.get("ok"):
        return {"ok": False, "url": url, "status": r.get("status"), "error": r.get("error")}
    return {"ok": True, "url": url, "data": r.get("data")}


@app.post("/api/ollama/generate", dependencies=[Depends(_require_token)])
def api_ollama_generate(body: dict[str, Any]) -> dict[str, Any]:
    model = str(body.get("model") or "").strip()
    prompt = str(body.get("prompt") or "").strip()
    if not model:
        raise HTTPException(status_code=400, detail="model is required")
    if not prompt:
        raise HTTPException(status_code=400, detail="prompt is required")

    url = f"{DEFAULT_OLLAMA_BASE}/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
    }
    r = _http_json_post(url, payload=payload, timeout_s=120.0)
    if not r.get("ok"):
        return {"ok": False, "url": url, "status": r.get("status"), "error": r.get("error")}

    data = r.get("data") or {}
    text = str(data.get("response") or "")
    append_event(EVENTS_FILE, "ollama_generate", "Ollama generate", {"model": model, "chars": len(text)})
    return {"ok": True, "url": url, "model": model, "response": text, "raw": data}


@app.post("/api/generate/image", dependencies=[Depends(_require_token)])
def api_generate_image(body: dict[str, Any]) -> dict[str, Any]:
    # Unified API の comfyui/generate に投げる（ダッシュボード側は“操作入口”に徹する）
    prompt = str(body.get("prompt") or "").strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="prompt is required")

    width = int(body.get("width") or 768)
    height = int(body.get("height") or 768)
    steps = int(body.get("steps") or 20)
    negative = str(body.get("negative_prompt") or "")

    payload = {
        "prompt": prompt,
        "width": max(64, min(width, 2048)),
        "height": max(64, min(height, 2048)),
        "steps": max(1, min(steps, 80)),
        "negative_prompt": negative,
        "seed": int(body.get("seed") or -1),
        # 安全寄り: lab/mufufu などは露出しない
        "mufufu_mode": False,
        "lab_mode": False,
    }

    url = f"{DEFAULT_UNIFIED_API_BASE}/api/comfyui/generate"
    r = _http_json_post(url, payload=payload, timeout_s=60.0)
    if not r.get("ok"):
        return {"ok": False, "url": url, "status": r.get("status"), "error": r.get("error")}

    data = r.get("data") or {}
    append_event(EVENTS_FILE, "image_generate", "Image generate queued", {"status": data.get("status"), "prompt": prompt[:80]})
    return {"ok": True, "url": url, "data": data}


@app.get("/api/unified/comfyui/queue")
def api_unified_comfyui_queue() -> dict[str, Any]:
    return _unified_get("/api/comfyui/queue", timeout_s=8.0)


@app.get("/api/unified/comfyui/history")
def api_unified_comfyui_history() -> dict[str, Any]:
    return _unified_get("/api/comfyui/history", timeout_s=12.0)


@app.get("/api/unified/svi/queue")
def api_unified_svi_queue() -> dict[str, Any]:
    return _unified_get("/api/svi/queue", timeout_s=8.0)


@app.get("/api/unified/svi/history")
def api_unified_svi_history() -> dict[str, Any]:
    return _unified_get("/api/svi/history", timeout_s=12.0)


@app.get("/api/unified/ltx2/queue")
def api_unified_ltx2_queue() -> dict[str, Any]:
    return _unified_get("/api/ltx2/queue", timeout_s=8.0)


@app.get("/api/unified/ltx2/history")
def api_unified_ltx2_history() -> dict[str, Any]:
    return _unified_get("/api/ltx2/history", timeout_s=12.0)


@app.get("/api/unified/images/recent")
def api_unified_images_recent(limit: int = 20) -> dict[str, Any]:
    limit = max(1, min(int(limit), 200))
    return _unified_get(f"/api/images/recent?limit={limit}", timeout_s=8.0)


@app.get("/api/unified/llm/health")
def api_unified_llm_health() -> dict[str, Any]:
    return _unified_get("/api/llm/health", timeout_s=8.0)


@app.get("/api/unified/llm/models-enhanced")
def api_unified_llm_models_enhanced() -> dict[str, Any]:
    return _unified_get("/api/llm/models-enhanced", timeout_s=12.0)


@app.get("/api/unified/openapi")
def api_unified_openapi() -> dict[str, Any]:
    # Unified が openapi.json を expose している場合のみ取得できる
    return _unified_get("/openapi.json", timeout_s=12.0)


@app.get("/api/unified/memory/recall")
def api_unified_memory_recall(
    query: str,
    scope: str = "all",
    limit: int = 10,
) -> dict[str, Any]:
    q = str(query or "").strip()
    if not q:
        raise HTTPException(status_code=400, detail="query is required")
    scope_s = str(scope or "all").strip() or "all"
    limit_i = max(1, min(int(limit), 50))

    qs = urllib.parse.urlencode(
        {"query": q, "scope": scope_s, "limit": str(limit_i)}
    )
    return _unified_get(f"/api/memory/recall?{qs}", timeout_s=12.0)


@app.get("/api/unified/notify/job/{job_id}")
def api_unified_notify_job(job_id: str) -> dict[str, Any]:
    jid = str(job_id or "").strip()
    if not jid:
        raise HTTPException(status_code=400, detail="job_id is required")
    return _unified_get(f"/notify/job/{urllib.parse.quote(jid, safe='')}", timeout_s=8.0)


def _validate_proxy_body(body: Any) -> dict[str, Any]:
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="JSON object is required")
    try:
        raw = json.dumps(body, ensure_ascii=False)
        if len(raw) > 200_000:
            raise HTTPException(status_code=413, detail="payload too large")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="invalid JSON")
    return body


def _require_unified_write() -> None:
    if not _unified_write_enabled():
        raise HTTPException(status_code=403, detail="unified write disabled. set MANAOS_RPG_ENABLE_UNIFIED_WRITE=1")


def _expand_item_uris(obj: Any) -> Any:
    # item://<root_id>/<rel_path> を items.yaml の root に基づいて実パスへ展開
    # - パストラバーサル対策は safe_resolve_under_root に委譲
    # - 展開できない場合は元の文字列のまま
    try:
        items_yaml = load_yaml(REG / "items.yaml")
        item_roots = resolve_item_roots(REPO_ROOT, items_yaml)
        roots_by_id = {r.id: r for r in item_roots}
    except Exception:
        roots_by_id = {}

    def _expand(v: Any) -> Any:
        if isinstance(v, str) and v.startswith("item://"):
            rest = v[len("item://"):]
            if "/" not in rest:
                return v
            root_id, rel = rest.split("/", 1)
            root = roots_by_id.get(root_id)
            if root is None:
                return v
            p = safe_resolve_under_root(root.path, rel)
            if p is None or (not p.exists()) or (not p.is_file()):
                return v
            return str(p)
        if isinstance(v, list):
            return [_expand(x) for x in v]
        if isinstance(v, dict):
            return {str(k): _expand(x) for k, x in v.items()}
        return v

    return _expand(obj)


@app.post("/api/unified/llm/route-enhanced")
def api_unified_llm_route_enhanced(body: dict[str, Any]) -> dict[str, Any]:
    _require_unified_write()
    payload = _validate_proxy_body(body)
    prompt = str(payload.get("prompt") or "").strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="prompt is required")
    return _unified_post(
        "/api/llm/route-enhanced",
        payload=payload,
        timeout_s=60.0,
    )


@app.post("/api/unified/llm/analyze")
def api_unified_llm_analyze(body: dict[str, Any]) -> dict[str, Any]:
    # LLM呼び出しなしの難易度分析（非破壊）なので write gate なし
    payload = _validate_proxy_body(body)
    prompt = str(payload.get("prompt") or "").strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="prompt is required")
    return _unified_post(
        "/api/llm/analyze",
        payload=payload,
        timeout_s=12.0,
    )


@app.post("/api/unified/notify/send")
def api_unified_notify_send(body: dict[str, Any]) -> dict[str, Any]:
    _require_unified_write()
    payload = _validate_proxy_body(body)
    # message or text is required by Unified
    message = str(payload.get("message") or payload.get("text") or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="message (or text) is required")

    # This endpoint is not under /api/* in Unified; keep it explicit.
    return _unified_post(
        "/notify/send",
        payload=payload,
        timeout_s=30.0,
    )


@app.post("/api/unified/memory/store")
def api_unified_memory_store(body: dict[str, Any]) -> dict[str, Any]:
    _require_unified_write()
    payload = _validate_proxy_body(body)
    if payload.get("content") is None:
        raise HTTPException(status_code=400, detail="content is required")
    meta = payload.get("metadata")
    if meta is not None and not isinstance(meta, dict):
        raise HTTPException(status_code=400, detail="metadata must be an object")
    return _unified_post(
        "/api/memory/store",
        payload=payload,
        timeout_s=20.0,
    )


@app.post("/api/unified/svi/generate")
def api_unified_svi_generate(body: dict[str, Any]) -> dict[str, Any]:
    _require_unified_write()
    payload = _expand_item_uris(_validate_proxy_body(body))
    return _unified_post("/api/svi/generate", payload=payload, timeout_s=30.0)


@app.post("/api/unified/svi/extend")
def api_unified_svi_extend(body: dict[str, Any]) -> dict[str, Any]:
    _require_unified_write()
    payload = _expand_item_uris(_validate_proxy_body(body))
    return _unified_post("/api/svi/extend", payload=payload, timeout_s=30.0)


@app.post("/api/unified/ltx2/generate")
def api_unified_ltx2_generate(body: dict[str, Any]) -> dict[str, Any]:
    _require_unified_write()
    payload = _expand_item_uris(_validate_proxy_body(body))
    return _unified_post("/api/ltx2/generate", payload=payload, timeout_s=180.0)


@app.post("/api/unified/ltx2-infinity/generate")
def api_unified_ltx2_infinity_generate(body: dict[str, Any]) -> dict[str, Any]:
    _require_unified_write()
    payload = _expand_item_uris(_validate_proxy_body(body))
    return _unified_post("/api/ltx2-infinity/generate", payload=payload, timeout_s=300.0)


@app.get("/api/items")
def api_items(limit: int = 120) -> dict[str, Any]:
    limit = max(1, min(int(limit), 500))
    items_yaml = load_yaml(REG / "items.yaml")
    item_roots = resolve_item_roots(REPO_ROOT, items_yaml)
    items_recent = scan_items(item_roots)
    return {
        "roots": [{"id": r.id, "label": r.label} for r in item_roots],
        "recent": items_recent[:limit],
    }


@app.get("/files/{root_id}/{rel_path:path}")
def get_item_file(root_id: str, rel_path: str):
    items_yaml = load_yaml(REG / "items.yaml")
    item_roots = resolve_item_roots(REPO_ROOT, items_yaml)
    root = next((r for r in item_roots if r.id == root_id), None)
    if root is None:
        raise HTTPException(status_code=404, detail="unknown root_id")

    p = safe_resolve_under_root(root.path, rel_path)
    if p is None or (not p.exists()) or (not p.is_file()):
        raise HTTPException(status_code=404, detail="file not found")

    return FileResponse(path=str(p))
