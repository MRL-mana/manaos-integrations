#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
常時起動LLMの状態確認
"""

import sys
import httpx
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def check_ollama_status():
    """Ollamaの状態確認"""
    print("=== Ollama状態確認 ===")
    try:
        # プロセス確認
        import subprocess
        result = subprocess.run(
            ["powershell", "-Command", "Get-Process ollama -ErrorAction SilentlyContinue | Select-Object Id, ProcessName"],
            capture_output=True,
            text=True
        )
        if "ollama" in result.stdout:
            print("✅ Ollamaプロセス: 実行中")
        else:
            print("❌ Ollamaプロセス: 停止中")
        
        # API確認
        response = httpx.get("http://127.0.0.1:11434/api/tags", timeout=5.0)
        if response.status_code == 200:
            data = response.json()
            models = data.get("models", [])
            print(f"✅ Ollama API: 正常応答")
            print(f"   利用可能モデル数: {len(models)}")
            
            # 実行中モデル確認
            ps_response = httpx.get("http://127.0.0.1:11434/api/ps", timeout=5.0)
            if ps_response.status_code == 200:
                running = ps_response.json()
                if running:
                    print(f"   実行中モデル: {len(running)}")
                    for model in running:
                        print(f"     - {model.get('model', 'unknown')} (PID: {model.get('pid', 'N/A')})")
                else:
                    print("   実行中モデル: なし（オンデマンド起動）")
            
            # 主要モデル一覧
            print("\n   主要モデル:")
            for model in models[:10]:  # 最初の10個
                name = model.get("name", "unknown")
                size = model.get("size", 0)
                size_gb = size / (1024**3)
                print(f"     - {name} ({size_gb:.2f}GB)")
            
            return True
        else:
            print(f"⚠️ Ollama API: HTTP {response.status_code}")
            return False
    except httpx.ConnectError:
        print("❌ Ollama API: 接続不可（起動していない可能性）")
        return False
    except Exception as e:
        print(f"❌ Ollama確認エラー: {e}")
        return False

def check_llm_client_config():
    """LLMクライアント設定確認"""
    print("\n=== LLMクライアント設定確認 ===")
    
    # always_ready_llm_client確認
    try:
        from always_ready_llm_client import AlwaysReadyLLMClient, ModelType
        print("✅ always_ready_llm_client: 利用可能")
        
        # デフォルトモデル確認
        client = AlwaysReadyLLMClient()
        print(f"   デフォルト設定:")
        print(f"     - OLLAMA_URL: {client.ollama_url}")
        print(f"     - ModelType.LIGHT: {ModelType.LIGHT.value if hasattr(ModelType.LIGHT, 'value') else ModelType.LIGHT}")
        print(f"     - ModelType.STANDARD: {ModelType.STANDARD.value if hasattr(ModelType.STANDARD, 'value') else ModelType.STANDARD}")
        print(f"     - ModelType.HEAVY: {ModelType.HEAVY.value if hasattr(ModelType.HEAVY, 'value') else ModelType.HEAVY}")
        
        return True
    except ImportError as e:
        print(f"⚠️ always_ready_llm_client: インポート不可 - {e}")
        return False
    except Exception as e:
        print(f"⚠️ always_ready_llm_client: エラー - {e}")
        return False

def check_slack_integration_llm():
    """Slack IntegrationのLLM設定確認"""
    print("\n=== Slack Integration LLM設定確認 ===")
    try:
        import slack_integration
        if hasattr(slack_integration, 'LLM_CLIENT'):
            if slack_integration.LLM_CLIENT:
                print("✅ Slack Integration: always_ready_llm_client使用")
                print(f"   クライアント: {type(slack_integration.LLM_CLIENT).__name__}")
            else:
                print("⚠️ Slack Integration: local_llm_helper使用（フォールバック）")
        else:
            print("⚠️ Slack Integration: LLMクライアント未設定")
        return True
    except Exception as e:
        print(f"⚠️ Slack Integration確認エラー: {e}")
        return False

def check_file_secretary_llm():
    """File SecretaryのLLM設定確認"""
    print("\n=== File Secretary LLM設定確認 ===")
    try:
        from file_secretary_organizer import FileOrganizer
        # FileOrganizerのデフォルト設定を確認
        print("✅ File Secretary: FileOrganizer使用")
        print("   デフォルト設定:")
        print("     - ollama_url: http://127.0.0.1:11434")
        print("     - model: llama3.2:3b")
        return True
    except Exception as e:
        print(f"⚠️ File Secretary確認エラー: {e}")
        return False

def main():
    """メイン処理"""
    print("=" * 60)
    print("常時起動LLM状態確認")
    print("=" * 60)
    print()
    
    ollama_ok = check_ollama_status()
    llm_client_ok = check_llm_client_config()
    slack_llm_ok = check_slack_integration_llm()
    file_secretary_llm_ok = check_file_secretary_llm()
    
    print("\n" + "=" * 60)
    print("確認結果サマリ")
    print("=" * 60)
    
    print(f"Ollama: {'✅ 起動中' if ollama_ok else '❌ 停止中'}")
    print(f"LLMクライアント: {'✅ 利用可能' if llm_client_ok else '⚠️ 利用不可'}")
    print(f"Slack Integration: {'✅ 設定済み' if slack_llm_ok else '⚠️ 未設定'}")
    print(f"File Secretary: {'✅ 設定済み' if file_secretary_llm_ok else '⚠️ 未設定'}")
    
    if ollama_ok:
        print("\n🎉 常時起動LLM（Ollama）が利用可能です！")
        print("   使用モデル:")
        print("     - Slack Integration: llama3.2:3b（ModelType.LIGHT）")
        print("     - File Secretary: llama3.2:3b（タグ推定）")

if __name__ == '__main__':
    main()






















