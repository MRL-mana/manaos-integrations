#!/usr/bin/env python3
# -*- coding: utf-8 -*-


# -*- coding: utf-8 -*-


"""























































































































# System3_Status.md 繧堤函謌舌・譖ｴ譁ｰ縺吶ｋ繧ｹ繧ｯ繝ｪ繝励ヨ























































































































# ﾃ｣竄ｬﾅ担ystem 3ﾃ｣・ｽﾅ津､ﾂｻﾅﾃ｣・ｽﾂｪﾃ｣・ｽﾂｫﾃ｣・ｽ窶氾｣・ｽﾂｦﾃ｣窶壺ｹﾃ｣・ｽ窶ｹﾃ｣竄ｬ・ｽﾃ｣窶壺凖･・ｽﾂｯﾃｨﾂｦ窶禿･ﾅ停・























































































































"""


import json
import os


import httpx


import re


from pathlib import Path


from datetime import datetime, timedelta


from typing import Dict, Any, Optional, List


from obsidian_integration import ObsidianIntegration


# System 3ﾃｩ窶督｢ﾃｩ竄ｬﾂ｣ﾃ｣窶堋ｵﾃ｣ﾆ陳ｼﾃ｣ﾆ停愿｣窶堋ｹﾃ｣・ｽﾂｮURL


LEARNING_SYSTEM_URL = "http://127.0.0.1:5126"


METRICS_COLLECTOR_URL = "http://127.0.0.1:5127"


TASK_CRITIC_URL = "http://127.0.0.1:5102"


AUTONOMY_SYSTEM_URL = "http://127.0.0.1:5124"


INTRINSIC_MOTIVATION_URL = "http://127.0.0.1:5130"


TODO_QUEUE_URL = "http://127.0.0.1:5134"


def get_learning_stats() -> Dict[str, Any]:

    # Learning System statistics

    try:

        response = httpx.get(f"{LEARNING_SYSTEM_URL}/api/analyze", timeout=5)

        if response.status_code == 200:

            return response.json()

    except Exception:

        pass

    return {}


def get_metrics_stats() -> Dict[str, Any]:

    # Metrics Collectorから統計を取得

    try:

        response = httpx.get(f"{METRICS_COLLECTOR_URL}/api/metrics/summary", timeout=5)

        if response.status_code == 200:

            return response.json()

    except Exception:

        pass

    return {}


def get_autonomy_status() -> Dict[str, Any]:

    # Autonomy System statistics

    try:

        response = httpx.get(f"{AUTONOMY_SYSTEM_URL}/api/status", timeout=5)

        if response.status_code == 200:

            return response.json()

    except Exception:

        pass

    return {"autonomy_level": "Level 1", "status": "active"}


def get_intrinsic_score_history(days: int = 7) -> List[Dict[str, Any]]:

    # 7-day score history

    scores = []

    try:

        # Obsidian Vault path (OBSIDIAN_VAULT_PATH を優先)
        env_path = os.getenv("OBSIDIAN_VAULT_PATH", "").strip()
        vault_path = Path(env_path) if env_path else None
        if not vault_path or not vault_path.exists():
            vault_path = Path.home() / "Documents" / "Obsidian Vault"
        if not vault_path.exists():
            vault_path = Path.home() / "Documents" / "Obsidian"
        if not vault_path.exists():
            return scores

        daily_dir = vault_path / "ManaOS" / "System" / "Daily"

        if not daily_dir.exists():

            return scores

        today = datetime.now().date()

        for i in range(days):

            target_date = today - timedelta(days=i)

            log_file = daily_dir / f"System3_Daily_{target_date.isoformat()}.md"

            if log_file.exists():

                try:

                    content = log_file.read_text(encoding="utf-8")

                    # ﾃ｣窶堋ｹﾃ｣窶堋ｳﾃ｣窶堋｢ﾃ｣窶壺凖ｦﾅﾂｽﾃ･窶｡ﾂｺ

                    #                     score_match = re.search(r"\*\*ﾃｧﾂｷ・ｽﾃ･・ｽﾋ・｣窶堋ｹﾃ｣窶堋ｳﾃ｣窶堋｢\*\*: ([\d.]+)/100", content)

                    if score_match:

                        score = float(score_match.group(1))

                        scores.append({"date": target_date.isoformat(), "score": score})

                except Exception:

                    pass

    except Exception:

        pass

    return sorted(scores, key=lambda x: x["date"])


