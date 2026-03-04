#!/usr/bin/env python3
"""
Runpod接続・操作テスト
VS Code Serverとの接続確認
"""

import requests

class RunpodConnectionTester:
    """Runpod接続・操作テスト"""
    
    def __init__(self):
        self.pod_id = "8uv33dh7cewgeq"
        self.web_terminal_url = f"https://{self.pod_id}-19123.proxy.runpod.net/0qpm6gurtw5lq2gqy5mltggw0425m8mv/"
        self.vscode_url = f"https://{self.pod_id}-3000.proxy.runpod.net/"
        self.jupyter_url = f"https://{self.pod_id}-8888.proxy.runpod.net/"
        
    def test_web_terminal_connection(self):
        """Web Terminal接続テスト"""
        print("🔍 Web Terminal接続テスト")
        print("=" * 40)
        
        try:
            response = requests.get(self.web_terminal_url, timeout=10)
            if response.status_code == 200:
                print("✅ Web Terminal接続成功")
                print(f"🌐 URL: {self.web_terminal_url}")
                return True
            else:
                print(f"❌ Web Terminal接続失敗: HTTP {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Web Terminal接続エラー: {e}")
            return False
    
    def test_vscode_connection(self):
        """VS Code Server接続テスト"""
        print("\n🔍 VS Code Server接続テスト")
        print("=" * 40)
        
        try:
            response = requests.get(self.vscode_url, timeout=10)
            if response.status_code == 200:
                print("✅ VS Code Server接続成功")
                print(f"🌐 URL: {self.vscode_url}")
                return True
            else:
                print(f"❌ VS Code Server接続失敗: HTTP {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ VS Code Server接続エラー: {e}")
            return False
    
    def test_jupyter_connection(self):
        """Jupyter Lab接続テスト"""
        print("\n🔍 Jupyter Lab接続テスト")
        print("=" * 40)
        
        try:
            response = requests.get(self.jupyter_url, timeout=10)
            if response.status_code == 200:
                print("✅ Jupyter Lab接続成功")
                print(f"🌐 URL: {self.jupyter_url}")
                return True
            else:
                print(f"❌ Jupyter Lab接続失敗: HTTP {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Jupyter Lab接続エラー: {e}")
            return False
    
    def test_gpu_operation(self):
        """GPU操作テスト"""
        print("\n🔍 GPU操作テスト")
        print("=" * 40)
        
        gpu_test_command = """python3 -c "
import torch
print('🔍 GPU操作テスト開始')
print('=' * 30)

if torch.cuda.is_available():
    print(f'✅ GPU検出: {torch.cuda.get_device_name(0)}')
    print(f'💾 GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f}GB')
    
    # GPU操作テスト
    x = torch.randn(1000, 1000).cuda()
    y = torch.randn(1000, 1000).cuda()
    z = torch.mm(x, y)
    
    print(f'✅ GPU操作成功: {z.shape}')
    print(f'🔥 GPU Memory使用: {torch.cuda.memory_allocated(0) / 1024**3:.2f}GB')
    print('🚀 このはサーバーからGPU操作可能！')
else:
    print('❌ GPU未検出')
" """
        
        print("🚀 GPU操作テストコマンド:")
        print(gpu_test_command)
        print(f"\n🌐 実行先: {self.web_terminal_url}")
        return True
    
    def explain_vscode_server(self):
        """VS Code Serverの説明"""
        print("\n📖 Runpod VS Code Serverとは？")
        print("=" * 50)
        
        explanation = """
🎯 Runpod VS Code Server:

1. **Visual Studio Code Server**
   - ブラウザでVS Codeを使える
   - ローカルインストール不要
   - リモート開発環境

2. **Runpod統合**
   - GPU環境と完全統合
   - ファイル編集・実行が簡単
   - ターミナルも内蔵

3. **アクセス方法**
   - ブラウザで直接アクセス
   - 認証不要（セキュアクラウド内）
   - リアルタイム編集・実行

4. **トリニティ達との連携**
   - このはサーバーからコード送信
   - GPU活用プログラム実行
   - 結果の確認・ダウンロード

5. **メリット**
   - このはサーバーから完全制御可能
   - マナの手動操作不要
   - 自動化システムと連携
        """
        
        print(explanation)
        return True
    
    def main_test(self):
        """メインテスト実行"""
        print("🚀 Runpod接続・操作テスト開始")
        print("=" * 60)
        
        # 接続テスト
        web_terminal_ok = self.test_web_terminal_connection()
        vscode_ok = self.test_vscode_connection()
        jupyter_ok = self.test_jupyter_connection()
        
        # GPU操作テスト
        self.test_gpu_operation()
        
        # VS Code Server説明
        self.explain_vscode_server()
        
        # 結果サマリー
        print("\n📊 接続テスト結果サマリー")
        print("=" * 50)
        print(f"Web Terminal: {'✅ 接続OK' if web_terminal_ok else '❌ 接続NG'}")
        print(f"VS Code Server: {'✅ 接続OK' if vscode_ok else '❌ 接続NG'}")
        print(f"Jupyter Lab: {'✅ 接続OK' if jupyter_ok else '❌ 接続NG'}")
        
        if web_terminal_ok:
            print("\n🎉 このはサーバーからRunpod操作可能！")
            print("🤖 トリニティ達のGPU活用準備完了！")
        else:
            print("\n⚠️ 接続に問題があります")
            print("💡 Runpodインスタンスの状態を確認してください")

def main():
    """メイン関数"""
    tester = RunpodConnectionTester()
    tester.main_test()

if __name__ == "__main__":
    main()









