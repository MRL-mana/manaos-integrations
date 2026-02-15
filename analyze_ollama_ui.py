"""
Ollama UIとManaOS統合APIサーバーの違いを分析
"""

import requests
import subprocess
import os

try:
    from manaos_integrations._paths import OLLAMA_PORT, UNIFIED_API_PORT
except Exception:  # pragma: no cover
    try:
        from _paths import OLLAMA_PORT, UNIFIED_API_PORT  # type: ignore
    except Exception:  # pragma: no cover
        OLLAMA_PORT = int(os.getenv("OLLAMA_PORT", "11434"))
        UNIFIED_API_PORT = int(os.getenv("UNIFIED_API_PORT", "9502"))


DEFAULT_OLLAMA_URL = os.getenv("OLLAMA_URL", f"http://127.0.0.1:{OLLAMA_PORT}")
DEFAULT_UNIFIED_API_URL = os.getenv("UNIFIED_API_URL", f"http://127.0.0.1:{UNIFIED_API_PORT}")

print("=" * 60)
print("Ollama UI vs ManaOS統合APIサーバーの違い")
print("=" * 60)

# 1. Ollamaの状態確認
print("\n[1] Ollamaの状態")
try:
    result = subprocess.run(["ollama", "ps"], capture_output=True, text=True, timeout=5)
    print(result.stdout)
except Exception as e:
    print(f"エラー: {e}")

# 2. GPU使用状況
print("\n[2] GPU使用状況")
try:
    result = subprocess.run(
        ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used", "--format=csv,noheader"],
        capture_output=True,
        text=True,
        timeout=5
    )
    print(result.stdout)
except Exception as e:
    print(f"エラー: {e}")

# 3. Ollama API直接呼び出し（Ollama UIと同じ方法）
print("\n[3] Ollama API直接呼び出し（Ollama UIと同じ方法）")
try:
    response = requests.post(
        f"{DEFAULT_OLLAMA_URL}/api/chat",
        json={
            "model": "gpt-oss:20b",
            "messages": [{"role": "user", "content": "こんにちは"}],
            "stream": False
        },
        timeout=60
    )
    if response.status_code == 200:
        result = response.json()
        print(f"成功: {result.get('message', {}).get('content', '')[:100]}...")
    else:
        print(f"エラー: HTTP {response.status_code}")
except Exception as e:
    print(f"エラー: {e}")

# 4. ManaOS統合APIサーバー経由
print("\n[4] ManaOS統合APIサーバー経由")
try:
    response = requests.post(
        f"{DEFAULT_UNIFIED_API_URL}/api/llm/chat",
        json={
            "messages": [{"role": "user", "content": "こんにちは"}],
            "task_type": "conversation"
        },
        timeout=60
    )
    if response.status_code == 200:
        result = response.json()
        print(f"成功: {result.get('response', '')[:100]}...")
        print(f"モデル: {result.get('model', 'unknown')}")
        print(f"CPUモード: {result.get('cpu_mode', False)}")
    else:
        print(f"エラー: HTTP {response.status_code}")
        print(f"詳細: {response.text}")
except Exception as e:
    print(f"エラー: {e}")

print("\n" + "=" * 60)
print("分析完了")
print("=" * 60)



