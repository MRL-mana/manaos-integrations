#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google Driveバックアップ処理スクリプト
YAML形式のバックアップ設定を読み込み、Google Driveにアップロード
"""

import os
import sys
import json
import yaml
import zipfile
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from google_drive_integration import GoogleDriveIntegration
except ImportError:
    print("⚠️  google_drive_integration.pyが見つかりません")
    GoogleDriveIntegration = None

# 設定
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
HISTORY_FILE = project_root / "data" / "skill_drive_backup_history.json"
ARTIFACTS_DIR = project_root / "artifacts"
ARTIFACTS_DIR.mkdir(exist_ok=True)


def load_history() -> Dict[str, Any]:
    """処理履歴を読み込む"""
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️  履歴ファイルの読み込みエラー: {e}")
    return {"processed": []}


def save_history(history: Dict[str, Any]):
    """処理履歴を保存"""
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def is_already_processed(
    idempotency_key: str, history: Dict[str, Any]
) -> bool:
    """既に処理済みかチェック"""
    processed_keys = [
        item.get("idempotency_key")
        for item in history.get("processed", [])
    ]
    return idempotency_key in processed_keys


def mark_as_processed(
    idempotency_key: str, history: Dict[str, Any], result: Dict[str, Any]
):
    """処理済みとしてマーク"""
    if "processed" not in history:
        history["processed"] = []

    history["processed"].append({
        "idempotency_key": idempotency_key,
        "processed_at": datetime.now().isoformat(),
        "result": result
    })


def create_zip(source: Path, output: Path) -> bool:
    """ZIPファイルを作成"""
    try:
        with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as zipf:
            if source.is_file():
                zipf.write(source, source.name)
            else:
                for file_path in source.rglob("*"):
                    if file_path.is_file():
                        arcname = file_path.relative_to(source)
                        zipf.write(file_path, arcname)
        print(f"✅ ZIPファイル作成完了: {output}")
        return True
    except Exception as e:
        print(f"❌ ZIPファイル作成エラー: {e}")
        return False


def upload_to_drive(
    file_path: Path, destination: str
) -> Optional[str]:
    """Google Driveにアップロード"""
    if not GoogleDriveIntegration:
        print("❌ Google Drive統合が利用できません")
        return None

    try:
        drive = GoogleDriveIntegration()
        if not drive.is_available():
            print("❌ Google Driveが利用できません（認証が必要です）")
            return None

        file_id = drive.upload_file(
            str(file_path),
            folder_id=None,  # destinationパスを使用
            file_name=file_path.name,
            overwrite=True
        )

        if file_id:
            print(f"✅ Google Driveアップロード完了: {file_id}")
            return file_id
        else:
            print("❌ Google Driveアップロード失敗")
            return None
    except Exception as e:
        print(f"❌ Google Driveアップロードエラー: {e}")
        return None


def send_slack_notification(data: Dict[str, Any], file_id: Optional[str]) -> bool:
    """Slack通知を送信"""
    if not SLACK_WEBHOOK_URL:
        print("⚠️  SLACK_WEBHOOK_URLが設定されていません。スキップします。")
        return False

    try:
        date = data.get("date", datetime.now().strftime("%Y-%m-%d"))
        source = data.get("source", "")
        destination = data.get("destination", "")
        description = data.get("description", "")

        message = f"📦 *Google Driveバックアップ完了*\n\n"
        message += f"*日付:* {date}\n"
        if description:
            message += f"*説明:* {description}\n"
        message += f"*ソース:* `{source}`\n"
        message += f"*保存先:* `{destination}`\n"
        if file_id:
            message += f"*ファイルID:* {file_id}"

        payload = {
            "text": message,
            "username": "ManaOS Backup",
            "icon_emoji": ":package:"
        }

        response = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=10)

        if response.status_code == 200:
            print("✅ Slack通知送信完了")
            return True
        else:
            print(f"❌ Slack通知送信失敗: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Slack通知送信エラー: {e}")
        return False


def process_yaml_file(yaml_file: Path) -> bool:
    """YAMLファイルを処理"""
    print(f"\n📁 処理開始: {yaml_file}")

    # YAML読み込み
    try:
        with open(yaml_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
    except Exception as e:
        print(f"❌ YAMLファイル読み込みエラー: {e}")
        return False

    # バリデーション
    if data.get("kind") != "drive_backup":
        print("⚠️  kindが'drive_backup'ではありません。スキップします。")
        return False

    idempotency_key = data.get("idempotency_key")
    if not idempotency_key:
        print("⚠️  idempotency_keyが設定されていません。スキップします。")
        return False

    source = data.get("source")
    if not source:
        print("⚠️  sourceが設定されていません。スキップします。")
        return False

    destination = data.get("destination", "")
    if not destination:
        print("⚠️  destinationが設定されていません。スキップします。")
        return False

    # 履歴チェック
    history = load_history()
    if is_already_processed(idempotency_key, history):
        print(f"⏭️  既に処理済みです: {idempotency_key}")
        return True

    # ソース確認
    source_path = Path(source)
    if not source_path.exists():
        print(f"❌ ソースが見つかりません: {source}")
        return False

    # 処理実行
    result = {
        "drive": False,
        "slack": False,
        "file_id": None
    }

    # アップロード用ファイルを準備
    upload_file = source_path
    temp_zip = None

    if data.get("compress", False):
        # ZIP圧縮
        temp_dir = ARTIFACTS_DIR / "temp"
        temp_dir.mkdir(exist_ok=True)
        zip_name = f"{source_path.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        temp_zip = temp_dir / zip_name

        if create_zip(source_path, temp_zip):
            upload_file = temp_zip
        else:
            print("⚠️  ZIP圧縮に失敗しました。元ファイルをアップロードします。")

    # Google Driveにアップロード
    file_id = upload_to_drive(upload_file, destination)
    result["drive"] = file_id is not None
    result["file_id"] = file_id

    # 一時ZIPファイルを削除
    if temp_zip and temp_zip.exists():
        try:
            temp_zip.unlink()
        except Exception as e:
            print(f"⚠️  一時ファイル削除エラー: {e}")

    # Slack通知
    if data.get("notify", {}).get("slack", False):
        result["slack"] = send_slack_notification(data, file_id)
    else:
        print("⏭️  Slack通知はスキップされます")

    # 履歴に記録
    mark_as_processed(idempotency_key, history, result)
    save_history(history)

    print(f"✅ 処理完了: {yaml_file}")
    return True


def main():
    """メイン処理"""
    if len(sys.argv) < 2:
        print(
            "使用方法: python apply_skill_drive_backup.py "
            "<yaml_file> [yaml_file2 ...]"
        )
        sys.exit(1)

    yaml_files = [Path(f) for f in sys.argv[1:]]

    success_count = 0
    for yaml_file in yaml_files:
        if not yaml_file.exists():
            print(f"❌ ファイルが見つかりません: {yaml_file}")
            continue

        if process_yaml_file(yaml_file):
            success_count += 1

    print(f"\n🎉 処理完了: {success_count}/{len(yaml_files)} ファイル")

    if success_count < len(yaml_files):
        sys.exit(1)


if __name__ == "__main__":
    main()
