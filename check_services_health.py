# pyright: reportMissingTypeStubs=false

"""ManaOSサービスヘルスチェックスクリプト

起動後の全サービスの実際のレスポンス検査を行い、簡潔に情報整理する。

NOTE:
- Unified API の /ready は「依存関係まで含めた」レディネスであり、Ollama などが未起動だと 503 のままになり得る。
- 本スクリプトの目的は「サービスが起動して応答するか」の確認なので、Unified API は軽量な /health を検査する。
"""
import io
import os
import shutil
import sys
import time
import unicodedata
from typing import Dict, List, Optional, Tuple

import requests  # pyright: ignore[reportMissingTypeStubs]

_UTF8_ENCODINGS = ("utf-8", "utf8")
_stdout_encoding = (getattr(sys.stdout, "encoding", "") or "").lower()
_force_utf8 = os.getenv("MANAOS_FORCE_UTF8", "0") == "1"

if sys.platform == "win32" and (_force_utf8 or _stdout_encoding in _UTF8_ENCODINGS):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(  # type: ignore[attr-defined]
                    encoding="utf-8",
                    errors="replace",
                )
                continue
            except (TypeError, ValueError):
                pass

        # フォールバック（可能ならバッファを保持したまま差し替え）
        if hasattr(stream, "buffer"):
            try:
                wrapped = io.TextIOWrapper(
                    stream.buffer,  # type: ignore[attr-defined]
                    encoding="utf-8",
                    errors="replace",
                )
                if stream is sys.stdout:
                    sys.stdout = wrapped
                else:
                    sys.stderr = wrapped
            except (AttributeError, TypeError, ValueError):
                pass

try:
    from unified_logging import get_service_logger
    logger = get_service_logger("check-services-health")
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

# ポート定数は _paths.py を SSOT とする
try:
    from _paths import (
        UNIFIED_API_PORT as _DEFAULT_UNIFIED_API_PORT,
        MRL_MEMORY_PORT as _DEFAULT_MRL_MEMORY_PORT,
        LEARNING_SYSTEM_PORT as _DEFAULT_LEARNING_SYSTEM_PORT,
        LLM_ROUTING_PORT,
        VIDEO_PIPELINE_PORT,
        PICO_HID_PORT,
        COMFYUI_PORT,
        OLLAMA_PORT,
        GALLERY_PORT,
        MOLTBOT_GATEWAY_PORT,
    )
except ImportError:
    _DEFAULT_UNIFIED_API_PORT = int(os.getenv("MANAOS_UNIFIED_API_PORT", "9502"))
    _DEFAULT_MRL_MEMORY_PORT = int(os.getenv("MANAOS_MRL_MEMORY_PORT", "5105"))
    _DEFAULT_LEARNING_SYSTEM_PORT = int(os.getenv("MANAOS_LEARNING_SYSTEM_PORT", "5126"))
    LLM_ROUTING_PORT = 5111
    VIDEO_PIPELINE_PORT = 5112
    PICO_HID_PORT = 5136
    COMFYUI_PORT = 8188
    OLLAMA_PORT = 11434
    GALLERY_PORT = 5559
    MOLTBOT_GATEWAY_PORT = 8088


def _resolve_openai_router_port(default_port: int = 5211) -> int:
    status_file = os.path.join(
        os.path.dirname(__file__),
        "logs",
        "manaos_llm_router_port.txt",
    )
    if not os.path.exists(status_file):
        return default_port

    try:
        with open(status_file, "r", encoding="utf-8") as fp:
            for line in fp:
                line = line.strip()
                if not line.startswith("port="):
                    continue
                value = line.replace("port=", "", 1).strip()
                if value.isdigit():
                    return int(value)
    except OSError:
        pass

    return default_port


OPENAI_ROUTER_PORT = _resolve_openai_router_port()

