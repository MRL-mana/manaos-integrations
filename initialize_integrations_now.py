"""
統合システムを即座に初期化するスクリプト
"""

import sys
import os
from pathlib import Path
import time

# Windows環境でのエンコーディング問題を回避
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).parent))

print("=" * 70)
print("ManaOS統合システム - 即座初期化")
print("=" * 70)
print()

# 環境変数の設定確認
print("【環境変数の確認】")
if not os.getenv("N8N_BASE_URL"):
    # n8nのデフォルトURLを設定
    os.environ["N8N_BASE_URL"] = "http://localhost:5678"
    print(f"  [OK] N8N_BASE_URLを設定: {os.getenv('N8N_BASE_URL')}")
else:
    print(f"  [OK] N8N_BASE_URL: {os.getenv('N8N_BASE_URL')}")
print()

# 統合システムを初期化
print("【統合システムの初期化】")
try:
    from unified_api_server import initialize_integrations, integrations, initialization_status
    
    print("  初期化を開始...")
    initialize_integrations()
    
    # 初期化の完了を待つ（最大30秒）
    print("  初期化の完了を待機中...")
    max_wait = 30
    waited = 0
    while waited < max_wait:
        with initialization_status.get("_lock", type('obj', (object,), {'__enter__': lambda x: x, '__exit__': lambda x, *args: None})()) if hasattr(initialization_status, '_lock') else type('obj', (object,), {'__enter__': lambda x: x, '__exit__': lambda x, *args: None})():
            status = initialization_status.get('status', 'unknown')
            completed = len(initialization_status.get('completed', []))
            failed = len(initialization_status.get('failed', []))
            pending = len(initialization_status.get('pending', []))
        
        if status == 'ready' or (completed > 0 and pending == 0):
            break
        
        time.sleep(1)
        waited += 1
        if waited % 5 == 0:
            print(f"    待機中... ({waited}秒経過)")
    
    print()
    print("【初期化結果】")
    print(f"  状態: {initialization_status.get('status', 'unknown')}")
    print(f"  完了: {len(initialization_status.get('completed', []))}")
    print(f"  失敗: {len(initialization_status.get('failed', []))}")
    print(f"  保留: {len(initialization_status.get('pending', []))}")
    print()
    
    if initialization_status.get('completed'):
        print("  完了した統合:")
        for name in initialization_status.get('completed', []):
            print(f"    [OK] {name}")
        print()
    
    if initialization_status.get('failed'):
        print("  失敗した統合:")
        for name in initialization_status.get('failed', []):
            print(f"    [NG] {name}")
        print()
    
    print(f"  初期化済み統合数: {len(integrations)}")
    if integrations:
        print("  統合システム一覧:")
        for name, integration in integrations.items():
            available = False
            if hasattr(integration, 'is_available'):
                try:
                    available = integration.is_available()
                except Exception:
                    pass
            status_icon = "[OK]" if available else "[NG]"
            print(f"    {status_icon} {name}")
    
except Exception as e:
    print(f"[ERROR] 初期化エラー: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 70)

