#!/usr/bin/env python3
"""
Remi Command Router ワークフローをn8nにインポート
"""

import json
import sys
import os
import time
from pathlib import Path
import requests

# 環境変数
N8N_BASE = os.getenv("N8N_BASE", "http://localhost:5678")
N8N_API_KEY = os.getenv("N8N_API_KEY", "")
WORKFLOW_FILE = Path("/root/manaos_command_hub/n8n_workflows/remi_command_webhook.json")


def wait_for_n8n(max_retries=10, delay=2):
    """n8nが起動するまで待つ"""
    for i in range(max_retries):
        try:
            response = requests.get(f"{N8N_BASE}/healthz", timeout=2)
            if response.status_code == 200:
                print("✅ n8nに接続できました")
                return True
        except Exception:
            pass
        if i < max_retries - 1:
            print(f"⏳ n8nの起動を待っています... ({i+1}/{max_retries})")
            time.sleep(delay)
    return False


def import_workflow(workflow_data: dict) -> bool:
    """ワークフローをn8nにインポート"""
    try:
        # n8nのワークフロー形式に変換
        n8n_workflow = {
            "name": workflow_data.get("name", "Unknown"),
            "nodes": workflow_data.get("nodes", []),
            "connections": workflow_data.get("connections", {}),
            "settings": workflow_data.get("settings", {}),
            "active": False,  # 最初は無効化
            "tags": workflow_data.get("tags", []),
            "pinData": workflow_data.get("pinData", {}),
            "staticData": workflow_data.get("staticData"),
            "triggerCount": workflow_data.get("triggerCount", 1),
            "updatedAt": workflow_data.get("updatedAt"),
            "versionId": workflow_data.get("versionId", "1")
        }

        headers = {"Content-Type": "application/json"}

        # APIキーがある場合は最初から含める
        if N8N_API_KEY:
            headers["X-N8N-API-KEY"] = N8N_API_KEY
            print(f"🔑 APIキーを使用してインポートを試行します...")

        # API経由でインポート
        response = requests.post(
            f"{N8N_BASE}/api/v1/workflows",
            json=n8n_workflow,
            headers=headers,
            timeout=10
        )

        # 認証が必要な場合、Basic認証で再試行
        if response.status_code == 401:
            print(f"⚠️ APIキー認証が失敗したため、Basic認証を試行します...")
            N8N_USER = os.getenv("N8N_USER", "mana")
            N8N_PASSWORD = os.getenv("N8N_PASSWORD", "trinity2025")
            response = requests.post(
                f"{N8N_BASE}/api/v1/workflows",
                json=n8n_workflow,
                auth=(N8N_USER, N8N_PASSWORD),
                timeout=10
            )

        if response.status_code in [200, 201]:
            result = response.json()
            workflow_id = result.get("id", "unknown")
            print(f"✅ ワークフロー '{workflow_data['name']}' をインポートしました")
            print(f"   ID: {workflow_id}")
            print(f"   URL: {N8N_BASE}/workflow/{workflow_id}")
            return True
        else:
            print(f"⚠️ ワークフロー '{workflow_data['name']}' のインポート失敗: {response.status_code}")
            print(f"   エラー: {response.text[:500]}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"❌ n8nに接続できません: {N8N_BASE}")
        print("   n8nが起動しているか確認してください")
        return False
    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """メイン処理"""
    print("🚀 Remi Command Router ワークフローインポート開始...")
    print(f"📍 n8n URL: {N8N_BASE}\n")

    # n8nの起動を待つ
    if not wait_for_n8n():
        print("❌ n8nに接続できませんでした")
        print("\n💡 手動でインポートする場合:")
        print(f"   1. {N8N_BASE} にアクセス")
        print(f"   2. ワークフロー → インポート")
        print(f"   3. {WORKFLOW_FILE} を選択")
        sys.exit(1)

    if not WORKFLOW_FILE.exists():
        print(f"❌ ワークフローファイルが見つかりません: {WORKFLOW_FILE}")
        sys.exit(1)

    # ワークフローファイルを読み込み
    print(f"📂 ワークフローファイルを読み込み: {WORKFLOW_FILE}")
    with open(WORKFLOW_FILE, "r", encoding="utf-8") as f:
        workflow_data = json.load(f)

    print(f"📋 ワークフロー名: {workflow_data.get('name', 'Unknown')}\n")

    # ワークフローをインポート
    if import_workflow(workflow_data):
        print("\n" + "=" * 60)
        print("✅ インポート完了！")
        print("=" * 60)
        print("\n💡 次のステップ:")
        print(f"1. n8nにアクセス: {N8N_BASE}")
        print("2. ワークフローを開いて設定を確認")
        print("3. 環境変数 COMMAND_HUB_TOKEN が設定されているか確認")
        print("4. ワークフローを有効化")
        print("5. Webhook URLを確認: /webhook/remi/command")
        print("=" * 60)
    else:
        print("\n❌ インポートに失敗しました")
        print("   手動でインポートしてください")
        sys.exit(1)


if __name__ == "__main__":
    main()

