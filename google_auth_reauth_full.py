#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow


SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/tasks",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/photoslibrary.readonly",
]


def main() -> int:
    root = Path(__file__).resolve().parent
    credentials_path = root / "credentials.json"
    token_path = root / "token.json"

    if not credentials_path.exists():
        print(f"[ERROR] credentials.json not found: {credentials_path}")
        return 1

    creds = None
    if token_path.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
        except Exception:
            creds = None

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception:
            creds = None

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
        creds = flow.run_local_server(port=0)

    token_path.write_text(creds.to_json(), encoding="utf-8")

    payload = json.loads(token_path.read_text(encoding="utf-8"))
    scopes = payload.get("scopes") or []
    print("[OK] token updated")
    print(f"token: {token_path}")
    print("scopes:")
    for scope in scopes:
        print(f"- {scope}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
