"""
共有型定義 – RLAnything
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional


# ─────────────────────── 列挙型 ───────────────────────
class TaskOutcome(str, enum.Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILURE = "failure"
    UNKNOWN = "unknown"


class FeedbackType(str, enum.Enum):
    INTEGRATION = "integration"      # 統合フィードバック
    CONSISTENCY = "consistency"      # 一貫性フィードバック
    EVALUATION = "evaluation"        # 評価フィードバック (カリキュラム)


class DifficultyLevel(str, enum.Enum):
    CONCRETE = "concrete"       # 具体的指示 (成功率 < 20%)
    GUIDED = "guided"           # ガイド付き (20-50%)
    STANDARD = "standard"       # 標準 (50-80%)
    ABSTRACT = "abstract"       # 抽象的指示 (> 80%)


# ─────────────────────── データクラス ───────────────────────
@dataclass
class ToolAction:
    """ツール使用 1 回分の記録"""
    tool_name: str
    parameters: Dict[str, Any]
    result_summary: str           # 成功/失敗の要約 (最大 500 文字)
    error: Optional[str] = None
    duration_ms: Optional[float] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class TaskRecord:
    """タスク全体の記録"""
    task_id: str
    description: str
    actions: List[ToolAction] = field(default_factory=list)
    outcome: TaskOutcome = TaskOutcome.UNKNOWN
    intermediate_scores: List[float] = field(default_factory=list)
    final_score: Optional[float] = None
    difficulty: DifficultyLevel = DifficultyLevel.STANDARD
    skills_used: List[str] = field(default_factory=list)
    start_time: str = field(default_factory=lambda: datetime.now().isoformat())
    end_time: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["outcome"] = self.outcome.value
        d["difficulty"] = self.difficulty.value
        return d


@dataclass
class Skill:
    """蓄積されたスキル (成功パターン)"""
    skill_id: str
    name: str
    description: str
    pattern: str               # どのような行動パターンか
    context_tags: List[str]    # 例: ["react", "test-first", "refactor"]
    success_rate: float        # 0.0‐1.0
    sample_count: int
    discovered_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_used: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RewardSignal:
    """報酬シグナル"""
    task_id: str
    feedback_type: FeedbackType
    score: float               # 0.0 – 1.0
    reasoning: str             # なぜこのスコアか
    adjustments: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        d = asdict(self)
        d["feedback_type"] = self.feedback_type.value
        return d
