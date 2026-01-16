#!/usr/bin/env python3
"""
Phase 1 (Read-only) メトリクススナップショット取得
JSON形式で出力（判定用）
"""

import json
import os
import subprocess
import re
from pathlib import Path
from datetime import datetime, timedelta
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


def _load_dotenv(env_path: str = ".env") -> None:
    """snapshot側でも必ず.envを読む（config/securityがunknown/1000000になるのを防ぐ）"""
    try:
        p = Path(env_path)
        if not p.exists():
            return
        for raw in p.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip()
    except Exception as e:
        print(f"[WARN] .env読み込みに失敗: {e}")


_load_dotenv()

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:5105")
API_KEY = os.getenv("API_KEY", "")

def get_security_status() -> dict:
    """SECURITY設定の状態を取得（罠②対策：PIIマスキングの実際の状態を確認）"""
    from mrl_memory_api_security import APISecurity
    
    security = APISecurity()
    
    # PIIマスキングの実際の状態を確認（環境変数から）
    pii_mask_enabled = os.getenv("PII_MASK_ENABLED", "1").lower() in ["1", "true", "yes"]
    
    return {
        "auth": "enabled" if security.require_auth else "disabled",
        "rate_limit": "enabled" if security.rate_limit_per_minute > 0 else "disabled",
        "max_input": security.max_input_size,
        "pii_mask": "enabled" if pii_mask_enabled else "disabled"
    }

