#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/misc/local_oss_absorption.py

LocalOSSAbsorption — ローカルノート（.md）を文脈として OH-MY-OPENCODE に
タスクを委譲するアダプター層。

設定ファイル: <base_dir>/config/local_oss_profile.json
  {
    "profile_name": "...",
    "notes": {
      "directory": "notes",   # base_dir からの相対パス
      "glob": "**/*.md",
      "max_context_files": 5,
      "max_chars_per_file": 800
    },
    "oh_my_opencode": {
      "default_mode": "normal",
      "default_task_type": "general",
      "use_trinity": false
    }
  }
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class LocalOSSAbsorption:
    """ローカルノートを文脈としてエージェントにタスクを委譲するオーケストレーター。"""

    _PROFILE_REL = "config/local_oss_profile.json"

    def __init__(self, base_dir: str = ".") -> None:
        self._base = Path(base_dir).resolve()
        self._profile: Optional[Dict[str, Any]] = None
        self._load_profile()

    # ──────────────────────────────────────────────
    # プロファイル読み込み
    # ──────────────────────────────────────────────

    def _load_profile(self) -> None:
        p = self._base / self._PROFILE_REL
        if p.exists():
            try:
                self._profile = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                self._profile = None

    # ──────────────────────────────────────────────
    # ノートファイル列挙
    # ──────────────────────────────────────────────

    def _notes_cfg(self) -> Dict[str, Any]:
        if self._profile:
            return self._profile.get("notes") or {}
        return {}

    def _notes_dir(self) -> Path:
        cfg = self._notes_cfg()
        return self._base / cfg.get("directory", "notes")

    def _list_notes(self) -> List[Path]:
        cfg = self._notes_cfg()
        glob = cfg.get("glob", "**/*.md")
        d = self._notes_dir()
        if not d.exists():
            return []
        return sorted(d.glob(glob))

    def _notes_count(self) -> int:
        return len(self._list_notes())

    # ──────────────────────────────────────────────
    # 文脈収集
    # ──────────────────────────────────────────────

    def _build_context(self, query: Optional[str] = None) -> str:
        """クエリに関連するノートを文脈文字列として返す。"""
        cfg = self._notes_cfg()
        max_files = int(cfg.get("max_context_files", 5))
        max_chars = int(cfg.get("max_chars_per_file", 800))

        files = self._list_notes()
        if query:
            # クエリが含まれるファイルを優先
            matched = [f for f in files if query.lower() in f.read_text(encoding="utf-8", errors="replace").lower()]
            others = [f for f in files if f not in matched]
            files = matched + others
        files = files[:max_files]

        parts: List[str] = []
        for f in files:
            txt = f.read_text(encoding="utf-8", errors="replace")[:max_chars]
            parts.append(f"## {f.name}\n{txt}")
        return "\n\n".join(parts)

    # ──────────────────────────────────────────────
    # ノート書き出し
    # ──────────────────────────────────────────────

    def _write_note(self, title: str, content: str) -> Path:
        notes_dir = self._notes_dir()
        notes_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        fname = f"{ts}_{title}.md"
        p = notes_dir / fname
        p.write_text(content, encoding="utf-8")
        return p

    # ──────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        """プロファイルとノートの状態を返す。"""
        if not self._profile:
            return {"available": False, "profile_name": None, "notes_files": 0}
        return {
            "available": True,
            "profile_name": self._profile.get("profile_name", ""),
            "notes_files": self._notes_count(),
        }

    async def execute(
        self,
        task_description: str,
        integrations: Dict[str, Any],
        context_query: Optional[str] = None,
        write_note: bool = False,
        note_title: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        タスクを oh_my_opencode インテグレーションに委譲する。

        Returns:
            {"status": "success"|"unavailable"|"error", "task_id": ..., "note_path": ...}
        """
        oh = integrations.get("oh_my_opencode")
        if oh is None:
            return {"status": "unavailable", "reason": "oh_my_opencode integration not available"}

        # ノート文脈を加える
        ctx = self._build_context(context_query)
        prompt = task_description
        if ctx:
            prompt = f"{task_description}\n\nNOTE:\n{ctx}"

        oh_cfg = (self._profile or {}).get("oh_my_opencode") or {}
        try:
            result = await oh.execute_task(
                task_description=prompt,
                mode=oh_cfg.get("default_mode"),
                task_type=oh_cfg.get("default_task_type"),
                use_trinity=oh_cfg.get("use_trinity"),
            )
        except Exception as e:
            return {"status": "error", "error": str(e)}

        out: Dict[str, Any] = {
            "status": getattr(result, "status", "unknown"),
            "task_id": getattr(result, "task_id", None),
            "cost": getattr(result, "cost", None),
            "execution_time": getattr(result, "execution_time", None),
            "iterations": getattr(result, "iterations", None),
            "error": getattr(result, "error", None),
            "result": getattr(result, "result", None),
        }

        # ノート保存
        if write_note:
            body = f"# {note_title or task_description}\n\n**task_id**: {out['task_id']}\n\n{json.dumps(out, ensure_ascii=False, indent=2)}"
            note_path = self._write_note(note_title or "task", body)
            out["note_path"] = str(note_path)

        return out
