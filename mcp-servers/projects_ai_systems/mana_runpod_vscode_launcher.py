#!/usr/bin/env python3
"""
Mana RunPod VS Code ランチャー
VS Code Remote SSHでRunPod GPUに接続して操作する
"""

import subprocess

def launch_vscode_runpod():
    """VS Code Remote SSHでRunPodに接続"""
    print("🚀 Mana RunPod VS Code ランチャー")
    print("=" * 50)
    
    print("📋 接続情報:")
    print("   Host: runpod-gpu")
    print("   User: 8uv33dh7cewgeq-644114e0")
    print("   GPU: RTX 4090 24GB")
    print("")
    
    print("🔧 VS Code接続手順:")
    print("1. VS Codeで Ctrl+Shift+P")
    print("2. 'Remote-SSH: Connect to Host' 選択")
    print("3. 'runpod-gpu' 選択")
    print("4. 接続完了！")
    print("")
    
    print("🎮 VS Code内でGPU操作:")
    print("```python")
    print("import torch")
    print("print(f'CUDA available: {torch.cuda.is_available()}')")
    print("print(f'GPU name: {torch.cuda.get_device_name(0)}')")
    print("```")
    print("")
    
    print("💡 利点:")
    print("- PTYエラー回避")
    print("- リアルタイム編集")
    print("- デバッグ可能")
    print("- 拡張機能使用可能")
    print("")
    
    # VS Code起動コマンド（可能であれば）
    try:
        print("🚀 VS Code起動中...")
        subprocess.run(["code", "--remote", "ssh-remote+runpod-gpu", "/workspace"], check=False)
        print("✅ VS Code起動完了！")
    except Exception as e:
        print(f"⚠️  VS Code自動起動失敗: {e}")
        print("手動でVS Code Remote SSH接続してください")
    
    print("=" * 50)
    print("🎉 RunPod VS Code接続準備完了！")

def test_runpod_connection():
    """RunPod接続テスト"""
    print("🔥 RunPod接続テスト開始")
    print("=" * 50)
    
    try:
        # SSH接続テスト
        result = subprocess.run([
            "ssh", "-o", "ConnectTimeout=10", 
            "runpod-gpu", 
            "echo 'SSH接続テスト成功'"
        ], capture_output=True, text=True, timeout=15)
        
        if result.returncode == 0:
            print("✅ SSH接続成功")
            print(f"出力: {result.stdout.strip()}")
        else:
            print("❌ SSH接続失敗")
            print(f"エラー: {result.stderr.strip()}")
            return False
        
        # GPU確認テスト
        print("\n🔥 GPU確認テスト")
        result = subprocess.run([
            "ssh", "-o", "ConnectTimeout=10",
            "runpod-gpu",
            "python3 -c \"import torch; print(f'CUDA available: {torch.cuda.is_available()}'); print(f'GPU name: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"No GPU\"}')\""
        ], capture_output=True, text=True, timeout=15)
        
        if result.returncode == 0:
            print("✅ GPU確認成功")
            print(f"結果: {result.stdout.strip()}")
        else:
            print("❌ GPU確認失敗")
            print(f"エラー: {result.stderr.strip()}")
        
        return True
        
    except Exception as e:
        print(f"❌ テスト失敗: {e}")
        return False

def main():
    """メイン実行"""
    print("🎯 Mana RunPod VS Code 統合システム")
    print("=" * 60)
    
    # 接続テスト
    if test_runpod_connection():
        print("\n🎉 接続テスト成功！")
        print("VS Code Remote SSHでRunPod GPUに接続可能です！")
        
        # VS Code起動
        launch_vscode_runpod()
    else:
        print("\n❌ 接続テスト失敗")
        print("SSH設定を確認してください")
    
    print("=" * 60)

if __name__ == "__main__":
    main()
