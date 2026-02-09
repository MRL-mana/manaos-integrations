#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ManaOS スクリプトカタログ生成ツール
ルートの全スクリプトをカテゴリ別に整理して一覧を出力する
"""
import os
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parent

# カテゴリ判定ルール（優先度順）
CATEGORY_RULES = [
    # (パターン, カテゴリ名)
    ("start_comfyui", "ComfyUI 起動"),
    ("comfyui", "ComfyUI"),
    ("start_pixel7", "Pixel 7 / ADB"),
    ("pixel7", "Pixel 7 / ADB"),
    ("start_slack", "Slack 連携"),
    ("slack", "Slack 連携"),
    ("start_n8n", "n8n 連携"),
    ("n8n", "n8n 連携"),
    ("start_ngrok", "ngrok / Tunnel"),
    ("ngrok", "ngrok / Tunnel"),
    ("start_ollama", "Ollama / LLM"),
    ("start_lm_studio", "Ollama / LLM"),
    ("start_llm", "Ollama / LLM"),
    ("llm_routing", "Ollama / LLM"),
    ("start_unified_api", "統合API"),
    ("unified_api", "統合API"),
    ("start_orchestrator", "Orchestrator"),
    ("orchestrator", "Orchestrator"),
    ("start_all_", "一括起動"),
    ("start_services", "一括起動"),
    ("start_manaos", "ManaOS 自動起動"),
    ("start_vscode", "ManaOS 自動起動"),
    ("autostart", "ManaOS 自動起動"),
    ("System3_", "System 3"),
    ("system3_", "System 3"),
    ("start_system3", "System 3"),
    ("start_intrinsic", "System 3"),
    ("start_monitoring", "監視 / ヘルスチェック"),
    ("health_check", "監視 / ヘルスチェック"),
    ("check_", "監視 / ヘルスチェック"),
    ("start_evaluation", "画像評価"),
    ("evaluation", "画像評価"),
    ("start_image_eval", "画像評価"),
    ("start_extension", "拡張フェーズ"),
    ("start_device", "デバイス管理"),
    ("run_v11", "LoRA 学習"),
    ("run_layer2", "LoRA 学習"),
    ("lora", "LoRA 学習"),
    ("training", "LoRA 学習"),
    ("start_redis", "インフラ"),
    ("docker", "インフラ"),
    ("setup_", "セットアップ"),
    ("install_", "セットアップ"),
    ("update_", "メンテナンス"),
    ("upgrade_", "メンテナンス"),
    ("kill_", "運用 / デバッグ"),
    ("restart_", "運用 / デバッグ"),
    ("emergency", "運用 / デバッグ"),
    ("run_", "運用 / デバッグ"),
    ("start_", "その他の起動"),
]


def categorize(name: str) -> str:
    lower = name.lower()
    for pattern, category in CATEGORY_RULES:
        if pattern.lower() in lower:
            return category
    return "未分類"


def main():
    exts = {".py", ".ps1", ".bat", ".vbs", ".sh"}
    scripts = []
    for f in ROOT.iterdir():
        if f.is_file() and f.suffix in exts and not f.name.startswith("__"):
            scripts.append(f)
    scripts.sort(key=lambda p: p.name.lower())

    by_cat = defaultdict(list)
    for s in scripts:
        cat = categorize(s.name)
        by_cat[cat].append(s)

    print(f"# ManaOS スクリプトカタログ ({len(scripts)} 件)\n")
    for cat in sorted(by_cat.keys()):
        items = by_cat[cat]
        print(f"## {cat} ({len(items)} 件)\n")
        for s in items:
            size_kb = s.stat().st_size / 1024
            print(f"- `{s.name}` ({size_kb:.1f} KB)")
        print()


if __name__ == "__main__":
    main()
