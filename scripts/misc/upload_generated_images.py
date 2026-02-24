#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成画像の自動連携: Google Drive / Notion へのアップロード
- 環境変数 GOOGLE_DRIVE_FOLDER_ID と認証が設定されていれば Drive にアップロード
- 環境変数 NOTION_API_KEY と NOTION_DATABASE_ID が設定されていれば Notion にページ作成
- 未設定の場合は対象ファイル一覧を出力（n8n 等で後続処理可能）
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timedelta

if sys.platform == "win32":
    try:
        import io

        if hasattr(sys.stdout, "buffer"):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

COMFYUI_BASE = Path(os.getenv("COMFYUI_BASE", "C:/ComfyUI"))
OUTPUT_DIR = COMFYUI_BASE / "output"
GENERATION_METADATA_DB = COMFYUI_BASE / "input/mana_favorites/generation_metadata.json"


def list_recent_outputs(max_age_hours=24, include_lab=True):
    """直近の出力画像パスとメタデータを取得"""
    since = datetime.now() - timedelta(hours=max_age_hours)
    paths = []
    lab_dir = OUTPUT_DIR / "lab"
    folders = [OUTPUT_DIR]
    if include_lab and lab_dir.exists():
        folders.append(lab_dir)
    for folder in folders:
        if not folder.exists():
            continue
        for f in folder.glob("*.png"):
            try:
                if datetime.fromtimestamp(f.stat().st_mtime) >= since:
                    paths.append(str(f))
            except Exception:
                pass
    paths.sort(key=lambda p: os.path.getmtime(p), reverse=True)

    meta_by_path = {}
    if GENERATION_METADATA_DB.exists():
        try:
            with open(GENERATION_METADATA_DB, "r", encoding="utf-8") as f:
                gen = json.load(f)
            for _pid, ent in gen.items():
                if not isinstance(ent, dict):
                    continue
                for op in ent.get("output_paths") or []:
                    meta_by_path[op] = {
                        "model": ent.get("model"),
                        "loras": ent.get("loras"),
                        "prompt": (ent.get("prompt") or "")[:200],
                        "profile": ent.get("profile", "safe"),
                    }
        except Exception:
            pass

    return paths, meta_by_path


def upload_to_drive(file_paths, folder_id):
    """Google Drive にアップロード（google-api-python-client が必要）"""
    try:
        from google.oauth2.credentials import Credentials
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
    except ImportError:
        print(
            "Google Drive アップロードには google-api-python-client が必要です: pip install google-api-python-client google-auth"
        )
        return 0

    creds = None
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if creds_path and Path(creds_path).exists():
        creds = service_account.Credentials.from_service_account_file(
            creds_path, scopes=["https://www.googleapis.com/auth/drive.file"]
        )
    if not creds:
        print("GOOGLE_APPLICATION_CREDENTIALS を設定してください")
        return 0

    drive = build("drive", "v3", credentials=creds)
    uploaded = 0
    for path in file_paths:
        p = Path(path)
        if not p.exists():
            continue
        try:
            meta = {"name": p.name, "parents": [folder_id]}
            media = MediaFileUpload(path, mimetype="image/png", resumable=True)
            drive.files().create(body=meta, media_body=media, fields="id").execute()
            uploaded += 1
            print(f"  Drive: {p.name}")
        except Exception as e:
            print(f"  Drive エラー {p.name}: {e}")
    return uploaded


def upload_to_notion(file_paths, meta_by_path, database_id, api_key):
    """Notion にページ作成（画像は URL が必要なため、ローカルパスはメモのみ）。"""
    try:
        import requests
    except ImportError:
        print("Notion 連携には requests が必要です: pip install requests")
        return 0

    headers = {
        "Authorization": "Bearer %s" % api_key,
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }
    created = 0
    for path in file_paths:
        p = Path(path)
        meta = meta_by_path.get(path) or {}
        name = p.name
        body = {
            "parent": {"database_id": database_id},
            "properties": {
                "Name": {"title": [{"text": {"content": name[:2000]}}]},
                "ファイル": {"rich_text": [{"text": {"content": path[:2000]}}]},
                "モデル": {"rich_text": [{"text": {"content": (meta.get("model") or "")[:2000]}}]},
                "プロファイル": {
                    "rich_text": [{"text": {"content": (meta.get("profile") or "safe")[:200]}}]
                },
            },
        }
        if meta.get("prompt"):
            body["properties"]["プロンプト"] = {
                "rich_text": [{"text": {"content": meta["prompt"][:2000]}}]
            }
        try:
            r = requests.post(
                "https://api.notion.com/v1/pages", headers=headers, json=body, timeout=10
            )
            if r.status_code in (200, 201):
                created += 1
                print(f"  Notion: {name}")
            else:
                print(f"  Notion エラー {name}: {r.status_code} {r.text[:200]}")
        except Exception as e:
            print(f"  Notion エラー {name}: {e}")
    return created


def main():
    parser = argparse.ArgumentParser(description="生成画像を Drive/Notion にアップロード")
    parser.add_argument("--hours", type=int, default=24, help="対象の直近時間（時間）")
    parser.add_argument("--drive", action="store_true", help="Google Drive にアップロード")
    parser.add_argument("--notion", action="store_true", help="Notion にページ作成")
    parser.add_argument(
        "--list-only", action="store_true", help="一覧のみ出力（アップロードしない）"
    )
    parser.add_argument("--no-lab", action="store_true", help="lab フォルダを対象に含めない")
    args = parser.parse_args()

    folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
    notion_key = os.getenv("NOTION_API_KEY")
    notion_db = os.getenv("NOTION_DATABASE_ID")

    paths, meta_by_path = list_recent_outputs(max_age_hours=args.hours, include_lab=not args.no_lab)
    print(f"対象画像: {len(paths)} 件（直近 {args.hours} 時間）")

    if args.list_only:
        for path in paths:
            m = meta_by_path.get(path) or {}
            print(f"  {path} | {m.get('model', '')} | {m.get('profile', '')}")
        return

    if args.drive and folder_id:
        print("Google Drive にアップロード中...")
        upload_to_drive(paths, folder_id)
    elif args.drive and not folder_id:
        print("GOOGLE_DRIVE_FOLDER_ID を設定してください")

    if args.notion and notion_key and notion_db:
        print("Notion にページ作成中...")
        upload_to_notion(paths, meta_by_path, notion_db, notion_key)
    elif args.notion and (not notion_key or not notion_db):
        print("NOTION_API_KEY と NOTION_DATABASE_ID を設定してください")

    if not args.drive and not args.notion:
        print("--drive または --notion を指定するか、" "--list-only で一覧を確認してください")


if __name__ == "__main__":
    main()
