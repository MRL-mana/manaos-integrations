#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🤖 AgentTracker
===============
Claude Code エージェントの使用追跡・ランク管理・品質監査モジュール。

機能:
  - 使用追跡 : agent_tracker.track(agent_name, task_summary)
  - ランク管理: agent_tracker.get_rank(agent_name) → N / N-C / N-B / N-A / N-S
  - 品質監査 : agent_tracker.audit(agent_dir) → 100点スコアリング
  - パーキング: 30日未使用エージェントを自動検出

ランク基準:
    N     : 0回（未使用）
    N-C   : 1〜4回
    N-B   : 5〜9回
    N-A   : 10〜19回
    N-S   : 20回以上

品質スコア基準 (100点満点):
    name + description あり : 20点
    "Use when" 記載          : 25点
    "Do not trigger" 記載    : 20点
    model 設定あり           : 20点
    isolation 設定あり       : 15点
"""

from __future__ import annotations

import json
import re
import os
import sqlite3
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from manaos_logger import get_service_logger
    _log = get_service_logger("agent-tracker")
except Exception:
    import logging
    _log = logging.getLogger("agent_tracker")

# ── 設定 ──────────────────────────────────────────────────────────────────

DEFAULT_DB_PATH = os.getenv(
    "AGENT_TRACKER_DB",
    str(Path(__file__).parent.parent.parent / "data" / "agent_tracker.db"),
)

DEFAULT_AGENTS_DIR = os.getenv(
    "CLAUDE_AGENTS_DIR",
    str(Path.home() / ".claude" / "agents"),
)

PARKING_DAYS = int(os.getenv("AGENT_PARKING_DAYS", "30"))

# ランク閾値
RANK_THRESHOLDS: List[Tuple[int, str]] = [
    (20, "N-S"),
    (10, "N-A"),
    (5,  "N-B"),
    (1,  "N-C"),
    (0,  "N"),
]

# 品質スコア基準
QUALITY_CRITERIA = {
    "has_name_and_description": 20,
    "has_use_when":             25,
    "has_do_not_trigger":       20,
    "has_model":                20,
    "has_isolation":            15,
}


# ── データクラス ───────────────────────────────────────────────────────────

@dataclass
class UsageRecord:
    agent_name: str
    task_summary: str
    session_id: str
    recorded_at: str


@dataclass
class AgentStats:
    agent_name: str
    total_uses: int
    rank: str
    last_used_at: str
    days_since_use: Optional[int]
    is_parking_candidate: bool


@dataclass
class AuditResult:
    agent_name: str
    score: int                           # 0〜100
    passed_criteria: List[str]
    failed_criteria: List[str]
    suggestions: List[str]


# ── AgentTracker ──────────────────────────────────────────────────────────

class AgentTracker:
    """エージェントの使用追跡・ランク管理・品質監査"""

    def __init__(self, db_path: Optional[str] = None,
                 agents_dir: Optional[str] = None):
        self.db_path = Path(db_path or DEFAULT_DB_PATH)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.agents_dir = Path(agents_dir or DEFAULT_AGENTS_DIR)
        self._lock = threading.Lock()
        self._persistent_conn: Optional[sqlite3.Connection] = None
        if str(self.db_path) == ":memory:":
            self._persistent_conn = sqlite3.connect(":memory:", check_same_thread=False)
        self._init_db()

    # ── DB ────────────────────────────────────────────────────────────────

    @contextmanager
    def _conn(self):
        if self._persistent_conn is not None:
            yield self._persistent_conn
        else:
            conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            try:
                yield conn
                conn.commit()
            finally:
                conn.close()

    def _init_db(self):
        with self._conn() as c:
            c.execute("""
                CREATE TABLE IF NOT EXISTS usage_log (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_name   TEXT NOT NULL,
                    task_summary TEXT NOT NULL DEFAULT '',
                    session_id   TEXT NOT NULL DEFAULT '',
                    recorded_at  TEXT NOT NULL
                )
            """)
            c.execute("""
                CREATE INDEX IF NOT EXISTS idx_usage_agent ON usage_log(agent_name)
            """)
            c.execute("""
                CREATE INDEX IF NOT EXISTS idx_usage_time ON usage_log(recorded_at)
            """)
            if self._persistent_conn:
                self._persistent_conn.commit()

    # ── 使用追跡 ──────────────────────────────────────────────────────────

    def track(
        self,
        agent_name: str,
        task_summary: str = "",
        session_id: str = "",
    ) -> UsageRecord:
        """エージェント使用を記録する"""
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            with self._conn() as c:
                c.execute(
                    "INSERT INTO usage_log (agent_name, task_summary, session_id, recorded_at) "
                    "VALUES (?, ?, ?, ?)",
                    (agent_name, task_summary, session_id, now),
                )
                if self._persistent_conn:
                    self._persistent_conn.commit()
        record = UsageRecord(
            agent_name=agent_name,
            task_summary=task_summary,
            session_id=session_id,
            recorded_at=now,
        )
        _log.info(f"エージェント使用記録: {agent_name}")
        return record

    # ── ランク管理 ────────────────────────────────────────────────────────

    @staticmethod
    def calc_rank(total_uses: int) -> str:
        """使用回数からランクを計算する"""
        for threshold, rank in RANK_THRESHOLDS:
            if total_uses >= threshold:
                return rank
        return "N"

    def get_stats(self, agent_name: str) -> AgentStats:
        """エージェントの統計を取得する"""
        with self._conn() as c:
            row = c.execute(
                "SELECT COUNT(*), MAX(recorded_at) FROM usage_log WHERE agent_name = ?",
                (agent_name,),
            ).fetchone()
        total = row[0] or 0
        last_used = row[1] or ""
        rank = self.calc_rank(total)

        days_since: Optional[int] = None
        if last_used:
            try:
                last_dt = datetime.fromisoformat(last_used)
                if last_dt.tzinfo is None:
                    last_dt = last_dt.replace(tzinfo=timezone.utc)
                days_since = (datetime.now(timezone.utc) - last_dt).days
            except Exception:
                pass

        is_parking = (
            (days_since is not None and days_since >= PARKING_DAYS)
            or (total == 0)
        ) and total < 5  # N or N-C で長期未使用

        return AgentStats(
            agent_name=agent_name,
            total_uses=total,
            rank=rank,
            last_used_at=last_used,
            days_since_use=days_since,
            is_parking_candidate=is_parking,
        )

    def list_all_ranks(self) -> List[AgentStats]:
        """全エージェントのランクを返す（DBにある全エージェント）"""
        with self._conn() as c:
            names = [
                r[0]
                for r in c.execute(
                    "SELECT DISTINCT agent_name FROM usage_log ORDER BY agent_name"
                ).fetchall()
            ]
        # agents_dir からも読み込む
        if self.agents_dir.exists():
            for f in self.agents_dir.glob("*.md"):
                name = f.stem
                if name not in names:
                    names.append(name)
        return [self.get_stats(name) for name in sorted(set(names))]

    def get_parking_candidates(self) -> List[AgentStats]:
        """パーキング候補（30日未使用 or 未使用）を返す"""
        return [s for s in self.list_all_ranks() if s.is_parking_candidate]

    # ── 品質監査 ──────────────────────────────────────────────────────────

    def audit_agent_text(self, agent_name: str, agent_text: str) -> AuditResult:
        """
        エージェント定義テキスト（Markdown）を品質スコアリングする。

        スコア基準:
            name + description あり : 20点
            "Use when" 記載          : 25点
            "Do not trigger" 記載    : 20点
            model 設定あり           : 20点
            isolation 設定あり       : 15点

        Returns:
            AuditResult (score 0〜100)
        """
        text_lower = agent_text.lower()
        score = 0
        passed: List[str] = []
        failed: List[str] = []
        suggestions: List[str] = []

        # name + description
        has_name = bool(re.search(r"name\s*:", agent_text, re.IGNORECASE))
        has_desc = bool(re.search(r"description\s*:", agent_text, re.IGNORECASE))
        if has_name and has_desc:
            score += QUALITY_CRITERIA["has_name_and_description"]
            passed.append("name + description")
        else:
            failed.append("name + description")
            suggestions.append("フロントマターに name: と description: を追加してください")

        # "Use when"
        if "use when" in text_lower or "使用するとき" in agent_text or "呼び出し条件" in agent_text:
            score += QUALITY_CRITERIA["has_use_when"]
            passed.append("Use when")
        else:
            failed.append("Use when")
            suggestions.append("description に 'Use when: ...' を追加してください")

        # "Do not trigger"
        if "do not trigger" in text_lower or "使わない" in agent_text or "除外条件" in agent_text:
            score += QUALITY_CRITERIA["has_do_not_trigger"]
            passed.append("Do not trigger")
        else:
            failed.append("Do not trigger")
            suggestions.append("description に 'Do not trigger: ...' を追加してください")

        # model 設定
        if re.search(r"model\s*:", agent_text, re.IGNORECASE):
            score += QUALITY_CRITERIA["has_model"]
            passed.append("model")
        else:
            failed.append("model")
            suggestions.append("model: claude-sonnet-4-5 などを追加してください")

        # isolation 設定
        if "isolation" in text_lower or "worktree" in text_lower:
            score += QUALITY_CRITERIA["has_isolation"]
            passed.append("isolation")
        else:
            failed.append("isolation")
            suggestions.append("isolation: worktree をフロントマターに追加することを推奨します")

        return AuditResult(
            agent_name=agent_name,
            score=score,
            passed_criteria=passed,
            failed_criteria=failed,
            suggestions=suggestions,
        )

    def audit_agents_dir(
        self,
        agents_dir: Optional[str] = None,
        min_score: int = 70,
    ) -> Dict[str, Any]:
        """
        agents ディレクトリ内の全エージェントを監査する。

        Returns:
            {
                "total": N,
                "passing": N,
                "failing": N,
                "results": [AuditResult, ...],
                "low_quality": [AuditResult, ...],  # min_score 未満
            }
        """
        target = Path(agents_dir or self.agents_dir)
        if not target.exists():
            return {
                "total": 0,
                "passing": 0,
                "failing": 0,
                "results": [],
                "low_quality": [],
                "error": f"ディレクトリが存在しません: {target}",
            }

        results: List[AuditResult] = []
        for md_file in sorted(target.glob("*.md")):
            text = md_file.read_text(encoding="utf-8", errors="ignore")
            result = self.audit_agent_text(md_file.stem, text)
            results.append(result)

        low_quality = [r for r in results if r.score < min_score]
        return {
            "total": len(results),
            "passing": len(results) - len(low_quality),
            "failing": len(low_quality),
            "results": [asdict(r) for r in results],
            "low_quality": [asdict(r) for r in low_quality],
        }

    def stats(self) -> Dict[str, Any]:
        """全体統計情報"""
        all_stats = self.list_all_ranks()
        rank_dist = {}
        for s in all_stats:
            rank_dist[s.rank] = rank_dist.get(s.rank, 0) + 1
        parking = self.get_parking_candidates()
        return {
            "total_agents": len(all_stats),
            "rank_distribution": rank_dist,
            "parking_candidates": len(parking),
            "parking_list": [p.agent_name for p in parking],
            "db_path": str(self.db_path),
            "agents_dir": str(self.agents_dir),
        }


# ── シングルトン ────────────────────────────────────────────────────────────

_instance: Optional[AgentTracker] = None
_instance_lock = threading.Lock()


def get_agent_tracker(
    db_path: Optional[str] = None,
    agents_dir: Optional[str] = None,
) -> AgentTracker:
    """プロセス内でシングルトンを返す"""
    global _instance
    if _instance is None:
        with _instance_lock:
            if _instance is None:
                _instance = AgentTracker(db_path, agents_dir)
    return _instance
