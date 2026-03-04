"""
SVI × Wan 2.2統合の実用例: バッチ動画生成
複数の動画を一括で生成
"""

import requests
import json
import os
from pathlib import Path
from typing import List, Dict, Any

try:
    from manaos_integrations._paths import UNIFIED_API_PORT
except Exception:  # pragma: no cover
    try:
        from _paths import UNIFIED_API_PORT  # type: ignore
    except Exception:  # pragma: no cover
        UNIFIED_API_PORT = int(os.getenv("UNIFIED_API_PORT", "9510"))

API_BASE = os.getenv("MANAOS_INTEGRATION_API_URL", f"http://127.0.0.1:{UNIFIED_API_PORT}")


def batch_generate_videos(batch_items: List[Dict[str, Any]]) -> List[str]:
    """複数の動画を一括生成"""
    print(f"🎬 バッチ動画生成を開始... ({len(batch_items)}件)")
    
    for i, item in enumerate(batch_items, 1):
        print(f"   {i}. {item.get('start_image_path', 'N/A')}")
        print(f"      プロンプト: {item.get('prompt', 'N/A')[:50]}...")
    
    data = {
        "batch_items": batch_items
    }
    
    response = requests.post(
        f"{API_BASE}/api/svi/batch/generate",
        json=data,
        timeout=60
    )
    
    if response.status_code == 200:
        result = response.json()
        execution_ids = result.get("execution_ids", [])
        total = result.get("total", 0)
        success = result.get("success", 0)
        
        print(f"✓ バッチ生成が開始されました")
        print(f"   総数: {total}件")
        print(f"   成功: {success}件")
        print(f"   実行ID数: {len(execution_ids)}")
        
        return execution_ids
    else:
        print(f"✗ バッチ生成失敗: {response.status_code}")
        print(f"   レスポンス: {response.text}")
        return []


def check_status(prompt_id: str):
    """実行状態を確認"""
    print(f"\n📊 実行状態を確認中... (ID: {prompt_id[:20]}...)")
    
    response = requests.get(
        f"{API_BASE}/api/svi/status/{prompt_id}",
        timeout=10
    )
    
    if response.status_code == 200:
        result = response.json()
        status = result.get("status", "unknown")
        print(f"   ステータス: {status}")
        return result
    elif response.status_code == 404:
        print(f"   [INFO] 実行IDが見つかりません（まだ履歴に反映されていない可能性があります）")
        return None
    else:
        print(f"✗ 取得失敗: {response.status_code}")
        return None


def main():
    """メイン処理"""
    print("="*60)
    print("SVI × Wan 2.2統合: バッチ動画生成の実例")
    print("="*60)
    
    # バッチ生成の例
    # 実際の使用時は、存在する画像パスを指定してください
    print("\nバッチ生成アイテムを設定してください")
    print("（Enterでスキップしてデフォルト例を表示）")
    
    batch_items = []
    
    # 最初のアイテム
    image_path1 = input("\n画像パス1（Enterでスキップ）: ").strip()
    if image_path1:
        prompt1 = input("プロンプト1（Enterでデフォルト）: ").strip()
        if not prompt1:
            prompt1 = "beautiful landscape, cinematic, smooth motion"
        
        batch_items.append({
            "start_image_path": image_path1,
            "prompt": prompt1,
            "video_length_seconds": 5,
            "steps": 6,
            "motion_strength": 1.3
        })
    
    # 2つ目のアイテム
    image_path2 = input("\n画像パス2（Enterでスキップ）: ").strip()
    if image_path2:
        prompt2 = input("プロンプト2（Enterでデフォルト）: ").strip()
        if not prompt2:
            prompt2 = "ocean waves, peaceful, serene"
        
        batch_items.append({
            "start_image_path": image_path2,
            "prompt": prompt2,
            "video_length_seconds": 5,
            "steps": 6,
            "motion_strength": 1.3
        })
    
    if not batch_items:
        print("\n[スキップ] 画像パスが指定されていないため、バッチ生成をスキップします")
        print("\n使用例:")
        print("  python svi_example_batch_generation.py")
        print("  画像パス1: /path/to/image1.png")
        print("  プロンプト1: beautiful landscape")
        print("  画像パス2: /path/to/image2.png")
        print("  プロンプト2: ocean waves")
        return
    
    # バッチ生成実行
    execution_ids = batch_generate_videos(batch_items)
    
    if execution_ids:
        print("\n" + "="*60)
        print("バッチ生成完了")
        print(f"実行ID数: {len(execution_ids)}")
        print("="*60)
        
        # 各実行IDの状態を確認（オプション）
        check_all = input("\n各実行IDの状態を確認しますか？ (y/n): ").strip().lower()
        if check_all == 'y':
            for i, exec_id in enumerate(execution_ids, 1):
                print(f"\n[{i}/{len(execution_ids)}]")
                check_status(exec_id)
    else:
        print("\n[エラー] バッチ生成に失敗しました")


if __name__ == "__main__":
    main()











