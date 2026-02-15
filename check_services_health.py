# pyright: reportMissingTypeStubs=false

"""ManaOSサービスヘルスチェックスクリプト

起動後の全サービスの実際のレスポンス検査を行い、簡潔に情報整理する。

NOTE:
- Unified API の /ready は「依存関係まで含めた」レディネスであり、Ollama などが未起動だと 503 のままになり得る。
- 本スクリプトの目的は「サービスが起動して応答するか」の確認なので、Unified API は軽量な /health を検査する。
"""
import io
import os
import sys
import time
from typing import Dict, List, Optional, Tuple

import requests  # pyright: ignore[reportMissingTypeStubs]

_ENCODINGS_TO_NORMALIZE = ("cp932", "cp936", "cp949")
if sys.platform == "win32" and getattr(sys.stdout, "encoding", "") in (
    _ENCODINGS_TO_NORMALIZE
):
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
    from manaos_logger import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

# チェック対象のサービス
_DEFAULT_UNIFIED_API_PORT = int(os.getenv("MANAOS_UNIFIED_API_PORT", "9510"))
_DEFAULT_MRL_MEMORY_PORT = int(os.getenv("MANAOS_MRL_MEMORY_PORT", "5105"))
_DEFAULT_LEARNING_SYSTEM_PORT = int(
    os.getenv("MANAOS_LEARNING_SYSTEM_PORT", "5126")
)

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
        "port": 5111,
        "path": "/health",
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
        "port": 11434,
        "path": "/api/tags",
        "timeout": 5,
        "group": "infra",
    },
    {
        "name": "Gallery API",
        "port": 5559,
        "path": "/health",
        "timeout": 5,
        "group": "infra",
    },
    # === コンテンツ生成 ===
    {
        "name": "Video Pipeline",
        "port": 5112,
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
        "port": 5136,
        "path": "/health",
        "timeout": 5,
        "group": "optional",
    },
    {
        "name": "ComfyUI",
        "port": 8188,
        "path": "/system_stats",
        "timeout": 5,
        "group": "optional",
    },
    {
        "name": "Moltbot Gateway",
        "port": 8088,
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
            return f"正常稼働（/ready {ms}）" if ms else "正常稼働（初期化完了）"
        return f"正常稼働（{ms}）" if ms else "正常稼働"
    if "Timeout" in str(detail):
        return "要検査（タイムアウト）"
    if "Connection" in str(detail):
        return "未起動"
    return f"要検査（{detail}）"


def check_all_services(retry_count: int = 3, retry_delay: int = 2) -> bool:
    """
    全サービスの実際のレスポンス検査（リトライ付き）。結果を簡潔な表で表示。
    """
    print("\n" + "=" * 70)
    print("[*] ManaOS 本体検査（実レスポンス確認）")
    print("=" * 70)

    all_healthy = False
    last_results: List[
        Tuple[Dict[str, object], bool, object, Optional[float]]
    ] = []

    for attempt in range(retry_count):
        if attempt > 0:
            print(
                f"\n[retry] {attempt}/{retry_count - 1}... ({retry_delay}秒待機)"
            )
            time.sleep(retry_delay)

        last_results = []
        current_group = None
        for service in SERVICES:
            # グループヘッダー表示
            group = str(service.get("group", "other"))
            if group != current_group:
                current_group = group
                group_labels = {
                    "core": "コアサービス",
                    "infra": "インフラ",
                    "optional": "オプショナル",
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

    # 簡潔な情報整理テーブル
    print("\n" + "-" * 78)
    print("[完成状況] 簡潔")
    print("-" * 78)
    print(f"{'サービス':<20} {'ポート':<8} {'種別':<10} {'結果':<28} {'説明'}")
    print("-" * 78)
    for service, success, detail, elapsed_ms in last_results:
        ep = service["path"]
        group = str(service.get("group", "other"))
        group_map = {"core": "コア", "infra": "インフラ", "optional": "任意"}
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
        line = (
            f"{service_name:<20} {service_port:<8} {group_label:<10} "
            f"{http_col:<28} {desc}"
        )
        print(line)
    print("-" * 78)

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
        f"[コア] {core_ok}/{core_total} 稼働  "
        f"[インフラ/任意] {optional_ok}/{optional_total} 稼働"
    )

    if all_healthy:
        print("[OK] すべてのコアサービスが正常稼働中")
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
        print("[!!] 一部のコアサービスが応答しません")
        print("   対処: タスク \"ManaOS: すべてのサービスを起動\" を再実行してください")
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
