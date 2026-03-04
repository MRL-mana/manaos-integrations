#!/usr/bin/env python3
"""
organized_from_c フォルダのファイルを並列でGoogle Driveへアップロードし、
完了分を backup_staged へ移動するバルクアップローダー。
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload


REPO_ROOT = Path(__file__).resolve().parents[3]
DESKTOP = Path(os.path.expandvars(r"%USERPROFILE%/Desktop")).resolve()

SOURCE_ROOT = Path(r"D:\AI_Storage\organized_from_c")
STAGE_ROOT  = Path(r"D:\AI_Storage\backup_staged")
DRIVE_FOLDER = "ManaOS_Backup/D_AI"
WORKERS = 5
LOG_FILE = REPO_ROOT / "drive_bulk_progress.log"


def _log(msg: str) -> None:
    line = f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {msg}"
    print(line, flush=True)
    try:
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def _pick_existing(candidates: list[Path]) -> Path | None:
    for p in candidates:
        if p.exists():
            return p
    return None


def _build_service(token_path: Path):
    scopes = ["https://www.googleapis.com/auth/drive.file"]
    creds = Credentials.from_authorized_user_file(str(token_path), scopes)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_path.write_text(creds.to_json(), encoding="utf-8")
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def _ensure_folder(service, folder_path: str) -> str | None:
    parent_id = None
    for name in folder_path.strip("/").split("/"):
        safe = name.replace("'", "\\'")
        q_parts = [
            "mimeType='application/vnd.google-apps.folder'",
            "trashed=false",
            f"name='{safe}'",
        ]
        if parent_id:
            q_parts.append(f"'{parent_id}' in parents")
        res = service.files().list(q=" and ".join(q_parts), fields="files(id)", pageSize=5).execute()
        files = res.get("files") or []
        if files:
            parent_id = files[0]["id"]
        else:
            body: dict[str, Any] = {"name": name, "mimeType": "application/vnd.google-apps.folder"}
            if parent_id:
                body["parents"] = [parent_id]
            parent_id = service.files().create(body=body, fields="id").execute()["id"]
    return parent_id


def _upload_one(token_path: Path, parent_id: str | None, src: Path, stage_dir: Path) -> dict[str, Any]:
    """1ファイルをアップロードし、完了後に stage_dir へ移動する"""
    # ファイルがロックされていたらスキップ（別プロセスが処理中）
    try:
        with open(src, "rb") as _fh:
            pass
    except PermissionError:
        return {"ok": False, "src": str(src), "error": "locked_skip", "skip": True}
    except OSError:
        return {"ok": False, "src": str(src), "error": "read_error", "skip": True}

    try:
        svc = _build_service(token_path)
        body: dict[str, Any] = {"name": src.name}
        if parent_id:
            body["parents"] = [parent_id]
        media = MediaFileUpload(str(src), resumable=False)
        result = svc.files().create(body=body, media_body=media, fields="id").execute()
        file_id = result.get("id", "")

        # stage へ移動（失敗してもアップロードは成功扱い）
        stage_dir.mkdir(parents=True, exist_ok=True)
        dest = stage_dir / src.name
        if dest.exists():
            dest = stage_dir / f"{src.stem}_{int(time.time()*1000)}{src.suffix}"
        try:
            shutil.move(str(src), str(dest))
            moved = True
        except Exception:
            moved = False  # ロックされていてもアップロード済みとして記録

        return {"ok": True, "src": str(src), "file_id": file_id, "dest": str(dest), "moved": moved}
    except HttpError as e:
        return {"ok": False, "src": str(src), "error": f"http_{e.status_code}: {e.reason}"}
    except Exception as e:
        return {"ok": False, "src": str(src), "error": str(e)[:120]}


def main() -> int:
    token = _pick_existing([DESKTOP / "token.json", REPO_ROOT / "token.json"])
    if not token:
        _log("ERROR: token.json not found")
        return 2

    # 対象ファイルをすべて収集（stage済=存在しない → 自動スキップ）
    all_files = sorted(
        SOURCE_ROOT.rglob("*"),
        key=lambda p: p.stat().st_mtime if p.is_file() else 0,
        reverse=True,
    )
    targets = [p for p in all_files if p.is_file()]
    total = len(targets)
    _log(f"START: {total} files found in {SOURCE_ROOT}")

    if total == 0:
        _log("DONE: nothing to upload")
        return 0

    # Drive フォルダ ID を事前に取得（共有用サービスで1回だけ）
    try:
        shared_svc = _build_service(token)
        parent_id = _ensure_folder(shared_svc, DRIVE_FOLDER)
        _log(f"Drive folder ready: {DRIVE_FOLDER} (id={parent_id})")
    except Exception as e:
        _log(f"ERROR: drive init failed: {e}")
        return 4

    stage_today = STAGE_ROOT / time.strftime("%Y%m%d")
    stage_today.mkdir(parents=True, exist_ok=True)

    uploaded = 0
    failed = 0
    done = 0

    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        futures = {executor.submit(_upload_one, token, parent_id, f, stage_today): f for f in targets}
        for future in as_completed(futures):
            done += 1
            result = future.result()
            if result["ok"]:
                uploaded += 1
            else:
                failed += 1
                _log(f"FAIL [{done}/{total}]: {Path(result['src']).name} -- {result.get('error','')}")

            if done % 50 == 0 or done == total:
                _log(f"PROGRESS: {done}/{total} | uploaded={uploaded} failed={failed}")

    _log(f"DONE: uploaded={uploaded} failed={failed} total={total}")
    print(json.dumps({"ok": True, "uploaded": uploaded, "failed": failed, "total": total}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
