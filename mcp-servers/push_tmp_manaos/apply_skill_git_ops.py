#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Git操作処理スクリプト
YAML形式のGit操作設定を読み込み、Gitコマンドを実行
"""

import os
import sys
import json
import yaml
import requests
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List

# 設定
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")

project_root = Path(__file__).parent.parent
HISTORY_FILE = project_root / "data" / "skill_git_ops_history.json"
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


def run_git_command(
    repo_path: Path, command: List[str]
) -> tuple[bool, str, str]:
    """Gitコマンドを実行"""
    try:
        result = subprocess.run(
            ["git"] + command,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=60
        )
        return (
            result.returncode == 0,
            result.stdout.strip(),
            result.stderr.strip()
        )
    except subprocess.TimeoutExpired:
        return (False, "", "コマンドがタイムアウトしました")
    except Exception as e:
        return (False, "", f"エラー: {str(e)}")


def git_status(repo_path: Path) -> Dict[str, Any]:
    """Gitの状態を取得"""
    success, stdout, stderr = run_git_command(repo_path, ["status", "--porcelain"])
    if not success:
        return {"success": False, "message": stderr}

    files = []
    for line in stdout.split("\n"):
        if line.strip():
            status = line[:2]
            filename = line[3:]
            files.append({"status": status, "filename": filename})

    return {"success": True, "files": files, "output": stdout}


def git_commit(
    repo_path: Path, message: str, files: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Gitコミットを実行"""
    # ファイルをステージング
    if files:
        for file_pattern in files:
            success, stdout, stderr = run_git_command(
                repo_path, ["add", file_pattern]
            )
            if not success:
                return {"success": False, "message": f"git add失敗: {stderr}"}
    else:
        # すべてのファイルをステージング
        success, stdout, stderr = run_git_command(repo_path, ["add", "."])
        if not success:
            return {"success": False, "message": f"git add失敗: {stderr}"}

    # コミット
    success, stdout, stderr = run_git_command(
        repo_path, ["commit", "-m", message]
    )

    if success:
        # コミットハッシュを取得
        hash_success, commit_hash, _ = run_git_command(
            repo_path, ["rev-parse", "HEAD"]
        )
        return {
            "success": True,
            "message": "コミットしました",
            "commit_hash": commit_hash.strip() if hash_success else None,
            "output": stdout
        }
    else:
        if "nothing to commit" in stderr.lower():
            return {"success": True, "message": "コミットする変更がありません", "output": stderr}
        return {"success": False, "message": f"git commit失敗: {stderr}"}


def git_push(
    repo_path: Path, branch: Optional[str] = None, remote: str = "origin"
) -> Dict[str, Any]:
    """Gitプッシュを実行"""
    if branch:
        command = ["push", remote, branch]
    else:
        command = ["push"]

    success, stdout, stderr = run_git_command(repo_path, command)

    if success:
        return {"success": True, "message": "プッシュしました", "output": stdout}
    else:
        return {"success": False, "message": f"git push失敗: {stderr}"}


def git_pull(
    repo_path: Path, branch: Optional[str] = None, remote: str = "origin"
) -> Dict[str, Any]:
    """Gitプルを実行"""
    command = ["pull", remote]
    if branch:
        command.append(branch)

    success, stdout, stderr = run_git_command(repo_path, command)

    if success:
        return {"success": True, "message": "プルしました", "output": stdout}
    else:
        return {"success": False, "message": f"git pull失敗: {stderr}"}


def git_tag(
    repo_path: Path, tag_name: str, tag_message: Optional[str] = None,
    push_tag: bool = False
) -> Dict[str, Any]:
    """Gitタグを作成"""
    if tag_message:
        command = ["tag", "-a", tag_name, "-m", tag_message]
    else:
        command = ["tag", tag_name]

    success, stdout, stderr = run_git_command(repo_path, command)

    if not success:
        return {"success": False, "message": f"git tag失敗: {stderr}"}

    result = {"success": True, "message": "タグを作成しました", "tag": tag_name}

    # タグをプッシュ
    if push_tag:
        push_success, push_stdout, push_stderr = run_git_command(
            repo_path, ["push", "origin", tag_name]
        )
        if push_success:
            result["pushed"] = True
            result["message"] = "タグを作成してプッシュしました"
        else:
            result["pushed"] = False
            result["push_error"] = push_stderr

    return result


