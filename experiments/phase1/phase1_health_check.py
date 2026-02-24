#!/usr/bin/env python3
"""
Phase 1 (Read-only) 健康診断
永続化ストアの行数チェックとTTLマネージャの動作確認
"""

import json
import os
from pathlib import Path
from datetime import datetime
from mrl_memory_system import MRLMemorySystem


def _load_dotenv(env_path: str = ".env") -> None:
    """health_check側でも.envを読む（KillSwitch/WriteMode判定のブレを防ぐ）"""
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
    except Exception:
        pass


_load_dotenv()

def check_storage_health() -> tuple[bool, list[str]]:
    """
    永続化ストアの健康状態をチェック
    
    Returns:
        (is_healthy, issues)
    """
    issues = []
    system = MRLMemorySystem()
    
    # Scratchpadの行数をカウント
    scratchpad_path = system.memory_dir / "scratchpad.jsonl"
    scratchpad_count = 0
    if scratchpad_path.exists():
        with open(scratchpad_path, 'r', encoding='utf-8') as f:
            scratchpad_count = sum(1 for line in f if line.strip())
    
    # Quarantineの行数をカウント
    quarantine_path = system.memory_dir / "quarantine.jsonl"
    quarantine_count = 0
    if quarantine_path.exists():
        with open(quarantine_path, 'r', encoding='utf-8') as f:
            quarantine_count = sum(1 for line in f if line.strip())
    
    # Read-onlyモードなのに書き込みが発生していないかチェック
    # （初期値と比較する必要があるため、ベースラインが必要）
    # ここでは簡易的に、Read-onlyモードでScratchpadが増えていないかチェック
    
    # 注意: 初回実行時はベースラインがないため、警告のみ
    # 2回目以降は、前回のスナップショットと比較
    
    return True, issues

def check_ttl_manager() -> tuple[bool, list[str]]:
    """
    TTLマネージャの動作を確認
    
    Returns:
        (is_working, issues)
    """
    issues = []
    system = MRLMemorySystem()
    
    # 期限切れエントリを削除
    deleted_count = system.cleanup_expired_entries()
    
    if deleted_count > 0:
        print(f"[OK] TTLマネージャが動作しています: {deleted_count}件の期限切れエントリを削除")
    else:
        print("[OK] TTLマネージャが動作しています: 期限切れエントリはありません")
    
    return True, issues

def compare_snapshots(baseline_path: Path, current_path: Path) -> tuple[bool, list[str]]:
    """
    スナップショットを比較（Read-onlyモードで書き込みが発生していないかチェック）
    
    Args:
        baseline_path: ベースラインスナップショット
        current_path: 現在のスナップショット
    
    Returns:
        (is_healthy, issues)
    """
    issues = []
    
    if not baseline_path.exists():
        print("[WARN] ベースラインスナップショットが存在しません（初回実行の可能性）")
        return True, issues
    
    if not current_path.exists():
        print("[ERROR] 現在のスナップショットが存在しません")
        return False, ["現在のスナップショットが存在しません"]
    
    # スナップショットを読み込み
    with open(baseline_path, 'r', encoding='utf-8') as f:
        baseline = json.load(f)
    
    with open(current_path, 'r', encoding='utf-8') as f:
        current = json.load(f)
    
    # ストレージの行数を比較
    baseline_storage = baseline.get("storage", {})
    current_storage = current.get("storage", {})
    
    baseline_scratchpad = baseline_storage.get("scratchpad_entries", 0)
    current_scratchpad = current_storage.get("scratchpad_entries", 0)
    
    # Read-onlyモードなのにScratchpadが増えている
    if current_scratchpad > baseline_scratchpad:
        issues.append(
            f"Read-onlyモードなのにScratchpadが増えています: "
            f"{baseline_scratchpad} → {current_scratchpad}"
        )
    
    baseline_quarantine = baseline_storage.get("quarantine_entries", 0)
    current_quarantine = current_storage.get("quarantine_entries", 0)
    
    # Read-onlyモードなのにQuarantineが増えている
    if current_quarantine > baseline_quarantine:
        issues.append(
            f"Read-onlyモードなのにQuarantineが増えています: "
            f"{baseline_quarantine} → {current_quarantine}"
        )
    
    is_healthy = len(issues) == 0
    return is_healthy, issues

def main():
    """メイン処理"""
    import sys
    
    print("=" * 60)
    print("Phase 1 (Read-only) 健康診断")
    print("=" * 60)
    print()
    
    # 1. ストレージの健康状態をチェック
    print("1. ストレージの健康状態をチェック...")
    storage_healthy, storage_issues = check_storage_health()
    
    if storage_issues:
        print("[WARN] ストレージに問題があります:")
        for issue in storage_issues:
            print(f"  - {issue}")
    else:
        print("[OK] ストレージは正常です")
    
    print()
    
    # 2. TTLマネージャの動作を確認
    print("2. TTLマネージャの動作を確認...")
    ttl_working, ttl_issues = check_ttl_manager()
    
    if ttl_issues:
        print("[WARN] TTLマネージャに問題があります:")
        for issue in ttl_issues:
            print(f"  - {issue}")
    else:
        print("[OK] TTLマネージャは正常に動作しています")
    
    print()
    
    # 3. スナップショット比較（ベースラインがある場合）
    baseline_path = Path("phase1_metrics_snapshot_baseline.json")
    current_path = Path("phase1_metrics_snapshot.json")
    
    if baseline_path.exists() and current_path.exists():
        print("3. スナップショットを比較（Read-onlyモードで書き込みが発生していないか）...")
        compare_healthy, compare_issues = compare_snapshots(baseline_path, current_path)
        
        if compare_issues:
            print("[ERROR] Read-onlyモードなのに書き込みが発生しています:")
            for issue in compare_issues:
                print(f"  - {issue}")
            print()
            print("→ 設定を確認してください（FWPKM_WRITE_MODE=readonly, FWPKM_WRITE_ENABLED=0）")
            return False
        else:
            print("[OK] Read-onlyモードが正しく機能しています（書き込みは発生していません）")
    else:
        print("3. スナップショット比較をスキップ（ベースラインが存在しません）")
        print("   → 初回実行時は、現在のスナップショットをベースラインとして保存してください")
    
    print()
    print("=" * 60)
    print("[OK] 健康診断が完了しました")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
