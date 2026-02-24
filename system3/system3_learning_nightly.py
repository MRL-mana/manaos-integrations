#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
System 3 Learning Nightly Batch
深夜バッチでログ/メトリクス/失敗を分析し、学習結果と提案を生成
"""

import sys
import io

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import os
from pathlib import Path
from datetime import datetime, date, timedelta
import json
from typing import Dict, List, Any
from collections import Counter

from system3_http_retry import http_get_json_retry

try:
    from manaos_integrations._paths import INTRINSIC_MOTIVATION_PORT, LEARNING_SYSTEM_PORT, TODO_QUEUE_PORT
except Exception:  # pragma: no cover
    try:
        from _paths import INTRINSIC_MOTIVATION_PORT, LEARNING_SYSTEM_PORT, TODO_QUEUE_PORT  # type: ignore
    except Exception:  # pragma: no cover
        LEARNING_SYSTEM_PORT = int(os.getenv("LEARNING_SYSTEM_PORT", "5126"))
        INTRINSIC_MOTIVATION_PORT = int(os.getenv("INTRINSIC_MOTIVATION_PORT", "5130"))
        TODO_QUEUE_PORT = int(os.getenv("TODO_QUEUE_PORT", "5134"))

# 設定（環境変数から取得、デフォルト値あり）
VAULT_PATH = Path(os.getenv("OBSIDIAN_VAULT_PATH", r"C:\Users\mana4\Documents\Obsidian Vault"))
INTEGRATIONS_DIR = Path(
    os.getenv("MANAOS_INTEGRATIONS_DIR", r"C:\Users\mana4\Desktop\manaos_integrations")
)  # noqa: E501
LOGS_DIR = INTEGRATIONS_DIR / "logs"
OUT_DIR = VAULT_PATH / "ManaOS" / "System" / "Learning"

# API URLs
LEARNING_SYSTEM_URL = os.getenv("LEARNING_SYSTEM_URL", f"http://127.0.0.1:{LEARNING_SYSTEM_PORT}")
INTRINSIC_SCORE_URL = os.getenv(
    "INTRINSIC_SCORE_URL",
    f"http://127.0.0.1:{INTRINSIC_MOTIVATION_PORT}/api/score",
)
TODO_METRICS_URL = os.getenv(
    "TODO_METRICS_URL",
    f"http://127.0.0.1:{TODO_QUEUE_PORT}/api/metrics",
)


def http_get_json(url: str, timeout: int = 5) -> dict:
    """Get JSON from API (retry with backoff), empty dict on failure."""
    return http_get_json_retry(url, timeout=timeout, retries=3, base_delay=1.0) or {}


def read_jsonl_tail(path: Path, max_lines: int = 2000) -> List[Dict[str, Any]]:
    """Read last N lines from JSONL file"""
    if not path.exists():
        return []

    lines = []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()
            lines = all_lines[-max_lines:] if len(all_lines) > max_lines else all_lines
    except Exception:
        return []

    out = []
    for ln in lines:
        ln = ln.strip()
        if not ln:
            continue
        try:
            out.append(json.loads(ln))
        except Exception:
            continue

    return out


def read_error_logs(log_dir: Path, hours: int = 24) -> List[Dict[str, Any]]:
    """Read error logs from last N hours"""
    errors = []
    cutoff_time = datetime.now() - timedelta(hours=hours)

    for error_log in log_dir.glob("*_error.log"):
        try:
            mtime = datetime.fromtimestamp(error_log.stat().st_mtime)
            if mtime < cutoff_time:
                continue

            with open(error_log, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
                for line in lines:
                    line = line.strip()
                    if not line or len(line) < 10:
                        continue

                    # エラーログの簡易パース
                    errors.append(
                        {"file": error_log.name, "line": line, "timestamp": mtime.isoformat()}
                    )
        except Exception:
            continue

    return errors


def analyze_error_patterns(errors: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze error patterns"""
    if not errors:
        return {"total": 0, "by_file": {}, "common_patterns": []}

    by_file = Counter()
    error_keywords = Counter()

    for err in errors:
        by_file[err["file"]] += 1

        # エラーメッセージからキーワード抽出
        line_lower = err["line"].lower()
        keywords = ["error", "exception", "failed", "timeout", "connection", "not found"]
        for kw in keywords:
            if kw in line_lower:
                error_keywords[kw] += 1

    return {
        "total": len(errors),
        "by_file": dict(by_file.most_common(10)),
        "common_patterns": [{"keyword": k, "count": v} for k, v in error_keywords.most_common(5)],
    }


