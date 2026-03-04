#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
データベース操作処理スクリプト
YAML形式のデータベース操作設定を読み込み、データベース操作を実行
"""

import os
import sys
import json
import yaml
import requests
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List

# 設定
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")

# データベースライブラリのインポート（オプション）
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    POSTGRESQL_AVAILABLE = True
except ImportError:
    POSTGRESQL_AVAILABLE = False

try:
    from pymongo import MongoClient
    MONGODB_AVAILABLE = True
except ImportError:
    MONGODB_AVAILABLE = False

project_root = Path(__file__).parent.parent
HISTORY_FILE = project_root / "data" / "skill_database_ops_history.json"
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


def execute_query_postgresql(connection_string: str, query: str, params: Optional[tuple] = None) -> Dict[str, Any]:
    """PostgreSQLでクエリを実行"""
    if not POSTGRESQL_AVAILABLE:
        return {"success": False, "error": "psycopg2-binaryがインストールされていません"}
    
    try:
        conn = psycopg2.connect(connection_string)
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, params)
            if cursor.description:
                results = [dict(row) for row in cursor.fetchall()]
                return {"success": True, "results": results}
            else:
                conn.commit()
                return {"success": True, "affected_rows": cursor.rowcount}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        if 'conn' in locals():
            conn.close()


def execute_query_sqlite(connection_string: str, query: str, params: Optional[tuple] = None) -> Dict[str, Any]:
    """SQLiteでクエリを実行"""
    try:
        # sqlite:///path/to/db.db からパスを抽出
        db_path = connection_string.replace("sqlite:///", "")
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, params or ())
        
        if cursor.description:
            results = [dict(row) for row in cursor.fetchall()]
            return {"success": True, "results": results}
        else:
            conn.commit()
            return {"success": True, "affected_rows": cursor.rowcount}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        if 'conn' in locals():
            conn.close()


def insert_postgresql(connection_string: str, table: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """PostgreSQLにデータを挿入"""
    if not POSTGRESQL_AVAILABLE:
        return {"success": False, "error": "psycopg2-binaryがインストールされていません"}
    
    try:
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["%s"] * len(data))
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        
        conn = psycopg2.connect(connection_string)
        cursor = conn.cursor()
        cursor.execute(query, tuple(data.values()))
        conn.commit()
        return {"success": True, "affected_rows": cursor.rowcount}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        if 'conn' in locals():
            conn.close()


def insert_mongodb(connection_string: str, database_name: str, collection: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """MongoDBにデータを挿入"""
    if not MONGODB_AVAILABLE:
        return {"success": False, "error": "pymongoがインストールされていません"}
    
    try:
        client = MongoClient(connection_string)
        db = client[database_name]
        result = db[collection].insert_one(data)
        return {"success": True, "inserted_id": str(result.inserted_id)}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        if 'client' in locals():
            client.close()


def send_slack_notification(action: str, result: Dict[str, Any]) -> bool:
    """Slack通知を送信"""
    if not SLACK_WEBHOOK_URL:
        print("⚠️  SLACK_WEBHOOK_URLが設定されていません。スキップします。")
        return False
    
    try:
        action_names = {
            "execute_query": "クエリ実行",
            "insert": "データ挿入",
            "update": "データ更新",
            "delete": "データ削除"
        }
        action_name = action_names.get(action, action)
        
        message = f"💾 *データベース操作: {action_name}*\n\n"
        
        if result.get("success"):
            message += f"✅ 成功\n"
            if "results" in result:
                message += f"結果: {len(result['results'])}件\n"
            if "affected_rows" in result:
                message += f"影響を受けた行: {result['affected_rows']}件\n"
            if "inserted_id" in result:
                message += f"挿入ID: {result['inserted_id']}\n"
        else:
            message += f"❌ 失敗: {result.get('error', '不明なエラー')}\n"
        
        payload = {
            "text": message,
            "username": "ManaOS Database Ops",
            "icon_emoji": ":database:"
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
    if data.get("kind") != "database_ops":
        print("⚠️  kindが'database_ops'ではありません。スキップします。")
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
    database_type = data.get("database_type")
    connection_string = data.get("connection_string")
    
    if not connection_string:
        result = {"success": False, "error": "connection_stringが指定されていません"}
    elif not database_type:
        result = {"success": False, "error": "database_typeが指定されていません"}
    else:
        result = {"success": False, "error": "不明なアクション"}
        
        try:
            if action == "execute_query":
                query = data.get("query")
                if not query:
                    result = {"success": False, "error": "queryが指定されていません"}
                else:
                    params = data.get("params")
                    if database_type == "postgresql":
                        result = execute_query_postgresql(connection_string, query, params)
                    elif database_type == "sqlite":
                        result = execute_query_sqlite(connection_string, query, params)
                    else:
                        result = {"success": False, "error": f"execute_queryは{database_type}では未対応です"}
                    
                    # クエリ結果をYAMLに追記
                    if result.get("success") and "results" in result:
                        data["results"] = result["results"]
                        with open(yaml_file, 'w', encoding='utf-8') as f:
                            yaml.dump(data, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
            
            elif action == "insert":
                insert_data = data.get("data")
                if not insert_data:
                    result = {"success": False, "error": "dataが指定されていません"}
                else:
                    if database_type == "postgresql":
                        table = data.get("table")
                        if not table:
                            result = {"success": False, "error": "tableが指定されていません"}
                        else:
                            result = insert_postgresql(connection_string, table, insert_data)
                    elif database_type == "mongodb":
                        collection = data.get("collection")
                        database_name = data.get("database_name", "test")
                        if not collection:
                            result = {"success": False, "error": "collectionが指定されていません"}
                        else:
                            result = insert_mongodb(connection_string, database_name, collection, insert_data)
                            if result.get("success") and "inserted_id" in result:
                                data["inserted_id"] = result["inserted_id"]
                                with open(yaml_file, 'w', encoding='utf-8') as f:
                                    yaml.dump(data, f, allow_unicode=True, sort_keys=False)
                    else:
                        result = {"success": False, "error": f"insertは{database_type}では未対応です"}
            
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
            "使用方法: python apply_skill_database_ops.py "
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
