#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CivitAIでお気に入りしたモデル一覧を表示"""

import sys
import os
from pathlib import Path

# CivitAI統合をインポート
try:
    from civitai_integration import CivitAIIntegration
except ImportError:
    print("❌ civitai_integrationモジュールが見つかりません", file=sys.stderr)
    exit(1)

print("=" * 60)
print("CivitAIお気に入りモデル一覧")
print("=" * 60)
print()

# APIキーを確認
api_key = os.getenv("CIVITAI_API_KEY")
if not api_key:
    print("⚠️ CIVITAI_API_KEY環境変数が設定されていません", file=sys.stderr)
    print()
    print("設定方法:")
    print("  1. CivitAIのサイトでAPIキーを取得")
    print("  2. 環境変数を設定:")
    print("     set CIVITAI_API_KEY=your_api_key_here")
    print()
    print("または、.envファイルに追加:")
    print("     CIVITAI_API_KEY=your_api_key_here")
    print()
    exit(1)

# CivitAI統合を初期化
civitai = CivitAIIntegration(api_key=api_key)

if not civitai.is_available():
    print("❌ CivitAI統合が利用できません")
    exit(1)

print("✅ CivitAI APIに接続中...")
print()

# お気に入りモデルを取得
favorites = civitai.get_favorite_models(limit=100)

if not favorites:
    print("お気に入りモデルが見つかりませんでした。")
    print("CivitAIのサイトでモデルをお気に入りに追加してください。")
    exit(0)

print(f"🌟 お気に入りモデル: {len(favorites)} 件")
print()
print("=" * 60)
print("お気に入りモデル一覧")
print("=" * 60)
print()

for i, model in enumerate(favorites, 1):
    model_id = model.get("id", "N/A")
    model_name = model.get("name", "Unknown")
    model_type = model.get("type", "Unknown")
    description = model.get("description", "")
    stats = model.get("stats", {})
    download_count = stats.get("downloadCount", 0)
    favorite_count = stats.get("favoriteCount", 0)
    rating = stats.get("rating", 0)
    
    # モデルバージョン情報
    versions = model.get("modelVersions", [])
    latest_version = versions[0] if versions else None
    
    print(f"{i:2d}. {model_name}")
    print(f"     ID: {model_id} | タイプ: {model_type}")
    print(f"     ダウンロード: {download_count:,} | お気に入り: {favorite_count:,} | 評価: {rating:.1f}")
    
    if latest_version:
        version_name = latest_version.get("name", "Unknown")
        version_id = latest_version.get("id", "N/A")
        print(f"     最新バージョン: {version_name} (ID: {version_id})")
    
    if description:
        desc_short = description[:100] + "..." if len(description) > 100 else description
        print(f"     説明: {desc_short}")
    
    print()

print("=" * 60)
print("ダウンロード方法:")
print("  python -c \"from civitai_integration import CivitAIIntegration; import os;")
print("  civitai = CivitAIIntegration(api_key=os.getenv('CIVITAI_API_KEY'));")
print("  civitai.download_model(MODEL_ID)\"")
print("=" * 60)
