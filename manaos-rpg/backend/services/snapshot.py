from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

from core.config import (
    DEFAULT_MRL_MEMORY_BASE,
    DEFAULT_UNIFIED_API_BASE,
    EVENTS_FILE,
    REG,
    REPO_ROOT,
    STATE_FILE,
)
from core.helpers import load_yaml, _append_next_action, _append_next_action_hint
from core.unified_client import (
    _unified_api_key,
    _unified_dangerous_enabled,
    _unified_write_enabled,
    get_unified_integrations_status,
)
from core.http_client import _http_json_get
from collectors.events import append_event
from collectors.host_stats import get_host_stats
from collectors.items_collector import resolve_item_roots, scan_items
from collectors.ollama_runtime import get_ollama_ps_models
from collectors.services_runtime import compute_services_status
from services.actions import _actions_enabled, _load_actions


# ── RLAnything 統合 (安全インポート) ──
def _get_rl_dashboard() -> dict | None:
    """RLAnything のダッシュボード情報を安全に取得"""
    try:
        _repo_root = str(Path(__file__).resolve().parent.parent.parent.parent)
        if _repo_root not in sys.path:
            sys.path.insert(0, _repo_root)
        from rl_anything.orchestrator import RLAnythingOrchestrator
        rl = RLAnythingOrchestrator()
        dash = rl.get_dashboard()
        dash["skills"] = [s.to_dict() for s in rl.evolution.skills]
        dash["enabled"] = True
        return dash
    except Exception:
        return {"enabled": False, "error": "rl_anything not available"}
from services.unified_doctor import (
    _load_unified_proxy_rules,
    _maybe_refresh_unified_doctor_cache,
)


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

    # mrl-memory (Unified memory未搭載時のフォールバック先)
    mrl_health = _http_json_get(f"{DEFAULT_MRL_MEMORY_BASE}/health", timeout_s=3.0)
    mrl_metrics = _http_json_get(f"{DEFAULT_MRL_MEMORY_BASE}/api/metrics", timeout_s=4.0)
    mrl_status: dict[str, Any] = {
        "ok": bool(mrl_health.get("ok")),
        "base": DEFAULT_MRL_MEMORY_BASE,
        "health": mrl_health.get("data") if mrl_health.get("ok") else None,
        "metrics": mrl_metrics.get("data") if mrl_metrics.get("ok") else None,
        "checks": {
            "health": {
                "url": f"{DEFAULT_MRL_MEMORY_BASE}/health",
                "ok": bool(mrl_health.get("ok")),
                "status": mrl_health.get("status"),
                "error": mrl_health.get("error"),
            },
            "metrics": {
                "url": f"{DEFAULT_MRL_MEMORY_BASE}/api/metrics",
                "ok": bool(mrl_metrics.get("ok")),
                "status": mrl_metrics.get("status"),
                "error": mrl_metrics.get("error"),
            },
        },
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

        prev_blocked = bool((prev_by_id.get(sid) or {}).get("blocked"))
        now_blocked = bool(s.get("blocked"))
        if now_blocked and not prev_blocked:
            append_event(EVENTS_FILE, "blocked", "依存関係によりブロックされました", {"service": sid, "deps_down": deps_down})
        if (not now_blocked) and prev_blocked:
            append_event(EVENTS_FILE, "unblocked", "ブロックが解除されました", {"service": sid})

        prev_health = (prev_by_id.get(sid) or {}).get("docker_health")
        now_health = s.get("docker_health")
        if now_health and now_health != prev_health:
            if now_health == "unhealthy":
                append_event(EVENTS_FILE, "unhealthy", "Docker health が UNHEALTHY になりました", {"service": sid})
            if prev_health == "unhealthy" and now_health == "healthy":
                append_event(EVENTS_FILE, "healthy", "Docker health が HEALTHY に復帰しました", {"service": sid})

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

    try:
        if mrl_status.get("ok") and isinstance(mrl_status.get("metrics"), dict):
            cfg = mrl_status.get("metrics", {}).get("config")
            if isinstance(cfg, dict):
                write_mode = str(cfg.get("write_mode") or "").strip().lower()
                write_enabled = str(cfg.get("write_enabled") or "").strip()
                if write_mode == "readonly" or write_enabled in {"0", "false", "no"}:
                    next_actions.append(
                        "mrl-memory が readonly：memory store は readonly_mode（永続化したいなら MRL_FWPKM_WRITE_ENABLED=1 を明示）"
                    )
                    _append_next_action_hint(
                        next_action_hints,
                        label="実行：mrl-memory 書き込みON（full / recreate）",
                        action_id="mrl_memory_write_on_full",
                    )
                else:
                    _append_next_action_hint(
                        next_action_hints,
                        label="実行：mrl-memory 書き込みOFF（readonly / recreate）",
                        action_id="mrl_memory_write_off",
                    )
    except Exception:
        pass

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

            if can_act_on_unified and sync_likely_useful:
                _append_next_action_hint(
                    next_action_hints,
                    label="実行：Unified allowlist 同期（OpenAPI→unified_proxy.yaml）",
                    action_id="unified_proxy_sync",
                )

            if conn_err >= 8:
                _append_next_action(
                    next_actions,
                    "Unified API到達エラー多数：unified_api_server(9502) の起動/復旧を確認",
                )

            if total >= 1 and skipped >= total:
                if int(counts.get("skipped_post") or 0) >= 1:
                    _append_next_action(
                        next_actions,
                        "Unified allowlist が POST中心のため安全probeができない：OpenAPI/実行結果ベースで運用（必要ならinclude_disabledで一覧確認）",
                    )
                    if can_act_on_unified and (not has_enabled_get_rule):
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

            if auth_cnt >= 1 and not bool(_unified_api_key()):
                _append_next_action(
                    next_actions,
                    "Unified API認証が必要：環境変数 MANAOS_UNIFIED_API_KEY（read-only可）を設定",
                )

            if not_found_get >= 1:
                _append_next_action(
                    next_actions,
                    "Unified allowlistにGET 404が残存：クエスト『Unified allowlist 404自動無効化（台帳掃除）』を実行",
                )

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
            "mrl_memory": mrl_status,
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
        "rl_anything": _get_rl_dashboard(),
    }
