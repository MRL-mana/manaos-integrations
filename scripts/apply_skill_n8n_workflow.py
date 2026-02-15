#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
n8nワークフロー操作スクリプト
YAML形式のワークフロー操作設定を読み込み、n8nワークフローを操作
"""

import os
import sys
import json
import yaml
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

# 設定
try:
    from manaos_integrations._paths import N8N_PORT
except Exception:  # pragma: no cover
    try:
        from _paths import N8N_PORT  # type: ignore
    except Exception:  # pragma: no cover
        N8N_PORT = int(os.getenv("N8N_PORT", "5678"))

N8N_BASE_URL = os.getenv("N8N_BASE_URL", f"http://127.0.0.1:{N8N_PORT}")
N8N_API_KEY = os.getenv("N8N_API_KEY", "")
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")

project_root = Path(__file__).parent.parent
HISTORY_FILE = project_root / "data" / "skill_n8n_workflow_history.json"
ARTIFACTS_DIR = project_root / "artifacts"
ARTIFACTS_DIR.mkdir(exist_ok=True)


def get_headers() -> Dict[str, str]:
    """n8n APIヘッダーを取得"""
    headers = {"Content-Type": "application/json"}
    if N8N_API_KEY:
        headers["X-N8N-API-KEY"] = N8N_API_KEY
    return headers


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


def activate_workflow(workflow_id: str) -> Dict[str, Any]:
    """ワークフローを有効化"""
    try:
        url = f"{N8N_BASE_URL}/api/v1/workflows/{workflow_id}/activate"
        response = requests.post(url, headers=get_headers(), timeout=30)

        if response.status_code == 200:
            return {"success": True, "message": "ワークフローを有効化しました"}
        else:
            return {
                "success": False,
                "message": f"エラー: {response.status_code} - {response.text}"
            }
    except Exception as e:
        return {"success": False, "message": f"エラー: {str(e)}"}


def deactivate_workflow(workflow_id: str) -> Dict[str, Any]:
    """ワークフローを無効化"""
    try:
        url = f"{N8N_BASE_URL}/api/v1/workflows/{workflow_id}/deactivate"
        response = requests.post(url, headers=get_headers(), timeout=30)

        if response.status_code == 200:
            return {"success": True, "message": "ワークフローを無効化しました"}
        else:
            return {
                "success": False,
                "message": f"エラー: {response.status_code} - {response.text}"
            }
    except Exception as e:
        return {"success": False, "message": f"エラー: {str(e)}"}


def execute_workflow(
    workflow_id: str, payload: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """ワークフローを実行"""
    try:
        url = f"{N8N_BASE_URL}/api/v1/workflows/{workflow_id}/execute"
        response = requests.post(
            url, json=payload or {}, headers=get_headers(), timeout=60
        )

        if response.status_code in [200, 201]:
            result = response.json()
            return {
                "success": True,
                "message": "ワークフローを実行しました",
                "execution_id": result.get("id")
            }
        else:
            return {
                "success": False,
                "message": f"エラー: {response.status_code} - {response.text}"
            }
    except Exception as e:
        return {"success": False, "message": f"エラー: {str(e)}"}


def import_workflow(
    workflow_file: Path, activate: bool = True
) -> Dict[str, Any]:
    """ワークフローをインポート"""
    try:
        # ワークフローファイルを読み込み
        with open(workflow_file, 'r', encoding='utf-8') as f:
            workflow_data = json.load(f)

        url = f"{N8N_BASE_URL}/api/v1/workflows"
        response = requests.post(
            url, json=workflow_data, headers=get_headers(), timeout=30
        )

        if response.status_code in [200, 201]:
            result = response.json()
            workflow_id = result.get("id")

            # 有効化
            activated = False
            if activate and workflow_id:
                activate_result = activate_workflow(workflow_id)
                activated = activate_result.get("success", False)

            return {
                "success": True,
                "message": "ワークフローをインポートしました",
                "workflow_id": workflow_id,
                "activated": activated
            }
        else:
            return {
                "success": False,
                "message": f"エラー: {response.status_code} - {response.text}"
            }
    except Exception as e:
        return {"success": False, "message": f"エラー: {str(e)}"}


def send_slack_notification(
    data: Dict[str, Any], result: Dict[str, Any]
) -> bool:
    """Slack通知を送信"""
    if not SLACK_WEBHOOK_URL:
        print("⚠️  SLACK_WEBHOOK_URLが設定されていません。スキップします。")
        return False

    try:
        action = data.get("action", "")
        workflow_id = data.get("workflow_id", "")
        workflow_file = data.get("workflow_file", "")

        action_names = {
            "activate": "有効化",
            "deactivate": "無効化",
            "execute": "実行",
            "import": "インポート"
        }

        message = f"⚙️  *n8nワークフロー{action_names.get(action, action)}*\n\n"
        message += f"*アクション:* {action}\n"

        if workflow_id:
            message += f"*ワークフローID:* {workflow_id}\n"
        if workflow_file:
            message += f"*ワークフローファイル:* {workflow_file}\n"

        if result.get("success"):
            message += f"*結果:* ✅ 成功\n"
            if result.get("workflow_id"):
                message += f"*新しいワークフローID:* {result.get('workflow_id')}\n"
            if result.get("execution_id"):
                message += f"*実行ID:* {result.get('execution_id')}\n"
        else:
            message += f"*結果:* ❌ 失敗\n"
            message += f"*エラー:* {result.get('message', '')}"

        payload = {
            "text": message,
            "username": "ManaOS n8n",
            "icon_emoji": ":gear:"
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
    if data.get("kind") != "n8n_workflow":
        print("⚠️  kindが'n8n_workflow'ではありません。スキップします。")
        return False

    idempotency_key = data.get("idempotency_key")
    if not idempotency_key:
        print("⚠️  idempotency_keyが設定されていません。スキップします。")
        return False

    action = data.get("action")
    if not action:
        print("⚠️  actionが設定されていません。スキップします。")
        return False

    # 履歴チェック
    history = load_history()
    if is_already_processed(idempotency_key, history):
        print(f"⏭️  既に処理済みです: {idempotency_key}")
        return True

    # アクション実行
    result = {"success": False, "message": ""}

    if action == "activate":
        workflow_id = data.get("workflow_id")
        if not workflow_id:
            print("⚠️  workflow_idが設定されていません。")
            return False
        result = activate_workflow(workflow_id)
        print(f"{'✅' if result['success'] else '❌'} {result['message']}")

    elif action == "deactivate":
        workflow_id = data.get("workflow_id")
        if not workflow_id:
            print("⚠️  workflow_idが設定されていません。")
            return False
        result = deactivate_workflow(workflow_id)
        print(f"{'✅' if result['success'] else '❌'} {result['message']}")

    elif action == "execute":
        workflow_id = data.get("workflow_id")
        if not workflow_id:
            print("⚠️  workflow_idが設定されていません。")
            return False
        payload = data.get("execute_payload")
        result = execute_workflow(workflow_id, payload)
        print(f"{'✅' if result['success'] else '❌'} {result['message']}")

    elif action == "import":
        workflow_file = data.get("workflow_file")
        if not workflow_file:
            print("⚠️  workflow_fileが設定されていません。")
            return False
        workflow_path = Path(workflow_file)
        if not workflow_path.exists():
            # プロジェクトルートからの相対パスも試す
            workflow_path = project_root / workflow_file
            if not workflow_path.exists():
                print(f"❌ ワークフローファイルが見つかりません: {workflow_file}")
                return False
        activate = data.get("activate_after_import", True)
        result = import_workflow(workflow_path, activate)
        print(f"{'✅' if result['success'] else '❌'} {result['message']}")

    else:
        print(f"⚠️  不明なアクション: {action}")
        return False

    # Slack通知
    if data.get("notify", {}).get("slack", False):
        send_slack_notification(data, result)
    else:
        print("⏭️  Slack通知はスキップされます")

    # 履歴に記録
    mark_as_processed(idempotency_key, history, result)
    save_history(history)

    print(f"✅ 処理完了: {yaml_file}")
    return result.get("success", False)


def main():
    """メイン処理"""
    if len(sys.argv) < 2:
        print(
            "使用方法: python apply_skill_n8n_workflow.py "
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
