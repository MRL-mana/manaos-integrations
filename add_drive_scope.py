#!/usr/bin/env python3
"""
token.json に drive.file スコープを追加して再認証する。
既存のスコープ（calendar, tasks, sheets 等）も全て維持する。
"""
import sys
import json
from pathlib import Path

try:
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
except ImportError:
    print("[ERROR] google-auth-oauthlib が不足。以下を実行してください:")
    print("  py -3.10 -m pip install google-auth-oauthlib")
    sys.exit(1)

REPO_ROOT = Path(__file__).parent
CREDS_PATH = REPO_ROOT / "credentials.json"
TOKEN_PATH = REPO_ROOT / "token.json"

# 既存スコープ ＋ drive.file を全部含める
SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/tasks",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/photoslibrary.readonly",
]

def main():
    if not CREDS_PATH.exists():
        print(f"[ERROR] credentials.json not found: {CREDS_PATH}")
        sys.exit(1)

    creds = None
    # 既存トークンがあれば読み込み試行（スコープ違いは無視してOK、再取得するので）
    if TOKEN_PATH.exists():
        try:
            existing = json.loads(TOKEN_PATH.read_text(encoding="utf-8"))
            existing_scopes = existing.get("scopes", [])
            print(f"[INFO] 既存スコープ: {existing_scopes}")
            if "https://www.googleapis.com/auth/drive.file" in existing_scopes:
                # 既に drive.file がある → リフレッシュ試行
                creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                    TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")
                    print("[OK] drive.file スコープ、トークンリフレッシュ完了")
                    return
        except Exception as e:
            print(f"[WARN] 既存トークン読み込みスキップ: {e}")

    print("[INFO] ブラウザで再認証します（drive.file スコープ追加）...")
    flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_PATH), SCOPES)
    creds = flow.run_local_server(port=0)

    TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")
    print(f"[OK] token.json 更新完了: {TOKEN_PATH}")
    saved = json.loads(TOKEN_PATH.read_text(encoding="utf-8"))
    print(f"[INFO] 新スコープ: {saved.get('scopes', [])}")

if __name__ == "__main__":
    main()
