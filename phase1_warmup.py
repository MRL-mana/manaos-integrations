#!/usr/bin/env python3
"""
Phase 1 (Read-only) Warm-up
APIに軽く負荷をかけてからスナップショットを取得
"""

import requests
import os
import time
from pathlib import Path

# .envファイルを読み込み
env_path = Path(".env")
if env_path.exists():
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:5105")
API_KEY = os.getenv("API_KEY", "")

def warmup_api(count: int = 20):
    """
    APIに軽く負荷をかける
    
    Args:
        count: リクエスト回数（デフォルト: 20回）
    """
    print(f"Warm-up: {count}回のリクエストを送信します...")
    
    headers = {"X-API-Key": API_KEY} if API_KEY else {}
    
    success_count = 0
    error_count = 0
    
    for i in range(count):
        try:
            response = requests.post(
                f"{API_BASE_URL}/api/memory/search",
                json={"query": f"warmup_test_{i}"},
                headers=headers,
                timeout=5
            )
            
            if response.status_code == 200:
                success_count += 1
            else:
                error_count += 1
                print(f"  [WARN] リクエスト {i+1}: ステータス {response.status_code}")
            
            # 少し間隔を空ける（レート制限対策）
            time.sleep(0.1)
            
        except Exception as e:
            error_count += 1
            print(f"  [ERROR] リクエスト {i+1}: {e}")
    
    print(f"Warm-up完了: 成功 {success_count}/{count}, エラー {error_count}/{count}")
    return success_count, error_count

def main():
    """メイン処理"""
    import sys
    
    print("=" * 60)
    print("Phase 1 (Read-only) Warm-up")
    print("=" * 60)
    print()
    
    # リクエスト回数を指定（デフォルト: 20回）
    count = 20
    if len(sys.argv) > 1:
        try:
            count = int(sys.argv[1])
        except ValueError:
            print(f"[WARN] 無効な回数: {sys.argv[1]}。デフォルトの20回を使用します")
    
    print(f"API URL: {API_BASE_URL}")
    print(f"API Key: {'設定済み' if API_KEY else '未設定'}")
    print()
    
    # Warm-up実行
    success_count, error_count = warmup_api(count)
    
    print()
    
    if error_count > count * 0.1:  # 10%以上エラー
        print("[WARN] エラー率が高いです。APIサーバーの状態を確認してください")
        return False
    
    print("[OK] Warm-upが完了しました")
    print()
    print("次のステップ:")
    print("1. スナップショットを取得: python phase1_metrics_snapshot.py phase1_metrics_snapshot_warmup.json")
    print("2. 健康診断を実行: python phase1_health_check.py")
    print("3. 自動判定を実行: python phase1_decision_maker.py phase1_metrics_snapshot_warmup.json")
    
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