SERVICES: List[Dict[str, object]] = [
    # === コアサービス ===
    {
        "name": "MRL Memory",
        "port": _DEFAULT_MRL_MEMORY_PORT,
        "path": "/health",
        "timeout": 5,
        "group": "core",
    },
    {
        "name": "Learning System",
        "port": _DEFAULT_LEARNING_SYSTEM_PORT,
        "path": "/health",
        "timeout": 5,
        "group": "core",
    },
    {
        "name": "LLM Routing",
        "port": LLM_ROUTING_PORT,
        "path": "/health",
        "timeout": 5,
        "group": "core",
    },
    {
        "name": "OpenAI Router",
        "port": OPENAI_ROUTER_PORT,
        "path": "/api/llm/health",
        "timeout": 5,
        "group": "core",
    },
    {
        "name": "Unified API",
        "port": _DEFAULT_UNIFIED_API_PORT,
        "path": "/health",
        "timeout": 5,
        "group": "core",
    },
    # === インフラストラクチャ ===
    {
        "name": "Ollama",
        "port": OLLAMA_PORT,
        "path": "/api/tags",
        "timeout": 5,
        "group": "infra",
    },
    {
        "name": "Gallery API",
        "port": GALLERY_PORT,
        "path": "/health",
        "timeout": 5,
        "group": "infra",
    },
    # === コンテンツ生成 ===
    {
        "name": "Video Pipeline",
        "port": VIDEO_PIPELINE_PORT,
        "path": "/health",
        "timeout": 5,
        "group": "core",
    },
    # === 外部統合（オプショナル）===
    {
        "name": "Unified API (/ready)",
        "port": _DEFAULT_UNIFIED_API_PORT,
        "path": "/ready",
        "timeout": 5,
        "group": "optional",
    },
    {
        "name": "Pico HID MCP",
        "port": PICO_HID_PORT,
        "path": "/health",
        "timeout": 5,
        "group": "optional",
    },
    {
        "name": "ComfyUI",
        "port": COMFYUI_PORT,
        "path": "/system_stats",
        "timeout": 5,
        "group": "optional",
    },
    {
        "name": "Moltbot Gateway",
        "port": MOLTBOT_GATEWAY_PORT,
        "path": "/moltbot/health",
        "timeout": 5,
        "group": "optional",
    },
]


def check_service(
    service: Dict[str, object],
) -> Tuple[bool, object, Optional[float]]:
    """単一サービスの実際のレスポンス検査。"""
    port = service["port"]
    path = service["path"]
    timeout_obj = service.get("timeout", 5)
    try:
        timeout = float(timeout_obj)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        timeout = 5.0
    base = f"http://127.0.0.1:{port}"
    url = base + str(path)

    try:
        t0 = time.perf_counter()
        response = requests.get(url, timeout=timeout)
        elapsed_ms = (time.perf_counter() - t0) * 1000

        if response.status_code != 200:
            return False, f"HTTP {response.status_code}", elapsed_ms

        content_type = response.headers.get("content-type", "")
        if content_type.startswith("application/json"):
            try:
                body = response.json()
            except ValueError:
                body = response.text
        else:
            body = response.text
        return True, body, elapsed_ms
    except requests.exceptions.Timeout:
        return False, f"Timeout (>{timeout}s)", None
    except requests.exceptions.ConnectionError:
        return False, "Connection refused", None
    except requests.RequestException as e:
        return False, str(e), None


def _summary_row(
    service: Dict[str, object],
    ok: bool,
    detail: object,
    elapsed_ms: Optional[float],
) -> str:
    """1行の説明テキスト（表の「説明」列用）"""
    if ok:
        ms = f"{elapsed_ms:.0f}ms" if elapsed_ms is not None else ""
        if service.get("path") == "/ready":
            return f"healthy (/ready {ms})" if ms else "healthy (ready)"
        return f"healthy ({ms})" if ms else "healthy"
    if "Timeout" in str(detail):
        return "check timeout"
    if "Connection" in str(detail):
        return "not running"
    return f"check ({detail})"


def _fit_text(text: object, width: int) -> str:
    def _char_width(ch: str) -> int:
        return 2 if unicodedata.east_asian_width(ch) in ("W", "F", "A") else 1

    value = str(text)
    if width <= 1:
        return value[:width]

    display_width = sum(_char_width(ch) for ch in value)
    if display_width <= width:
        return value

    limit = max(1, width - 1)
    out_chars: List[str] = []
    used = 0
    for ch in value:
        ch_w = _char_width(ch)
        if used + ch_w > limit:
            break
        out_chars.append(ch)
        used += ch_w
    return "".join(out_chars) + "…"


