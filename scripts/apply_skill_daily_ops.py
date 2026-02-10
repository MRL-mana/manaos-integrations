#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日次運用タスク処理スクリプト
YAML形式の日次運用データをObsidianノートとSlack通知に変換
"""

import os
import sys
import json
import yaml
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from obsidian_integration import ObsidianIntegration
except ImportError:
    print("⚠️  obsidian_integration.pyが見つかりません。直接実装を使用します。")
    ObsidianIntegration = None

# 設定
OBSIDIAN_VAULT_PATH = os.getenv(
    "OBSIDIAN_VAULT_PATH",
    str(Path.home() / "Documents" / "Obsidian Vault")
)
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
HISTORY_FILE = project_root / "data" / "skill_daily_ops_history.json"
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


def mark_as_processed(idempotency_key: str, history: Dict[str, Any], result: Dict[str, Any]):
    """処理済みとしてマーク"""
    if "processed" not in history:
        history["processed"] = []
    
    history["processed"].append({
        "idempotency_key": idempotency_key,
        "processed_at": datetime.now().isoformat(),
        "result": result
    })


def generate_obsidian_content(data: Dict[str, Any]) -> str:
    """Obsidianノートの内容を生成"""
    lines = []
    
    # フロントマター
    frontmatter = {
        "title": data.get("title", "日報"),
        "date": data.get("date", datetime.now().strftime("%Y-%m-%d")),
        "tags": data.get("tags", []),
        "kind": data.get("kind", "daily_ops")
    }
    lines.append("---")
    for key, value in frontmatter.items():
        if isinstance(value, list):
            lines.append(f"{key}: {json.dumps(value, ensure_ascii=False)}")
        elif isinstance(value, str):
            lines.append(f"{key}: {value}")
        else:
            lines.append(f"{key}: {json.dumps(value, ensure_ascii=False, default=str)}")
    lines.append("---")
    lines.append("")
    
    # 要約
    if summary := data.get("summary"):
        lines.append("## 要約")
        lines.append("")
        lines.append(summary.strip())
        lines.append("")
    
    # タスク
    if tasks := data.get("tasks"):
        lines.append("## タスク")
        lines.append("")
        for task in tasks:
            status_emoji = {
                "todo": "⬜",
                "doing": "🔄",
                "done": "✅"
            }.get(task.get("status", "todo"), "⬜")
            
            priority_mark = {
                "high": "🔴",
                "medium": "🟡",
                "low": "🟢"
            }.get(task.get("priority", "medium"), "")
            
            lines.append(f"- {status_emoji} {priority_mark} {task.get('title', '')}")
            if task.get("status") == "doing":
                lines.append(f"  - 進行中")
        lines.append("")
    
    # メモ
    if notes := data.get("notes"):
        lines.append("## メモ")
        lines.append("")
        for note in notes:
            lines.append(f"- {note}")
        lines.append("")
    
    # メタ情報
    lines.append("---")
    lines.append(f"作成日時: {datetime.now().isoformat()}")
    lines.append(f"ID: {data.get('idempotency_key', 'unknown')}")
    
    return "\n".join(lines)


def create_obsidian_note(data: Dict[str, Any]) -> Optional[Path]:
    """Obsidianノートを作成"""
    if ObsidianIntegration:
        try:
            obsidian = ObsidianIntegration(OBSIDIAN_VAULT_PATH)
            if not obsidian.is_available():
                print(f"⚠️  Obsidian Vaultが見つかりません: {OBSIDIAN_VAULT_PATH}")
                return None
            
            title = data.get("title", "日報")
            date = data.get("date", datetime.now().strftime("%Y-%m-%d"))
            safe_title = title.replace("/", "-").replace("\\", "-")
            note_title = f"{date}_{safe_title}"
            
            content = generate_obsidian_content(data)
            tags = data.get("tags", [])
            
            note_path = obsidian.create_note(
                title=note_title,
                content=content,
                tags=tags,
                folder="Daily"
            )
            
            if note_path:
                print(f"✅ Obsidianノート作成完了: {note_path}")
                return note_path
            else:
                print("❌ Obsidianノート作成失敗")
                return None
        except Exception as e:
            print(f"❌ Obsidianノート作成エラー: {e}")
            return None
    else:
        # フォールバック: 直接ファイル作成
        try:
            vault_path = Path(OBSIDIAN_VAULT_PATH)
            daily_dir = vault_path / "Daily"
            daily_dir.mkdir(parents=True, exist_ok=True)
            
            title = data.get("title", "日報")
            date = data.get("date", datetime.now().strftime("%Y-%m-%d"))
            safe_title = title.replace("/", "-").replace("\\", "-")
            note_title = f"{date}_{safe_title}"
            
            content = generate_obsidian_content(data)
            note_path = daily_dir / f"{note_title}.md"
            
            with open(note_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"✅ Obsidianノート作成完了: {note_path}")
            return note_path
        except Exception as e:
            print(f"❌ Obsidianノート作成エラー: {e}")
            return None


def send_slack_notification(data: Dict[str, Any]) -> bool:
    """Slack通知を送信"""
    if not SLACK_WEBHOOK_URL:
        print("⚠️  SLACK_WEBHOOK_URLが設定されていません。スキップします。")
        return False
    
    try:
        title = data.get("title", "日報")
        date = data.get("date", datetime.now().strftime("%Y-%m-%d"))
        summary = data.get("summary", "")
        
        # タスクの要約
        tasks = data.get("tasks", [])
        task_summary = []
        for task in tasks:
            status_emoji = {
                "todo": "⬜",
                "doing": "🔄",
                "done": "✅"
            }.get(task.get("status", "todo"), "⬜")
            task_summary.append(f"{status_emoji} {task.get('title', '')}")
        
        message = f"📝 *{date} {title}*\n\n"
        if summary:
            message += f"{summary}\n\n"
        if task_summary:
            message += "*タスク:*\n" + "\n".join(task_summary)
        
        payload = {
            "text": message,
            "username": "ManaOS Daily Ops",
            "icon_emoji": ":memo:"
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
    if data.get("kind") != "daily_ops":
        print("⚠️  kindが'daily_ops'ではありません。スキップします。")
        return False
    
    idempotency_key = data.get("idempotency_key")
    if not idempotency_key:
        print("⚠️  idempotency_keyが設定されていません。スキップします。")
        return False
    
    # 履歴チェック
    history = load_history()
    if is_already_processed(idempotency_key, history):
        print(f"⏭️  既に処理済みです: {idempotency_key}")
        return True
    
    # 処理実行
    result = {
        "obsidian": False,
        "slack": False
    }
    
    # Obsidian保存
    if data.get("notify", {}).get("obsidian", True):
        note_path = create_obsidian_note(data)
        result["obsidian"] = note_path is not None
    else:
        print("⏭️  Obsidian保存はスキップされます")
    
    # Slack通知
    if data.get("notify", {}).get("slack", False):
        result["slack"] = send_slack_notification(data)
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
            "使用方法: python apply_skill_daily_ops.py "
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
