"""ManaOS 共通パス定数 ─ ハードコードパスの排除.

すべてのモジュールで ``from _paths import INTEGRATIONS_DIR, OBSIDIAN_VAULT``
のようにインポートして使う。環境変数 > Path.home() フォールバック。
"""

from __future__ import annotations

import os
from pathlib import Path

# ---------- ベースディレクトリ ----------
# このファイル自体が manaos_integrations/ の直下にある前提
INTEGRATIONS_DIR: Path = Path(__file__).resolve().parent

USER_HOME: Path = Path.home()

# ---------- Obsidian ----------
OBSIDIAN_VAULT: Path = Path(
    os.getenv(
        "OBSIDIAN_VAULT_PATH",
        str(USER_HOME / "Documents" / "Obsidian Vault"),
    )
)

# ---------- プロジェクトルート（manaos_integrations の親 = Desktop）----------
PROJECT_ROOT: Path = INTEGRATIONS_DIR.parent

# ---------- ログ ----------
LOGS_DIR: Path = INTEGRATIONS_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)