def check_all_services(retry_count: int = 3, retry_delay: int = 2) -> bool:
    """
    全サービスの実際のレスポンス検査（リトライ付き）。結果を簡潔な表で表示。
    """
    print("\n" + "=" * 70)
    print("[*] ManaOS Health Check (live responses)")
    print("=" * 70)

    all_healthy = False
    last_results: List[
        Tuple[Dict[str, object], bool, object, Optional[float]]
    ] = []

    for attempt in range(retry_count):
        if attempt > 0:
            print(f"\n[retry] {attempt}/{retry_count - 1}... (wait {retry_delay}s)")
            time.sleep(retry_delay)

        last_results = []
        current_group = None
        for service in SERVICES:
            # グループヘッダー表示
            group = str(service.get("group", "other"))
            if group != current_group:
                current_group = group
                group_labels = {
                    "core": "Core",
                    "infra": "Infra",
                    "optional": "Optional",
                }
                group_label = group_labels.get(group, group)
                print(f"\n  --- {group_label} ---")

            ok, detail, elapsed_ms = check_service(service)
            last_results.append((service, ok, detail, elapsed_ms))

            status_icon = "[OK]" if ok else "[NG]"
            endpoint = service["path"]
            if ok and elapsed_ms is not None:
                status_text = f"HTTP 200 ({elapsed_ms:.0f}ms)"
            elif ok:
                status_text = "HTTP 200"
            else:
                status_text = str(detail)
            service_name = service["name"]
            service_port = service["port"]
            line = (
                f"{status_icon} {service_name:20} port {service_port} "
                f"{endpoint}: {status_text}"
            )
            print(line)

        # コアサービスのみで全体判定（オプショナルは判定に含めない）
        core_results = [
            r for r in last_results if str(r[0].get("group", "")) == "core"
        ]
        if all(r[1] for r in core_results):
            all_healthy = True
            break

    # 簡潔な情報整理テーブル（端末幅に合わせて表示崩れを抑制）
    terminal_width = shutil.get_terminal_size(fallback=(120, 30)).columns
    table_width = max(72, min(terminal_width - 1, 140))
    service_width = 16
    port_width = 5
    group_width = 5
    result_width = 24
    fixed_width = service_width + port_width + group_width + result_width + 12
    desc_width = max(8, table_width - fixed_width)

    print("\n" + "-" * table_width)
    print("[Summary] Compact")
    print("-" * table_width)
    header = (
        f"{_fit_text('Service', service_width)} | "
        f"{_fit_text('Port', port_width)} | "
        f"{_fit_text('Kind', group_width)} | "
        f"{_fit_text('Result', result_width)} | "
        f"{_fit_text('Notes', desc_width)}"
    )
    print(header)
    print("-" * table_width)
    for service, success, detail, elapsed_ms in last_results:
        ep = service["path"]
        group = str(service.get("group", "other"))
        group_map = {"core": "core", "infra": "infra", "optional": "opt"}
        group_label = group_map.get(group, group)
        if success:
            http_col = f"OK {ep} 200"
            if elapsed_ms is not None:
                http_col += f" ({elapsed_ms:.0f}ms)"
        else:
            if "Timeout" in str(detail):
                http_col = f"Timeout {detail}"
            else:
                http_col = f"NG {detail}"
        desc = _summary_row(service, success, detail, elapsed_ms)
        service_name = service["name"]
        service_port = service["port"]
        service_cell = _fit_text(service_name, service_width)
        result_cell = _fit_text(http_col, result_width)
        desc_cell = _fit_text(desc, desc_width)
        line = (
            f"{service_cell} | {service_port} | "
            f"{group_label} | {result_cell} | {desc_cell}"
        )
        print(line)
    print("-" * table_width)

    # サマリー
    core_ok = sum(
        1 for r in last_results if str(r[0].get("group")) == "core" and r[1]
    )
    core_total = sum(1 for r in last_results if r[0].get("group") == "core")
    optional_ok = sum(
        1 for r in last_results if str(r[0].get("group")) != "core" and r[1]
    )
    optional_total = sum(
        1 for r in last_results if str(r[0].get("group")) != "core"
    )

    print(
        f"[core] {core_ok}/{core_total} up  "
        f"[infra/opt] {optional_ok}/{optional_total} up"
    )

    if all_healthy:
        print("[OK] all core services healthy")
        logger.info(
            "ヘルスチェック完了: コア %d/%d 稼働, インフラ/任意 %d/%d 稼働",
            core_ok,
            core_total,
            optional_ok,
            optional_total,
        )
    else:
        failed = [
            str(r[0].get("name", ""))
            for r in last_results
            if str(r[0].get("group")) == "core" and not r[1]
        ]
        print("[!!] some core services are not responding")
        print("   Action: rerun task \"ManaOS: すべてのサービスを起動\"")
        logger.warning(
            "ヘルスチェック失敗: コア %d/%d, 障害サービス: %s",
            core_ok,
            core_total,
            ", ".join(failed),
        )
    print("=" * 78 + "\n")

    return all_healthy


if __name__ == "__main__":
    main_ok = check_all_services()
    sys.exit(0 if main_ok else 1)
