#!/usr/bin/env python3
"""
Remi Command Router ワークフローをn8nデータベースに直接インポート
"""

import json
import sqlite3
import sys
from pathlib import Path
from datetime import datetime
import uuid

# ワークフローファイル
WORKFLOW_FILE = Path("/root/manaos_command_hub/n8n_workflows/remi_command_webhook.json")
# n8nデータベースパス
N8N_DB = Path("/root/n8n_data/database.sqlite")


def import_workflow_to_db(workflow_data: dict) -> bool:
    """ワークフローをn8nデータベースに直接インポート"""
    try:
        if not N8N_DB.exists():
            print(f"❌ n8nデータベースが見つかりません: {N8N_DB}")
            print("   n8nが起動しているか確認してください")
            return False

        # データベースに接続
        conn = sqlite3.connect(str(N8N_DB))
        cursor = conn.cursor()

        # ワークフローIDを生成
        workflow_id = str(uuid.uuid4())
        workflow_name = workflow_data.get("name", "Remi Command Router")

        # 既存のワークフローをチェック（同じ名前があるか）
        cursor.execute(
            "SELECT id FROM workflow_entity WHERE name = ?",
            (workflow_name,)
        )
        existing = cursor.fetchone()
        if existing:
            print(f"⚠️ ワークフロー '{workflow_name}' は既に存在します")
            print(f"   既存のワークフローを更新しますか？ (y/n): ", end="")
            # 自動で更新する
            workflow_id = existing[0]
            cursor.execute(
                "DELETE FROM workflow_entity WHERE id = ?",
                (workflow_id,)
            )
            print("更新します")

        # ワークフローをJSONに変換
        workflow_json = json.dumps({
            "name": workflow_name,
            "nodes": workflow_data.get("nodes", []),
            "connections": workflow_data.get("connections", {}),
            "settings": workflow_data.get("settings", {}),
            "pinData": workflow_data.get("pinData", {}),
            "staticData": workflow_data.get("staticData"),
            "triggerCount": workflow_data.get("triggerCount", 1),
            "updatedAt": workflow_data.get("updatedAt", datetime.utcnow().isoformat() + "Z"),
            "versionId": workflow_data.get("versionId", "1")
        })

        # ワークフローをデータベースに挿入（既存のスクリプトと同じ形式）
        cursor.execute(
            """INSERT INTO workflow_entity
               (id, name, nodes, connections, settings, active, createdAt, updatedAt)
               VALUES (?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))""",
            (
                workflow_id,
                workflow_name,
                json.dumps(workflow_data.get("nodes", [])),
                json.dumps(workflow_data.get("connections", {})),
                json.dumps(workflow_data.get("settings", {})),
                0  # active = False
            )
        )

        conn.commit()
        conn.close()

        print(f"✅ ワークフロー '{workflow_name}' をデータベースにインポートしました")
        print(f"   ID: {workflow_id}")
        return True

    except sqlite3.Error as e:
        print(f"❌ データベースエラー: {e}")
        return False
    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """メイン処理"""
    print("🚀 Remi Command Router ワークフロー（データベース直接インポート）")
    print(f"📍 データベース: {N8N_DB}\n")

    if not WORKFLOW_FILE.exists():
        print(f"❌ ワークフローファイルが見つかりません: {WORKFLOW_FILE}")
        sys.exit(1)

    # ワークフローファイルを読み込み
    print(f"📂 ワークフローファイルを読み込み: {WORKFLOW_FILE}")
    with open(WORKFLOW_FILE, "r", encoding="utf-8") as f:
        workflow_data = json.load(f)

    print(f"📋 ワークフロー名: {workflow_data.get('name', 'Unknown')}\n")

    # ワークフローをインポート
    if import_workflow_to_db(workflow_data):
        print("\n" + "=" * 60)
        print("✅ インポート完了！")
        print("=" * 60)
        print("\n💡 次のステップ:")
        print("1. n8nを再起動するか、n8n UIでワークフローを確認")
        print("2. ワークフローを開いて設定を確認")
        print("3. 環境変数 COMMAND_HUB_TOKEN が設定されているか確認")
        print("4. ワークフローを有効化")
        print("5. Webhook URLを確認: /webhook/remi/command")
        print("=" * 60)
        print("\n⚠️ 注意: n8nを再起動すると、インポートしたワークフローが表示されます")
    else:
        print("\n❌ インポートに失敗しました")
        sys.exit(1)


if __name__ == "__main__":
    main()

