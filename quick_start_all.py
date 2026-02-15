"""
全システム一括起動スクリプト（Python版）
"""

import subprocess
import time
import os
import sys
from pathlib import Path

def start_streamlit():
    """Streamlitアプリを起動"""
    print("[起動] Free-personal-AI-Assistant...")
    os.chdir("repos/Free-personal-AI-Assistant-with-plugin")
    subprocess.Popen([sys.executable, "-m", "streamlit", "run", "streamlit_app.py", "--server.port", "8501"])
    os.chdir("../..")
    time.sleep(2)
    print("  ✓ 起動しました（ポート8501）")

def start_sara_backend():
    """Sara-AI-Platformバックエンドを起動"""
    print("[起動] Sara-AI-Platform バックエンド...")
    os.chdir("repos/Sara-AI-Platform")
    subprocess.Popen([sys.executable, "-m", "uvicorn", "backend.server:app", "--reload", "--port", "8000"])
    os.chdir("../..")
    time.sleep(2)
    print("  ✓ 起動しました（ポート8000）")

def check_ollama():
    """Ollamaの状態を確認"""
    import httpx
    try:
        response = httpx.get("http://127.0.0.1:11434/api/tags", timeout=2.0)
        if response.status_code == 200:
            models = response.json().get("models", [])
            print(f"  [OK] Ollama起動中（モデル数: {len(models)}）")
            return True
    except Exception:
        print("  [WARN] Ollama未起動")
        return False

def main():
    print("=" * 60)
    print("全ローカルLLMシステム起動")
    print("=" * 60)
    print("")
    
    # Ollama確認
    print("[確認] Ollama状態...")
    check_ollama()
    print("")
    
    # 各システムを起動
    start_streamlit()
    print("")
    start_sara_backend()
    print("")
    
    print("=" * 60)
    print("起動完了")
    print("=" * 60)
    print("")
    print("アクセスURL:")
    print("  - Free-personal-AI-Assistant: http://127.0.0.1:8501")
    print("  - Sara-AI-Platform API: http://127.0.0.1:8000/docs")
    print("  - n8n: http://127.0.0.1:5678")
    print("")
    print("プロセスはバックグラウンドで実行中です。")
    print("停止する場合はタスクマネージャーから終了してください。")

if __name__ == "__main__":
    main()

