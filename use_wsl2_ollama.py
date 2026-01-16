#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WSL2内のOllamaを使用するためのヘルパー
"""

import subprocess
import requests
import sys

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def call_wsl2_ollama_api(endpoint: str, method: str = "GET", json_data: dict = None):
    """WSL2内のOllama APIを呼び出す"""
    url = f"http://localhost:11434{endpoint}"
    
    # WSL2内からAPIを呼び出す
    if method == "GET":
        cmd = f"curl -s {url}"
    else:
        import json
        json_str = json.dumps(json_data)
        cmd = f"curl -s -X {method} -H 'Content-Type: application/json' -d '{json_str}' {url}"
    
    result = subprocess.run(
        ["wsl", "-d", "Ubuntu-22.04", "--", "bash", "-c", cmd],
        capture_output=True,
        text=True,
        timeout=30
    )
    
    if result.returncode == 0:
        try:
            import json
            return json.loads(result.stdout)
        except:
            return result.stdout
    else:
        return None

if __name__ == "__main__":
    print("WSL2内のOllamaを確認中...")
    result = call_wsl2_ollama_api("/api/tags")
    if result:
        print("✅ WSL2内のOllamaに接続できました")
        models = result.get('models', [])
        print(f"利用可能なモデル: {len(models)}個")
        for m in models:
            print(f"  - {m.get('name', 'unknown')}")
    else:
        print("❌ WSL2内のOllamaに接続できませんでした")
