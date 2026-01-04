"""
SVI × Wan 2.2 テスト動画生成スクリプト
実際に動画を生成してテストします
"""

import sys
import os
from pathlib import Path
import io

# Windows環境での文字エンコーディング設定
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).parent))

from svi_wan22_video_integration import SVIWan22VideoIntegration

def find_test_image():
    """テスト用の画像を探す"""
    search_paths = [
        Path("C:/Users/mana4/OneDrive/Desktop"),
        Path("C:/Users/mana4/OneDrive/Desktop/output"),
        Path("C:/Users/mana4/OneDrive/Desktop/mufufu_cyberrealistic_10"),
        Path("C:/Users/mana4/OneDrive/Desktop/mufufu_combined_10"),
    ]
    
    image_extensions = ['.png', '.jpg', '.jpeg']
    
    for search_path in search_paths:
        if not search_path.exists():
            continue
        
        for ext in image_extensions:
            images = list(search_path.glob(f"*{ext}"))
            if images:
                return images[0]
    
    return None

def main():
    """メイン関数"""
    print("=" * 60)
    print("SVI × Wan 2.2 テスト動画生成")
    print("=" * 60)
    print()
    
    # ComfyUI接続確認
    print("[1] ComfyUIへの接続確認...")
    svi = SVIWan22VideoIntegration(base_url="http://localhost:8188")
    
    if not svi.is_available():
        print("   [NG] ComfyUIに接続できません")
        print("   ComfyUIを起動してください:")
        print("   cd C:\\ComfyUI")
        print("   python main.py --port 8188")
        return False
    
    print("   [OK] ComfyUIに接続できました")
    print()
    
    # テスト画像の検索
    print("[2] テスト画像の検索...")
    test_image = find_test_image()
    
    if not test_image:
        print("   [WARN] テスト画像が見つかりませんでした")
        print("   画像パスを手動で指定してください")
        print()
        image_path = input("画像パスを入力してください（Enterでスキップ）: ").strip()
        if not image_path:
            print("   スキップしました")
            return False
        test_image = Path(image_path)
    
    if not test_image.exists():
        print(f"   [NG] 画像が見つかりません: {test_image}")
        return False
    
    print(f"   [OK] テスト画像が見つかりました: {test_image}")
    print()
    
    # 動画生成
    print("[3] 動画生成を開始...")
    print(f"   開始画像: {test_image}")
    print("   プロンプト: a beautiful landscape with dynamic camera movement")
    print("   動画の長さ: 5秒")
    print("   ステップ数: 6")
    print("   モーション強度: 1.3")
    print()
    
    try:
        prompt_id = svi.generate_video(
            start_image_path=str(test_image),
            prompt="a beautiful landscape with dynamic camera movement",
            video_length_seconds=5,
            steps=6,
            motion_strength=1.3,
            sage_attention=True
        )
        
        if prompt_id:
            print(f"   [OK] 動画生成が開始されました")
            print(f"   実行ID: {prompt_id}")
            print()
            print("   生成状況を確認するには:")
            print("   - ComfyUIのUIで確認: http://localhost:8188")
            print("   - キュー状態を確認:")
            print("     python -c \"from svi_wan22_video_integration import SVIWan22VideoIntegration; svi = SVIWan22VideoIntegration(); print(svi.get_queue_status())\"")
            return True
        else:
            print("   [NG] 動画生成に失敗しました")
            print("   エラーログを確認してください")
            return False
            
    except Exception as e:
        print(f"   [ERROR] エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        success = main()
        if success:
            print()
            print("=" * 60)
            print("[OK] テスト動画生成が開始されました！")
            print("=" * 60)
        else:
            print()
            print("=" * 60)
            print("[NG] テスト動画生成に失敗しました")
            print("=" * 60)
    except KeyboardInterrupt:
        print("\n\n中断されました")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)











