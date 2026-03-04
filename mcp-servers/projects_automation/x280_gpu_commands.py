#!/usr/bin/env python3
"""
X280 GPU コマンドライン
X280からManaを通してRunPod GPUを操作するコマンド集
"""

import requests
import sys
import time

class X280GPUCommands:
    """X280 GPU コマンドライン"""
    
    def __init__(self):
        self.このは_server = "http://localhost:5000"
    
    def send_request(self, endpoint, data=None):
        """このはサーバーにリクエスト送信"""
        try:
            if data:
                response = requests.post(f"{self.このは_server}{endpoint}", json=data, timeout=60)
            else:
                response = requests.get(f"{self.このは_server}{endpoint}", timeout=60)
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"HTTP {response.status_code}: {response.text}"}
        except Exception as e:
            return {"error": str(e)}
    
    def status(self):
        """GPU状態確認"""
        print("🔥 X280指示: GPU状態確認中...")
        result = self.send_request("/api/gpu_status")
        
        if result and "error" not in result:
            print("✅ X280指示によるGPU状態確認完了")
            return True
        else:
            print(f"❌ GPU状態確認失敗: {result.get('error', 'Unknown error') if result else 'Connection failed'}")
            return False
    
    def images(self, count=4):
        """画像生成"""
        print(f"🎨 X280指示: {count}枚の画像生成中...")
        result = self.send_request("/api/generate_images")
        
        if result and "error" not in result:
            print(f"✅ X280指示による{count}枚の画像生成完了")
            return True
        else:
            print(f"❌ 画像生成失敗: {result.get('error', 'Unknown error') if result else 'Connection failed'}")
            return False
    
    def learning(self, epochs=50):
        """深層学習"""
        print(f"🧠 X280指示: {epochs}エポックの深層学習中...")
        result = self.send_request("/api/deep_learning")
        
        if result and "error" not in result:
            print(f"✅ X280指示による{epochs}エポックの深層学習完了")
            return True
        else:
            print(f"❌ 深層学習失敗: {result.get('error', 'Unknown error') if result else 'Connection failed'}")
            return False
    
    def transformers(self):
        """Transformers実行"""
        print("🤖 X280指示: Transformers実行中...")
        result = self.send_request("/api/transformers")
        
        if result and "error" not in result:
            print("✅ X280指示によるTransformers実行完了")
            return True
        else:
            print(f"❌ Transformers実行失敗: {result.get('error', 'Unknown error') if result else 'Connection failed'}")
            return False
    
    def demo(self):
        """全機能デモ"""
        print("🚀 X280 → このはサーバー → Trinity達 → RunPod GPU デモ開始")
        print("=" * 60)
        
        self.status()
        time.sleep(1)
        self.images(6)
        time.sleep(1)
        self.learning(30)
        time.sleep(1)
        self.transformers()
        
        print("🎉 X280デモ完了！")

def print_help():
    """ヘルプ表示"""
    print("🚀 X280 GPU コマンドライン")
    print("=" * 50)
    print("使用方法:")
    print("  python3 x280_gpu_commands.py <コマンド> [オプション]")
    print("")
    print("コマンド:")
    print("  status                    GPU状態確認")
    print("  images [枚数]            画像生成 (デフォルト: 4枚)")
    print("  learning [エポック]      深層学習 (デフォルト: 50エポック)")
    print("  transformers             Transformers実行")
    print("  demo                     全機能デモ実行")
    print("  help                     このヘルプを表示")
    print("")
    print("例:")
    print("  python3 x280_gpu_commands.py status")
    print("  python3 x280_gpu_commands.py images 8")
    print("  python3 x280_gpu_commands.py learning 100")
    print("  python3 x280_gpu_commands.py demo")

def main():
    """メイン実行"""
    if len(sys.argv) < 2:
        print_help()
        return
    
    command = sys.argv[1]
    args = sys.argv[2:] if len(sys.argv) > 2 else []
    
    if command == "help":
        print_help()
        return
    
    x280 = X280GPUCommands()
    
    if command == "status":
        x280.status()
    elif command == "images":
        count = int(args[0]) if args else 4
        x280.images(count)
    elif command == "learning":
        epochs = int(args[0]) if args else 50
        x280.learning(epochs)
    elif command == "transformers":
        x280.transformers()
    elif command == "demo":
        x280.demo()
    else:
        print(f"❌ 不明なコマンド: {command}")
        print_help()

if __name__ == "__main__":
    main()
