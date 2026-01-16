#!/usr/bin/env python3
"""
System 3 Daily Improvement Log Generator
- Reads today's metrics/failures (if available)
- Writes a daily note to Obsidian
- Runs daily to track System 3's self-improvement
"""

from pathlib import Path
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional, List
import json
import httpx
from obsidian_integration import ObsidianIntegration

# Obsidian Vault設定
VAULT_BASE = Path.home() / "Documents" / "Obsidian"
if not VAULT_BASE.exists():
    VAULT_BASE = Path.home() / "Documents" / "Obsidian Vault"
if not VAULT_BASE.exists():
    VAULT_BASE = Path.cwd()

OUT_DIR = VAULT_BASE / "ManaOS" / "System" / "Daily"

# ログファイルパス（ManaOS環境に合わせて調整）
LOG_BASE = Path(__file__).parent / "logs"
LLM_ROUTING_LOG_DIR = LOG_BASE / "llm_routing"
NOTIFICATION_LOG_DIR = LOG_BASE / "notifications"

# System 3関連サービスのURL
LEARNING_SYSTEM_URL = "http://localhost:5126"
METRICS_COLLECTOR_URL = "http://localhost:5127"
TASK_CRITIC_URL = "http://localhost:5102"
AUTONOMY_SYSTEM_URL = "http://localhost:5124"
INTRINSIC_MOTIVATION_URL = "http://localhost:5130"
TODO_QUEUE_URL = "http://localhost:5134"
REWARD_LOOP_URL = "http://localhost:5133"


def read_jsonl_today(path: Path, date_field: str = "timestamp") -> List[Dict[str, Any]]:
    """今日の日付を含むJSONLファイルから行を読み込む"""
    if not path.exists():
        return []

    today = date.today().isoformat()
    rows = []

    try:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue

                # タイムスタンプフィールドを探す
                ts = str(obj.get(date_field) or obj.get("date") or obj.get("day") or
                         obj.get("timestamp") or obj.get("ts") or obj.get("created_at") or "")

                # ISO形式の日付を含むかチェック
                if today in ts or (ts and date.fromisoformat(ts[:10]) == date.today()):
                    rows.append(obj)
    except Exception as e:
        print(f"⚠️ ログ読み込みエラー ({path}): {e}")

    return rows


def get_today_log_files() -> List[Path]:
    """今日のログファイルのパスを取得"""
    today_str = date.today().strftime("%Y%m%d")
    log_files = []

    # LLMルーティング監査ログ
    audit_log = LLM_ROUTING_LOG_DIR / f"audit_{today_str}.jsonl"
    if audit_log.exists():
        log_files.append(audit_log)

    # 失敗通知ログ
    failed_notifications = NOTIFICATION_LOG_DIR / f"failed_{today_str}.jsonl"
    if failed_notifications.exists():
        log_files.append(failed_notifications)

    return log_files


def get_learning_stats() -> Dict[str, Any]:
    """Learning Systemから統計を取得"""
    try:
        response = httpx.get(f"{LEARNING_SYSTEM_URL}/api/analyze", timeout=5)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return {}


def get_metrics_stats() -> Dict[str, Any]:
    """Metrics Collectorから統計を取得"""
    try:
        response = httpx.get(f"{METRICS_COLLECTOR_URL}/api/metrics/summary", timeout=5)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return {}


def get_autonomy_status() -> Dict[str, Any]:
    """Autonomy Systemから状態を取得"""
    try:
        response = httpx.get(f"{AUTONOMY_SYSTEM_URL}/api/status", timeout=5)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return {"autonomy_level": "Level 1", "status": "active"}


