#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
System 3 Playbook自動昇格システム
- Tier1のみ自動昇格（安全域）
- Tier2/3はNeed Approvalに回す
- メトリクス: Markdown優先、不足時は Score/Todo API で補完
"""

import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import json

try:
    from manaos_integrations._paths import INTRINSIC_MOTIVATION_PORT, TODO_QUEUE_PORT
except Exception:  # pragma: no cover
    try:
        from _paths import INTRINSIC_MOTIVATION_PORT, TODO_QUEUE_PORT  # type: ignore
    except Exception:  # pragma: no cover
        INTRINSIC_MOTIVATION_PORT = int(os.getenv("INTRINSIC_MOTIVATION_PORT", "5130"))
        TODO_QUEUE_PORT = int(os.getenv("TODO_QUEUE_PORT", "5134"))

# 設定（環境変数から取得、デフォルト値あり）
VAULT_PATH = Path(os.getenv("OBSIDIAN_VAULT_PATH", r"C:\Users\mana4\Documents\Obsidian Vault"))
PLAYBOOK_DIR = VAULT_PATH / "ManaOS" / "System" / "Playbook_Review"
DAILY_DIR = VAULT_PATH / "ManaOS" / "System" / "Daily"
TODO_METRICS_URL = os.getenv(
    "TODO_METRICS_URL",
    f"http://127.0.0.1:{TODO_QUEUE_PORT}/api/metrics",
)
SCORE_URL = os.getenv(
    "INTRINSIC_SCORE_URL",
    f"http://127.0.0.1:{INTRINSIC_MOTIVATION_PORT}/api/score",
)

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


def _fetch_metrics_from_api() -> Dict[str, Any]:
    """Score / Todo API からメトリクスを取得（Markdown不足時のフォールバック）"""
    out = {"score_avg": 0.0, "approval_rate": 0.0, "execution_rate": 0.0, "noise_index": 0.0}
    try:
        from system3_http_retry import http_get_json_retry

        j = http_get_json_retry(TODO_METRICS_URL, timeout=3, retries=2) or {}
        c = j.get("counts", j)
        p, a, e, x = (
            int(c.get("proposed", 0)),
            int(c.get("approved", 0)),
            int(c.get("executed", 0)),
            int(c.get("expired", 0)),
        )
        out["approval_rate"] = max(0.0, min(1.0, (a + e) / p if p else 0.0))
        out["execution_rate"] = max(0.0, min(1.0, e / (a + e) if (a + e) else 0.0))
        out["noise_index"] = max(0.0, min(1.0, (c.get("rejected", 0) + x) / p if p else 0.0))
        s = http_get_json_retry(SCORE_URL, timeout=3, retries=2) or {}
        out["score_avg"] = max(0.0, min(100.0, float(s.get("score", s.get("score_today", 10.0)))))
    except Exception:
        pass
    return out


def _clamp_rate(v: float) -> float:
    return max(0.0, min(1.0, float(v))) if v is not None else 0.0


def get_playbook_metrics(playbook_id: str, days: int = 7) -> Dict[str, Any]:
    """Playbookのメトリクスを取得（Markdown優先、不足時はAPIで補完）"""
    metrics = {
        "score_avg": 0.0,
        "approval_rate": 0.0,
        "execution_rate": 0.0,
        "noise_index": 0.0,
        "days_active": 0,
    }

    today = datetime.now().date()
    scores: List[float] = []
    approvals: List[float] = []
    executions: List[float] = []
    expirations: List[float] = []

    # 日次ログから集計（try/except でパース崩れをガード）
    for i in range(days):
        d = today - timedelta(days=i)
        daily_file = DAILY_DIR / f"System3_Daily_{d.isoformat()}.md"
        if not daily_file.exists():
            continue
        try:
            content = daily_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        if "score_today" not in content.lower():
            continue
        for line in content.splitlines():
            if "score_today" not in line.lower():
                continue
            try:
                parts = line.replace("：", ":").split(":")
                if len(parts) < 2:
                    continue
                tok = parts[1].strip().split()
                if not tok:
                    continue
                v = float(tok[0])
                if 0 <= v <= 100:
                    scores.append(v)
            except (ValueError, IndexError):
                pass
            break

    # 週次レビューから集計
    review_files = list(PLAYBOOK_DIR.glob("Playbook_Review_*.md"))
    if review_files:
        try:
            latest = max(review_files, key=lambda p: p.stat().st_mtime)
            content = latest.read_text(encoding="utf-8", errors="replace")
        except Exception:
            content = ""
        for needle, rate_key in (
            ("Approval Rate", "approvals"),
            ("Execution Rate", "executions"),
            ("Noise Index", "expirations"),
        ):
            if needle not in content:
                continue
            for line in content.splitlines():
                if needle not in line or ":" not in line:
                    continue
                try:
                    parts = line.replace("：", ":").split(":", 1)
                    s = parts[1].strip().replace("%", "").strip()
                    v = float(s)
                    if v > 1:
                        v /= 100.0
                    v = _clamp_rate(v)
                except Exception:
                    continue
                if rate_key == "approvals":
                    approvals.append(v)
                elif rate_key == "executions":
                    executions.append(v)
                else:
                    expirations.append(v)
                break

    if scores:
        metrics["score_avg"] = sum(scores) / len(scores)
    if approvals:
        metrics["approval_rate"] = sum(approvals) / len(approvals)
    if executions:
        metrics["execution_rate"] = sum(executions) / len(executions)
    if expirations:
        metrics["noise_index"] = sum(expirations) / len(expirations)

    metrics["days_active"] = sum(
        1
        for i in range(days)
        if (DAILY_DIR / f"System3_Daily_{(today - timedelta(days=i)).isoformat()}.md").exists()
    )

    # API フォールバック（Markdownで不足している項目を補完）
    # 不足判定: 全レートが0 / スコアが0 / 日数が少なくてデータ薄い
    has_gaps = (
        (
            metrics["approval_rate"] == 0.0
            and metrics["execution_rate"] == 0.0
            and metrics["noise_index"] == 0.0
        )
        or metrics["score_avg"] == 0.0
        or metrics["days_active"] < 3  # データが薄いときもAPIで補完
    )
    if has_gaps:
        api = _fetch_metrics_from_api()
        if metrics["score_avg"] == 0.0 and api["score_avg"] > 0:
            metrics["score_avg"] = api["score_avg"]
        if metrics["approval_rate"] == 0.0 and api["approval_rate"] > 0:
            metrics["approval_rate"] = api["approval_rate"]
        if metrics["execution_rate"] == 0.0 and api["execution_rate"] > 0:
            metrics["execution_rate"] = api["execution_rate"]
        if metrics["noise_index"] == 0.0 and (api["noise_index"] > 0 or api["approval_rate"] > 0):
            metrics["noise_index"] = api["noise_index"]

    metrics["approval_rate"] = _clamp_rate(metrics["approval_rate"])
    metrics["execution_rate"] = _clamp_rate(metrics["execution_rate"])
    metrics["noise_index"] = _clamp_rate(metrics["noise_index"])

    return metrics


def determine_tier(metrics: Dict[str, Any]) -> str:
    """メトリクスからTierを判定"""
    # 不正値ガード（None/NaN/範囲外）
    safe = {
        "score_avg": max(0.0, min(100.0, float(metrics.get("score_avg") or 0))),
        "approval_rate": _clamp_rate(metrics.get("approval_rate")),  # type: ignore
        "execution_rate": _clamp_rate(metrics.get("execution_rate")),  # type: ignore
        "noise_index": _clamp_rate(metrics.get("noise_index")),  # type: ignore
        "days_active": max(0, int(metrics.get("days_active") or 0)),
    }
    metrics = safe

    # Tier1チェック
    tier1 = TIER_CRITERIA["tier1"]
    if (
        metrics["score_avg"] >= tier1["min_score"]
        and metrics["approval_rate"] >= tier1["min_approval_rate"]
        and metrics["execution_rate"] >= tier1["min_execution_rate"]
        and metrics["noise_index"] <= tier1["max_noise_index"]
        and metrics["days_active"] >= tier1["min_days_active"]
    ):
        return "tier1"

    # Tier2チェック
    tier2 = TIER_CRITERIA["tier2"]
    if (
        metrics["score_avg"] >= tier2["min_score"]
        and metrics["approval_rate"] >= tier2["min_approval_rate"]
        and metrics["execution_rate"] >= tier2["min_execution_rate"]
        and metrics["noise_index"] <= tier2["max_noise_index"]
        and metrics["days_active"] >= tier2["min_days_active"]
    ):
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

        # 昇格記録を保存（try/except でファイル破損・書き込み失敗をガード）
        promotion_file = PLAYBOOK_DIR / "promotions.json"
        promotions = []
        try:
            if promotion_file.exists():
                raw = promotion_file.read_text(encoding="utf-8")
                loaded = json.loads(raw)
                promotions = loaded if isinstance(loaded, list) else []
        except (json.JSONDecodeError, OSError) as e:
            promotions = []  # 破損時は新規リストで再開

        promotions.append(promotion_record)
        try:
            PLAYBOOK_DIR.mkdir(parents=True, exist_ok=True)
            promotion_file.write_text(
                json.dumps(promotions, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except OSError:
            pass  # 書き込み失敗時は promoted には追加済み、ログは省略

        promoted.append(promotion_record)

    return promoted


def get_pending_approvals() -> List[Dict[str, Any]]:
    """承認待ちのPlaybook（Tier2/3）を取得"""
    pending = []

    metrics = get_playbook_metrics("system3", days=7)
    tier = determine_tier(metrics)

    if tier in ["tier2", "tier3"]:
        pending.append(
            {
                "playbook_id": "system3",
                "tier": tier,
                "metrics": metrics,
                "needs_approval": True,
            }
        )

    return pending


if __name__ == "__main__":
    import sys
    import io

    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding='utf-8')  # type: ignore[attr-defined]
        sys.stderr.reconfigure(encoding='utf-8')  # type: ignore[attr-defined]

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