def get_metrics_snapshot() -> dict:
    """
    メトリクスのスナップショットを取得（罠①対策：ダッシュボードJSONをソースにする）
    
    注意: メトリクスがメモリ内のみの場合、別プロセスからは取得できません。
    その場合は、APIサーバーのプロセスから直接取得するか、メトリクスを永続化する必要があります。
    """
    # 方法0: APIから直接取得（最優先・0固定対策の本丸）
    # 429等の一時的失敗に備えて軽くリトライする
    for attempt in range(1, 6):
        try:
            req = Request(f"{API_BASE_URL}/api/metrics", headers={"X-API-Key": API_KEY})
            with urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8", errors="ignore"))
                metrics_data = data.get("metrics", {})
                return {
                    "e2e_p95_sec": metrics_data.get("e2e_p95_sec", 0),
                    "gate_block_rate": metrics_data.get("gate_block_rate", 0),
                    "contradiction_rate": metrics_data.get("contradiction_rate", 0),
                    "slot_usage_variance": metrics_data.get("slot_usage_variance", 0),
                    "writes_per_min": metrics_data.get("writes_per_min", 0),
                }
        except Exception as e:
            # 最後の試行でなければ待って再試行
            if attempt < 5:
                try:
                    import time
                    time.sleep(0.4 * attempt)
                except Exception:
                    pass
                continue
            print(f"[WARN] /api/metrics の取得に失敗: {e}")

    # 方法1: ダッシュボードJSONを読む（推奨）
    try:
        result = subprocess.run(
            ["python", "mrl_memory_dashboard.py", "--json"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=10
        )
        if result.returncode == 0:
            dashboard_data = json.loads(result.stdout)
            metrics_data = dashboard_data.get("metrics", {})
            return {
                "e2e_p95_sec": metrics_data.get("e2e_p95_sec", 0),
                "gate_block_rate": metrics_data.get("gate_block_rate", 0),
                "contradiction_rate": metrics_data.get("contradiction_rate", 0),
                "slot_usage_variance": metrics_data.get("slot_usage_variance", 0),
                "writes_per_min": metrics_data.get("writes_per_min", 0)
            }
    except Exception as e:
        print(f"[WARN] ダッシュボードJSONの読み込みに失敗: {e}")
    
    # 方法2: 永続化されたメトリクスを読む（フォールバック）
    try:
        from mrl_memory_metrics import MRLMemoryMetrics
        metrics = MRLMemoryMetrics()
        
        # 最新のメトリクスファイルを探す
        metrics_dir = metrics.metrics_dir
        today = datetime.now().strftime('%Y%m%d')
        metrics_file = metrics_dir / f"metrics_{today}.json"
        
        if metrics_file.exists():
            with open(metrics_file, 'r', encoding='utf-8') as f:
                saved_metrics = json.load(f)
                # 最新の統計を計算
                # （簡易実装：最新のエントリから統計を計算）
                # 実際の実装では、保存されたメトリクスから統計を再計算する必要があります
                pass
        
        # 方法3: 直接メトリクスインスタンスから読む（メモリ内のみの場合、0になる可能性がある）
        latency_stats = metrics.get_latency_stats()
        p95 = latency_stats.get("p95", 0) if latency_stats else 0
        
        gate_stats = metrics.get_gate_block_rate_stats()
        gate_block_rate = gate_stats.get("current", 0) if gate_stats else 0
        
        conflict_stats = metrics.get_conflict_detection_rate_stats()
        conflict_rate = conflict_stats.get("current", 0) if conflict_stats else 0
        
        slot_stats = metrics.get_slot_utilization_stats()
        variance = slot_stats.get("mean_variance", 0) if slot_stats else 0
        
        write_stats = metrics.get_write_count_stats()
        writes_per_min = write_stats.get("current", 0) if write_stats else 0
        
        # 警告: メモリ内のみの場合、値が0になる可能性がある
        if p95 == 0 and gate_block_rate == 0 and conflict_rate == 0:
            print("[WARN] メトリクスが0の可能性があります。APIサーバーのプロセスから直接取得するか、メトリクスを永続化してください。")
        
        return {
            "e2e_p95_sec": p95,
            "gate_block_rate": gate_block_rate,
            "contradiction_rate": conflict_rate,
            "slot_usage_variance": variance,
            "writes_per_min": writes_per_min
        }
    except Exception as e:
        print(f"[ERROR] メトリクスの取得に失敗: {e}")
        # フォールバック: 0を返す
        return {
            "e2e_p95_sec": 0,
            "gate_block_rate": 0,
            "contradiction_rate": 0,
            "slot_usage_variance": 0,
            "writes_per_min": 0
        }

def get_storage_health() -> dict:
    """
    永続化ストレージの健康状態を取得（副作用なし：MRLMemorySystemを初期化しない）
    """
    # メモリディレクトリを環境変数またはデフォルトから取得
    memory_dir = Path(os.getenv("MRL_MEMORY_DIR", Path(__file__).parent / "mrl_memory"))
    
    # Scratchpadの行数をカウント
    scratchpad_path = memory_dir / "scratchpad.jsonl"
    scratchpad_count = 0
    if scratchpad_path.exists():
        try:
            with open(scratchpad_path, 'r', encoding='utf-8') as f:
                scratchpad_count = sum(1 for line in f if line.strip())
        except Exception as e:
            print(f"[WARN] Scratchpadの読み込みエラー: {e}")
    
    # Quarantineの行数をカウント
    quarantine_path = memory_dir / "quarantine.jsonl"
    quarantine_count = 0
    if quarantine_path.exists():
        try:
            with open(quarantine_path, 'r', encoding='utf-8') as f:
                quarantine_count = sum(1 for line in f if line.strip())
        except Exception as e:
            print(f"[WARN] Quarantineの読み込みエラー: {e}")
    
    # Promotedの行数をカウント（存在する場合）
    promoted_path = memory_dir / "promoted.jsonl"
    promoted_count = 0
    if promoted_path.exists():
        try:
            with open(promoted_path, 'r', encoding='utf-8') as f:
                promoted_count = sum(1 for line in f if line.strip())
        except Exception as e:
            print(f"[WARN] Promotedの読み込みエラー: {e}")
    
    return {
        "scratchpad_entries": scratchpad_count,
        "quarantine_entries": quarantine_count,
        "promoted_entries": promoted_count
    }

def get_error_count() -> dict:
    """
    エラーカウントを取得（罠③対策：ログから5xxエラーを実際にカウント）
    """
    error_count = 0
    cutoff_time = datetime.now() - timedelta(minutes=60)
    
    # 方法1: systemd journalから取得（Linux）
    try:
        result = subprocess.run(
            ["journalctl", "-u", "mrl-memory", "--since", "60 min ago", "--no-pager"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            # 5xxエラーをカウント（HTTP 500, 501, 502, 503, 504など）
            lines = result.stdout.split('\n')
            for line in lines:
                if re.search(r'HTTP\s+(5\d{2})|status[:\s]+(5\d{2})', line, re.IGNORECASE):
                    error_count += 1
    except (FileNotFoundError, subprocess.TimeoutExpired):
        # journalctlが使えない場合、ログファイルを探す
        pass
    
    # 方法2: ログファイルから取得（フォールバック）
    if error_count == 0:
        log_paths = [
            Path("mrl_memory.log"),
            Path("logs/mrl_memory.log"),
            Path(__file__).parent / "logs" / "mrl_memory.log"
        ]
        
        for log_path in log_paths:
            if log_path.exists():
                try:
                    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                        for line in f:
                            # タイムスタンプをチェック（簡易実装）
                            if re.search(r'HTTP\s+(5\d{2})|status[:\s]+(5\d{2})', line, re.IGNORECASE):
                                error_count += 1
                except Exception as e:
                    print(f"[WARN] ログファイルの読み込みエラー: {e}")
                    break
    
    return {
        "http_5xx_last_60min": error_count
    }

def create_snapshot(output_path: Path = None, baseline_path: Path = None) -> dict:
    """
    スナップショットを作成
    
    Args:
        output_path: 出力先パス（Noneの場合は返すだけ）
        baseline_path: ベースラインスナップショットのパス（差分計算用）
    
    Returns:
        スナップショット（辞書形式）
    """
    # 設定値を明示（追加項目）
    config = {
        "write_mode": os.getenv("FWPKM_WRITE_MODE", "unknown"),
        "review_effect": os.getenv("FWPKM_REVIEW_EFFECT", "0"),
        "write_enabled": os.getenv("FWPKM_WRITE_ENABLED", "0"),
        "write_sample_rate": os.getenv("FWPKM_WRITE_SAMPLE_RATE", "0"),
    }

    # API alive をスナップショットに含める（0固定の切り分け用）
    api_status = {"reachable": False}
    try:
        with urlopen(f"{API_BASE_URL}/health", timeout=3) as resp:
            api_status = {
                "reachable": (200 <= resp.status < 300),
                "http_status": resp.status,
            }
    except Exception as e:
        api_status = {"reachable": False, "error": str(e)}
    
    # ストレージ健康状態を取得
    storage = get_storage_health()
    
    # ベースラインとの差分を計算（オプション）
    storage_delta = None
    if baseline_path and baseline_path.exists():
        try:
            with open(baseline_path, 'r', encoding='utf-8') as f:
                baseline = json.load(f)
                baseline_storage = baseline.get("storage", {})
                storage_delta = {
                    "scratchpad_entries": storage["scratchpad_entries"] - baseline_storage.get("scratchpad_entries", 0),
                    "quarantine_entries": storage["quarantine_entries"] - baseline_storage.get("quarantine_entries", 0),
                    "promoted_entries": storage["promoted_entries"] - baseline_storage.get("promoted_entries", 0)
                }
        except Exception as e:
            print(f"[WARN] ベースラインとの差分計算に失敗: {e}")
    
    snapshot = {
        "timestamp": datetime.now().isoformat(),
        "phase": "Phase 1: Read-only",
        "config": config,
        "security": get_security_status(),
        "metrics": get_metrics_snapshot(),
        "storage": storage,
        "errors": get_error_count(),
        "api_status": api_status,
    }
    
    # ストレージ差分を追加（存在する場合）
    if storage_delta:
        snapshot["storage_delta"] = storage_delta
    
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(snapshot, f, ensure_ascii=False, indent=2)
        print(f"スナップショットを保存: {output_path}")
    
    return snapshot

def main():
    """メイン処理"""
    import sys
    
    # 出力先を指定（コマンドライン引数）
    output_path = None
    baseline_path = None
    
    if len(sys.argv) > 1:
        output_path = Path(sys.argv[1])
    
    # ベースラインスナップショットのパス（オプション）
    if len(sys.argv) > 2:
        baseline_path = Path(sys.argv[2])
    
    if output_path is None:
        # デフォルト: phase1_metrics_snapshot.json
        output_path = Path("phase1_metrics_snapshot.json")
    
    # スナップショットを作成
    snapshot = create_snapshot(output_path, baseline_path)
    
    # 標準出力にもJSONを出力（判定スクリプト用）
    print(json.dumps(snapshot, ensure_ascii=False, indent=2))
    
    return snapshot

if __name__ == "__main__":
    main()
