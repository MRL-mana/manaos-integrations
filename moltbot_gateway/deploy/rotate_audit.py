#!/usr/bin/env python3
"""
監査ローテ: moltbot_audit の古い日付フォルダをアーカイブ or 削除する。
本格運用で月 1 回などに実行する。
"""

import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path

# この日数より古い監査を整理する（デフォルト 30 日）
KEEP_DAYS = int(os.getenv("MOLTBOT_AUDIT_KEEP_DAYS", "30"))
# True なら削除、False なら archive/ に移動
DELETE_INSTEAD_OF_ARCHIVE = os.getenv("MOLTBOT_AUDIT_DELETE", "").lower() in ("1", "true", "yes")


def main():
    repo_root = Path(__file__).resolve().parent.parent.parent
    audit_dir = repo_root / "moltbot_audit"
    if not audit_dir.exists():
        print("moltbot_audit がありません。")
        return

    cutoff = datetime.now() - timedelta(days=KEEP_DAYS)
    removed = 0
    archive_dir = audit_dir / "archive" if not DELETE_INSTEAD_OF_ARCHIVE else None
    if archive_dir and not archive_dir.exists():
        archive_dir.mkdir(parents=True)

    for path in sorted(audit_dir.iterdir()):
        if not path.is_dir() or path.name == "archive":
            continue
        try:
            # フォルダ名は YYYY-MM-DD 想定
            d = datetime.strptime(path.name, "%Y-%m-%d")
        except ValueError:
            continue
        if d.date() >= cutoff.date():
            continue
        if DELETE_INSTEAD_OF_ARCHIVE:
            shutil.rmtree(path)
            print(f"削除: {path}")
        else:
            dest = archive_dir / path.name
            if dest.exists():
                shutil.rmtree(dest)
            shutil.move(str(path), str(dest))
            print(f"アーカイブ: {path} -> {dest}")
        removed += 1

        action = "削除" if DELETE_INSTEAD_OF_ARCHIVE else "アーカイブ"
        print(f"完了. {removed} 件を{action}しました。（{KEEP_DAYS} 日以内は保持）")


if __name__ == "__main__":
    main()
