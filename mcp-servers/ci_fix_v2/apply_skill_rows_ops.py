#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rows操作処理スクリプト
YAML形式のRows操作設定を読み込み、Rowsスプレッドシート操作を実行
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

# 設定
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")

try:
    from rows_integration import RowsIntegration
except ImportError:
    print("⚠️  rows_integration.pyが見つかりません。")
    RowsIntegration = None

HISTORY_FILE = project_root / "data" / "skill_rows_ops_history.json"
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


def send_data_to_rows(data: Dict[str, Any]) -> Dict[str, Any]:
    """Rowsスプレッドシートにデータを送信"""
    if not RowsIntegration:
        return {"success": False, "error": "RowsIntegrationが利用できません"}
    
    rows = RowsIntegration()
    if not rows.is_available():
        return {"success": False, "error": "Rows APIキーが設定されていません"}
    
    spreadsheet_id = data.get("spreadsheet_id")
    if not spreadsheet_id:
        return {"success": False, "error": "spreadsheet_idが指定されていません"}
    
    send_data = data.get("data")
    if not send_data:
        return {"success": False, "error": "dataが指定されていません"}
    
    sheet_name = data.get("sheet_name", "Sheet1")
    append = data.get("append", True)
    
    try:
        result = rows.send_to_rows(
            spreadsheet_id=spreadsheet_id,
            data=send_data,
            sheet_name=sheet_name,
            append=append
        )
        
        if result:
            return {"success": True, "result": result}
        else:
            return {"success": False, "error": "データ送信に失敗しました"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def query_rows(data: Dict[str, Any]) -> Dict[str, Any]:
    """Rowsスプレッドシートにクエリを実行"""
    if not RowsIntegration:
        return {"success": False, "error": "RowsIntegrationが利用できません"}
    
    rows = RowsIntegration()
    if not rows.is_available():
        return {"success": False, "error": "Rows APIキーが設定されていません"}
    
    spreadsheet_id = data.get("spreadsheet_id")
    if not spreadsheet_id:
        return {"success": False, "error": "spreadsheet_idが指定されていません"}
    
    query = data.get("query")
    if not query:
        return {"success": False, "error": "queryが指定されていません"}
    
    sheet_name = data.get("sheet_name", "Sheet1")
    
    try:
        result = rows.ai_query(
            spreadsheet_id=spreadsheet_id,
            query=query,
            sheet_name=sheet_name
        )
        
        if result:
            return {"success": True, "results": result}
        else:
            return {"success": False, "error": "クエリ実行に失敗しました"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def list_spreadsheets(data: Dict[str, Any]) -> Dict[str, Any]:
    """Rowsスプレッドシート一覧を取得"""
    if not RowsIntegration:
        return {"success": False, "error": "RowsIntegrationが利用できません"}
    
    rows = RowsIntegration()
    if not rows.is_available():
        return {"success": False, "error": "Rows APIキーが設定されていません"}
    
    try:
        result = rows.list_spreadsheets()
        
        if result:
            return {"success": True, "results": result}
        else:
            return {"success": False, "error": "スプレッドシート一覧取得に失敗しました"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def send_slack_notification(action: str, result: Dict[str, Any]) -> bool:
    """Slack通知を送信"""
    if not SLACK_WEBHOOK_URL:
        print("⚠️  SLACK_WEBHOOK_URLが設定されていません。スキップします。")
        return False
    
    try:
        action_names = {
            "send_data": "データ送信",
            "query": "クエリ実行",
            "list": "スプレッドシート一覧取得"
        }
        action_name = action_names.get(action, action)
        
        message = f"📊 *Rows操作: {action_name}*\n\n"
        
        if result.get("success"):
            message += f"✅ 成功\n"
            if "results" in result:
                if isinstance(result["results"], list):
                    message += f"結果: {len(result['results'])}件\n"
                else:
                    message += f"結果: {result['results']}\n"
            if "result" in result:
                message += f"結果: {result['result']}\n"
        else:
            message += f"❌ 失敗: {result.get('error', '不明なエラー')}\n"
        
        payload = {
            "text": message,
            "username": "ManaOS Rows Ops",
            "icon_emoji": ":chart_with_upwards_trend:"
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
    if data.get("kind") != "rows_ops":
        print("⚠️  kindが'rows_ops'ではありません。スキップします。")
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
        if action == "send_data":
            result = send_data_to_rows(data)
        elif action == "query":
            result = query_rows(data)
            # クエリ結果をYAMLに追記
            if result.get("success") and "results" in result:
                data["results"] = result["results"]
                with open(yaml_file, 'w', encoding='utf-8') as f:
                    yaml.dump(data, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
        elif action == "list":
            result = list_spreadsheets(data)
            # スプレッドシート一覧をYAMLに追記
            if result.get("success") and "results" in result:
                data["results"] = result["results"]
                with open(yaml_file, 'w', encoding='utf-8') as f:
                    yaml.dump(data, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
        else:
            result = {"success": False, "error": f"不明なアクション: {action}"}
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
            "使用方法: python apply_skill_rows_ops.py "
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
