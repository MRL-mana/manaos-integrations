#!/usr/bin/env python3
"""
まなOS → Moltbot 最小ランナー（貼って使えるサンプル）
Phase1: ファイル整理オンリー。dry_run → 実行 → 監査ログが残る。
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

# リポジトリルートの .env を読み込み（MOLTBOT_GATEWAY_URL / MOLTBOT_GATEWAY_SECRET）
try:
    from dotenv import load_dotenv

    _env_path = Path(__file__).resolve().parent / ".env"
    if _env_path.exists():
        load_dotenv(_env_path)
except ImportError:
    pass

from moltbot_integration.schema import (
    Plan,
    PlanStep,
    PlanScope,
    PlanMetadata,
    PlanConstraints,
    RiskLevel,
    AuditRecord,
)
from moltbot_integration.approval import plan_requires_approval
from moltbot_integration.gateway import MoltbotGatewayClient


def build_phase1_file_sort_plan(user_text: str) -> Plan:
    """Phase1: Downloads 整理プラン（ファイル整理のみ・送信・削除なし）。Phase1 安全 constraints 付き。"""
    plan_id = f"plan-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    scope = PlanScope.file_organize()
    meta = PlanMetadata(user_hint=user_text, phase="1")
    constraints = PlanConstraints.phase1_safe()  # dry_run 推奨・write_paths 制限・max_actions 50

    steps = [
        PlanStep(
            step_id="scan_downloads",
            action="list_files",
            params={"path": "~/Downloads"},
        ),
        PlanStep(
            step_id="classify",
            action="classify_files",
            params={
                "rules": [
                    {"if_ext": [".pdf"], "move_to": "~/Documents/PDF"},
                    {"if_ext": [".png", ".jpg", ".webp"], "move_to": "~/Pictures/Inbox"},
                    {"if_ext": [".zip"], "move_to": "~/Downloads/Archives"},
                ],
                "dry_run": True,  # 最初は絶対 dry_run 推奨
            },
        ),
        PlanStep(
            step_id="apply_moves",
            action="move_files",
            params={"from_dry_run": True},
        ),
    ]

    plan = Plan(
        plan_id=plan_id,
        intent=user_text,
        risk_level=RiskLevel.LOW,
        requires_approval=False,
        scope=scope,
        steps=steps,
        metadata=meta,
        constraints=constraints,
    )
    plan.requires_approval = plan_requires_approval(plan.risk_level, plan.steps)
    return plan


def build_list_files_only_plan(path: str = "~/Downloads") -> Plan:
    """B 用: list_files だけの Plan（EXECUTOR=moltbot で成功する最小）。"""
    plan_id = f"plan-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    scope = PlanScope.file_organize()
    meta = PlanMetadata(user_hint="list_files only (B test)", phase="1")
    constraints = PlanConstraints.phase1_safe()

    steps = [
        PlanStep(step_id="scan", action="list_files", params={"path": path}),
    ]

    plan = Plan(
        plan_id=plan_id,
        intent="list_files only",
        risk_level=RiskLevel.LOW,
        requires_approval=False,
        scope=scope,
        steps=steps,
        metadata=meta,
        constraints=constraints,
    )
    return plan


def build_file_read_only_plan(path: str) -> Plan:
    """B 用: file_read だけの Plan（EXECUTOR=moltbot で成功する最小）。"""
    plan_id = f"plan-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    scope = PlanScope.file_organize()
    meta = PlanMetadata(user_hint="file_read only (B test)", phase="1")
    constraints = PlanConstraints.phase1_safe()

    steps = [
        PlanStep(step_id="read", action="file_read", params={"path": path}),
    ]

    plan = Plan(
        plan_id=plan_id,
        intent="file_read only",
        risk_level=RiskLevel.LOW,
        requires_approval=False,
        scope=scope,
        steps=steps,
        metadata=meta,
        constraints=constraints,
    )
    return plan


def run_list_files_only(path: str = "~/Downloads"):
    """B 用: list_files だけ送って監査まで流す。EXECUTOR=moltbot で通す確認用。"""
    plan = build_list_files_only_plan(path)
    client = MoltbotGatewayClient()
    submit_resp = client.submit_plan(plan)
    if not submit_resp.get("ok"):
        print("Submit failed:", submit_resp.get("error"))
        return submit_resp
    plan_id = plan.plan_id
    client.write_audit(AuditRecord.from_plan(plan, phase="plan"))
    result_resp = client.get_result(plan_id)
    if not result_resp.get("ok"):
        print("Get result failed:", result_resp.get("error"))
        return result_resp
    result = result_resp.get("data", {})
    full_record = AuditRecord.from_result(
        plan_id=plan_id,
        plan_dict=plan.to_dict(),
        result=result,
        execute_events=result.get("execute_events", []),
        decision={"phase": "result", "recorded_at": datetime.now().isoformat()},
    )
    client.write_audit(full_record)
    return result


def run_file_read_only(path: str):
    """B 用: file_read だけ送って監査まで流す。EXECUTOR=moltbot で通す確認用。"""
    plan = build_file_read_only_plan(path)
    client = MoltbotGatewayClient()
    submit_resp = client.submit_plan(plan)
    if not submit_resp.get("ok"):
        print("Submit failed:", submit_resp.get("error"))
        return submit_resp
    plan_id = plan.plan_id
    client.write_audit(AuditRecord.from_plan(plan, phase="plan"))
    result_resp = client.get_result(plan_id)
    if not result_resp.get("ok"):
        print("Get result failed:", result_resp.get("error"))
        return result_resp
    result = result_resp.get("data", {})
    full_record = AuditRecord.from_result(
        plan_id=plan_id,
        plan_dict=plan.to_dict(),
        result=result,
        execute_events=result.get("execute_events", []),
        decision={"phase": "result", "recorded_at": datetime.now().isoformat()},
    )
    client.write_audit(full_record)
    return result


def run_plan(user_text: str):
    """
    1) 承認要否判定 → 2) ゲートに投げる → 3) 監査ログ（plan）→ 4) 結果ポーリング → 5) 監査ログ（result）
    """
    plan = build_phase1_file_sort_plan(user_text)

    # 1) 承認要否判定
    if plan.requires_approval:
        # 既存の Slack / Obsidian 承認フローに載せる想定（例: enqueue_approval_request(plan)）
        print("Approval required -> send to existing approval flow")
        return {"status": "approval_required", "plan_id": plan.plan_id}

    # 2) ゲートに投げる
    client = MoltbotGatewayClient()
    submit_resp = client.submit_plan(plan)
    if not submit_resp.get("ok"):
        print("Submit failed:", submit_resp.get("error"))
        return submit_resp

    plan_id = plan.plan_id

    # 3) 監査ログ（plan）書き出し
    client.write_audit(AuditRecord.from_plan(plan, phase="plan"))

    # 4) 結果ポーリング（最小）
    result_resp = client.get_result(plan_id)
    if not result_resp.get("ok"):
        print("Get result failed:", result_resp.get("error"))
        return result_resp

    result = result_resp.get("data", {})
    execute_events = result.get("execute_events", [])
    decision = {"phase": "result", "recorded_at": datetime.now().isoformat()}

    # 5) 監査ログ（result・3層）書き出し
    full_record = AuditRecord.from_result(
        plan_id=plan_id,
        plan_dict=plan.to_dict(),
        result=result,
        execute_events=execute_events,
        decision=decision,
    )
    client.write_audit(full_record)

    return result


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "list_only":
        # B 用: list_files だけ（EXECUTOR=moltbot で成功する）
        path = sys.argv[2] if len(sys.argv) > 2 else "~/Downloads"
        res = run_list_files_only(path)
        print(res)
    elif len(sys.argv) > 1 and sys.argv[1] == "read_only":
        # B 用: file_read だけ（EXECUTOR=moltbot で成功する）
        path = sys.argv[2] if len(sys.argv) > 2 else str(Path(__file__).resolve())
        res = run_file_read_only(path)
        print(res)
    else:
        res = run_plan("Downloadsの散らかりを整理して。PDFはDocumentsへ、画像はPicturesへ。")
        print(res)
