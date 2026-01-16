#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ファイル整理処理スクリプト
YAML形式のファイル整理設定を読み込み、ファイルを分類・移動・整理
"""

import os
import sys
import json
import yaml
import requests
import shutil
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
import fnmatch

# 設定
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")

project_root = Path(__file__).parent.parent
HISTORY_FILE = project_root / "data" / "skill_file_organize_history.json"
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


def get_file_hash(file_path: Path) -> str:
    """ファイルのハッシュを計算"""
    hash_md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception:
        return ""


def organize_files(data: Dict[str, Any]) -> Dict[str, Any]:
    """ファイルを整理"""
    source_dir = Path(data.get("source_directory", ""))
    if not source_dir.exists():
        return {"success": False, "error": f"ソースディレクトリが見つかりません: {source_dir}"}
    
    if not source_dir.is_dir():
        return {"success": False, "error": f"ソースパスはディレクトリではありません: {source_dir}"}
    
    rules = data.get("rules", [])
    if not rules:
        return {"success": False, "error": "rulesが指定されていません"}
    
    move_files = data.get("move_files", True)
    results = {
        "processed": 0,
        "moved": [],
        "errors": []
    }
    
    try:
        # すべてのファイルを取得
        files = [f for f in source_dir.iterdir() if f.is_file()]
        
        for file_path in files:
            matched = False
            for rule in rules:
                pattern = rule.get("pattern", "")
                destination = rule.get("destination", "")
                
                if fnmatch.fnmatch(file_path.name, pattern):
                    # 相対パスの場合はプロジェクトルートから
                    if not Path(destination).is_absolute():
                        dest_dir = project_root / destination
                    else:
                        dest_dir = Path(destination)
                    
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    dest_path = dest_dir / file_path.name
                    
                    try:
                        if move_files:
                            shutil.move(str(file_path), str(dest_path))
                            results["moved"].append({
                                "file": str(file_path),
                                "destination": str(dest_path)
                            })
                        else:
                            shutil.copy2(str(file_path), str(dest_path))
                            results["moved"].append({
                                "file": str(file_path),
                                "destination": str(dest_path),
                                "action": "copied"
                            })
                        results["processed"] += 1
                        matched = True
                        break
                    except Exception as e:
                        results["errors"].append({
                            "file": str(file_path),
                            "error": str(e)
                        })
            
            if not matched:
                # どのルールにもマッチしない場合、ログに記録
                pass
        
        return {"success": True, "results": results}
    except Exception as e:
        return {"success": False, "error": str(e)}


def deduplicate_files(data: Dict[str, Any]) -> Dict[str, Any]:
    """重複ファイルを削除"""
    source_dir = Path(data.get("source_directory", ""))
    if not source_dir.exists():
        return {"success": False, "error": f"ソースディレクトリが見つかりません: {source_dir}"}
    
    keep_oldest = data.get("keep_oldest", True)
    results = {
        "processed": 0,
        "duplicates_removed": [],
        "errors": []
    }
    
    try:
        # すべてのファイルを取得
        files = [f for f in source_dir.rglob("*") if f.is_file()]
        
        # ハッシュでグループ化
        hash_groups: Dict[str, List[Path]] = {}
        for file_path in files:
            file_hash = get_file_hash(file_path)
            if file_hash:
                if file_hash not in hash_groups:
                    hash_groups[file_hash] = []
                hash_groups[file_hash].append(file_path)
        
        # 重複グループを処理
        for file_hash, file_group in hash_groups.items():
            if len(file_group) > 1:
                # 保持するファイルを決定
                if keep_oldest:
                    file_group.sort(key=lambda p: p.stat().st_mtime)
                    keep_file = file_group[0]
                    remove_files = file_group[1:]
                else:
                    file_group.sort(key=lambda p: p.stat().st_mtime, reverse=True)
                    keep_file = file_group[0]
                    remove_files = file_group[1:]
                
                # 重複ファイルを削除
                for remove_file in remove_files:
                    try:
                        remove_file.unlink()
                        results["duplicates_removed"].append({
                            "file": str(remove_file),
                            "kept": str(keep_file)
                        })
                        results["processed"] += 1
                    except Exception as e:
                        results["errors"].append({
                            "file": str(remove_file),
                            "error": str(e)
                        })
        
        return {"success": True, "results": results}
    except Exception as e:
        return {"success": False, "error": str(e)}


def send_slack_notification(action: str, result: Dict[str, Any]) -> bool:
    """Slack通知を送信"""
    if not SLACK_WEBHOOK_URL:
        print("⚠️  SLACK_WEBHOOK_URLが設定されていません。スキップします。")
        return False
    
    try:
        action_names = {
            "organize": "ファイル整理",
            "classify": "ファイル分類",
            "deduplicate": "重複ファイル削除"
        }
        action_name = action_names.get(action, action)
        
        message = f"📁 *ファイル整理: {action_name}*\n\n"
        
        if result.get("success"):
            message += f"✅ 成功\n"
            if "results" in result:
                results = result["results"]
                if "processed" in results:
                    message += f"処理ファイル数: {results['processed']}\n"
                if "moved" in results:
                    message += f"移動/コピー: {len(results['moved'])}件\n"
                if "duplicates_removed" in results:
                    message += f"重複削除: {len(results['duplicates_removed'])}件\n"
        else:
            message += f"❌ 失敗: {result.get('error', '不明なエラー')}\n"
        
        payload = {
            "text": message,
            "username": "ManaOS File Organize",
            "icon_emoji": ":file_folder:"
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
    if data.get("kind") != "file_organize":
        print("⚠️  kindが'file_organize'ではありません。スキップします。")
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
    action = data.get("action")
    result = {"success": False, "error": "不明なアクション"}
    
    try:
        if action == "organize":
            result = organize_files(data)
            # 整理結果をYAMLに追記
            if result.get("success") and "results" in result:
                data["results"] = result["results"]
                with open(yaml_file, 'w', encoding='utf-8') as f:
                    yaml.dump(data, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
        elif action == "deduplicate":
            result = deduplicate_files(data)
            # 削除結果をYAMLに追記
            if result.get("success") and "results" in result:
                data["results"] = result["results"]
                with open(yaml_file, 'w', encoding='utf-8') as f:
                    yaml.dump(data, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
        else:
            result = {"success": False, "error": f"未実装のアクション: {action}"}
    except Exception as e:
        result = {"success": False, "error": str(e)}
        print(f"❌ 処理エラー: {e}")
    
    # Slack通知
    if data.get("notify", {}).get("slack", False):
        send_slack_notification(action, result)
    else:
        print("⏭️  Slack通知はスキップされます")
    
    # 履歴に記録
    mark_as_processed(idempotency_key, history, result)
    save_history(history)
    
    if result.get("success"):
        print(f"✅ 処理完了: {yaml_file}")
        return True
    else:
        print(f"❌ 処理失敗: {yaml_file} - {result.get('error', '')}")
        return False


def main():
    """メイン処理"""
    if len(sys.argv) < 2:
        print(
            "使用方法: python apply_skill_file_organize.py "
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
