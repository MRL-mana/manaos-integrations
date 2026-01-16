"""手動で初期化をテストするスクリプト"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

print("統合システムの初期化をテスト中...")

try:
    from unified_api_server import initialize_integrations, integrations, initialization_status
    
    print("初期化前の状態:")
    print(f"  統合数: {len(integrations)}")
    print(f"  ステータス: {initialization_status.get('status')}")
    
    print("\n初期化を実行中...")
    initialize_integrations()
    
    print("\n初期化後の状態:")
    print(f"  統合数: {len(integrations)}")
    print(f"  ステータス: {initialization_status.get('status')}")
    print(f"  完了: {len(initialization_status.get('completed', []))}")
    print(f"  失敗: {len(initialization_status.get('failed', []))}")
    
    if initialization_status.get('completed'):
        print(f"\n完了した統合: {', '.join(initialization_status.get('completed', []))}")
    
    if initialization_status.get('failed'):
        print(f"\n失敗した統合: {', '.join(initialization_status.get('failed', []))}")
        
except Exception as e:
    print(f"エラー: {e}")
    import traceback
    traceback.print_exc()
