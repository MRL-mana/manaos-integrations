#!/usr/bin/env python3
"""
manaOS Command Hub - 月次まとめ生成スクリプト

過去30日分のdaily-logを読み込んで、月次まとめを生成する
"""

import json
import sys
from pathlib import Path
from datetime import date, timedelta
from typing import List, Dict
from collections import Counter
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

BASE = Path("/root")
LOGS_DIR = BASE / "logs"
OUTPUT_DIR = BASE / "manaos_command_hub" / "summaries"


def read_daily_log(log_date: date) -> str:
    """指定日のログファイルを読み込む"""
    log_file = LOGS_DIR / f"daily-{log_date.strftime('%Y-%m-%d')}.log"

    if not log_file.exists():
        return None

    try:
        return log_file.read_text(encoding="utf-8")
    except Exception as e:
        logger.warning(f"Failed to read {log_file}: {e}")
        return None


def parse_daily_log(content: str) -> Dict:
    """日次ログをパースして構造化"""
    if not content:
        return None

    lines = content.strip().split('\n')
    if not lines:
        return None

    # 日付を抽出
    date_line = lines[0]
    if not date_line.startswith('['):
        return None

    result = {
        "date": date_line.strip('[]'),
        "what": [],
        "why": [],
        "next": []
    }

    current_section = None
    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue

        if line.startswith("## 今日やったこと"):
            current_section = "what"
        elif line.startswith("## なんでやったか"):
            current_section = "why"
        elif line.startswith("## 次どうするか"):
            current_section = "next"
        elif line.startswith("- "):
            if current_section:
                result[current_section].append(line[2:])
        elif line.startswith("##"):
            current_section = None

    return result


def generate_monthly_summary(start_date: date, end_date: date) -> str:
    """月次まとめを生成"""
    logger.info(f"Generating monthly summary: {start_date} to {end_date}")

    daily_logs = []
    current_date = start_date

    while current_date <= end_date:
        content = read_daily_log(current_date)
        if content:
            parsed = parse_daily_log(content)
            if parsed:
                daily_logs.append(parsed)
        current_date += timedelta(days=1)

    if not daily_logs:
        return None

    # Markdown形式でまとめを生成
    summary_lines = [
        f"# 月次まとめ: {start_date.strftime('%Y年%m月%d日')} 〜 {end_date.strftime('%Y年%m月%d日')}",
        "",
        f"**期間**: {len(daily_logs)}日分のログ",
        "",
        "## 📊 統計",
        "",
        f"- **ログ日数**: {len(daily_logs)}日",
        f"- **期間**: {(end_date - start_date).days + 1}日間",
        "",
        "## 🎯 今月やったこと（まとめ）",
        "",
    ]

    # 全体の「やったこと」をまとめる
    all_what = []
    all_why = []
    all_next = []

    for log in daily_logs:
        all_what.extend(log["what"])
        all_why.extend(log["why"])
        all_next.extend(log["next"])

    # 頻出キーワードを抽出
    what_keywords = []
    for item in all_what:
        what_keywords.extend(item.split())

    keyword_counter = Counter(what_keywords)
    top_keywords = [word for word, count in keyword_counter.most_common(10) if len(word) > 2]

    if top_keywords:
        summary_lines.append("### 頻出キーワード")
        summary_lines.append("")
        for keyword in top_keywords[:5]:
            summary_lines.append(f"- {keyword}")
        summary_lines.append("")

    if all_what:
        summary_lines.append("### 主な活動")
        summary_lines.append("")
        # 重複を除去して表示
        unique_what = list(dict.fromkeys(all_what))
        for item in unique_what[:20]:  # 最大20件
            summary_lines.append(f"- {item}")
        summary_lines.append("")

    if all_why:
        summary_lines.append("### 動機・理由")
        summary_lines.append("")
        unique_why = list(dict.fromkeys(all_why))
        for item in unique_why[:10]:  # 最大10件
            summary_lines.append(f"- {item}")
        summary_lines.append("")

    if all_next:
        summary_lines.append("### 次のアクション（まとめ）")
        summary_lines.append("")
        unique_next = list(dict.fromkeys(all_next))
        for item in unique_next[:15]:  # 最大15件
            summary_lines.append(f"- {item}")
        summary_lines.append("")

    # 週別のサマリー
    summary_lines.append("## 📅 週別サマリー")
    summary_lines.append("")

    week_start = start_date
    week_num = 1

    while week_start <= end_date:
        week_end = min(week_start + timedelta(days=6), end_date)
        week_logs = [log for log in daily_logs
                     if start_date <= date.fromisoformat(log["date"]) <= week_end]

        if week_logs:
            summary_lines.append(f"### 第{week_num}週: {week_start.strftime('%m/%d')} 〜 {week_end.strftime('%m/%d')}")
            summary_lines.append("")
            summary_lines.append(f"**ログ日数**: {len(week_logs)}日")
            summary_lines.append("")

            week_what = []
            for log in week_logs:
                week_what.extend(log["what"])

            if week_what:
                summary_lines.append("**主な活動**:")
                unique_week_what = list(dict.fromkeys(week_what))
                for item in unique_week_what[:5]:  # 週ごとに最大5件
                    summary_lines.append(f"- {item}")
                summary_lines.append("")

        week_start = week_end + timedelta(days=1)
        week_num += 1

    return "\n".join(summary_lines)


def main():
    """メイン処理"""
    # 過去30日間
    today = date.today()
    start_date = today - timedelta(days=29)
    end_date = today

    logger.info(f"Monthly summary: {start_date} to {end_date}")

    summary = generate_monthly_summary(start_date, end_date)

    if not summary:
        logger.warning("No logs found for this month")
        return 1

    # 出力ディレクトリを作成
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # ファイルに保存
    output_file = OUTPUT_DIR / f"monthly-{start_date.strftime('%Y%m')}.md"
    output_file.write_text(summary, encoding="utf-8")

    logger.info(f"✅ Monthly summary saved: {output_file}")

    # 標準出力にも出力
    print(summary)

    return 0


if __name__ == "__main__":
    sys.exit(main())