def analyze_failures(failures: List[Dict[str, Any]]) -> Dict[str, Any]:
    """失敗パターンを分析"""
    if not failures:
        return {
            "count": 0,
            "patterns": [],
            "top_errors": []
        }

    # エラータイプを集計
    error_types = {}
    for failure in failures:
        error_type = failure.get("error_type") or failure.get("type") or "unknown"
        error_types[error_type] = error_types.get(error_type, 0) + 1

    # 上位3つのエラータイプ
    top_errors = sorted(error_types.items(), key=lambda x: x[1], reverse=True)[:3]

    return {
        "count": len(failures),
        "patterns": list(error_types.keys()),
        "top_errors": [{"type": k, "count": v} for k, v in top_errors]
    }


def render_note(
    failures: List[Dict[str, Any]],
    metrics: List[Dict[str, Any]],
    learning_stats: Dict[str, Any],
    metrics_stats: Dict[str, Any],
    autonomy_status: Dict[str, Any]
) -> str:
    """日次ログの内容を生成"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    d = date.today().isoformat()

    # 失敗分析
    failure_analysis = analyze_failures(failures)

    # メトリクス統計
    success_rate = metrics_stats.get("success_rate", 0.0)
    avg_response_time = metrics_stats.get("avg_response_time", 0.0)
    error_rate = metrics_stats.get("error_rate", 0.0)

    # 学習統計
    total_actions = learning_stats.get("total_actions_recorded", 0)
    patterns_learned = learning_stats.get("patterns_learned", 0)

    # Autonomy Level
    autonomy_level = autonomy_status.get("autonomy_level", "Level 1")

    # 失敗パターンの説明
    failure_patterns_text = ""
    if failure_analysis["top_errors"]:
        failure_patterns_text = "\n".join([
            f"  - **{err['type']}**: {err['count']}回"
            for err in failure_analysis["top_errors"]
        ])
    else:
        failure_patterns_text = "  - （本日の失敗はありません）"

    # Intrinsic Motivation Scoreを取得
    intrinsic_score = 10.0  # デフォルト値（最低保証）
    score_breakdown = {"base": 10, "idle": 0.0, "executed": 0, "accepted": 0, "generated": 0, "learning": 0, "safety_penalty": 0}
    try:
        response = httpx.get(f"{INTRINSIC_MOTIVATION_URL}/api/score", timeout=5)
        if response.status_code == 200:
            score_data = response.json()
            intrinsic_score = score_data.get("score", 10.0)  # 最低10保証
            score_breakdown = score_data.get("breakdown", score_breakdown)
    except:
        pass  # エラー時はデフォルト値を使用

    # 承認待ちToDoを取得
    proposed_todos_text = ""
    try:
        response = httpx.get(f"{TODO_QUEUE_URL}/api/todos?state=PROPOSED", timeout=5)
        if response.status_code == 200:
            todos_data = response.json()
            proposed_todos = todos_data.get("todos", [])
            if proposed_todos:
                proposed_todos_text = "\n".join([
                    f"- **{todo.get('title', 'N/A')}** (ID: `{todo.get('id', 'N/A')}`) - {todo.get('reason', '')}"
                    for todo in proposed_todos[:5]
                ])
    except:
        pass

    if not proposed_todos_text:
        proposed_todos_text = "- （承認待ちの提案はありません）"

    # ご褒美をチェック
    reward_message = ""
    try:
        response = httpx.post(f"{REWARD_LOOP_URL}/api/check", timeout=5)
        if response.status_code == 200:
            reward_data = response.json()
            if reward_data.get("achievement", False):
                event = reward_data.get("event", {})
                reward_message = f"""
### 🎉 今日の成長

**{event.get('message', 'N/A')}**

達成レベル: {event.get('achievement_level', 'N/A').upper()}

"""
    except:
        pass

    return f"""# System 3 Daily Log: {d}

**Generated**: {now}
**Autonomy Level**: {autonomy_level}（Internal Maintenance Only）

---

## ✅ 今日やった改善（Done）

### 自動実行
- 失敗ログ検出: **{failure_analysis['count']}件**
- メトリクス記録: **{len(metrics)}件**
- 学習アクション記録: **{total_actions}件**

