#!/usr/bin/env python3
"""
Playbook Review 週次レビュー生成スクリプト
- 日次ログからCandidateを抽出
- Gate判定の準備
- 週次レビューノートを生成
"""

from pathlib import Path
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional
import re
import httpx
from obsidian_integration import ObsidianIntegration

# System 3関連サービスのURL
INTRINSIC_MOTIVATION_URL = "http://localhost:5130"

# Obsidian Vault設定
VAULT_BASE = Path.home() / "Documents" / "Obsidian"
if not VAULT_BASE.exists():
    VAULT_BASE = Path.home() / "Documents" / "Obsidian Vault"
if not VAULT_BASE.exists():
    VAULT_BASE = Path.cwd()

DAILY_DIR = VAULT_BASE / "ManaOS" / "System" / "Daily"
PLAYBOOKS_DIR = VAULT_BASE / "ManaOS" / "System" / "Playbooks"
ANTI_PLAYBOOKS_DIR = VAULT_BASE / "ManaOS" / "System" / "AntiPlaybooks"


def extract_candidates_from_daily_log(log_file: Path) -> List[Dict[str, Any]]:
    """日次ログからCandidateを抽出"""
    if not log_file.exists():
        return []

    candidates = []

    try:
        content = log_file.read_text(encoding="utf-8")

        # "Done"セクションから成功パターンを抽出
        done_section = re.search(r"## ✅ 今日やった改善.*?## 🧠", content, re.DOTALL)
        if done_section:
            done_text = done_section.group(0)
            # 箇条書きの項目を抽出
            items = re.findall(r"- \*\*(.+?)\*\*: (.+?)(?=\n-|\n##|$)", done_text)
            for title, description in items:
                if "改善" in title or "成功" in title.lower() or "完了" in title:
                    candidates.append({
                        "type": "success",
                        "title": title.strip(),
                        "description": description.strip(),
                        "source": log_file.name,
                        "date": log_file.stem.split("_")[-1] if "_" in log_file.stem else ""
                    })

        # "Learned"セクションから学習パターンを抽出
        learned_section = re.search(r"## 🧠 今日学んだこと.*?## 🎯", content, re.DOTALL)
        if learned_section:
            learned_text = learned_section.group(0)
            # 失敗パターンから学習したことを抽出
            patterns = re.findall(r"- \*\*(.+?)\*\*: (.+?)(?=\n-|\n##|$)", learned_text)
            for title, description in patterns:
                if "パターン" in title or "学習" in title:
                    candidates.append({
                        "type": "learned",
                        "title": title.strip(),
                        "description": description.strip(),
                        "source": log_file.name,
                        "date": log_file.stem.split("_")[-1] if "_" in log_file.stem else ""
                    })

        # "Next"セクションから提案を抽出
        next_section = re.search(r"## 🎯 明日の狙い.*?## 🛂", content, re.DOTALL)
        if next_section:
            next_text = next_section.group(0)
            items = re.findall(r"- (.+?)(?=\n-|\n##|$)", next_text)
            for item in items:
                if item.strip() and not item.strip().startswith("（"):
                    candidates.append({
                        "type": "proposal",
                        "title": "提案",
                        "description": item.strip(),
                        "source": log_file.name,
                        "date": log_file.stem.split("_")[-1] if "_" in log_file.stem else ""
                    })

    except Exception as e:
        print(f"⚠️ ログ解析エラー ({log_file}): {e}")

    return candidates


def get_weekly_daily_logs() -> List[Path]:
    """直近7日間の日次ログを取得"""
    logs = []
    today = date.today()

    for i in range(7):
        target_date = today - timedelta(days=i)
        log_file = DAILY_DIR / f"System3_Daily_{target_date.isoformat()}.md"
        if log_file.exists():
            logs.append(log_file)

    return sorted(logs, reverse=True)


