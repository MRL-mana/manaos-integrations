"""
LTX-2統合の実用例: シンプルな動画生成（Super LTX-2設定）
"""

import requests
import json
from pathlib import Path
from typing import Optional
import sys

API_BASE = "http://localhost:9500"


def generate_simple_video(
    start_image_path: str,
    prompt: str = "a beautiful landscape, mountains, sunset, highly detailed",
    negative_prompt: str = "blurry, low quality, distorted",
    video_length_seconds: int = 5,
    use_two_pass: bool = True,
    use_nag: bool = True,
    use_res2s_sampler: bool = True,
    model_name: str = "ltx2-q8.gguf"
) -> Optional[str]:
    """
    シンプルな動画を生成（Super LTX-2設定）
    
    Args:
        start_image_path: 開始画像のパス
        prompt: プロンプト
        negative_prompt: ネガティブプロンプト
        video_length_seconds: 動画の長さ（秒）
        use_two_pass: 2段階生成を使用（推奨）
        use_nag: NAGを使用（推奨）
        use_res2s_sampler: res_2sサンプラーを使用（推奨）
        model_name: モデルファイル名
        
    Returns:
        プロンプトID（成功時）、None（失敗時）
    """
    print("🎬 LTX-2動画生成を開始（Super LTX-2設定）...")
    print(f"   開始画像: {start_image_path}")
    print(f"   プロンプト: {prompt}")
    print(f"   動画長: {video_length_seconds}秒")
    print(f"   2段階生成: {use_two_pass}")
    print(f"   NAG: {use_nag}")
    print(f"   res_2sサンプラー: {use_res2s_sampler}")
    
    # 画像パスの存在確認
    if not Path(start_image_path).exists():
        print(f"❌ 画像が見つかりません: {start_image_path}")
        return None
    
    data = {
        "start_image_path": start_image_path,
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "video_length_seconds": video_length_seconds,
        "width": 512,
        "height": 512,
        "use_two_pass": use_two_pass,
        "use_nag": use_nag,
        "use_res2s_sampler": use_res2s_sampler,
        "model_name": model_name
    }
    
    try:
        response = requests.post(
            f"{API_BASE}/api/ltx2/generate",
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            prompt_id = result.get("prompt_id")
            print(f"✅ 動画生成が開始されました")
            print(f"   プロンプトID: {prompt_id}")
            return prompt_id
        else:
            print(f"❌ 生成失敗: {response.status_code}")
            print(f"   レスポンス: {response.text}")
            return None
    except requests.exceptions.ConnectionError:
        print(f"❌ APIサーバーに接続できません: {API_BASE}")
        print("   unified_api_server.pyが起動しているか確認してください")
        return None
    except Exception as e:
        print(f"❌ エラー: {e}")
        return None


def check_queue_status():
    """キュー状態を確認"""
    try:
        response = requests.get(f"{API_BASE}/api/ltx2/queue", timeout=10)
        if response.status_code == 200:
            queue_status = response.json()
            print("\n📊 キュー状態:")
            if "queue_running" in queue_status:
                print(f"   実行中: {len(queue_status['queue_running'])}件")
            if "queue_pending" in queue_status:
                print(f"   待機中: {len(queue_status['queue_pending'])}件")
            return queue_status
        else:
            print(f"⚠️ キュー状態取得エラー: {response.status_code}")
            return None
    except Exception as e:
        print(f"⚠️ キュー状態取得エラー: {e}")
        return None


def check_status(prompt_id: str):
    """実行状態を確認"""
    try:
        response = requests.get(
            f"{API_BASE}/api/ltx2/status/{prompt_id}",
            timeout=10
        )
        if response.status_code == 200:
            status = response.json()
            print(f"\n📈 実行状態 (ID: {prompt_id}):")
            print(f"   ステータス: {status.get('status', 'unknown')}")
            return status
        else:
            print(f"⚠️ 状態取得エラー: {response.status_code}")
            return None
    except Exception as e:
        print(f"⚠️ 状態取得エラー: {e}")
        return None


def main():
    """メイン関数"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="LTX-2動画生成（Super LTX-2設定）"
    )
    parser.add_argument(
        "image_path",
        help="開始画像のパス"
    )
    parser.add_argument(
        "--prompt",
        default="a beautiful landscape, mountains, sunset, highly detailed",
        help="プロンプト"
    )
    parser.add_argument(
        "--negative-prompt",
        default="blurry, low quality, distorted",
        help="ネガティブプロンプト"
    )
    parser.add_argument(
        "--length",
        type=int,
        default=5,
        help="動画の長さ（秒）"
    )
    parser.add_argument(
        "--no-two-pass",
        action="store_true",
        help="2段階生成を無効化"
    )
    parser.add_argument(
        "--no-nag",
        action="store_true",
        help="NAGを無効化"
    )
    parser.add_argument(
        "--no-res2s",
        action="store_true",
        help="res_2sサンプラーを無効化"
    )
    parser.add_argument(
        "--model",
        default="ltx2-q8.gguf",
        help="モデルファイル名"
    )
    parser.add_argument(
        "--check-queue",
        action="store_true",
        help="キュー状態を確認"
    )
    
    args = parser.parse_args()
    
    # 動画生成
    prompt_id = generate_simple_video(
        start_image_path=args.image_path,
        prompt=args.prompt,
        negative_prompt=args.negative_prompt,
        video_length_seconds=args.length,
        use_two_pass=not args.no_two_pass,
        use_nag=not args.no_nag,
        use_res2s_sampler=not args.no_res2s,
        model_name=args.model
    )
    
    if prompt_id:
        # キュー状態を確認
        if args.check_queue:
            check_queue_status()
        
        # 実行状態を確認
        check_status(prompt_id)
        
        print("\n💡 ヒント:")
        print("   - 生成状況はComfyUIのUIで確認できます: http://localhost:8188")
        print("   - 状態確認: python ltx2_example_simple_video.py <image> --check-queue")
        print("   - 履歴確認: curl http://localhost:9500/api/ltx2/history")
    
    return prompt_id is not None


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n[INFO] 処理が中断されました")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] 予期しないエラー: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