def get_todo_metrics() -> Dict[str, Any]:

    # ToDo queue metrics

    try:

        response = httpx.get(f"{TODO_QUEUE_URL}/api/todos", timeout=5)

        if response.status_code == 200:

            data = response.json()

            todos = data.get("todos", [])

            proposed = len([t for t in todos if t.get("state") == "PROPOSED"])

            approved = len([t for t in todos if t.get("state") == "APPROVED"])

            executed = len([t for t in todos if t.get("state") == "EXECUTED"])

            expired = len([t for t in todos if t.get("state") == "EXPIRED"])

            # ﾃｩ・ｽﾅｽﾃ･ﾅｽﾂｻ7ﾃｦ窶板･ﾃｩ窶凪愿｣・ｽﾂｮﾃｧﾂｵﾂｱﾃｨﾂｨﾋ・｣窶壺堙･・ｽ窶禿･ﾂｾ窶・

            today = datetime.now().date()

            week_proposed = 0

            week_expired = 0

            for i in range(7):

                target_date = today - timedelta(days=i)

                day_proposed = len(
                    [
                        t
                        for t in todos
                        if t.get("state") == "PROPOSED"
                        and t.get("created_at", "").startswith(target_date.isoformat())
                    ]
                )

                day_expired = len(
                    [
                        t
                        for t in todos
                        if t.get("state") == "EXPIRED"
                        and t.get("created_at", "").startswith(target_date.isoformat())
                    ]
                )

                week_proposed += day_proposed

                week_expired += day_expired

            approval_rate = (approved / proposed * 100) if proposed > 0 else 0.0

            execution_rate = (executed / approved * 100) if approved > 0 else 0.0

            noise_index = (expired / proposed * 100) if proposed > 0 else 0.0

            return {
                "proposed": proposed,
                "approved": approved,
                "executed": executed,
                "expired": expired,
                "approval_rate": approval_rate,
                "execution_rate": execution_rate,
                "noise_index": noise_index,
                "week_proposed": week_proposed,
                "week_expired": week_expired,
            }

    except Exception:

        pass

    return {
        "proposed": 0,
        "approved": 0,
        "executed": 0,
        "expired": 0,
        "approval_rate": 0.0,
        "execution_rate": 0.0,
        "noise_index": 0.0,
        "week_proposed": 0,
        "week_expired": 0,
    }


def count_recent_improvements(hours: int = 24) -> Dict[str, int]:
    """直近の改善数をカウントする（未実装 — 現在はゼロ値を返す）"""
    # NOTE: stub — not yet implemented (returns zero values)

    return {
        "playbooks_created": 0,
        "failures_learned": 0,
        "optimizations_applied": 0,
        "evaluations_performed": 0,
    }