def categorize_candidate(candidate: Dict[str, Any]) -> str:
    """Candidateをカテゴリに分類"""
    title_lower = candidate["title"].lower()
    desc_lower = candidate.get("description", "").lower()

    # カテゴリ判定
    if "api" in title_lower or "api" in desc_lower:
        return "API"
    elif "rag" in title_lower or "rag" in desc_lower:
        return "RAG"
    elif "llm" in title_lower or "llm" in desc_lower:
        return "LLM"
    elif "slack" in title_lower or "slack" in desc_lower:
        return "Slack"
    elif "github" in title_lower or "github" in desc_lower:
        return "GitHub"
    elif "obsidian" in title_lower or "obsidian" in desc_lower:
        return "Obsidian"
    elif "最適化" in title_lower or "optimization" in desc_lower:
        return "Optimization"
    elif "エラー" in title_lower or "error" in desc_lower:
        return "Error Handling"
    else:
        return "General"


def generate_playbook_review() -> str:
    """週次レビューの内容を生成"""
    now = datetime.now()
    week_start = now - timedelta(days=7)

    # 直近7日間のログを取得
    daily_logs = get_weekly_daily_logs()

    # 全Candidateを抽出
    all_candidates = []
    for log_file in daily_logs:
        candidates = extract_candidates_from_daily_log(log_file)
        all_candidates.extend(candidates)

    # カテゴリ別に分類
    candidates_by_category = {}
    for candidate in all_candidates:
        category = categorize_candidate(candidate)
        if category not in candidates_by_category:
            candidates_by_category[category] = []
        candidates_by_category[category].append(candidate)

    # スコア変化を取得
    score_start = 10.0
    score_end = 10.0
    score_change = 0.0
    score_trend = "→"

    try:
        # 週初めのスコアを取得
        week_start_log = DAILY_DIR / f"System3_Daily_{week_start.strftime('%Y-%m-%d')}.md"
        if week_start_log.exists():
            content_start = week_start_log.read_text(encoding="utf-8")
            score_match = re.search(r"\*\*総合スコア\*\*: ([\d.]+)/100", content_start)
            if score_match:
                score_start = float(score_match.group(1))

        # 今日のスコアを取得
        today_log = DAILY_DIR / f"System3_Daily_{now.strftime('%Y-%m-%d')}.md"
        if today_log.exists():
            content_end = today_log.read_text(encoding="utf-8")
            score_match = re.search(r"\*\*総合スコア\*\*: ([\d.]+)/100", content_end)
            if score_match:
                score_end = float(score_match.group(1))

        score_change = score_end - score_start
        if score_change > 0:
            score_trend = "↑"
        elif score_change < 0:
            score_trend = "↓"
    except:
        pass

    # レビュー内容を生成
    content = f"""# Playbook Review: {week_start.strftime('%Y-%m-%d')} ~ {now.strftime('%Y-%m-%d')}

**Generated**: {now.strftime('%Y-%m-%d %H:%M:%S')}
**Review Period**: 直近7日間
**Total Candidates**: {len(all_candidates)}件

---

## 📊 サマリー

- **抽出されたCandidate数**: {len(all_candidates)}件
- **カテゴリ数**: {len(candidates_by_category)}カテゴリ
- **レビュー対象ログ**: {len(daily_logs)}日分

---

## 📈 内発的動機づけスコア変化

**週初め**: {score_start:.1f}/100
**週末**: {score_end:.1f}/100
**変化**: {score_change:+.1f} {score_trend}

### スコア変化の分析

"""

    if score_change > 0:
        content += f"""
**今週スコアが上がった理由**:
- 実行タスク数が増加した可能性
- 学習成果が蓄積された可能性
- 承認・実行のサイクルが回った可能性

**来週の1手（Top 3）**:
1. 承認待ちToDoを1つ実行して実行率を上げる
2. 学習パターンをPlaybook化して資産化する
3. 失敗パターンを分析して安全ペナルティを減らす

"""
    elif score_change < 0:
        content += f"""
**今週スコアが下がった原因**:
- 提案が多すぎて承認率が下がった可能性
- 失敗が多くて安全ペナルティが増えた可能性
- 実行タスクが少なかった可能性

**来週の1手（Top 3）**:
1. 提案の質を上げる（ノイズ指数を下げる）
2. 承認待ちToDoを整理する
3. 失敗パターンを学習して再発防止する

"""
    else:
        content += f"""
**今週スコアは安定**:
- システムは正常に動作しています
- 継続的な改善を維持しましょう

**来週の1手（Top 3）**:
1. 新しい改善提案を検討する
2. 既存のPlaybookを活用する
3. 学習サイクルを継続する

"""

    content += """
---

## 🎯 Gate判定待ちCandidate

### Gate A: 再現性チェック

以下のCandidateは再現性の確認が必要です。

"""

    # カテゴリ別にCandidateを表示
    for category, candidates in sorted(candidates_by_category.items()):
        content += f"\n#### {category} ({len(candidates)}件)\n\n"

        for i, candidate in enumerate(candidates, 1):
            content += f"{i}. **{candidate['title']}**\n"
            content += f"   - タイプ: {candidate['type']}\n"
            content += f"   - 説明: {candidate['description'][:100]}...\n"
            content += f"   - ソース: [[{candidate['source'].replace('.md', '')}]]\n"
            content += f"   - 日付: {candidate['date']}\n"
            content += f"   - Gate A判定: ⏳ 待ち\n"
            content += f"   - Gate B判定: ⏳ 待ち\n"
            content += f"   - Gate C判定: ⏳ 待ち\n"
            content += "\n"

    content += f"""
---

## 🔍 Gate判定ガイド

### Gate A: 再現性（Reproducibility）

- [ ] 同系タスクで連続2回成功しているか？
- [ ] 7日以内に同カテゴリで成功率80%以上か？
- [ ] "失敗→修正→成功"の流れが記録され、修正点が明確か？

### Gate B: コスト価値（Value）

- [ ] 推論/実行ステップを30%以上削減できるか？
- [ ] 失敗率を明確に下げるか？
- [ ] 標準化の価値が高いか？

### Gate C: 安全性（Safety）

- [ ] APIキー、認証、重要設定を書き換えないか？
- [ ] 外部サービス設定を勝手に変えないか？
- [ ] データ削除・破壊リスクがないか？
- [ ] Autonomy Level 1の範囲に収まるか？

---

## 📝 判定結果

### ✅ Playbook昇格候補

*（Gate A/B/C すべて通過したCandidateをここに記載）*

-

### ⚠️ Anti-Playbook候補

*（失敗パターンや危険な手順をここに記載）*

-

### 🔄 継続観察

*（判定を保留し、さらに観察が必要なCandidate）*

-

---

## 🎯 次のアクション

1. Gate判定を実施
2. Playbook昇格候補を `ManaOS/System/Playbooks/` に作成
3. Anti-Playbook候補を `ManaOS/System/AntiPlaybooks/` に作成
4. 次回レビュー: {(now + timedelta(days=7)).strftime('%Y-%m-%d')}

---

**関連リンク**:
- [[Playbook_Promotion_Rules]] - 昇格ルール定義
- [[System3_Status]] - System 3ステータス
- [[System3_Daily_*]] - 日次ログ

---

**最終更新**: {now.strftime('%Y-%m-%d %H:%M:%S')}
"""

    return content


def create_playbook_review():
    """Playbook Reviewを作成"""
    # ディレクトリを作成
    PLAYBOOKS_DIR.mkdir(parents=True, exist_ok=True)
    ANTI_PLAYBOOKS_DIR.mkdir(parents=True, exist_ok=True)

    # レビュー内容を生成
    content = generate_playbook_review()

    # Obsidianにノートを作成
    obsidian = ObsidianIntegration(str(VAULT_BASE))

    # 週次レビューファイル名
    today = date.today()
    week_start = today - timedelta(days=7)
    review_filename = f"Playbook_Review_{week_start.isoformat()}_to_{today.isoformat()}"

    note_path = obsidian.create_note(
        title=review_filename,
        content=content,
        tags=["ManaOS", "System3", "Playbook", "Review"],
        folder="ManaOS/System"
    )

    if note_path:
        print(f"✅ Playbook Reviewを作成しました: {note_path}")
        return note_path
    else:
        print("❌ Playbook Reviewの作成に失敗しました")
        return None


if __name__ == "__main__":
    create_playbook_review()