### 手動/自動改善
- （ここは後から埋められるように空欄を残す）
  -

---

## 🧠 今日学んだこと（Learned）

### 失敗パターン分析
{failure_patterns_text}

### 学習統計
- 学習済みパターン数: **{patterns_learned}**
- 記録されたアクション数: **{total_actions:,}**

### 気づき・洞察
- （ここは後から埋められるように空欄を残す）
  -

---

## 🎯 明日の狙い（Next）

### 成功率向上のための一手
- （ここは後から埋められるように空欄を残す）
  -

### Playbook候補抽出
- （ここは後から埋められるように空欄を残す）
  -

---

## 🛂 承認が必要な提案（Need Approval）

{proposed_todos_text}

---

## 💡 System 3の自己評価

**「今日のSystem 3は何をしたか」**

### 内発的動機づけスコア

**総合スコア**: {intrinsic_score:.1f}/100

**内訳**:
- ベース: {score_breakdown.get('base', 0):.1f}
- アイドル時間: {score_breakdown.get('idle', 0):.1f}
- 実行タスク: {score_breakdown.get('executed', 0):.1f}
- 承認タスク: {score_breakdown.get('accepted', 0):.1f}
- 生成タスク: {score_breakdown.get('generated', 0):.1f}
- 学習成果: {score_breakdown.get('learning', 0):.1f}
- 安全ペナルティ: {score_breakdown.get('safety_penalty', 0):.1f}

{reward_message}
---

## 🚨 異常・注意（Alerts）

### パフォーマンスメトリクス
- **成功率**: {success_rate:.1%}
- **平均レスポンス時間**: {avg_response_time:.2f}ms
- **エラー率**: {error_rate:.2%}

### 異常検知
- （ここは後から埋められるように空欄を残す）
  -

---

## 📊 統計サマリー

- **失敗件数**: {failure_analysis['count']}件
- **メトリクス記録数**: {len(metrics)}件
- **学習パターン数**: {patterns_learned}
- **成功率**: {success_rate:.1%}
- **内発的動機づけスコア**: {intrinsic_score:.1f}/100

---

**次回更新**: {(datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')} 21:30
"""


def main():
    """メイン処理"""
    # 出力ディレクトリを作成
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # 今日の日付
    d = date.today().isoformat()
    out_file = OUT_DIR / f"System3_Daily_{d}.md"

    # 既存のファイルがあるかチェック（追記モードにするか、上書きするか）
    # 今回は上書きモードで実装

    print(f"📊 System 3日次ログを生成中...")

    # ログファイルからデータを取得
    log_files = get_today_log_files()
    all_failures = []
    all_metrics = []

    for log_file in log_files:
        if "failed" in log_file.name:
            failures = read_jsonl_today(log_file, date_field="timestamp")
            all_failures.extend(failures)
        elif "audit" in log_file.name:
            metrics = read_jsonl_today(log_file, date_field="timestamp")
            all_metrics.extend(metrics)

    # APIから統計を取得
    learning_stats = get_learning_stats()
    metrics_stats = get_metrics_stats()
    autonomy_status = get_autonomy_status()

    # ログ内容を生成
    content = render_note(
        all_failures,
        all_metrics,
        learning_stats,
        metrics_stats,
        autonomy_status
    )

    # Obsidianにノートを作成
    obsidian = ObsidianIntegration(str(VAULT_BASE))
    note_path = obsidian.create_note(
        title=f"System3_Daily_{d}",
        content=content,
        tags=["ManaOS", "System3", "Daily", "Log"],
        folder="ManaOS/System/Daily"
    )

    if note_path:
        print(f"✅ System 3日次ログを作成しました: {note_path}")
        return note_path
    else:
        # Obsidian統合が失敗した場合、直接ファイルに書き込む
        out_file.write_text(content, encoding="utf-8")
        print(f"✅ System 3日次ログを作成しました（直接書き込み）: {out_file}")
        return out_file


if __name__ == "__main__":
    main()
