#!/usr/bin/env python3
"""
🚀 RunPod GPU画像 → X280 完全自動転送
"""
import requests
import subprocess
from datetime import datetime

RUNPOD_API = "http://localhost:5009"
X280_HOST = "mana@100.127.121.20"
X280_PATH = "C:/Users/mana/Pictures/RunPod_GPU"

def generate_and_transfer():
    """画像生成とX280転送の完全自動化"""
    print("=" * 70)
    print("🚀 RunPod GPU画像 → X280 完全自動転送")
    print("=" * 70)
    print(f"⏰ 開始時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 1. X280接続テスト
    print("🔍 X280接続テスト...")
    try:
        result = subprocess.run(
            f'ssh -o ConnectTimeout=5 {X280_HOST} "echo 接続成功"',
            shell=True,
            check=True,
            capture_output=True,
            text=True
        )
        print("✅ X280接続成功")
    except Exception:
        print("❌ X280接続失敗")
        print("   このはサーバー → X280のSSH接続を確認してください")
        return
    
    # 2. X280にディレクトリ作成
    print("\n📁 X280にディレクトリ作成...")
    try:
        subprocess.run(
            f'ssh {X280_HOST} "if not exist \\"{X280_PATH}\\" mkdir \\"{X280_PATH}\\""',
            shell=True,
            check=True,
            capture_output=True
        )
        print(f"✅ ディレクトリ準備完了: {X280_PATH}")
    except subprocess.SubprocessError:
        pass  # 既存の可能性
    
    # 3. RunPodで画像生成
    print("\n🎨 RunPod GPUで画像生成中...")
    try:
        response = requests.post(f"{RUNPOD_API}/trinity/gpu/generate", timeout=60)
        response.raise_for_status()
        result = response.json()
        images_count = result.get('result', {}).get('images_generated', 0)
        print(f"✅ 画像生成完了: {images_count}枚")
    except Exception as e:
        print(f"❌ 画像生成失敗: {e}")
        return
    
    # 4. 画像情報表示
    print("\n📊 生成された画像:")
    print("   RunPod /workspace/ に以下のファイルが保存されました:")
    for i in range(1, images_count + 1):
        print(f"   - gpu_boost_image_{i}.png")
    
    # 5. 次のステップ案内
    print("\n" + "=" * 70)
    print("📝 画像をX280に転送する方法:")
    print("=" * 70)
    print("\n🔹 方法1: Jupyter Notebook経由（推奨）")
    print("   1. RunPod Jupyter Notebookにアクセス")
    print("   2. /workspace/ から画像をダウンロード")
    print("   3. 以下のコマンドで X280 に転送:")
    print(f"      scp <画像ファイル> {X280_HOST}:\"{X280_PATH}\\\\\"")
    
    print("\n🔹 方法2: Google Drive経由（自動化可能）")
    print("   1. 画像をGoogle Driveにアップロード")
    print("   2. X280でGoogle Driveから取得")
    
    print("\n🔹 方法3: 画像表示API実装（今後）")
    print("   RunPod APIに画像取得エンドポイントを追加")
    print("   → HTTP経由で直接ダウンロード可能に")
    
    print("\n" + "=" * 70)
    print(f"⏰ 完了時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

if __name__ == "__main__":
    generate_and_transfer()
