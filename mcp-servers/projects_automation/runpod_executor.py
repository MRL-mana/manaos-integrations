#!/usr/bin/env python3
"""
Runpod実行システム
このはサーバーからRunpod GPU環境を実行するシステム
"""

import requests

class RunpodExecutor:
    """Runpod実行システム"""
    
    def __init__(self):
        self.runpod_host = "213.181.111.2"
        self.web_terminal_port = "19123"
        self.jupyter_port = "8888"
        
    def check_runpod_status(self):
        """Runpod接続状態確認"""
        try:
            # Web Terminal確認
            response = requests.get(f"http://{self.runpod_host}:{self.web_terminal_port}", timeout=5)
            web_terminal_ok = response.status_code == 200
            
            # Jupyter確認
            response = requests.get(f"http://{self.runpod_host}:{self.jupyter_port}", timeout=5)
            jupyter_ok = response.status_code == 200
            
            return {
                "web_terminal": web_terminal_ok,
                "jupyter": jupyter_ok,
                "runpod_accessible": web_terminal_ok or jupyter_ok
            }
        except requests.RequestException:
            return {
                "web_terminal": False,
                "jupyter": False,
                "runpod_accessible": False
            }
    
    def execute_on_runpod(self, command):
        """Runpodでコマンド実行（Web Terminal経由）"""
        print(f"🚀 Runpodで実行: {command}")
        print(f"🌐 Web Terminal: http://{self.runpod_host}:{self.web_terminal_port}")
        print("📝 上記URLにアクセスして以下を実行してください:")
        print(f"   {command}")
        print("")
        
        return True
    
    def run_gpu_projects_on_runpod(self):
        """RunpodでGPUプロジェクト実行"""
        status = self.check_runpod_status()
        
        if not status["runpod_accessible"]:
            print("❌ Runpodにアクセスできません")
            print("💡 Runpodが起動しているか確認してください")
            return False
        
        print("✅ Runpod GPU環境確認")
        print(f"🖥️ Web Terminal: {'✅' if status['web_terminal'] else '❌'}")
        print(f"📓 Jupyter Lab: {'✅' if status['jupyter'] else '❌'}")
        print("")
        
        # GPUプロジェクト実行指示
        projects = [
            {
                "name": "GPUクリエイティブプロジェクト集",
                "command": "python /root/gpu_creative_projects.py",
                "description": "🎨 AIアート、🎵音楽、🎲3D形状、🌀フラクタル、✨パーティクル"
            },
            {
                "name": "GPUメガプロジェクト集", 
                "command": "python /root/gpu_mega_project.py",
                "description": "🌌宇宙、⚛️量子、🌀ハイパースペース、🧠意識、⏰タイムマシン"
            },
            {
                "name": "GPU自動統合システム",
                "command": "python /root/gpu_auto_integration.py", 
                "description": "🔥自動GPU検出、🚀自動セットアップ、📊GPU監視"
            }
        ]
        
        print("🚀 Runpod GPU環境で実行可能なプロジェクト:")
        print("=" * 60)
        
        for i, project in enumerate(projects, 1):
            print(f"{i}. {project['name']}")
            print(f"   📝 コマンド: {project['command']}")
            print(f"   📋 内容: {project['description']}")
            print("")
        
        print("🎯 実行方法:")
        print("1. ブラウザで http://213.181.111.2:19123 にアクセス")
        print("2. 上記のコマンドを実行")
        print("3. RTX 4090 24GBの威力を体験！")
        print("")
        
        return True

def main():
    """メイン関数"""
    print("🤖 Runpod実行システム")
    print("=" * 40)
    
    executor = RunpodExecutor()
    
    # Runpod状態確認
    status = executor.check_runpod_status()
    
    if status["runpod_accessible"]:
        print("✅ Runpod GPU環境利用可能")
        executor.run_gpu_projects_on_runpod()
    else:
        print("❌ Runpod GPU環境にアクセスできません")
        print("💡 以下を確認してください:")
        print("   1. Runpodが起動しているか")
        print("   2. Web Terminal: http://213.181.111.2:19123")
        print("   3. Jupyter Lab: http://213.181.111.2:8888")

if __name__ == "__main__":
    main()










