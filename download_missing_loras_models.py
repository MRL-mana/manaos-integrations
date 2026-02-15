#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
見つからないLoRA・モデルをCivitAIからダウンロードするスクリプト
"""

import sys
import os
from pathlib import Path

# Windowsでのエンコーディング設定（必要に応じて）
# if sys.platform == 'win32':
#     import io
#     if hasattr(sys.stdout, 'buffer'):
#         try:
#             sys.stdout.reconfigure(encoding='utf-8', errors='replace')
#         except (AttributeError, ValueError, OSError):
#             pass

# 見つからないLoRA・モデルのリスト
MISSING_LORAS = [
    "cuteGirlMix4_v10",
    "koreanDollLikeness_v10",
    "aliceNikke_v20",
    "japaneseDollLikeness_v10",
    "koreanDollLikeness_v15",
    "chilloutmixss30_v30",
    "pureerosface_v1",
    "GodPussy1 v2",
    "virtualgirlRin_v30",
    "upshirtUnderboob_v10",
    "FilmG3",
    "cowgirl-1.0",
]

MISSING_MODELS = [
    "chilloutmix_NiPrunedFp32Fix",
    "braBeautifulRealistic_brav5",
    "majicmixRealistic_v4",
]

# ダウンロード先
COMFYUI_LORA_DIR = Path("C:/ComfyUI/models/loras")
COMFYUI_MODELS_DIR = Path("C:/ComfyUI/models/checkpoints")

try:
    from civitai_integration import CivitAIIntegration
    CIVITAI_AVAILABLE = True
except ImportError:
    CIVITAI_AVAILABLE = False
    print("⚠️ CivitAI統合モジュールが見つかりません")

# プロキシ設定を無効化
import os
os.environ.pop('HTTP_PROXY', None)
os.environ.pop('HTTPS_PROXY', None)
os.environ.pop('http_proxy', None)
os.environ.pop('https_proxy', None)

def search_and_download(query: str, model_type: str = "LoRA", download_dir: Path = None):
    """
    CivitAIで検索してダウンロード

    Args:
        query: 検索クエリ
        model_type: モデルタイプ（LoRA, Checkpoint）
        download_dir: ダウンロード先ディレクトリ
    """
    if not CIVITAI_AVAILABLE:
        print(f"❌ CivitAI統合が利用できません")
        return None

    # プロキシを無効化
    civitai = CivitAIIntegration()
    # セッションのプロキシ設定を無効化
    civitai.session.proxies = {
        'http': None,
        'https': None
    }

    if not civitai.is_available():
        print(f"❌ CivitAI APIキーが設定されていません")
        print("   💡 環境変数 CIVITAI_API_KEY を設定してください")
        return None

    print(f"\n🔍 検索中: '{query}' ({model_type})...")

    # モデルを検索
    models = civitai.search_models(
        query=query,
        limit=5,
        model_type=model_type
    )

    if not models:
        print(f"  ❌ 検索結果が見つかりませんでした")
        return None

    # 最初の結果を表示
    print(f"  📊 {len(models)}件の候補が見つかりました")
    for i, model in enumerate(models[:3], 1):
        name = model.get("name", "N/A")
        model_id = model.get("id", "N/A")
        downloads = model.get("downloadCount", 0)
        rating = model.get("rating", 0)
        print(f"    {i}. {name}")
        print(f"       ID: {model_id}, 評価: {rating}/5, DL: {downloads:,}")

    # 最初の結果をダウンロード
    if models:
        best_match = models[0]
        model_id = str(best_match.get("id"))
        model_name = best_match.get("name", "unknown")

        print(f"\n📥 ダウンロード開始: {model_name}")

        try:
            if download_dir:
                # ファイル名から無効な文字を削除（Windowsのファイル名に使用できない文字）
                import re
                invalid_chars = r'[<>:"/\\|?*]'
                safe_name = re.sub(invalid_chars, '_', model_name)
                download_path = download_dir / f"{safe_name}.safetensors"
            else:
                download_path = None

            result = civitai.download_model(
                model_id=model_id,
                download_path=str(download_path) if download_path else None
            )

            if result:
                print(f"  ✅ ダウンロード完了: {result}")
                return result
            else:
                print(f"  ❌ ダウンロードに失敗しました")
                return None
        except Exception as e:
            print(f"  ❌ エラー: {e}")
            return None

    return None

def main():
    print("=" * 60)
    print("見つからないLoRA・モデルをCivitAIからダウンロード")
    print("=" * 60)
    print()

    if not CIVITAI_AVAILABLE:
        print("❌ CivitAI統合モジュールが見つかりません")
        print("   💡 civitai_integration.py が必要です")
        return

    civitai = CivitAIIntegration()
    if not civitai.is_available():
        print("❌ CivitAI APIキーが設定されていません")
        print("   💡 環境変数 CIVITAI_API_KEY を設定してください")
        print("   💡 または、.envファイルに CIVITAI_API_KEY=your_key を追加")
        return

    print("✅ CivitAI統合が利用可能です")
    print()

    # LoRAをダウンロード
    print("=" * 60)
    print("LoRAのダウンロード")
    print("=" * 60)

    downloaded_loras = []
    for lora_name in MISSING_LORAS:
        result = search_and_download(
            query=lora_name,
            model_type="LoRA",
            download_dir=COMFYUI_LORA_DIR
        )
        if result:
            downloaded_loras.append(lora_name)
        print()

    # モデルをダウンロード
    print("=" * 60)
    print("モデルのダウンロード")
    print("=" * 60)

    downloaded_models = []
    for model_name in MISSING_MODELS:
        result = search_and_download(
            query=model_name,
            model_type="Checkpoint",
            download_dir=COMFYUI_MODELS_DIR
        )
        if result:
            downloaded_models.append(model_name)
        print()

    # 結果サマリー
    print("=" * 60)
    print("ダウンロード結果")
    print("=" * 60)
    print(f"✅ ダウンロード成功 - LoRA: {len(downloaded_loras)}件, モデル: {len(downloaded_models)}件")
    if downloaded_loras:
        print("\nダウンロードしたLoRA:")
        for lora in downloaded_loras:
            print(f"  - {lora}")
    if downloaded_models:
        print("\nダウンロードしたモデル:")
        for model in downloaded_models:
            print(f"  - {model}")
    print()

if __name__ == '__main__':
    main()