def get_learning_system_data() -> Dict[str, Any]:
    """Get data from Learning System API"""
    data = {}

    # パターン分析
    try:
        analysis = http_get_json(f"{LEARNING_SYSTEM_URL}/api/analyze")
        if analysis:
            data["analysis"] = analysis
    except Exception:
        pass

    # 学習された好み
    try:
        preferences = http_get_json(f"{LEARNING_SYSTEM_URL}/api/preferences")
        if preferences:
            data["preferences"] = preferences
    except Exception:
        pass

    # 最適化提案
    try:
        optimizations = http_get_json(f"{LEARNING_SYSTEM_URL}/api/optimizations")
        if optimizations:
            data["optimizations"] = optimizations.get("optimizations", [])
    except Exception:
        pass

    # 状態
    try:
        status = http_get_json(f"{LEARNING_SYSTEM_URL}/api/status")
        if status:
            data["status"] = status
    except Exception:
        pass

    return data


def generate_proposals(
    error_analysis: Dict[str, Any], learning_data: Dict[str, Any], todo_metrics: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Generate proposals based on analysis"""
    proposals = []

    # エラーが多いファイルの提案
    if error_analysis.get("total", 0) > 10:
        top_error_file = None
        by_file = error_analysis.get("by_file", {})
        if by_file:
            top_error_file = max(by_file.items(), key=lambda x: x[1])
            if top_error_file[1] > 5:
                proposals.append(
                    {
                        "title": f"{top_error_file[0]}のエラーハンドリング改善",
                        "reason": f"エラー数: {top_error_file[1]}件（24h）",
                        "risk": "low",
                        "autonomy_level_required": 2,
                        "type": "error_handling",
                    }
                )

    # 学習システムからの最適化提案
    optimizations = learning_data.get("optimizations", [])
    for opt in optimizations[:3]:  # 上位3件
        proposals.append(
            {
                "title": opt.get("suggestion", "最適化提案"),
                "reason": f"type: {opt.get('type', 'unknown')}",
                "risk": "low",
                "autonomy_level_required": 2,
                "type": "optimization",
            }
        )

    # ToDoメトリクスに基づく提案
    if todo_metrics:
        noise_index = todo_metrics.get("noise_index", 0)
        if noise_index > 0.3:
            proposals.append(
                {
                    "title": "ToDo提案品質の改善",
                    "reason": f"ノイズ指数が高い: {noise_index:.1%}",
                    "risk": "low",
                    "autonomy_level_required": 1,
                    "type": "todo_quality",
                }
            )

        approval_rate = todo_metrics.get("approval_rate", 1.0)
        if approval_rate < 0.5:
            proposals.append(
                {
                    "title": "ToDo提案の粒度・優先順位の改善",
                    "reason": f"承認率が低い: {approval_rate:.1%}",
                    "risk": "low",
                    "autonomy_level_required": 1,
                    "type": "todo_granularity",
                }
            )

    return proposals


def main():
    """Main function"""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print(f"System 3 Learning Nightly Batch - {now}")
    print("=" * 60)

    # 1. エラーログの分析
    print("\n[1] エラーログを分析中...")
    errors = read_error_logs(LOGS_DIR, hours=24)
    error_analysis = analyze_error_patterns(errors)
    print(f"  エラー数: {error_analysis['total']}")

    # 2. Learning System APIからデータ取得
    print("\n[2] Learning System APIからデータ取得中...")
    learning_data = get_learning_system_data()
    print(f"  分析データ: {'取得済み' if learning_data.get('analysis') else '取得失敗'}")
    print(f"  最適化提案: {len(learning_data.get('optimizations', []))}件")

    # 3. ToDoメトリクス取得
    print("\n[3] ToDoメトリクス取得中...")
    todo_metrics = http_get_json(TODO_METRICS_URL)

    # 4. Intrinsic Score取得
    print("\n[4] Intrinsic Score取得中...")
    intrinsic_score = http_get_json(INTRINSIC_SCORE_URL)
    score_value = intrinsic_score.get("score", 10.0) if intrinsic_score else 10.0

    # 5. 提案生成
    print("\n[5] 提案生成中...")
    proposals = generate_proposals(error_analysis, learning_data, todo_metrics)
    print(f"  提案数: {len(proposals)}件")

    # 6. Markdown生成
    md = []
    md.append(f"# System 3 Learning Nightly\n\n")
    md.append(f"**生成**: {now}  \n")
    md.append(f"**Autonomy Level**: Level 1（内部メンテナンス限定）\n\n")
    md.append(f"---\n\n")

    # スコア
    md.append(f"## 📈 Intrinsic Score\n\n")
    md.append(f"- **score_today**: {score_value:.1f}\n\n")

    # 集計
    md.append(f"## 📊 集計（24h）\n\n")
    md.append(f"- **エラー数**: {error_analysis['total']}\n")

    if error_analysis.get("by_file"):
        md.append(f"- **エラーが多いファイル**:\n")
        for file, count in list(error_analysis["by_file"].items())[:5]:
            md.append(f"  - `{file}`: {count}件\n")

    if learning_data.get("status"):
        status = learning_data["status"]
        md.append(f"- **記録されたアクション数**: {status.get('total_actions_recorded', 0)}\n")
        md.append(f"- **ユニークアクション数**: {status.get('unique_actions', 0)}\n")

    md.append(f"\n")

    # 学習結果
    md.append(f"## 🧠 学習（Learned）\n\n")

    if learning_data.get("analysis"):
        analysis = learning_data["analysis"]
        most_used = analysis.get("most_used_actions", [])[:5]
        if most_used:
            md.append(f"### 最も使用されるアクション\n\n")
            for item in most_used:
                md.append(f"- **{item.get('action', 'unknown')}**: {item.get('count', 0)}回\n")
            md.append(f"\n")

        success_rates = analysis.get("success_rates", {})
        if success_rates:
            md.append(f"### 成功率\n\n")
            for action, stats in list(success_rates.items())[:5]:
                rate = stats.get("rate", 0)
                total = stats.get("total", 0)
                md.append(f"- **{action}**: {rate:.1f}% ({stats.get('success', 0)}/{total})\n")
            md.append(f"\n")

    if learning_data.get("preferences"):
        prefs = learning_data["preferences"]
        md.append(f"### 学習された好み\n\n")
        for key, value in prefs.items():
            md.append(f"- **{key}**: {json.dumps(value, ensure_ascii=False)}\n")
        md.append(f"\n")

    # 提案
    md.append(f"## 🛂 提案（Need Approval）\n\n")
    if proposals:
        for i, p in enumerate(proposals, 1):
            md.append(f"### {i}. {p['title']}\n\n")
            md.append(f"- **理由**: {p['reason']}\n")
            md.append(f"- **リスク**: {p['risk']}\n")
            md.append(f"- **必要な自律レベル**: Level {p['autonomy_level_required']}以上\n")
            md.append(f"- **タイプ**: {p.get('type', 'unknown')}\n\n")
    else:
        md.append(f"- なし\n\n")

    # ファイルに保存
    out_file = OUT_DIR / f"System3_Learning_{today}.md"
    out_file.write_text("".join(md), encoding="utf-8", newline="\n")

    print(f"\n✅ 学習レポートを生成しました: {out_file}")
    print(f"   提案数: {len(proposals)}件")

    return str(out_file)


if __name__ == "__main__":
    try:
        result = main()
        print(f"\n✅ 完了: {result}")
    except Exception as e:
        print(f"\n❌ エラー: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
