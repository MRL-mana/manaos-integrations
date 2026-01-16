"""
LTX-2 バッチ動画生成の実用例
複数の画像から動画を生成
"""

import requests
import json
from pathlib import Path
from typing import List, Optional
import sys
import time

API_BASE = "http://localhost:9500"


def generate_batch_videos(
    image_paths: List[str],
    prompt: str = "a beautiful landscape, mountains, sunset, highly detailed",
    negative_prompt: str = "blurry, low quality, distorted",
    video_length_seconds: int = 5,
    use_two_pass: bool = True,
    use_nag: bool = True,
    use_res2s_sampler: bool = True,
    model_name: str = "ltx2-q8.gguf",
    delay_seconds: float = 2.0
) -> List[Optional[str]]:
    """
    複数の画像から動画をバッチ生成
    
    Args:
        image_paths: 開始画像のパスリスト
        prompt: プロンプト
        negative_prompt: ネガティブプロンプト
        video_length_seconds: 動画の長さ（秒）
        use_two_pass: 2段階生成を使用
        use_nag: NAGを使用
        use_res2s_sampler: res_2sサンプラーを使用
        model_name: モデルファイル名
        delay_seconds: 各リクエスト間の遅延（秒）
        
    Returns:
        プロンプトIDのリスト
    """
    print(f"🎬 バッチ動画生成を開始（{len(image_paths)}件）...")
    print(f"   プロンプト: {prompt}")
    print(f"   動画長: {video_length_seconds}秒")
    print(f"   遅延: {delay_seconds}秒\n")
    
    prompt_ids = []
    
    for i, image_path in enumerate(image_paths, 1):
        print(f"[{i}/{len(image_paths)}] {Path(image_path).name} を処理中...")
        
        # 画像パスの存在確認
        if not Path(image_path).exists():
            print(f"   ⚠️ 画像が見つかりません: {image_path}")
            prompt_ids.append(None)
            continue
        
        data = {
            "start_image_path": image_path,
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
                prompt_ids.append(prompt_id)
                print(f"   ✅ 生成開始: {prompt_id}")
            else:
                print(f"   ❌ 生成失敗: {response.status_code}")
                prompt_ids.append(None)
        except Exception as e:
            print(f"   ❌ エラー: {e}")
            prompt_ids.append(None)
        
        # 最後のリクエスト以外は遅延
        if i < len(image_paths):
            time.sleep(delay_seconds)
    
    # 結果サマリー
    success_count = sum(1 for pid in prompt_ids if pid is not None)
    print(f"\n📊 バッチ生成結果:")
    print(f"   成功: {success_count}/{len(image_paths)}")
    print(f"   失敗: {len(image_paths) - success_count}/{len(image_paths)}")
    
    return prompt_ids


def check_queue_status():
    """キュー状態を確認"""
    try:
        response = requests.get(f"{API_BASE}/api/ltx2/queue", timeout=10)
        if response.status_code == 200:
            queue_status = response.json()
            print("\n📊 現在のキュー状態:")
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


def main():
    """メイン関数"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="LTX-2バッチ動画生成（Super LTX-2設定）"
    )
    parser.add_argument(
        "image_paths",
        nargs="+",
        help="開始画像のパス（複数指定可能）"
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
        "--delay",
        type=float,
        default=2.0,
        help="各リクエスト間の遅延（秒）"
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
        help="生成後にキュー状態を確認"
    )
    
    args = parser.parse_args()
    
    # バッチ生成
    prompt_ids = generate_batch_videos(
        image_paths=args.image_paths,
        prompt=args.prompt,
        negative_prompt=args.negative_prompt,
        video_length_seconds=args.length,
        use_two_pass=not args.no_two_pass,
        use_nag=not args.no_nag,
        use_res2s_sampler=not args.no_res2s,
        model_name=args.model,
        delay_seconds=args.delay
    )
    
    # キュー状態を確認
    if args.check_queue:
        check_queue_status()
    
    print("\n💡 ヒント:")
    print("   - 生成状況はComfyUIのUIで確認できます: http://localhost:8188")
    print("   - 履歴確認: curl http://localhost:9500/api/ltx2/history")
    print("   - キュー確認: curl http://localhost:9500/api/ltx2/queue")
    
    # 成功したプロンプトIDを出力
    success_ids = [pid for pid in prompt_ids if pid is not None]
    if success_ids:
        print(f"\n✅ 生成開始したプロンプトID: {success_ids}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[INFO] 処理が中断されました")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] 予期しないエラー: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
