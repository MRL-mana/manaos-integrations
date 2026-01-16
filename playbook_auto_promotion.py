#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
System 3 Playbook自動昇格システム
- Tier1のみ自動昇格（安全域）
- Tier2/3はNeed Approvalに回す
"""

import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import json

# 設定（環境変数から取得、デフォルト値あり）
VAULT_PATH = Path(os.getenv("OBSIDIAN_VAULT_PATH", r"C:\Users\mana4\Documents\Obsidian Vault"))
PLAYBOOK_DIR = VAULT_PATH / "ManaOS" / "System" / "Playbook_Review"
DAILY_DIR = VAULT_PATH / "ManaOS" / "System" / "Daily"

# Tier定義
TIER_CRITERIA = {
    "tier1": {
        "min_score": 10.0,
        "min_approval_rate": 0.7,  # 70%以上
        "min_execution_rate": 0.8,  # 80%以上
        "max_noise_index": 0.2,  # 20%以下
        "min_days_active": 7,  # 7日以上
        "auto_promote": True,  # 自動昇格可能
    },
    "tier2": {
        "min_score": 8.0,
        "min_approval_rate": 0.5,
        "min_execution_rate": 0.6,
        "max_noise_index": 0.4,
        "min_days_active": 3,
        "auto_promote": False,  # 承認必要
    },
    "tier3": {
        "min_score": 5.0,
        "min_approval_rate": 0.3,
        "min_execution_rate": 0.4,
        "max_noise_index": 0.6,
        "min_days_active": 1,
        "auto_promote": False,  # 承認必要
    },
}


def get_playbook_metrics(playbook_id: str, days: int = 7) -> Dict[str, Any]:
    """Playbookのメトリクスを取得"""
    metrics = {
        "score_avg": 0.0,
        "approval_rate": 0.0,
        "execution_rate": 0.0,
        "noise_index": 0.0,
        "days_active": 0,
    }

    # 日次ログから集計
    today = datetime.now().date()
    scores = []
    approvals = []
    executions = []
    expirations = []

    for i in range(days):
        date = today - timedelta(days=i)
        daily_file = DAILY_DIR / f"System3_Daily_{date.isoformat()}.md"

        if daily_file.exists():
            content = daily_file.read_text(encoding="utf-8")

            # スコア抽出
            if "score_today" in content.lower():
                try:
                    for line in content.splitlines():
                        if "score_today" in line.lower():
                            parts = line.split(":")
                            if len(parts) > 1:
                                score = float(parts[1].strip().split()[0])
                                scores.append(score)
                                break
                except Exception:
                    pass

    # 週次レビューから集計
    review_files = list(PLAYBOOK_DIR.glob("Playbook_Review_*.md"))
    if review_files:
        latest_review = max(review_files, key=lambda p: p.stat().st_mtime)
        content = latest_review.read_text(encoding="utf-8")

        # メトリクス抽出
        if "Approval Rate" in content:
            try:
                for line in content.splitlines():
                    if "Approval Rate" in line:
                        parts = line.split(":")
                        if len(parts) > 1:
                            rate_str = parts[1].strip().rstrip("%")
                            approvals.append(float(rate_str) / 100)
                            break
            except Exception:
                pass

    # 集計
    if scores:
        metrics["score_avg"] = sum(scores) / len(scores)

    metrics["days_active"] = len([d for d in range(days) if (DAILY_DIR / f"System3_Daily_{(today - timedelta(days=d)).isoformat()}.md").exists()])

    return metrics


def determine_tier(metrics: Dict[str, Any]) -> str:
    """メトリクスからTierを判定"""
    # Tier1チェック
    tier1 = TIER_CRITERIA["tier1"]
    if (metrics["score_avg"] >= tier1["min_score"] and
        metrics["approval_rate"] >= tier1["min_approval_rate"] and
        metrics["execution_rate"] >= tier1["min_execution_rate"] and
        metrics["noise_index"] <= tier1["max_noise_index"] and
        metrics["days_active"] >= tier1["min_days_active"]):
        return "tier1"

    # Tier2チェック
    tier2 = TIER_CRITERIA["tier2"]
    if (metrics["score_avg"] >= tier2["min_score"] and
        metrics["approval_rate"] >= tier2["min_approval_rate"] and
        metrics["execution_rate"] >= tier2["min_execution_rate"] and
        metrics["noise_index"] <= tier2["max_noise_index"] and
        metrics["days_active"] >= tier2["min_days_active"]):
        return "tier2"

    # Tier3
    return "tier3"


def auto_promote_tier1() -> List[Dict[str, Any]]:
    """Tier1のPlaybookを自動昇格"""
    promoted = []

    # 現在のメトリクスを取得
    metrics = get_playbook_metrics("system3", days=7)
    tier = determine_tier(metrics)

    if tier == "tier1":
        # 自動昇格
        promotion_record = {
            "playbook_id": "system3",
            "tier": tier,
            "promoted_at": datetime.now().isoformat(),
            "metrics": metrics,
            "auto": True,
        }

        # 昇格記録を保存
        promotion_file = PLAYBOOK_DIR / "promotions.json"
        promotions = []

        if promotion_file.exists():
            promotions = json.loads(promotion_file.read_text(encoding="utf-8"))

        promotions.append(promotion_record)
        promotion_file.write_text(json.dumps(promotions, ensure_ascii=False, indent=2), encoding="utf-8")

        promoted.append(promotion_record)

    return promoted


def get_pending_approvals() -> List[Dict[str, Any]]:
    """承認待ちのPlaybook（Tier2/3）を取得"""
    pending = []

    metrics = get_playbook_metrics("system3", days=7)
    tier = determine_tier(metrics)

    if tier in ["tier2", "tier3"]:
        pending.append({
            "playbook_id": "system3",
            "tier": tier,
            "metrics": metrics,
            "needs_approval": True,
        })

    return pending


if __name__ == "__main__":
    import sys
    import io
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

    print("=" * 60)
    print("System 3 Playbook Auto Promotion")
    print("=" * 60)
    print()

    # Tier1自動昇格
    print("[1] Checking Tier1 auto-promotion...")
    promoted = auto_promote_tier1()
    if promoted:
        for p in promoted:
            print(f"    Promoted: {p['playbook_id']} to {p['tier']}")
    else:
        print("    No Tier1 playbooks to promote")

    # 承認待ち確認
    print("\n[2] Checking pending approvals...")
    pending = get_pending_approvals()
    if pending:
        for p in pending:
            print(f"    Needs approval: {p['playbook_id']} ({p['tier']})")
    else:
        print("    No playbooks pending approval")

    print()
