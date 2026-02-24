#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CivitAIでいいね（お気に入り）したモデルとLoRAをComfyUI用にダウンロードするスクリプト。
環境変数 CIVITAI_API_KEY が必要です。

使い方:
  python download_civitai_favorites.py           # 全件ダウンロード（既存はスキップ）
  python download_civitai_favorites.py --dry-run # 一覧表示のみ
  python download_civitai_favorites.py --limit 5  # 先頭5件のみ
  python download_civitai_favorites.py --fix-corrupted  # 破損ファイルを検出して再ダウンロード
"""

import argparse
import os
import re
import sys
from pathlib import Path


def is_safetensors_corrupted(path: Path) -> bool:
    """safetensors が開けない場合 True（破損・未完了）"""
    if not path.exists() or path.suffix.lower() not in (".safetensors",):
        return False
    try:
        import safetensors

        with safetensors.safe_open(path, framework="pt", device="cpu") as f:
            _ = list(f.keys())[:1]
        return False
    except Exception:
        return True


# プロキシ無効化（CivitAI接続のため）
for key in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
    os.environ.pop(key, None)

COMFYUI_CHECKPOINTS = Path(os.getenv("COMFYUI_CHECKPOINTS", "C:/ComfyUI/models/checkpoints"))
COMFYUI_LORAS = Path(os.getenv("COMFYUI_LORAS", "C:/ComfyUI/models/loras"))


# Windowsでファイル名に使えない文字をアンダースコアに置換
def sanitize_filename(name: str) -> str:
    if not name:
        return "download"
    bad = r'[<>:"/\\|?*\[\]]'
    return re.sub(bad, "_", name).strip() or "download"


def main():
    parser = argparse.ArgumentParser(description="CivitAIいいね一覧をComfyUI用にダウンロード")
    parser.add_argument("--dry-run", action="store_true", help="ダウンロードせず一覧表示のみ")
    parser.add_argument("--limit", type=int, default=0, help="ダウンロードする件数（0=全部）")
    parser.add_argument(
        "--fix-corrupted",
        action="store_true",
        help="既存ファイルが破損している場合に削除して再ダウンロード（.safetensors のみ検証）",
    )
    args = parser.parse_args()

    try:
        from civitai_integration import CivitAIIntegration
    except ImportError:
        print("[NG] civitai_integration が見つかりません")
        return 1

    api_key = os.getenv("CIVITAI_API_KEY")
    if not api_key:
        print("[NG] CIVITAI_API_KEY が設定されていません")
        print("     CivitAIのサイトでAPIキーを発行し、環境変数に設定してください")
        return 1

    civitai = CivitAIIntegration()
    civitai.session.proxies = {"http": None, "https": None}

    if not civitai.is_available():
        print("[NG] CivitAIが利用できません（APIキーを確認してください）")
        return 1

    print("=" * 60)
    print("CivitAI いいね一覧ダウンロード（ComfyUI用）")
    print("=" * 60)
    print(f"Checkpoints: {COMFYUI_CHECKPOINTS}")
    print(f"LoRAs:      {COMFYUI_LORAS}")
    if args.dry_run:
        print(" [dry-run] 一覧表示のみ")
    if args.limit:
        print(f" [limit] 先頭{args.limit}件のみ")
    if args.fix_corrupted:
        print(" [fix-corrupted] 破損ファイルを検出して再ダウンロード")
    print()

    # お気に入り取得（モデルタイプ指定なし＝全部）
    favorites = civitai.get_favorite_models(limit=100)
    if not favorites:
        print("お気に入りモデルが0件です。CivitAIでいいねしたモデル・LoRAが対象です。")
        return 0

    if args.limit:
        favorites = favorites[: args.limit]
    print(f"お気に入り: {len(favorites)}件（対象）")
    print()

    COMFYUI_CHECKPOINTS.mkdir(parents=True, exist_ok=True)
    COMFYUI_LORAS.mkdir(parents=True, exist_ok=True)

    downloaded = []
    skipped = []
    failed = []

    for i, model in enumerate(favorites):
        name = model.get("name", "Unknown")
        model_id = model.get("id")
        model_type = (model.get("type") or "").strip()

        versions = model.get("modelVersions") or []
        if not versions:
            skipped.append((name, "バージョンなし"))
            continue

        latest = versions[0]
        version_id = latest.get("id")
        files = latest.get("files") or []
        if not files:
            skipped.append((name, "ファイルなし"))
            continue

        file_info = files[0]
        raw_name = file_info.get("name") or f"model_{model_id}.safetensors"
        file_name = sanitize_filename(raw_name)

        # 保存先ディレクトリ
        if model_type == "Checkpoint":
            dest_dir = COMFYUI_CHECKPOINTS
        elif model_type in ("LORA", "LoRA", "LoCon", "LyCORIS"):
            dest_dir = COMFYUI_LORAS
        else:
            skipped.append((name, f"未対応タイプ: {model_type}"))
            continue

        dest_path = dest_dir / file_name
        if dest_path.exists():
            if args.fix_corrupted and is_safetensors_corrupted(dest_path):
                try:
                    dest_path.unlink()
                    print(
                        f"[{i+1}/{len(favorites)}] {name[:50]} ({model_type}) -> 破損のため削除し再ダウンロード"
                    )
                except OSError as e:
                    failed.append((name, f"削除失敗: {e}"))
                    if not args.dry_run:
                        print(f"  -> 削除NG: {e}")
                    continue
            else:
                skipped.append((name, "既存のためスキップ"))
                if args.dry_run:
                    print(
                        f"[{i+1}/{len(favorites)}] {name[:50]} ({model_type}) -> 既存のためスキップ"
                    )
                continue

        if args.dry_run:
            print(f"[{i+1}/{len(favorites)}] {name[:50]} ({model_type}) -> {file_name[:50]}")
            downloaded.append((name, str(dest_path)))
            continue

        print(f"[{i+1}/{len(favorites)}] {name[:50]} ({model_type}) -> {file_name[:40]}...")
        try:
            result = civitai.download_model(
                model_id=model_id,
                version_id=version_id,
                download_path=str(dest_path),
            )
            if result:
                downloaded.append((name, str(dest_path)))
                print(f"  -> OK")
            else:
                failed.append((name, "download_model が None"))
                print(f"  -> NG")
        except Exception as e:
            failed.append((name, str(e)))
            print(f"  -> NG: {e}")

    print()
    print("=" * 60)
    print(f"ダウンロード成功: {len(downloaded)}件")
    print(f"スキップ: {len(skipped)}件")
    print(f"失敗: {len(failed)}件")
    print("=" * 60)
    if downloaded:
        for n, p in downloaded:
            print(f"  [OK] {n} -> {p}")
    if failed:
        for n, reason in failed:
            print(f"  [NG] {n}: {reason}")

    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
