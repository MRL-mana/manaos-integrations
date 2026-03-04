#!/usr/bin/env python3
"""
🌟 Trinity ⇄ RunPod GPU Bridge
Trinity達がRunPod GPUを自動操作するための統合ブリッジ
"""
import requests
import json
import sys
from datetime import datetime

class TrinityRunPodBridge:
    def __init__(self):
        self.runpod_api_url = "https://8uv33dh7cewgeq-8080.proxy.runpod.net"
        self.log_file = "/root/logs/trinity_runpod_bridge.log"
        
    def log(self, message):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_msg = f"[{timestamp}] {message}"
        print(log_msg)
        try:
            with open(self.log_file, 'a') as f:
                f.write(log_msg + '\n')
        except IOError:
            pass
    
    def get_gpu_status(self):
        """GPU状態取得"""
        try:
            self.log("🔍 GPU状態取得開始")
            response = requests.get(f"{self.runpod_api_url}/", timeout=10)
            response.raise_for_status()
            data = response.json()
            self.log(f"✅ GPU状態: {data}")
            return {'success': True, 'data': data}
        except Exception as e:
            self.log(f"❌ GPU状態取得失敗: {e}")
            return {'success': False, 'error': str(e)}
    
    def generate_images(self):
        """GPU画像生成"""
        try:
            self.log("🎨 GPU画像生成開始")
            response = requests.post(f"{self.runpod_api_url}/gpu/image_generation", timeout=30)
            response.raise_for_status()
            data = response.json()
            self.log(f"✅ 画像生成完了: {data}")
            return {'success': True, 'data': data}
        except Exception as e:
            self.log(f"❌ 画像生成失敗: {e}")
            return {'success': False, 'error': str(e)}
    
    def run_deep_learning(self):
        """GPU深層学習"""
        try:
            self.log("🧠 GPU深層学習開始")
            response = requests.post(f"{self.runpod_api_url}/gpu/deep_learning", timeout=60)
            response.raise_for_status()
            data = response.json()
            self.log(f"✅ 深層学習完了: {data}")
            return {'success': True, 'data': data}
        except Exception as e:
            self.log(f"❌ 深層学習失敗: {e}")
            return {'success': False, 'error': str(e)}
    
    def execute_command(self, command):
        """Trinity達からのコマンド実行"""
        self.log(f"📥 コマンド受信: {command}")
        
        if command == "status":
            return self.get_gpu_status()
        elif command == "generate":
            return self.generate_images()
        elif command == "learn":
            return self.run_deep_learning()
        elif command == "test":
            # フル統合テスト
            results = []
            results.append(("GPU状態", self.get_gpu_status()))
            results.append(("画像生成", self.generate_images()))
            results.append(("深層学習", self.run_deep_learning()))
            return {'success': True, 'results': results}
        else:
            return {'success': False, 'error': f'Unknown command: {command}'}

def main():
    bridge = TrinityRunPodBridge()
    
    if len(sys.argv) < 2:
        print("使用方法: python3 trinity_runpod_gpu_bridge.py <command>")
        print("コマンド: status, generate, learn, test")
        sys.exit(1)
    
    command = sys.argv[1]
    result = bridge.execute_command(command)
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
