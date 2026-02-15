"""
SVI × Wan 2.2統合の実用例: ストーリー性のある長編動画生成
"""

import requests
import json
from pathlib import Path
from typing import List, Optional

API_BASE = "http://127.0.0.1:9510"


def create_story_video(
    start_image_path: str,
    story_prompts: List[str],
    segment_length_seconds: int = 5,
    steps: int = 6,
    motion_strength: float = 1.3
) -> Optional[List[str]]:
    """ストーリー性のある長編動画を生成"""
    print("🎬 ストーリー動画生成を開始...")
    print(f"   開始画像: {start_image_path}")
    print(f"   ストーリーセグメント数: {len(story_prompts)}")
    print(f"   各セグメント長: {segment_length_seconds}秒")
    
    for i, prompt in enumerate(story_prompts, 1):
        print(f"     {i}. {prompt}")
    
    data = {
        "start_image_path": start_image_path,
        "story_prompts": story_prompts,
        "segment_length_seconds": segment_length_seconds,
        "steps": steps,
        "motion_strength": motion_strength
    }
    
    response = requests.post(
        f"{API_BASE}/api/svi/story",
        json=data,
        timeout=60
    )
    
    if response.status_code == 200:
        result = response.json()
        execution_ids = result.get("execution_ids", [])
        print(f"✓ ストーリー動画生成が開始されました")
        print(f"   実行ID数: {len(execution_ids)}")
        for i, exec_id in enumerate(execution_ids, 1):
            print(f"     セグメント{i}: {exec_id[:20]}...")
        return execution_ids
    else:
        print(f"✗ 生成失敗: {response.status_code}")
        print(f"   レスポンス: {response.text}")
        return None


def extend_video(
    previous_video_path: str,
    prompt: str = "continue the scene smoothly",
    extend_seconds: int = 5,
    steps: int = 6,
    motion_strength: float = 1.3
) -> Optional[str]:
    """既存の動画を延長"""
    print("\n🔄 動画延長を開始...")
    print(f"   前の動画: {previous_video_path}")
    print(f"   プロンプト: {prompt}")
    print(f"   延長秒数: {extend_seconds}秒")
    
    data = {
        "previous_video_path": previous_video_path,
        "prompt": prompt,
        "extend_seconds": extend_seconds,
        "steps": steps,
        "motion_strength": motion_strength
    }
    
    response = requests.post(
        f"{API_BASE}/api/svi/extend",
        json=data,
        timeout=30
    )
    
    if response.status_code == 200:
        result = response.json()
        prompt_id = result.get("prompt_id")
        print(f"✓ 動画延長が開始されました")
        print(f"   プロンプトID: {prompt_id}")
        return prompt_id
    else:
        print(f"✗ 延長失敗: {response.status_code}")
        return None


def main():
    """メイン処理"""
    print("="*60)
    print("SVI × Wan 2.2統合: ストーリー動画生成の実例")
    print("="*60)
    
    # 使用例: 画像パスを指定
    start_image_path = input("開始画像のパスを入力してください（Enterでスキップ）: ").strip()
    
    if not start_image_path:
        print("\n[スキップ] 画像パスが指定されていないため、生成をスキップします")
        print("\n使用例:")
        print("  python svi_example_story_video.py")
        print("  開始画像のパス: /path/to/image.png")
        print("\nストーリー例:")
        print("  1. sunrise over mountains")
        print("  2. birds flying in the sky")
        print("  3. sunset over ocean")
        return
    
    if not Path(start_image_path).exists():
        print(f"\n[エラー] 画像ファイルが見つかりません: {start_image_path}")
        return
    
    # ストーリープロンプトを入力
    print("\nストーリープロンプトを入力してください（1行1セグメント、空行で終了）:")
    story_prompts = []
    while True:
        prompt = input(f"  セグメント{len(story_prompts) + 1}: ").strip()
        if not prompt:
            break
        story_prompts.append(prompt)
    
    if not story_prompts:
        # デフォルトのストーリー
        story_prompts = [
            "sunrise over mountains, peaceful morning",
            "birds flying in the sky, graceful movement",
            "sunset over ocean, beautiful colors"
        ]
        print("\nデフォルトのストーリーを使用します:")
        for i, prompt in enumerate(story_prompts, 1):
            print(f"  {i}. {prompt}")
    
    # ストーリー動画生成
    execution_ids = create_story_video(
        start_image_path=start_image_path,
        story_prompts=story_prompts,
        segment_length_seconds=5,
        steps=6,
        motion_strength=1.3
    )
    
    if execution_ids:
        print("\n" + "="*60)
        print("処理完了")
        print(f"実行ID数: {len(execution_ids)}")
        print("ComfyUIで各セグメントの生成進行状況を確認できます")
        print("="*60)
        
        # 動画延長の例（オプション）
        extend = input("\n最初の動画を延長しますか？ (y/n): ").strip().lower()
        if extend == 'y':
            previous_video_path = input("延長する動画のパス: ").strip()
            if previous_video_path and Path(previous_video_path).exists():
                extend_prompt = input("延長プロンプト（Enterでデフォルト）: ").strip()
                if not extend_prompt:
                    extend_prompt = "continue the scene smoothly"
                
                extend_video(
                    previous_video_path=previous_video_path,
                    prompt=extend_prompt,
                    extend_seconds=5
                )
    else:
        print("\n[エラー] ストーリー動画生成に失敗しました")


if __name__ == "__main__":
    main()











