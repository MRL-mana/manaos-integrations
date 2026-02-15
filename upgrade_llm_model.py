#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLMモデルをより高性能なモデルにアップグレード
"""

import httpx
import sys
from pathlib import Path

import os

try:
    from manaos_integrations._paths import OLLAMA_PORT
except Exception:  # pragma: no cover
    try:
        from _paths import OLLAMA_PORT  # type: ignore
    except Exception:  # pragma: no cover
        OLLAMA_PORT = int(os.getenv("OLLAMA_PORT", "11434"))


DEFAULT_OLLAMA_URL = os.getenv("OLLAMA_URL", f"http://127.0.0.1:{OLLAMA_PORT}")

def check_available_models():
    """利用可能なモデルを確認"""
    print("=== 利用可能なモデル確認 ===")
    try:
        response = httpx.get(f"{DEFAULT_OLLAMA_URL}/api/tags", timeout=5.0)
        if response.status_code == 200:
            data = response.json()
            models = data.get("models", [])
            print(f"✅ 利用可能モデル数: {len(models)}")
            
            model_names = [m.get("name", "unknown") for m in models]
            
            # 高性能モデル候補
            smart_models = {
                "llama3.2:3b": {"level": "軽量", "用途": "会話・軽量タスク"},
                "qwen2.5:7b": {"level": "中", "用途": "バランス型"},
                "qwen2.5:14b": {"level": "高", "用途": "高品質生成・ツール使用"},
                "llama3.1:8b": {"level": "中", "用途": "バランス型"},
                "qwen2.5:32b": {"level": "非常に高", "用途": "高品質生成"},
                "qwen2.5:72b": {"level": "最高", "用途": "複雑な推論"},
            }
            
            print("\n利用可能なモデル:")
            for name in model_names:
                if name in smart_models:
                    info = smart_models[name]
                    print(f"  ✅ {name:20s} - {info['level']:8s} ({info['用途']})")
                else:
                    print(f"  - {name:20s}")
            
            # 推奨モデル
            print("\n推奨モデル（性能順）:")
            recommended = [
                ("qwen2.5:14b", "バランス型・高品質生成"),
                ("qwen2.5:7b", "バランス型・軽量"),
                ("llama3.1:8b", "バランス型"),
            ]
            
            for model, desc in recommended:
                if model in model_names:
                    print(f"  ✅ {model:20s} - {desc}")
                else:
                    print(f"  ⚠️ {model:20s} - {desc}（インストールが必要）")
            
            return model_names
        else:
            print(f"⚠️ Ollama API: HTTP {response.status_code}")
            return []
    except httpx.ConnectError:
        print("❌ Ollama API: 接続不可")
        return []
    except Exception as e:
        print(f"❌ エラー: {e}")
        return []

def suggest_upgrade(current_model="llama3.2:3b"):
    """アップグレード提案"""
    print(f"\n=== 現在のモデル: {current_model} ===")
    
    upgrades = [
        {
            "from": "llama3.2:3b",
            "to": "qwen2.5:7b",
            "reason": "バランス型・軽量・性能向上",
            "install": "ollama pull qwen2.5:7b"
        },
        {
            "from": "llama3.2:3b",
            "to": "qwen2.5:14b",
            "reason": "高品質生成・ツール使用得意",
            "install": "ollama pull qwen2.5:14b"
        },
        {
            "from": "llama3.2:3b",
            "to": "llama3.1:8b",
            "reason": "バランス型・性能向上",
            "install": "ollama pull llama3.1:8b"
        },
    ]
    
    print("\n推奨アップグレード:")
    for i, upgrade in enumerate(upgrades, 1):
        print(f"\n{i}. {upgrade['from']} → {upgrade['to']}")
        print(f"   理由: {upgrade['reason']}")
        print(f"   インストール: {upgrade['install']}")

def show_current_usage():
    """現在の使用状況"""
    print("\n=== 現在の使用状況 ===")
    
    usage = [
        ("Slack Integration", "llama3.2:3b", "always_ready_llm_client.py", "ModelType.LIGHT"),
        ("File Secretary", "llama3.2:3b", "file_secretary_organizer.py", "model='llama3.2:3b'"),
    ]
    
    print("サービス別モデル使用:")
    for service, model, file, location in usage:
        print(f"  - {service:20s}: {model:15s} ({file}:{location})")

def main():
    """メイン処理"""
    print("=" * 60)
    print("LLMモデルアップグレード提案")
    print("=" * 60)
    
    models = check_available_models()
    show_current_usage()
    suggest_upgrade()
    
    print("\n" + "=" * 60)
    print("次のステップ")
    print("=" * 60)
    print("\n1. モデルをインストール:")
    print("   ollama pull qwen2.5:14b")
    print("\n2. 設定を変更:")
    print("   - Slack Integration: ModelType.MEDIUM に変更")
    print("   - File Secretary: model='qwen2.5:14b' に変更")
    print("\n3. サービスを再起動")

if __name__ == '__main__':
    main()






















