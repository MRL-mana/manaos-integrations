#!/usr/bin/env python3
"""
🎨 RunPod GPU生成画像 → X280自動転送システム
"""
import requests
import subprocess
import os

class RunPodImageTransfer:
    def __init__(self):
        self.runpod_api = "https://8uv33dh7cewgeq-8080.proxy.runpod.net"
        self.x280_host = "x280"
        self.x280_path = "C:/Users/mana/Pictures/RunPod_GPU_Images"
        self.local_temp = "/tmp/runpod_images"
        
    def setup_local_temp(self):
        """ローカル一時ディレクトリ作成"""
        os.makedirs(self.local_temp, exist_ok=True)
        print(f"📁 一時ディレクトリ: {self.local_temp}")
    
    def generate_images(self):
        """RunPodで画像生成"""
        print("🎨 RunPod GPUで画像生成中...")
        try:
            response = requests.post(
                f"{self.runpod_api}/gpu/image_generation",
                timeout=60
            )
            response.raise_for_status()
            result = response.json()
            print(f"✅ 画像生成完了: {result.get('images_generated', 0)}枚")
            return result
        except Exception as e:
            print(f"❌ 画像生成失敗: {e}")
            return None
    
    def setup_x280_directory(self):
        """X280に保存ディレクトリ作成"""
        print(f"📁 X280にディレクトリ作成: {self.x280_path}")
        try:
            cmd = f'ssh {self.x280_host} "mkdir -p \\"{self.x280_path}\\""'
            subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
            print("✅ X280ディレクトリ作成完了")
            return True
        except Exception as e:
            print(f"⚠️  ディレクトリ作成スキップ: {e}")
            return True  # 既に存在する可能性があるので続行
    
    def download_images_from_runpod(self):
        """RunPodから画像をダウンロード（Web Terminal経由）"""
        print("📥 RunPodから画像ダウンロード...")
        print("⚠️  注意: 現在RunPodからの自動ダウンロードは未実装")
        print("   → Jupyter Notebookから手動ダウンロードが必要です")
        print("")
        print("🔧 今すぐ実装する場合は、以下の方法があります:")
        print("   1. RunPod APIに画像取得エンドポイントを追加")
        print("   2. HTTP経由で画像をダウンロード")
        return False
    
    def transfer_local_to_x280(self, local_file, x280_filename):
        """ローカルファイルをX280に転送"""
        print(f"📤 X280に転送中: {x280_filename}")
        try:
            # Windows パス形式に変換
            x280_file = f"{self.x280_path}\\{x280_filename}"
            # SCPでX280に転送
            cmd = f'scp "{local_file}" {self.x280_host}:"{x280_file}"'
            result = subprocess.run(
                cmd, 
                shell=True, 
                check=True, 
                capture_output=True, 
                text=True
            )
            print(f"✅ 転送完了: {x280_filename}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ 転送失敗: {e}")
            print(f"   stderr: {e.stderr}")
            return False
    
    def test_x280_connection(self):
        """X280接続テスト"""
        print("🔍 X280接続テスト...")
        try:
            result = subprocess.run(
                f'ssh {self.x280_host} "echo X280接続成功"',
                shell=True,
                check=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            print(f"✅ {result.stdout.strip()}")
            return True
        except Exception as e:
            print(f"❌ X280接続失敗: {e}")
            return False

def main():
    print("=" * 70)
    print("🎨 RunPod GPU画像 → X280 自動転送システム")
    print("=" * 70)
    print()
    
    transfer = RunPodImageTransfer()
    
    # 1. X280接続テスト
    if not transfer.test_x280_connection():
        print("\n❌ X280に接続できません。Tailscale接続を確認してください。")
        return
    
    # 2. ローカル一時ディレクトリ作成
    transfer.setup_local_temp()
    
    # 3. X280にディレクトリ作成
    transfer.setup_x280_directory()
    
    # 4. RunPodで画像生成
    result = transfer.generate_images()
    if not result:
        return
    
    # 5. 画像転送の説明
    print("\n" + "=" * 70)
    print("📝 次のステップ（手動）:")
    print("=" * 70)
    print("\n1️⃣ RunPod Jupyter Notebookにアクセス:")
    print("   https://www.runpod.io/console/pods")
    print("   → 'Connect' → 'Start Jupyter Notebook'")
    print("\n2️⃣ /workspace/ フォルダを開く")
    print("   → gpu_boost_image_1.png ~ 4.png をダウンロード")
    print("\n3️⃣ このスクリプトを実行して画像をX280に転送:")
    print("   python3 /root/runpod_to_x280_image_transfer.py --upload /path/to/image.png")
    print("\n" + "=" * 70)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 2 and sys.argv[1] == "--upload":
        # 画像アップロードモード
        transfer = RunPodImageTransfer()
        local_file = sys.argv[2]
        filename = os.path.basename(local_file)
        
        if not os.path.exists(local_file):
            print(f"❌ ファイルが見つかりません: {local_file}")
            sys.exit(1)
        
        transfer.setup_x280_directory()
        if transfer.transfer_local_to_x280(local_file, filename):
            print("\n🎉 成功！X280で確認してください:")
            print(f"   {transfer.x280_path}\\{filename}")
    else:
        # 通常モード
        main()
