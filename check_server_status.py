"""
ManaOS統合APIサーバーの起動状況を確認
"""

import requests
import sys

def check_server_status():
    """統合APIサーバーの起動状況を確認"""
    print("=" * 60)
    print("ManaOS統合APIサーバーの起動状況確認")
    print("=" * 60)
    
    # ポート9405の確認
    api_url = "http://localhost:9405"
    
    print(f"\n[確認] 統合APIサーバー ({api_url})")
    try:
        response = requests.get(f"{api_url}/api/status", timeout=2)
        if response.status_code == 200:
            print("[OK] 統合APIサーバーが起動しています")
            status = response.json()
            print(f"   ステータス: {status.get('status', 'unknown')}")
        else:
            print(f"[WARN] 統合APIサーバーが応答しません: HTTP {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("[ERROR] 統合APIサーバーが起動していません")
        print("   起動方法: python manaos_integrations/unified_api_server.py")
    except Exception as e:
        print(f"[ERROR] 確認エラー: {e}")
    
    # Ollamaの確認
    ollama_url = "http://localhost:11434"
    print(f"\n[確認] Ollama ({ollama_url})")
    try:
        response = requests.get(f"{ollama_url}/api/tags", timeout=2)
        if response.status_code == 200:
            print("[OK] Ollamaが起動しています")
            models = response.json().get("models", [])
            print(f"   利用可能なモデル数: {len(models)}")
        else:
            print(f"[WARN] Ollamaが応答しません: HTTP {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("[ERROR] Ollamaが起動していません")
    except Exception as e:
        print(f"[ERROR] 確認エラー: {e}")
    
    print("\n" + "=" * 60)
    print("確認完了")
    print("=" * 60)


if __name__ == "__main__":
    check_server_status()