def generate_system3_status(
    vault_path: Optional[str] = None,
    status_relpath: str = r"ManaOS\System\System3_Status.md",
    daily_relpath: str = r"ManaOS\System\Daily",
    intrinsic_score_url: str = "http://127.0.0.1:5130/api/score",
    todo_metrics_url: str = "http://127.0.0.1:5134/api/metrics",
) -> str:
    # Generate/update System3_Status.md and return path (UTF-8 fixed)
    # - 7-day score trend
    # - Approval/execution rate
    # - Noise index
    from pathlib import Path
    from datetime import datetime, date, timedelta
    import json
    import urllib.request
    import math

    _vault = vault_path or os.getenv(
        "OBSIDIAN_VAULT_PATH", r"C:\Users\mana4\Documents\Obsidian Vault"
    )
    VAULT = Path(_vault)
    STATUS_MD = VAULT / status_relpath
    DAILY_DIR = VAULT / daily_relpath

    def http_get_json(url: str, timeout: int = 3) -> dict:
        """Get JSON from API with error handling"""
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
            return json.loads(raw.decode("utf-8"))
        except urllib.error.URLError:
            # API not available, return empty dict
            return {}
        except Exception:
            # Other errors, return empty dict
            return {}

    # Metrics Schema統合
    try:
        from metrics_schema import normalize_score_metrics, normalize_todo_metrics

        USE_METRICS_SCHEMA = True
    except ImportError:
        USE_METRICS_SCHEMA = False

    def fmt_num(x: float | None, nd: int = 1) -> str:
        if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
            return "N/A"
        return f"{x:.{nd}f}"

    def fmt_pct(x: float | None) -> str:
        if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
            return "N/A"
        return f"{x*100:.1f}%"

    def trend_arrow(delta: float, eps: float = 0.5) -> str:
        if delta > eps:
            return "↑"
        if delta < -eps:
            return "↓"
        return "→"

    def parse_score_from_daily(md_text: str) -> float | None:
        """Extract score from daily log with multiple patterns"""
        needles = [
            "Intrinsic Motivation Score",
            "score_today",
            "score:",
            "スコア",
            "Score:",
            "今日のスコア",
        ]

        # Try multiple patterns
        for line in md_text.splitlines():
            low = line.lower()
            if any(n.lower() in low for n in needles):
                # Pattern 1: "Score: 10.5" or "スコア: 10.5"
                for tok in (
                    line.replace("：", ":")
                    .replace("*", " ")
                    .replace("`", " ")
                    .replace("**", " ")
                    .split()
                ):
                    tok = tok.strip().strip(":").strip("/").strip("100")
                    try:
                        val = float(tok)
                        if 0 <= val <= 100:  # Valid score range
                            return val
                    except Exception:
                        continue

        # Pattern 2: Look for numbers near score keywords
        score_patterns = [
            r"score[:\s]+(\d+\.?\d*)",
            r"スコア[:\s]+(\d+\.?\d*)",
            r"score_today[:\s=]+(\d+\.?\d*)",
            r"(\d+\.?\d*)\s*/?\s*100",  # "10.5/100" or "10.5 / 100"
        ]

        for pattern in score_patterns:
            matches = re.findall(pattern, md_text, re.IGNORECASE)
            if matches:
                try:
                    val = float(matches[0])
                    if 0 <= val <= 100:
                        return val
                except Exception:
                    continue

        return None

    # --- 7d score ---
    scores = []
    today = date.today()
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        fn = DAILY_DIR / f"System3_Daily_{d.isoformat()}.md"
        if not fn.exists():
            continue
        txt = fn.read_text(encoding="utf-8", errors="replace")
        sc = parse_score_from_daily(txt)
        if sc is not None:
            scores.append((d, float(sc)))

    score_today = scores[-1][1] if scores else None
    score_7d_avg = (sum(s for _, s in scores) / len(scores)) if scores else None
    score_trend = trend_arrow(scores[-1][1] - scores[0][1]) if len(scores) >= 2 else "→"

    # fallback today score from API
    if score_today is None:
        try:
            j = http_get_json(intrinsic_score_url)
            score_today = float(j.get("score", 10.0))
        except Exception:
            score_today = 10.0

    # Metrics Schemaを使用してスコアメトリクスを正規化
    score_history = [{"date": d.isoformat(), "score": s} for d, s in scores]
    if USE_METRICS_SCHEMA:
        try:
            score_metrics_normalized = normalize_score_metrics(
                score_today=score_today or 10.0,
                score_7d_avg=score_7d_avg,
                score_trend=score_trend,
                score_history=score_history,
            )
        except Exception:
            pass

    # --- todo rates (Metrics Schema統合) ---
    approval_rate = execution_rate = noise_index = None
    todo_metrics_normalized = None
    try:
        j = http_get_json(todo_metrics_url)
        counts = j.get("counts", j)
        proposed = int(counts.get("proposed", 0))
        approved = int(counts.get("approved", 0))
        executed = int(counts.get("executed", 0))
        expired = int(counts.get("expired", 0))

        # Metrics Schemaを使用して正規化
        if USE_METRICS_SCHEMA:
            todo_metrics_normalized = normalize_todo_metrics(proposed, approved, executed, expired)
            approval_rate = todo_metrics_normalized.get("approval_rate")
            execution_rate = todo_metrics_normalized.get("execution_rate")
            noise_index = todo_metrics_normalized.get("noise_index")
        else:
            # フォールバック（従来の計算）
            approval_rate = (approved / proposed) if proposed > 0 else None
            execution_rate = (executed / approved) if approved > 0 else None
            noise_index = (expired / proposed) if proposed > 0 else None
    except Exception:
        pass

    # Self-Assessment 動的化（実メトリクスに応じて出し分け）
    assessment_lines = []
    if noise_index is not None and noise_index > 0.3:
        assessment_lines.append("High noise index: Review proposal quality or upper limit control")
    if approval_rate is not None and approval_rate < 0.5:
        assessment_lines.append(
            "Low approval rate: Improve proposal granularity and priority (use quality_config)"
        )
    if execution_rate is not None and execution_rate < 0.7:
        assessment_lines.append("Low execution rate: Check execution issues or post-approval flow")
    if not assessment_lines:
        if approval_rate is None and execution_rate is None and noise_index is None:
            assessment_lines.append(
                "No ToDo metrics yet. Generate and approve proposals to see insights."
            )
        else:
            assessment_lines.append("No critical issues. Keep monitoring.")
    self_assessment_block = (
        "## Self Assessment\n" + "\n".join("- " + line for line in assessment_lines) + "\n\n"
    )

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    content = (
        "# System 3 Status Dashboard\n\n"
        "**Updated**: " + now + "  \n"
        "**Autonomy Level**: Level 1 (Internal maintenance only)\n\n"
        "---\n\n"
        "## Score (Intrinsic Motivation)\n"
        "- **score_today**: " + fmt_num(score_today, 1) + "\n"
        "- **score_7d_avg**: " + fmt_num(score_7d_avg, 1) + "\n"
        "- **score_trend**: " + score_trend + "\n\n"
        "---\n\n"
        "## ToDo Metrics (24h)\n"
        "- **Approval Rate (approved / proposed)**: " + fmt_pct(approval_rate) + "\n"
        "- **Execution Rate (executed / approved)**: " + fmt_pct(execution_rate) + "\n"
        "- **Noise Index (expired / proposed)**: " + fmt_pct(noise_index) + "\n\n"
        "---\n\n" + self_assessment_block
    )

    STATUS_MD.parent.mkdir(parents=True, exist_ok=True)
    STATUS_MD.write_text(content, encoding="utf-8", newline="\n")
    return str(STATUS_MD)


