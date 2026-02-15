"""
SVI × Wan 2.2統合の実用例: シンプルな動画生成
"""

import requests
import json
from pathlib import Path
from typing import Optional

API_BASE = "http://127.0.0.1:9510"


def generate_simple_video(
    start_image_path: str,
    prompt: str = "beautiful landscape, cinematic, smooth motion",
    video_length_seconds: int = 5,
    steps: int = 6,
    motion_strength: float = 1.3
) -> Optional[str]:
    """シンプルな動画を生成"""
    print("🎬 動画生成を開始...")
    print(f"   開始画像: {start_image_path}")
    print(f"   プロンプト: {prompt}")
    print(f"   動画長: {video_length_seconds}秒")
    
    data = {
        "start_image_path": start_image_path,
        "prompt": prompt,
        "video_length_seconds": video_length_seconds,
        "steps": steps,
        "motion_strength": motion_strength,
        "sage_attention": True,
        "extend_enabled": False
    }
    
    response = requests.post(
        f"{API_BASE}/api/svi/generate",
        json=data,
        timeout=30
    )
    
    if response.status_code == 200:
        result = response.json()
        prompt_id = result.get("prompt_id")
        print(f"✓ 動画生成が開始されました")
        print(f"   プロンプトID: {prompt_id}")
        return prompt_id
    else:
        print(f"✗ 生成失敗: {response.status_code}")
        print(f"   レスポンス: {response.text}")
        return None


def check_queue_status():
    """キュー状態を確認"""
    print("\n📊 キュー状態を確認中...")
    
    response = requests.get(
        f"{API_BASE}/api/svi/queue",
        timeout=10
    )
    
    if response.status_code == 200:
        result = response.json()
        running = result.get("queue_running", 0)
        pending = result.get("queue_pending", 0)
        print(f"   実行中: {running}件")
        print(f"   待機中: {pending}件")
        return result
    else:
        print(f"✗ 取得失敗: {response.status_code}")
        return None


def get_history(max_items: int = 5):
    """実行履歴を取得"""
    print(f"\n📜 実行履歴を取得中... (最新{max_items}件)")
    
    response = requests.get(
        f"{API_BASE}/api/svi/history?max_items={max_items}",
        timeout=10
    )
    
    if response.status_code == 200:
        result = response.json()
        history = result.get("history", [])
        print(f"✓ 履歴取得成功: {len(history)}件")
        for i, item in enumerate(history, 1):
            print(f"   {i}. ID: {item.get('prompt_id', 'N/A')[:20]}...")
            print(f"      ステータス: {item.get('status', 'N/A')}")
        return history
    else:
        print(f"✗ 取得失敗: {response.status_code}")
        return None


def main():
    """メイン処理"""
    print("="*60)
    print("SVI × Wan 2.2統合: シンプルな動画生成の実例")
    print("="*60)
    
    # 使用例: 画像パスを指定
    # 実際の使用時は、存在する画像パスを指定してください
    start_image_path = input("開始画像のパスを入力してください（Enterでスキップ）: ").strip()
    
    if not start_image_path:
        print("\n[スキップ] 画像パスが指定されていないため、生成をスキップします")
        print("\n使用例:")
        print("  python svi_example_simple_video.py")
        print("  開始画像のパス: /path/to/image.png")
        return
    
    if not Path(start_image_path).exists():
        print(f"\n[エラー] 画像ファイルが見つかりません: {start_image_path}")
        return
    
    # プロンプトを入力
    prompt = input("プロンプトを入力してください（Enterでデフォルト）: ").strip()
    if not prompt:
        prompt = "beautiful landscape, cinematic, smooth motion"
    
    # 動画生成
    prompt_id = generate_simple_video(
        start_image_path=start_image_path,
        prompt=prompt,
        video_length_seconds=5,
        steps=6,
        motion_strength=1.3
    )
    
    if prompt_id:
        # キュー状態確認
        check_queue_status()
        
        # 履歴確認
        get_history(5)
        
        print("\n" + "="*60)
        print("処理完了")
        print(f"プロンプトID: {prompt_id}")
        print("ComfyUIで動画生成の進行状況を確認できます")
        print("="*60)
    else:
        print("\n[エラー] 動画生成に失敗しました")


if __name__ == "__main__":
    main()











