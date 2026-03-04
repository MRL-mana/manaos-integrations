#!/usr/bin/env python3
"""
Moltbot × まなOS 統合スキーマ
Plan JSON / 承認リクエスト / 実行結果 / 監査ログ
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class PlanStep:
    """Plan 内の1ステップ"""

    step_id: str
    action: str  # file_move, file_read, browser_navigate, ...
    params: Dict[str, Any]
    condition: Optional[str] = None
    rollback_hint: Optional[str] = None


@dataclass
class PlanScope:
    """Moltbot に許可する範囲（過剰な権限を防ぐ）"""

    max_steps: int = 10
    allowed_actions: List[str] = field(default_factory=list)
    forbidden_actions: List[str] = field(default_factory=list)
    allowed_paths: List[str] = field(default_factory=list)
    timeout_seconds: int = 300

    # Phase1 用プリセット：ファイル整理オンリー（送信・削除なし）
    @classmethod
    def file_organize(cls) -> "PlanScope":
        return cls(
            max_steps=5,
            allowed_actions=[
                "list_files",
                "classify_files",
                "move_files",
                "file_read",
                "file_move",
                "file_copy",
            ],
            forbidden_actions=[
                "file_delete",
                "os_command",
                "email_send",
                "slack_send",
                "payment",
                "browser_purchase",
                "password_input",
                "api_key_read",
            ],
            allowed_paths=[],
            timeout_seconds=300,
        )


@dataclass
class PlanConstraints:
    """
    運用で刺さる制約（二重実行防止・暴走ストッパー・安全柵）。
    idempotency / timeouts / max_actions / domains / paths / artifacts。
    """

    idempotency_key: Optional[str] = None  # 同じ命令を二重実行しない用（超重要）
    timeouts: Optional[Dict[str, Any]] = None  # ステップ単位 or 全体のタイムアウト
    max_actions: Optional[int] = None  # 1プランで実行できるアクション上限（暴走ストッパー）
    allowed_domains: List[str] = field(default_factory=list)  # ブラウザ系タスクの許可ドメイン
    blocked_domains: List[str] = field(default_factory=list)  # ブラウザ系タスクの禁止ドメイン
    read_only_paths: List[str] = field(default_factory=list)  # 読み取り専用パス
    write_paths: List[str] = field(default_factory=list)  # 書き込み許可パス（境界）
    artifacts: Optional[Dict[str, str]] = (
        None  # 出力先（例: screenshots -> ./artifacts/screenshots）
    )

    @classmethod
    def phase1_safe(cls) -> "PlanConstraints":
        """Phase1 推奨：dry_run デフォルト・write_paths 制限・max_actions 50（やらかし防止）。"""
        return cls(
            max_actions=50,
            write_paths=[
                "~/Downloads",
                "~/Documents/PDF",
                "~/Pictures/Inbox",
                "~/Downloads/Archives",
            ],
            read_only_paths=[],
        )


@dataclass
class PlanMetadata:
    """Plan のメタ情報"""

    user_hint: Optional[str] = None
    phase: str = "1"  # "1" | "2" | "3"


@dataclass
class Plan:
    """まなOS → Moltbot ゲートに渡す Plan JSON の型"""

    plan_id: str
    version: str = "1.0"
    created_at: str = ""
    source: str = "manaos"
    intent: str = ""
    risk_level: RiskLevel = RiskLevel.LOW
    requires_approval: bool = False
    approval_request_id: Optional[str] = None
    scope: PlanScope = field(default_factory=PlanScope)
    steps: List[PlanStep] = field(default_factory=list)
    metadata: PlanMetadata = field(default_factory=PlanMetadata)
    constraints: Optional[PlanConstraints] = (
        None  # idempotency / timeouts / max_actions / domains / paths / artifacts
    )

    def __post_init__(self) -> None:
        if not self.plan_id:
            self.plan_id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if isinstance(self.risk_level, str):
            self.risk_level = RiskLevel(self.risk_level)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["risk_level"] = self.risk_level.value
        d["scope"] = asdict(self.scope)
        d["steps"] = [asdict(s) for s in self.steps]
        d["metadata"] = asdict(self.metadata)
        if self.constraints is not None:
            d["constraints"] = asdict(self.constraints)
        else:
            d.pop("constraints", None)
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Plan:
        scope_data = data.get("scope") or {}
        scope = PlanScope(
            max_steps=scope_data.get("max_steps", 10),
            allowed_actions=scope_data.get("allowed_actions", []),
            forbidden_actions=scope_data.get("forbidden_actions", []),
            allowed_paths=scope_data.get("allowed_paths", []),
            timeout_seconds=scope_data.get("timeout_seconds", 300),
        )
        steps = [
            PlanStep(
                step_id=s.get("step_id", ""),
                action=s.get("action", ""),
                params=s.get("params", {}),
                condition=s.get("condition"),
                rollback_hint=s.get("rollback_hint"),
            )
            for s in (data.get("steps") or [])
        ]
        meta_data = data.get("metadata") or {}
        meta = PlanMetadata(
            user_hint=meta_data.get("user_hint"),
            phase=str(meta_data.get("phase", "1")),
        )
        constraints = None
        if data.get("constraints"):
            c = data["constraints"]
            constraints = PlanConstraints(
                idempotency_key=c.get("idempotency_key"),
                timeouts=c.get("timeouts"),
                max_actions=c.get("max_actions"),
                allowed_domains=c.get("allowed_domains", []),
                blocked_domains=c.get("blocked_domains", []),
                read_only_paths=c.get("read_only_paths", []),
                write_paths=c.get("write_paths", []),
                artifacts=c.get("artifacts"),
            )
        return cls(
            plan_id=data.get("plan_id") or str(uuid.uuid4()),
            version=data.get("version", "1.0"),
            created_at=data.get("created_at", ""),
            source=data.get("source", "manaos"),
            intent=data.get("intent", ""),
            risk_level=RiskLevel(data.get("risk_level", "low")),
            requires_approval=bool(data.get("requires_approval")),
            approval_request_id=data.get("approval_request_id"),
            scope=scope,
            steps=steps,
            metadata=meta,
            constraints=constraints,
        )


# --- 承認フロー ---


@dataclass
class ApprovalRequest:
    """
    人間の最終承認リクエスト（差し戻し前提）。
    proposed_patch / user_notes / resubmit_plan_id で「この部分だけ直して再提出」ができる。
    """

    approval_request_id: str
    plan_id: str
    reason: str
    action_summary: str
    risk_level: RiskLevel = RiskLevel.MEDIUM
    created_at: str = ""
    expires_at: str = ""
    approved_plan_snippet: Optional[Dict[str, Any]] = None
    proposed_patch: Optional[Dict[str, Any]] = None  # Plan の差分案（人間が修正案を渡す）
    user_notes: Optional[str] = None  # 人間からの追加制約
    resubmit_plan_id: Optional[str] = None  # 差し替え先 Plan ID（再提出用）

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if isinstance(self.risk_level, str):
            self.risk_level = RiskLevel(self.risk_level)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["risk_level"] = self.risk_level.value
        return d


# --- 実行結果・監査ログ ---


@dataclass
class ExecuteResult:
    """Moltbot が返す実行結果の要約"""

    plan_id: str
    success: bool
    steps_done: int
    steps_total: int
    duration_seconds: float
    error: Optional[str] = None
    step_results: List[Dict[str, Any]] = field(default_factory=list)
    finished_at: str = ""

    def __post_init__(self) -> None:
        if not self.finished_at:
            self.finished_at = datetime.now().isoformat()


@dataclass
class AuditRecord:
    """
    監査用レコード（3層構成：事故分析・テンプレ化・プロダクト資産に強い）。
    plan / decision / execute_events(jsonl) / result / artifacts_dir
    """

    plan_id: str
    plan: Dict[str, Any]  # 入力（plan.json）
    decision: Optional[Dict[str, Any]] = None  # 承認判定・理由・リスク根拠（decision.json）
    execute: Dict[str, Any] = field(default_factory=dict)  # 従来互換：step 要約
    execute_events: List[Dict[str, Any]] = field(
        default_factory=list
    )  # 時系列イベント（execute.jsonl 用、1行=1イベント）
    result: Dict[str, Any] = field(default_factory=dict)  # 出力（result.json）
    artifacts_dir: Optional[str] = None  # スクショ・生成物の保存先（artifacts/）
    recorded_at: str = ""

    def __post_init__(self) -> None:
        if not self.recorded_at:
            self.recorded_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_commit_message(self) -> str:
        success = self.result.get("success", False)
        risk = self.plan.get("risk_level", "low")
        steps = len(self.plan.get("steps", []))
        return (
            f"moltbot: execute plan_id={self.plan_id} risk={risk} steps={steps} success={success}"
        )

    @classmethod
    def from_plan(cls, plan: "Plan", phase: str = "plan") -> "AuditRecord":
        """Plan 送信時点の監査レコード（decision は後から埋める）。"""
        return cls(
            plan_id=plan.plan_id,
            plan=plan.to_dict(),
            decision={"phase": phase, "recorded_at": datetime.now().isoformat()},
            execute={},
            execute_events=[],
            result={},
            recorded_at=datetime.now().isoformat(),
        )

    @classmethod
    def from_result(
        cls,
        plan_id: str,
        plan_dict: Dict[str, Any],
        result: Dict[str, Any],
        execute_events: Optional[List[Dict[str, Any]]] = None,
        decision: Optional[Dict[str, Any]] = None,
    ) -> "AuditRecord":
        """実行結果回収後の監査レコード（3層一式）。"""
        return cls(
            plan_id=plan_id,
            plan=plan_dict,
            decision=decision or {"recorded_at": datetime.now().isoformat()},
            execute=result.get("execute", {}),
            execute_events=execute_events or result.get("execute_events", []),
            result=result,
            recorded_at=datetime.now().isoformat(),
        )
