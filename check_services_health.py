"""
ManaOSサービスヘルスチェックスクリプト
起動後の全サービスの実際のレスポンス検査を行い、簡潔に情報整理する。
Unified API は /health が初期化ブロックで遅延しうるため /ready で検査。
"""
import sys
import io
if sys.platform == "win32" and getattr(sys.stdout, "encoding", "") in ("cp932", "cp936", "cp949"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import requests
import time
from typing import Dict, List, Tuple, Optional

try:
    from manaos_logger import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

# チェック対象のサービス（Unified API は /ready で初期化完了を確認）
SERVICES = [
    # === コアサービス ===
    {"name": "MRL Memory", "port": 5105, "path": "/health", "timeout": 5, "group": "core"},
    {"name": "Learning System", "port": 5126, "path": "/health", "timeout": 5, "group": "core"},
    {"name": "LLM Routing", "port": 5111, "path": "/health", "timeout": 5, "group": "core"},
    {"name": "Unified API", "port": 9502, "path": "/ready", "timeout": 8, "group": "core"},
    # === インフラストラクチャ ===
    {"name": "Ollama", "port": 11434, "path": "/api/tags", "timeout": 5, "group": "infra"},
    {"name": "Gallery API", "port": 5559, "path": "/health", "timeout": 5, "group": "infra"},
    # === 外部統合（オプショナル）===
    {"name": "ComfyUI", "port": 8188, "path": "/system_stats", "timeout": 5, "group": "optional"},
    {"name": "Moltbot Gateway", "port": 8088, "path": "/health", "timeout": 5, "group": "optional"},
]

def check_service(service: Dict) -> Tuple[bool, str, Optional[float]]:
    """
    単一サービスの実際のレスポンス検査。

    Returns:
        (成功フラグ, レスポンス詳細またはエラーメッセージ, 応答時間ms or None)
    """
    base = f"http://127.0.0.1:{service['port']}"
    url = base + service["path"]
    timeout = service.get("timeout", 5)
    try:
        t0 = time.perf_counter()
        response = requests.get(url, timeout=timeout)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        if response.status_code == 200:
            body = response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text
            return True, body, elapsed_ms
        return False, f"HTTP {response.status_code}", elapsed_ms
    except requests.exceptions.Timeout:
        return False, f"Timeout (>{timeout}s)", None
    except requests.exceptions.ConnectionError:
        return False, "Connection refused", None
    except Exception as e:
        return False, str(e), None

def _summary_row(service: Dict, success: bool, detail: str, elapsed_ms: Optional[float]) -> str:
    """1行の説明テキスト（表の「説明」列用）"""
    if success:
        ms = f"{elapsed_ms:.0f}ms" if elapsed_ms is not None else ""
        if service["path"] == "/ready":
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
    last_results: List[Tuple[Dict, bool, str, Optional[float]]] = []

    for attempt in range(retry_count):
        if attempt > 0:
            print(f"\n[retry] {attempt}/{retry_count - 1}... ({retry_delay}秒待機)")
            time.sleep(retry_delay)

        last_results = []
        current_group = None
        for service in SERVICES:
            # グループヘッダー表示
            group = service.get("group", "other")
            if group != current_group:
                current_group = group
                group_labels = {"core": "コアサービス", "infra": "インフラ", "optional": "オプショナル"}
                print(f"\n  --- {group_labels.get(group, group)} ---")

            success, detail, elapsed_ms = check_service(service)
            last_results.append((service, success, detail, elapsed_ms))

            status_icon = "[OK]" if success else "[NG]"
            endpoint = service["path"]
            if success and elapsed_ms is not None:
                status_text = f"HTTP 200 ({elapsed_ms:.0f}ms)"
            elif success:
                status_text = "HTTP 200"
            else:
                status_text = str(detail)
            print(f"{status_icon} {service['name']:20} port {service['port']} {endpoint}: {status_text}")

        # コアサービスのみで全体判定（オプショナルは判定に含めない）
        core_results = [r for r in last_results if r[0].get("group") == "core"]
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
        group = service.get("group", "other")
        group_label = {"core": "コア", "infra": "インフラ", "optional": "任意"}.get(group, group)
        if success:
            http_col = f"OK {ep} 200" + (f" ({elapsed_ms:.0f}ms)" if elapsed_ms is not None else "")
        else:
            http_col = f"Timeout {detail}" if "Timeout" in str(detail) else f"NG {detail}"
        desc = _summary_row(service, success, detail, elapsed_ms)
        print(f"{service['name']:<20} {service['port']:<8} {group_label:<10} {http_col:<28} {desc}")
    print("-" * 78)

    # サマリー
    core_ok = sum(1 for r in last_results if r[0].get("group") == "core" and r[1])
    core_total = sum(1 for r in last_results if r[0].get("group") == "core")
    optional_ok = sum(1 for r in last_results if r[0].get("group") != "core" and r[1])
    optional_total = sum(1 for r in last_results if r[0].get("group") != "core")

    print(f"[コア] {core_ok}/{core_total} 稼働  [インフラ/任意] {optional_ok}/{optional_total} 稼働")

    if all_healthy:
        print("[OK] すべてのコアサービスが正常稼働中")
        logger.info("ヘルスチェック完了: コア %d/%d 稼働, インフラ/任意 %d/%d 稼働",
                     core_ok, core_total, optional_ok, optional_total)
    else:
        failed = [r[0]["name"] for r in last_results if r[0].get("group") == "core" and not r[1]]
        print("[!!] 一部のコアサービスが応答しません")
        print("   対処: タスク \"ManaOS: すべてのサービスを起動\" を再実行してください")
        logger.warning("ヘルスチェック失敗: コア %d/%d, 障害サービス: %s",
                       core_ok, core_total, ", ".join(failed))
    print("=" * 78 + "\n")

    return all_healthy

if __name__ == "__main__":
    import sys
    success = check_all_services()
    sys.exit(0 if success else 1)
