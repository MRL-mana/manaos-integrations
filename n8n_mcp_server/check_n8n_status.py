"""
n8nの状態を確認するスクリプト
"""
import requests
import sys

import os

DEFAULT_N8N_BASE_URL = f"http://127.0.0.1:{os.getenv('N8N_PORT', '5678')}"
N8N_BASE_URL = os.getenv("N8N_BASE_URL", DEFAULT_N8N_BASE_URL).rstrip("/")

def check_n8n_status():
    """n8nの状態を確認"""
    print("=" * 60)
    print("n8n状態確認")
    print("=" * 60)
    print(f"URL: {N8N_BASE_URL}")
    print()
    
    # ヘルスチェック
    try:
        response = requests.get(f"{N8N_BASE_URL}/healthz", timeout=5)
        if response.status_code == 200:
            print("[OK] n8nは起動しています")
            print(f"    ヘルスチェック: OK")
        else:
            print(f"[NG] ヘルスチェックエラー: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("[NG] n8nに接続できません")
        print("     n8nが起動していない可能性があります")
        return False
    except requests.exceptions.Timeout:
        print("[NG] n8nがタイムアウトしました")
        print("     n8nが応答していない可能性があります")
        return False
    except Exception as e:
        print(f"[NG] エラー: {e}")
        return False
    
    # メインページ
    try:
        response = requests.get(N8N_BASE_URL, timeout=5)
        if response.status_code == 200:
            print(f"[OK] Web UIはアクセス可能です")
            print(f"    ブラウザで {N8N_BASE_URL} を開いてください")
        else:
            print(f"[NG] Web UIエラー: {response.status_code}")
    except Exception as e:
        print(f"[警告] Web UI確認エラー: {e}")
    
    print()
    return True

if __name__ == "__main__":
    check_n8n_status()













