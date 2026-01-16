#!/usr/bin/env python3
"""
週次内発的動機づけサマリー生成スクリプト
- メトリクス収集
- Top 3 ToDo生成
- ご褒美チェック
- Obsidianに週次サマリーを作成
"""

import httpx
from datetime import datetime, date, timedelta
from pathlib import Path
from obsidian_integration import ObsidianIntegration

# API URL
METRICS_URL = "http://localhost:5131"
TODO_URL = "http://localhost:5132"
REWARD_URL = "http://localhost:5133"

def generate_weekly_summary():
    """週次サマリーを生成"""

    # Obsidian統合を初期化
    vault_path = Path.home() / "Documents" / "Obsidian Vault"
    if not vault_path.exists():
        vault_path = Path.home() / "Documents" / "Obsidian"
    if not vault_path.exists():
        vault_path = Path.cwd()

    obsidian = ObsidianIntegration(str(vault_path))

    now = datetime.now()
    week_start = now - timedelta(days=7)

    content = f"""# System 3 週次内発的動機づけサマリー

**期間**: {week_start.strftime('%Y-%m-%d')} ~ {now.strftime('%Y-%m-%d')}
**生成日**: {now.strftime('%Y-%m-%d %H:%M:%S')}

---

## 📊 メトリクス

"""

    # メトリクスを取得
    try:
        response = httpx.get(f"{METRICS_URL}/api/summary", timeout=10)
        if response.status_code == 200:
            metrics = response.json()
            today = metrics.get("today", {})
            weekly = metrics.get("weekly", {})

            content += f"""### 今日のメトリクス

- **改善意欲スコア**: {today.get('improvement_desire_score', 0):.1f}/100
- **自己改善実行率**: {today.get('execution_rate', 0):.1%}
- **生成されたタスク数**: {today.get('tasks_generated', 0)}件
- **実行されたタスク数**: {today.get('tasks_executed', 0)}件
- **作成されたPlaybook数**: {today.get('playbooks_created', 0)}件
- **学習アクション数**: {today.get('learning_actions', 0)}件

### 週次トレンド

- **平均改善意欲スコア**: {weekly.get('average_score', 0):.1f}/100
- **平均実行率**: {weekly.get('average_execution_rate', 0):.1%}
- **週間生成タスク数**: {weekly.get('total_tasks_generated', 0)}件
- **週間実行タスク数**: {weekly.get('total_tasks_executed', 0)}件

"""
        else:
            content += "*（メトリクス取得に失敗しました）*\n\n"
    except Exception as e:
        content += f"*（メトリクス取得エラー: {e}）*\n\n"

    content += "---\n\n## 🎯 今週のTop 3 改善ToDo\n\n"

    # Top 3 ToDoを生成
    try:
        response = httpx.post(f"{TODO_URL}/api/generate-top3", timeout=10)
        if response.status_code == 200:
            todos_data = response.json()
            todos = todos_data.get("todos", [])

            for i, todo in enumerate(todos, 1):
                content += f"""### {i}. {todo.get('title', 'N/A')}

**影響スコア**: {todo.get('impact_score', 0):.1f}/100
**工数スコア**: {todo.get('effort_score', 0):.1f}/100
**効率スコア**: {todo.get('efficiency_score', 0):.2f}
**優先度**: {todo.get('priority', 0)}/10
**推定時間**: {todo.get('estimated_hours', 0):.1f}時間
**承認必要**: {'はい' if todo.get('requires_approval', False) else 'いいえ'}

{todo.get('description', '')}

---
"""
        else:
            content += "*（ToDo生成に失敗しました）*\n\n"
    except Exception as e:
        content += f"*（ToDo生成エラー: {e}）*\n\n"

    content += "\n---\n\n## 🎉 ご褒美・達成状況\n\n"

    # ご褒美をチェック
    try:
        response = httpx.post(f"{REWARD_URL}/api/check", timeout=10)
        if response.status_code == 200:
            reward_data = response.json()
            if reward_data.get("achievement", False):
                event = reward_data.get("event", {})
                content += f"""**{event.get('message', 'N/A')}**

達成レベル: {event.get('achievement_level', 'N/A').upper()}

"""
            else:
                content += "*（新しい達成はありません）*\n\n"

        # 直近のご褒美を取得
        response = httpx.get(f"{REWARD_URL}/api/recent?days=7", timeout=10)
        if response.status_code == 200:
            recent_data = response.json()
            rewards = recent_data.get("rewards", [])
            if rewards:
                content += "### 直近7日間の達成\n\n"
                for reward in rewards:
                    content += f"- **{reward.get('achievement_level', 'N/A').upper()}**: {reward.get('message', 'N/A')}\n"
                content += "\n"
    except Exception as e:
        content += f"*（ご褒美チェックエラー: {e}）*\n\n"

    content += f"""
---

## 📝 次のアクション

1. Top 3 ToDoを確認し、優先順位を決定
2. 承認が必要なToDoは承認を取得
3. 実行を開始
4. 完了後に結果を記録

---

**次回更新**: {(now + timedelta(days=7)).strftime('%Y-%m-%d')}

**関連リンク**:
- [[System3_Status]] - System 3ステータス
- [[System3_Daily_*]] - 日次ログ
- [[Playbook_Promotion_Rules]] - Playbook昇格ルール
"""

    # Obsidianに保存
    week_num = date.today().isocalendar()[1]
    note_path = obsidian.create_note(
        title=f"System3_Weekly_Summary_Week_{week_num}",
        content=content,
        tags=["ManaOS", "System3", "Weekly", "Summary", "Intrinsic"],
        folder="ManaOS/System/Weekly"
    )

    if note_path:
        print(f"✅ 週次サマリーを作成しました: {note_path}")
        return note_path
    else:
        print("❌ 週次サマリーの作成に失敗しました")
        return None


if __name__ == "__main__":
    generate_weekly_summary()
