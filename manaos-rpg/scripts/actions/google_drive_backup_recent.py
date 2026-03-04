from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


def _pick_existing_path(candidates: list[Path]) -> Path | None:
    for candidate in candidates:
        try:
            if candidate.exists():
                return candidate
        except Exception:
            continue
    return None


def _load_manifest(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        return []
    out: list[dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        file_path = str(item.get("path") or "").strip()
        if not file_path:
            continue
        out.append(
            {
                "path": file_path,
                "name": str(item.get("name") or Path(file_path).name),
                "size_bytes": int(item.get("size_bytes") or 0),
                "last_write": str(item.get("last_write") or ""),
            }
        )
    return out


def _build_drive_service(token_path: Path) -> Any:
    scopes = ["https://www.googleapis.com/auth/drive.file"]
    creds = Credentials.from_authorized_user_file(str(token_path), scopes)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_path.write_text(creds.to_json(), encoding="utf-8")
    return build("drive", "v3", credentials=creds)


def _ensure_folder_path(service: Any, folder_path: str) -> str | None:
    folder_path = (folder_path or "").strip("/").strip()
    if not folder_path:
        return None

    parent_id = None
    for name in folder_path.split("/"):
        safe_name = name.replace("'", "\\'")
        q_parts = [
            "mimeType='application/vnd.google-apps.folder'",
            "trashed=false",
            f"name='{safe_name}'",
        ]
        if parent_id:
            q_parts.append(f"'{parent_id}' in parents")
        query = " and ".join(q_parts)
        res = service.files().list(q=query, fields="files(id,name)", pageSize=10).execute()
        files = res.get("files") or []
        if files:
            parent_id = str(files[0].get("id") or "")
            continue

        body: dict[str, Any] = {
            "name": name,
            "mimeType": "application/vnd.google-apps.folder",
        }
        if parent_id:
            body["parents"] = [parent_id]
        created = service.files().create(body=body, fields="id").execute()
        parent_id = str(created.get("id") or "")

    return parent_id or None


def main() -> int:
    parser = argparse.ArgumentParser(description="Backup recent files to Google Drive")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--folder-path", default="ManaOS_Backup/RPG")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[3]
    desktop = Path(os.path.expandvars(r"%USERPROFILE%/Desktop")).resolve()
    credentials = _pick_existing_path([desktop / "credentials.json", repo_root / "credentials.json"])
    token = _pick_existing_path([desktop / "token.json", repo_root / "token.json"])

    if not credentials or not token:
        print(
            json.dumps(
                {
                    "ok": False,
                    "reason": "auth_files_missing",
                    "detail": "credentials.json/token.json not found",
                },
                ensure_ascii=False,
            )
        )
        return 2

    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        print(json.dumps({"ok": False, "reason": "manifest_missing"}, ensure_ascii=False))
        return 3

    rows = _load_manifest(manifest_path)
    if not rows:
        print(json.dumps({"ok": True, "reason": "no_candidates", "uploaded": 0, "failed": 0}, ensure_ascii=False))
        return 0

    try:
        service = _build_drive_service(token)
        parent_id = _ensure_folder_path(service, args.folder_path)
    except Exception as e:
        print(json.dumps({"ok": False, "reason": "drive_init_failed", "error": str(e)}, ensure_ascii=False))
        return 4

    uploaded: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []

    for item in rows:
        file_path = item["path"]
        file_name = item["name"]
        try:
            body: dict[str, Any] = {"name": file_name}
            if parent_id:
                body["parents"] = [parent_id]
            media = MediaFileUpload(file_path, resumable=True)
            created = service.files().create(body=body, media_body=media, fields="id").execute()
            file_id = str(created.get("id") or "")
            if file_id:
                uploaded.append({"path": file_path, "name": file_name, "file_id": file_id})
            else:
                failed.append({"path": file_path, "name": file_name, "reason": "upload_failed"})
        except Exception as e:
            failed.append({"path": file_path, "name": file_name, "reason": str(e)})

    print(
        json.dumps(
            {
                "ok": True,
                "folder_path": args.folder_path,
                "requested": len(rows),
                "uploaded": len(uploaded),
                "failed": len(failed),
                "uploaded_items": uploaded[:20],
                "failed_items": failed[:20],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
