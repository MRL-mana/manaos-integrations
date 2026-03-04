#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Step-Deep-Research データスキーマ定義
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum


class TaskTool(str, Enum):
    """タスクツール"""
    SEARCH = "search"
    RAG = "rag"
    DOCS = "docs"
    PDF = "pdf"
    NONE = "none"


class TaskPriority(str, Enum):
    """タスク優先度"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class CitationTag(str, Enum):
    """引用タグ"""
    FACT = "fact"
    INFERENCE = "inference"


class ContradictionType(str, Enum):
    """矛盾タイプ"""
    DIRECT = "direct"
    INDIRECT = "indirect"
    TEMPORAL = "temporal"


class ContradictionSeverity(str, Enum):
    """矛盾の深刻度"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ReliabilityLevel(str, Enum):
    """信頼性レベル"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class JobStatus(str, Enum):
    """ジョブステータス"""
    PENDING = "pending"
    PLANNING = "planning"
    RESEARCHING = "researching"
    WRITING = "writing"
    CRITIQUING = "critiquing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class SuccessCriterion:
    """成功条件"""
    criterion: str
    priority: TaskPriority
    measurable: bool


@dataclass
class TodoItem:
    """タスクアイテム"""
    step: int
    description: str
    tool: TaskTool
    expected_output: str
    dependencies: List[int] = field(default_factory=list)
    priority: TaskPriority = TaskPriority.MEDIUM


@dataclass
class Risk:
    """リスク"""
    risk: str
    mitigation: str


@dataclass
class Plan:
    """調査計画"""
    goal: str
    success_criteria: List[SuccessCriterion] = field(default_factory=list)
    todo: List[TodoItem] = field(default_factory=list)
    risks: List[Risk] = field(default_factory=list)
    estimated_time_minutes: int = 60
    estimated_cost_tokens: int = 30000


@dataclass
class Citation:
    """引用"""
    id: str
    source: str
    quote: str
    summary: str
    tag: CitationTag
    relevance_score: float = 0.0
    warning: Optional[str] = None  # 品質警告（動的属性用）


@dataclass
class Summary:
    """要約"""
    source: str
    summary: str
    key_points: List[str] = field(default_factory=list)


@dataclass
class Contradiction:
    """矛盾"""
    type: ContradictionType
    source1: str
    source2: str
    description: str
    severity: ContradictionSeverity


@dataclass
class CounterArgument:
    """反証"""
    claim: str
    counter_evidence: str
    source: str


@dataclass
class ReliabilityAssessment:
    """信頼性評価"""
    source: str
    reliability: ReliabilityLevel
    reason: str


@dataclass
class RubricItemScore:
    """ルーブリック項目スコア"""
    item: str
    name: str
    passed: bool
    note: str


@dataclass
class RubricScores:
    """ルーブリックスコア"""
    citations: Dict[str, Any] = field(default_factory=dict)
    logic: Dict[str, Any] = field(default_factory=dict)
    practicality: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CritiqueResult:
    """採点結果"""
    score: int
    is_passed: bool
    rubric_scores: RubricScores = field(default_factory=RubricScores)
    fail_flags: List[str] = field(default_factory=list)
    fix_requests: List[str] = field(default_factory=list)
    iteration: int = 1


@dataclass
class SearchResult:
    """検索結果"""
    title: str
    url: str
    snippet: str
    source: str
    timestamp: Optional[datetime] = None
    quality: Optional[str] = None  # ソース品質（動的属性用）


@dataclass
class ResearchIteration:
    """調査イテレーション"""
    iteration: int
    timestamp: datetime
    search_results: List[SearchResult] = field(default_factory=list)
    citations: List[Citation] = field(default_factory=list)
    summaries: List[Summary] = field(default_factory=list)
    contradictions: List[Contradiction] = field(default_factory=list)


@dataclass
class ResearchResults:
    """調査結果"""
    iterations: List[ResearchIteration] = field(default_factory=list)
    citations: List[Citation] = field(default_factory=list)
    summaries: List[Summary] = field(default_factory=list)
    contradictions: List[Contradiction] = field(default_factory=list)
    counter_arguments: List[CounterArgument] = field(default_factory=list)
    reliability_assessments: List[ReliabilityAssessment] = field(default_factory=list)
    stop_reason: Optional[str] = None  # 停止理由（BudgetGuard.StopReason）


@dataclass
class JobBudget:
    """ジョブ予算"""
    max_tokens: int
    max_searches: int
    max_time_minutes: int
    used_tokens: int = 0
    used_searches: int = 0
    elapsed_seconds: float = 0.0


@dataclass
class Checkpoint:
    """チェックポイント"""
    timestamp: datetime
    status: JobStatus
    budget: JobBudget
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class JobState:
    """ジョブ状態"""
    job_id: str
    user_query: str
    status: JobStatus
    budget: JobBudget
    created_at: datetime
    planner_output: Optional[Plan] = None
    research_output: Optional[ResearchResults] = None
    writer_output: Optional[str] = None
    critic_output: Optional[List[CritiqueResult]] = None
    stop_reason: Optional[str] = None
    cache_hit: Optional[bool] = None


@dataclass
class JobLog:
    """ジョブログ"""
    job_id: str
    created_at: datetime
    user_query: str
    status: JobStatus = JobStatus.PENDING
    
    orchestrator: Dict[str, Any] = field(default_factory=dict)
    planner: Optional[Plan] = None
    research_loop: Optional[ResearchResults] = None
    writer: Optional[Dict[str, Any]] = None
    critic: Optional[List[CritiqueResult]] = None
    
    final_report_path: Optional[str] = None
    artifacts: List[str] = field(default_factory=list)
    
    checkpoints: List[Checkpoint] = field(default_factory=list)

