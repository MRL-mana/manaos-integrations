#!/usr/bin/env python3
"""
manaOS Command Hub - 週次まとめ生成スクリプト

過去7日分のdaily-logを読み込んで、週次まとめを生成する
"""

import json
import sys
from pathlib import Path
from datetime import date, timedelta
from typing import List, Dict
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
        return None  # type: ignore

    try:
        return log_file.read_text(encoding="utf-8")
    except Exception as e:
        logger.warning(f"Failed to read {log_file}: {e}")
        return None  # type: ignore


def parse_daily_log(content: str) -> Dict:
    """日次ログをパースして構造化"""
    if not content:
        return None  # type: ignore

    lines = content.strip().split('\n')
    if not lines:
        return None  # type: ignore

    # 日付を抽出
    date_line = lines[0]
    if not date_line.startswith('['):
        return None  # type: ignore

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
            # その他のセクション
            current_section = None

    return result


def generate_weekly_summary(start_date: date, end_date: date) -> str:
    """週次まとめを生成"""
    logger.info(f"Generating weekly summary: {start_date} to {end_date}")

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
        return None  # type: ignore

    # Markdown形式でまとめを生成
    summary_lines = [
        f"# 週次まとめ: {start_date.strftime('%Y-%m-%d')} 〜 {end_date.strftime('%Y-%m-%d')}",
        "",
        f"**期間**: {len(daily_logs)}日分のログ",
        "",
        "## 📊 サマリー",
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

    if all_what:
        summary_lines.append("### 今週やったこと")
        summary_lines.append("")
        for item in all_what:
            summary_lines.append(f"- {item}")
        summary_lines.append("")

    if all_why:
        summary_lines.append("### なんでやったか")
        summary_lines.append("")
        for item in all_why:
            summary_lines.append(f"- {item}")
        summary_lines.append("")

    if all_next:
        summary_lines.append("### 次どうするか")
        summary_lines.append("")
        # 重複を除去
        unique_next = list(dict.fromkeys(all_next))
        for item in unique_next:
            summary_lines.append(f"- {item}")
        summary_lines.append("")

    # 日別の詳細
    summary_lines.append("## 📅 日別詳細")
    summary_lines.append("")

    for log in daily_logs:
        summary_lines.append(f"### {log['date']}")
        summary_lines.append("")

        if log["what"]:
            summary_lines.append("**やったこと**:")
            for item in log["what"]:
                summary_lines.append(f"- {item}")
            summary_lines.append("")

        if log["why"]:
            summary_lines.append("**なんで**:")
            for item in log["why"]:
                summary_lines.append(f"- {item}")
            summary_lines.append("")

        if log["next"]:
            summary_lines.append("**次**:")
            for item in log["next"]:
                summary_lines.append(f"- {item}")
            summary_lines.append("")

        summary_lines.append("---")
        summary_lines.append("")

    return "\n".join(summary_lines)


def main():
    """メイン処理"""
    # 今週の日曜日から今日まで
    today = date.today()
    days_since_monday = today.weekday()
    start_date = today - timedelta(days=days_since_monday + 6)  # 先週の月曜日
    end_date = today

    logger.info(f"Weekly summary: {start_date} to {end_date}")

    summary = generate_weekly_summary(start_date, end_date)

    if not summary:
        logger.warning("No logs found for this week")
        return 1

    # 出力ディレクトリを作成
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # ファイルに保存
    output_file = OUTPUT_DIR / f"weekly-{start_date.strftime('%Y%m%d')}-{end_date.strftime('%Y%m%d')}.md"
    output_file.write_text(summary, encoding="utf-8")

    logger.info(f"✅ Weekly summary saved: {output_file}")

    # 標準出力にも出力
    print(summary)

    return 0


if __name__ == "__main__":
    sys.exit(main())








