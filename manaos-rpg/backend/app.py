from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import yaml
from fastapi import FastAPI
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

app = FastAPI(title="ManaOS RPG API", version="0.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


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

    services = list(services_yaml.get("services") or [])
    models = list(models_yaml.get("models") or [])
    menu = list(menu_yaml.get("menu") or [])
    devices = list(devices_yaml.get("devices") or [])
    quests = list(quests_yaml.get("quests") or [])
    skills = list(skills_yaml.get("skills") or [])

    item_roots = resolve_item_roots(REPO_ROOT, items_yaml)
    items_recent = scan_items(item_roots)

    host = get_host_stats()
    services_status = compute_services_status(services)
    danger = compute_danger(host, services_status)

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
        "models": models_enriched,
        "devices": devices,
        "quests": quests,
        "skills": skills,
        "items": {
            "roots": [{"id": r.id, "label": r.label} for r in item_roots],
            "recent": items_recent,
        },
        "danger": danger,
        "next_actions": next_actions,
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
    }


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
