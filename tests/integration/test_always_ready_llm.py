"""
🧪 常時起動LLM動作確認テスト
推奨される最初のステップ
"""

import sys
import os
import requests
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from manaos_integrations._paths import N8N_PORT, OLLAMA_PORT, UNIFIED_API_PORT
except Exception:  # pragma: no cover
    try:
        from _paths import N8N_PORT, OLLAMA_PORT, UNIFIED_API_PORT  # type: ignore
    except Exception:  # pragma: no cover
        N8N_PORT = int(os.getenv("N8N_PORT", "5678"))
        OLLAMA_PORT = int(os.getenv("OLLAMA_PORT", "11434"))
        UNIFIED_API_PORT = int(os.getenv("UNIFIED_API_PORT", "9510"))

DEFAULT_OLLAMA_URL = os.getenv("OLLAMA_URL", f"http://127.0.0.1:{OLLAMA_PORT}")
DEFAULT_N8N_URL = os.getenv("N8N_BASE_URL", f"http://127.0.0.1:{N8N_PORT}")

def check_ollama():
    """Ollamaサーバーの状態確認"""
    print("[確認] Ollamaサーバー確認中...")
    try:
        response = requests.get(f"{DEFAULT_OLLAMA_URL}/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            print(f"[OK] Ollama起動中（モデル数: {len(models)}）")
            if models:
                print("   インストール済みモデル:")
                for model in models[:5]:  # 最初の5つだけ表示
                    print(f"   - {model.get('name', 'unknown')}")
            return True
        else:
            print(f"[WARN] Ollama応答異常: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("[ERROR] Ollamaサーバーに接続できません")
        print("   起動方法: docker-compose -f docker-compose.always-ready-llm.yml up -d")
        return False
    except Exception as e:
        print(f"[ERROR] エラー: {e}")
        return False

def check_redis():
    """Redisサーバーの状態確認"""
    print("\n[確認] Redisサーバー確認中...")
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, decode_responses=True)
        r.ping()
        print("[OK] Redis起動中")
        return True
    except ImportError:
        print("[WARN] redisライブラリがインストールされていません")
        print("   インストール: pip install redis")
        return False
    except redis.ConnectionError:  # type: ignore[possibly-unbound]
        print("[ERROR] Redisサーバーに接続できません")
        print("   起動方法: docker-compose -f docker-compose.always-ready-llm.yml up -d redis")
        return False
    except Exception as e:
        print(f"[ERROR] エラー: {e}")
        return False

def check_n8n():
    """n8nサーバーの状態確認"""
    print("\n[確認] n8nサーバー確認中...")
    try:
        response = requests.get(f"{DEFAULT_N8N_URL}/healthz", timeout=5)
        if response.status_code == 200:
            print("[OK] n8n起動中")
            print(f"   URL: {DEFAULT_N8N_URL}")
            return True
        else:
            print(f"[WARN] n8n応答異常: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("[ERROR] n8nサーバーに接続できません")
        print("   起動方法: docker-compose -f docker-compose.always-ready-llm.yml up -d n8n")
        return False
    except Exception as e:
        print(f"[ERROR] エラー: {e}")
        return False

def check_unified_api():
    """統合APIサーバーの状態確認"""
    print("\n[確認] 統合APIサーバー確認中...")
    try:
        base_url = os.getenv("MANAOS_INTEGRATION_API_URL", f"http://127.0.0.1:{UNIFIED_API_PORT}")
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            print("[OK] 統合APIサーバー起動中")
            return True
        else:
            print(f"[WARN] 統合APIサーバー応答異常: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("[WARN] 統合APIサーバーに接続できません（オプション）")
        print("   起動方法: python unified_api_server.py")
        return False
    except Exception as e:
        print(f"[WARN] エラー: {e}")
        return False

def test_basic_chat():
    """基本的なチャットテスト"""
    print("\n[テスト] 基本的なチャットテスト...")
    try:
        from always_ready_llm_client import AlwaysReadyLLMClient, ModelType, TaskType
        
        client = AlwaysReadyLLMClient()
        
        # 簡単なテスト（直接Ollama呼び出しを試す）
        print("   メッセージ送信: 'こんにちは'")
        
        # まず直接Ollamaでテスト
        try:
            import requests
            ollama_response = requests.post(
                "http://127.0.0.1:11434/api/generate",
                json={
                    "model": "llama3.2:3b",
                    "prompt": "こんにちは！短く挨拶してください。",
                    "stream": False
                },
                timeout=30
            )
            
            if ollama_response.status_code == 200:
                data = ollama_response.json()
                response_text = data.get("response", "")
                print(f"[OK] 直接Ollama呼び出し成功！")
                print(f"   レスポンス: {response_text[:100]}...")
                print(f"   モデル: llama3.2:3b")
                return True
            else:
                print(f"[WARN] Ollama応答異常: {ollama_response.status_code}")
                return False
        except Exception as e:
            print(f"[WARN] 直接Ollama呼び出し失敗: {e}")
            print("   n8n Webhook経由を試します...")
        
        # n8n Webhook経由を試す
        response = client.chat(
            "こんにちは！短く挨拶してください。",
            model=ModelType.LIGHT,
            task_type=TaskType.CONVERSATION
        )
        
        print(f"[OK] 成功！")
        print(f"   レスポンス: {response.response[:100]}...")
        print(f"   モデル: {response.model}")
        print(f"   レイテンシ: {response.latency_ms:.2f}ms")
        print(f"   キャッシュ: {'OK' if response.cached else 'NG'}")
        
        return True
    except ImportError as e:
        print(f"[ERROR] インポートエラー: {e}")
        print("   必要なライブラリをインストールしてください")
        return False
    except Exception as e:
        print(f"[ERROR] テスト失敗: {e}")
        print("   ヒント: n8nワークフローをインポートしてください")
        print(f"   - {DEFAULT_N8N_URL} にアクセス")
        print("   - ワークフロー → インポート")
        print("   - n8n_workflows/always_ready_llm_workflow.json を選択")
        return False

def main():
    """メイン実行"""
    print("=" * 60)
    print("常時起動LLM動作確認テスト")
    print("=" * 60)
    
    # サービス確認
    ollama_ok = check_ollama()
    redis_ok = check_redis()
    n8n_ok = check_n8n()
    api_ok = check_unified_api()
    
    # 基本テスト
    if ollama_ok:
        chat_ok = test_basic_chat()
    else:
        print("\n⚠️ Ollamaが起動していないため、チャットテストをスキップします")
        chat_ok = False
    
    # 結果サマリー
    print("\n" + "=" * 60)
    print("テスト結果サマリー")
    print("=" * 60)
    print(f"Ollama:        {'[OK]' if ollama_ok else '[NG]'}")
    print(f"Redis:         {'[OK]' if redis_ok else '[NG]'}")
    print(f"n8n:           {'[OK]' if n8n_ok else '[NG]'}")
    print(f"統合API:       {'[OK]' if api_ok else '[WARN]'}")
    print(f"チャットテスト: {'[OK]' if chat_ok else '[NG]'}")
    
    if ollama_ok and chat_ok:
        print("\n基本動作確認完了！")
        print("\n次のステップ:")
        print("  1. python examples/llm_usage_examples.py  # 使用例を実行")
        print("  2. python llm_performance_monitor.py       # パフォーマンス監視開始")
    else:
        print("\n一部のサービスが起動していません")
        print("\n推奨される次のステップ:")
        if not ollama_ok:
            print("  1. Docker Compose起動:")
            print("     docker-compose -f docker-compose.always-ready-llm.yml up -d")
        if not redis_ok:
            print("  2. Redis起動確認")
        if not n8n_ok:
            print("  3. n8n起動確認")
    
    print("=" * 60)