def update_weekly_review(
    vault_path: Optional[str] = None,
    review_relpath: str = r"ManaOS\System\Playbook_Review",
    daily_relpath: str = r"ManaOS\System\Daily",
    intrinsic_score_url: str = "http://127.0.0.1:5130/api/score",
    todo_metrics_url: str = "http://127.0.0.1:5134/api/metrics",
) -> str:
    """
    Update weekly review with score changes and insights
    """
    from pathlib import Path
    from datetime import datetime, date, timedelta
    import json
    import urllib.request
    import math

    _vault = vault_path or os.getenv(
        "OBSIDIAN_VAULT_PATH", r"C:\Users\mana4\Documents\Obsidian Vault"
    )
    VAULT = Path(_vault)
    REVIEW_DIR = VAULT / review_relpath
    DAILY_DIR = VAULT / daily_relpath
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)

    def http_get_json(url: str, timeout: int = 3) -> dict:
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return {}

    def parse_score_from_daily(md_text: str) -> float | None:
        needles = ["Intrinsic Motivation Score", "score_today", "score:"]
        for line in md_text.splitlines():
            low = line.lower()
            if any(n.lower() in low for n in needles):
                for tok in line.replace("：", ":").replace("*", " ").replace("`", " ").split():
                    tok = tok.strip().strip(":")
                    try:
                        return float(tok)
                    except Exception:
                        continue
        return None

    # Get 7 days of scores
    today = date.today()
    scores = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        fn = DAILY_DIR / f"System3_Daily_{d.isoformat()}.md"
        if fn.exists():
            txt = fn.read_text(encoding="utf-8", errors="replace")
            sc = parse_score_from_daily(txt)
            if sc is not None:
                scores.append((d, float(sc)))

    if len(scores) < 2:
        return None  # Not enough data

    # Calculate score change
    week_start_score = scores[0][1]
    week_end_score = scores[-1][1]
    score_change = week_end_score - week_start_score
    score_change_pct = (score_change / week_start_score * 100) if week_start_score > 0 else 0

    # Get ToDo metrics
    todo_metrics = {}
    try:
        j = http_get_json(todo_metrics_url)
        counts = j.get("counts", j)
        todo_metrics = {
            "proposed": float(counts.get("proposed", 0)),
            "approved": float(counts.get("approved", 0)),
            "executed": float(counts.get("executed", 0)),
            "expired": float(counts.get("expired", 0)),
        }
    except Exception:
        pass

    # Analyze reasons
    reasons_up = []
    reasons_down = []

    if score_change > 0.5:
        reasons_up.append(f"スコアが {score_change:.1f} ポイント上昇（{score_change_pct:.1f}%）")
        if todo_metrics.get("executed", 0) > 0:
            reasons_up.append(f"実行完了タスク: {todo_metrics['executed']:.0f}件")
    elif score_change < -0.5:
        reasons_down.append(
            f"スコアが {abs(score_change):.1f} ポイント下降（{abs(score_change_pct):.1f}%）"
        )
        if todo_metrics.get("expired", 0) > todo_metrics.get("proposed", 0) * 0.5:
            reasons_down.append(f"期限切れタスクが多い: {todo_metrics['expired']:.0f}件")
        if (
            todo_metrics.get("approved", 0) > 0
            and todo_metrics.get("executed", 0) / todo_metrics.get("approved", 1) < 0.5
        ):
            reasons_down.append(
                f"実行率が低い: {todo_metrics['executed']:.0f}/{todo_metrics['approved']:.0f}"
            )

    # Top 3 actions for next week
    top3_actions = []
    if todo_metrics.get("noise_index", 0) > 0.3:
        top3_actions.append("提案品質の改善（ノイズ指数が高い）")
    if todo_metrics.get("approval_rate", 1) < 0.5:
        top3_actions.append("承認率の向上（提案の粒度・優先順位を見直し）")
    if todo_metrics.get("execution_rate", 1) < 0.7:
        top3_actions.append("実行率の向上（実行障害の確認とフロー改善）")

    if len(top3_actions) < 3:
        top3_actions.append("スコアの安定化（10以上を維持）")
    if len(top3_actions) < 3:
        top3_actions.append("週次レビューの継続")

    # Generate review content
    week_start = scores[0][0]
    week_end = scores[-1][0]
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    review_content = f"""# Weekly Review: {week_start.isoformat()} - {week_end.isoformat()}

**Generated**: {now}

---

## 📊 Score Changes

- **Week Start**: {week_start_score:.1f}/100
- **Week End**: {week_end_score:.1f}/100
- **Change**: {score_change:+.1f} points ({score_change_pct:+.1f}%)

---

## 📈 Reasons for Score Increase

"""

    if reasons_up:
        for reason in reasons_up:
            review_content += f"- {reason}\n"
    else:
        review_content += "- 特に大きな変化なし\n"

    review_content += "\n---\n\n"

    ## 📉 Reasons for Score Decrease\n\n"

    if reasons_down:
        for reason in reasons_down:
            review_content += f"- {reason}\n"
    else:
        review_content += "- 特に大きな下降なし\n"

    review_content += "\n---\n\n"

    ## 🎯 Top 3 Actions for Next Week\n\n"

    for i, action in enumerate(top3_actions[:3], 1):
        review_content += f"{i}. {action}\n"

    review_content += "\n---\n\n"

    ## 📋 ToDo Metrics Summary\n\n"
    review_content += f"- **Proposed**: {todo_metrics.get('proposed', 0):.0f}\n"
    review_content += f"- **Approved**: {todo_metrics.get('approved', 0):.0f}\n"
    review_content += f"- **Executed**: {todo_metrics.get('executed', 0):.0f}\n"
    review_content += f"- **Expired**: {todo_metrics.get('expired', 0):.0f}\n"

    # Save review file
    review_file = REVIEW_DIR / f"Playbook_Review_{week_end.isoformat()}.md"
    review_file.write_text(review_content, encoding="utf-8", newline="\n")

    return str(review_file)


def create_system3_status():
    """Main entry point"""
    try:
        path = generate_system3_status()
        print(f"✅ Updated: {path}")

        # Weekly review update (runs on Sunday)
        from datetime import datetime

        if datetime.now().weekday() == 6:  # Sunday
            try:
                review_path = update_weekly_review()
                if review_path:
                    print(f"✅ Weekly review updated: {review_path}")
                    # Run playbook auto promotion after weekly review
                    try:
                        import sys
                        import os

                        sys.path.insert(0, os.path.dirname(__file__))
                        from playbook_auto_promotion import auto_promote_tier1

                        promoted = auto_promote_tier1()
                        if promoted:
                            print(f"✅ Auto-promoted: {len(promoted)} playbook(s)")
                    except ImportError:
                        pass  # Optional integration
                    except Exception as e:
                        print(f"⚠️ Playbook promotion skipped: {e}")
            except Exception as e:
                print(f"⚠️ Weekly review update skipped: {e}")

        return path
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return None


if __name__ == "__main__":
    create_system3_status()
