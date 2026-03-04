#!/usr/bin/env python3
"""
manaOS Command Hub へのコマンド送信ユーティリティ

使い方:
    python send_command.py command.json
    または
    python send_command.py --task github_get_file --path dev_qa.md
"""

import json
import sys
import argparse
import requests
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

# デフォルト設定
DEFAULT_HUB_URL = os.getenv("COMMAND_HUB_URL", "http://localhost:9404")
DEFAULT_AUTH_TOKEN = os.getenv("COMMAND_HUB_TOKEN", "manaos-secret-token-please-change")

def send_command_from_file(file_path: str):
    """JSONファイルからコマンドを読み込んで送信"""
    with open(file_path, "r", encoding="utf-8") as f:
        cmd = json.load(f)

    return send_command(cmd)

def send_command(cmd: dict):
    """コマンドを送信"""
    url = f"{DEFAULT_HUB_URL}/command"

    try:
        response = requests.post(url, json=cmd, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"エラー: {e}", file=sys.stderr)
        if hasattr(e.response, 'text'):
            print(f"レスポンス: {e.response.text}", file=sys.stderr)
        sys.exit(1)

def create_github_get_command(path: str, repo: str = None, branch: str = "main"):
    """github_get_fileコマンドを作成"""
    return {
        "task": "github_get_file",
        "meta": {
            "caller": "cli",
            "reason": f"Get file: {path}"
        },
        "params": {
            "path": path,
            "repo": repo,
            "branch": branch
        },
        "auth_token": DEFAULT_AUTH_TOKEN
    }

def create_github_update_command(path: str, append_text: str = None, new_content: str = None,
                                repo: str = None, branch: str = "main",
                                commit_message: str = None):
    """github_update_fileコマンドを作成"""
    if append_text:
        content_mode = "append"
    elif new_content:
        content_mode = "overwrite"
    else:
        raise ValueError("append_text または new_content のいずれかが必要です")

    return {
        "task": "github_update_file",
        "meta": {
            "caller": "cli",
            "reason": f"Update file: {path}"
        },
        "params": {
            "path": path,
            "repo": repo,
            "branch": branch,
            "content_mode": content_mode,
            "append_text": append_text,
            "new_content": new_content,
            "commit_message": commit_message or f"Update {path} from manaOS Command Hub"
        },
        "auth_token": DEFAULT_AUTH_TOKEN
    }

def main():
    parser = argparse.ArgumentParser(description="manaOS Command Hub コマンド送信")
    parser.add_argument("command_file", nargs="?", help="コマンドJSONファイル")
    parser.add_argument("--task", choices=["github_get_file", "github_update_file", "file_write", "image_job"],
                       help="タスクタイプ")
    parser.add_argument("--path", help="ファイルパス")
    parser.add_argument("--repo", help="GitHubリポジトリ (owner/repo)")
    parser.add_argument("--branch", default="main", help="ブランチ名")
    parser.add_argument("--append", help="追記するテキスト")
    parser.add_argument("--content", help="上書きするコンテンツ")
    parser.add_argument("--message", help="コミットメッセージ")
    parser.add_argument("--url", default=DEFAULT_HUB_URL, help="Command Hub URL")
    parser.add_argument("--token", help="認証トークン")

    args = parser.parse_args()

    # 認証トークンの設定
    if args.token:
        global DEFAULT_AUTH_TOKEN
        DEFAULT_AUTH_TOKEN = args.token

    # コマンドファイルが指定されている場合
    if args.command_file:
        result = send_command_from_file(args.command_file)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    # コマンドライン引数からコマンドを作成
    if args.task == "github_get_file":
        if not args.path:
            print("エラー: --path が必要です", file=sys.stderr)
            sys.exit(1)
        cmd = create_github_get_command(args.path, args.repo, args.branch)
        if args.token:
            cmd["auth_token"] = args.token
        result = send_command(cmd)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.task == "github_update_file":
        if not args.path:
            print("エラー: --path が必要です", file=sys.stderr)
            sys.exit(1)
        if not args.append and not args.content:
            print("エラー: --append または --content が必要です", file=sys.stderr)
            sys.exit(1)
        cmd = create_github_update_command(
            args.path, args.append, args.content, args.repo, args.branch, args.message
        )
        if args.token:
            cmd["auth_token"] = args.token
        result = send_command(cmd)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    else:
        print("エラー: コマンドファイルを指定するか、--task と必要なパラメータを指定してください", file=sys.stderr)
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()