def send_slack_notification(
    data: Dict[str, Any], result: Dict[str, Any]
) -> bool:
    """Slack通知を送信"""
    if not SLACK_WEBHOOK_URL:
        print("⚠️  SLACK_WEBHOOK_URLが設定されていません。スキップします。")
        return False

    try:
        action = data.get("action", "")
        repo_path = data.get("repository_path", ".")

        action_names = {
            "commit": "コミット",
            "push": "プッシュ",
            "pull": "プル",
            "tag": "タグ作成",
            "status": "状態確認",
            "commit_and_push": "コミット&プッシュ"
        }

        message = f"🔀 *Git操作: {action_names.get(action, action)}*\n\n"
        message += f"*リポジトリ:* {repo_path}\n"
        message += f"*アクション:* {action}\n"

        if result.get("success"):
            message += f"*結果:* ✅ 成功\n"
            if result.get("commit_hash"):
                message += f"*コミットハッシュ:* `{result['commit_hash']}`\n"
            if result.get("tag"):
                message += f"*タグ:* `{result['tag']}`\n"
            if result.get("files"):
                file_count = len(result.get("files", []))
                message += f"*変更ファイル数:* {file_count}\n"
        else:
            message += f"*結果:* ❌ 失敗\n"
            message += f"*エラー:* {result.get('message', '')}"

        payload = {
            "text": message,
            "username": "ManaOS Git",
            "icon_emoji": ":octocat:"
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
    if data.get("kind") != "git_ops":
        print("⚠️  kindが'git_ops'ではありません。スキップします。")
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

    # リポジトリパス
    repo_path_str = data.get("repository_path", ".")
    repo_path = project_root / repo_path_str if not Path(repo_path_str).is_absolute() else Path(repo_path_str)
    
    # Gitリポジトリか確認
    git_dir = repo_path / ".git"
    if not git_dir.exists() and not git_dir.is_dir():
        print(f"❌ Gitリポジトリが見つかりません: {repo_path}")
        return False

    # アクション実行
    result = {"success": False, "message": ""}

    if action == "status":
        result = git_status(repo_path)
        print(f"{'✅' if result['success'] else '❌'} {result.get('message', '状態確認完了')}")

    elif action == "commit":
        commit_message = data.get("commit_message")
        if not commit_message:
            print("⚠️  commit_messageが設定されていません。")
            return False
        files = data.get("files")
        result = git_commit(repo_path, commit_message, files)
        print(f"{'✅' if result['success'] else '❌'} {result['message']}")

    elif action == "push":
        branch = data.get("branch")
        remote = data.get("remote", "origin")
        result = git_push(repo_path, branch, remote)
        print(f"{'✅' if result['success'] else '❌'} {result['message']}")

    elif action == "pull":
        branch = data.get("branch")
        remote = data.get("remote", "origin")
        result = git_pull(repo_path, branch, remote)
        print(f"{'✅' if result['success'] else '❌'} {result['message']}")

    elif action == "tag":
        tag_name = data.get("tag_name")
        if not tag_name:
            print("⚠️  tag_nameが設定されていません。")
            return False
        tag_message = data.get("tag_message")
        push_tag = data.get("push_tag", False)
        result = git_tag(repo_path, tag_name, tag_message, push_tag)
        print(f"{'✅' if result['success'] else '❌'} {result['message']}")

    elif action == "commit_and_push":
        commit_message = data.get("commit_message")
        if not commit_message:
            print("⚠️  commit_messageが設定されていません。")
            return False
        files = data.get("files")
        branch = data.get("branch")
        remote = data.get("remote", "origin")

        # コミット
        commit_result = git_commit(repo_path, commit_message, files)
        if not commit_result["success"]:
            result = commit_result
        else:
            # プッシュ
            push_result = git_push(repo_path, branch, remote)
            result = {
                "success": push_result["success"],
                "message": f"コミット: {commit_result['message']}, プッシュ: {push_result['message']}",
                "commit_hash": commit_result.get("commit_hash"),
                "push_result": push_result
            }
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
            "使用方法: python apply_skill_git_ops.py "
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
