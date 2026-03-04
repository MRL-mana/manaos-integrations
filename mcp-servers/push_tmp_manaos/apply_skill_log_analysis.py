#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ログ分析処理スクリプト
YAML形式のログ分析設定を読み込み、ログファイルを解析してレポートを生成
"""

import os
import sys
import json
import yaml
import requests
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
from collections import Counter, defaultdict

# 設定
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")

project_root = Path(__file__).parent.parent
HISTORY_FILE = project_root / "data" / "skill_log_analysis_history.json"
ARTIFACTS_DIR = project_root / "artifacts"
ARTIFACTS_DIR.mkdir(exist_ok=True)


def load_history() -> Dict[str, Any]:
    """処理履歴を読み込む"""
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️  履歴ファイルの読み込みエラー: {e}")
    return {"processed": []}


def save_history(history: Dict[str, Any]):
    """処理履歴を保存"""
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def is_already_processed(
    idempotency_key: str, history: Dict[str, Any]
) -> bool:
    """既に処理済みかチェック"""
    processed_keys = [
        item.get("idempotency_key")
        for item in history.get("processed", [])
    ]
    return idempotency_key in processed_keys


def mark_as_processed(
    idempotency_key: str, history: Dict[str, Any], result: Dict[str, Any]
):
    """処理済みとしてマーク"""
    if "processed" not in history:
        history["processed"] = []

    history["processed"].append({
        "idempotency_key": idempotency_key,
        "processed_at": datetime.now().isoformat(),
        "result": result
    })


def analyze_error_summary(log_file: Path) -> Dict[str, Any]:
    """エラーサマリーを分析"""
    error_patterns = [
        (r'ERROR', 'ERROR'),
        (r'CRITICAL', 'CRITICAL'),
        (r'WARNING', 'WARNING'),
        (r'Exception', 'Exception'),
        (r'Traceback', 'Traceback'),
    ]
    
    error_counts = Counter()
    error_lines = []
    
    try:
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line_num, line in enumerate(f, 1):
                for pattern, label in error_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        error_counts[label] += 1
                        error_lines.append({
                            "line": line_num,
                            "type": label,
                            "content": line.strip()[:200]  # 最初の200文字
                        })
                        break
        
        return {
            "success": True,
            "total_errors": sum(error_counts.values()),
            "error_counts": dict(error_counts),
            "sample_errors": error_lines[:50]  # 最初の50件
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def analyze_performance(log_file: Path) -> Dict[str, Any]:
    """パフォーマンス分析"""
    performance_patterns = [
        (r'(\d+\.?\d*)\s*(?:ms|秒)', 'duration'),
        (r'response_time[=:]\s*(\d+\.?\d*)', 'response_time'),
    ]
    
    durations = []
    
    try:
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                for pattern, _ in performance_patterns:
                    matches = re.findall(pattern, line, re.IGNORECASE)
                    for match in matches:
                        try:
                            durations.append(float(match))
                        except ValueError:
                            pass
        
        if durations:
            return {
                "success": True,
                "count": len(durations),
                "min": min(durations),
                "max": max(durations),
                "avg": sum(durations) / len(durations),
                "durations": durations[:100]  # 最初の100件
            }
        else:
            return {
                "success": True,
                "count": 0,
                "message": "パフォーマンスデータが見つかりませんでした"
            }
    except Exception as e:
        return {"success": False, "error": str(e)}


def analyze_pattern(log_file: Path, pattern: Optional[str] = None) -> Dict[str, Any]:
    """パターン分析"""
    if not pattern:
        pattern = r'ERROR|WARNING|Exception'
    
    matches = []
    
    try:
        compiled_pattern = re.compile(pattern, re.IGNORECASE)
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line_num, line in enumerate(f, 1):
                if compiled_pattern.search(line):
                    matches.append({
                        "line": line_num,
                        "content": line.strip()[:200]
                    })
        
        return {
            "success": True,
            "pattern": pattern,
            "matches_count": len(matches),
            "matches": matches[:100]  # 最初の100件
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def generate_markdown_report(analysis_result: Dict[str, Any], analysis_type: str) -> str:
    """Markdownレポートを生成"""
    lines = []
    lines.append(f"# ログ分析レポート: {analysis_type}")
    lines.append(f"")
    lines.append(f"生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"")
    
    if analysis_type == "error_summary":
        lines.append("## エラーサマリー")
        lines.append(f"")
        if analysis_result.get("success"):
            lines.append(f"- **合計エラー数**: {analysis_result.get('total_errors', 0)}")
            lines.append(f"")
            lines.append("### エラータイプ別")
            for error_type, count in analysis_result.get("error_counts", {}).items():
                lines.append(f"- {error_type}: {count}件")
            lines.append(f"")
            
            sample_errors = analysis_result.get("sample_errors", [])
            if sample_errors:
                lines.append("### エラーサンプル")
                for error in sample_errors[:20]:  # 最初の20件
                    lines.append(f"")
                    lines.append(f"**行 {error['line']}** ({error['type']}):")
                    lines.append(f"```")
                    lines.append(error['content'])
                    lines.append(f"```")
    
    elif analysis_type == "performance":
        lines.append("## パフォーマンス分析")
        lines.append(f"")
        if analysis_result.get("success"):
            if analysis_result.get("count", 0) > 0:
                lines.append(f"- **データポイント数**: {analysis_result['count']}")
                lines.append(f"- **最小値**: {analysis_result['min']}")
                lines.append(f"- **最大値**: {analysis_result['max']}")
                lines.append(f"- **平均値**: {analysis_result['avg']:.2f}")
            else:
                lines.append(analysis_result.get("message", "データが見つかりませんでした"))
    
    elif analysis_type == "pattern":
        lines.append("## パターン分析")
        lines.append(f"")
        if analysis_result.get("success"):
            lines.append(f"- **パターン**: `{analysis_result.get('pattern', '')}`")
            lines.append(f"- **マッチ数**: {analysis_result.get('matches_count', 0)}")
            lines.append(f"")
            matches = analysis_result.get("matches", [])
            if matches:
                lines.append("### マッチした行")
                for match in matches[:30]:  # 最初の30件
                    lines.append(f"")
                    lines.append(f"**行 {match['line']}**:")
                    lines.append(f"```")
                    lines.append(match['content'])
                    lines.append(f"```")
    
    return "\n".join(lines)


def analyze_logs(data: Dict[str, Any]) -> Dict[str, Any]:
    """ログを分析"""
    log_file = Path(data.get("log_file", ""))
    if not log_file.exists():
        return {"success": False, "error": f"ログファイルが見つかりません: {log_file}"}
    
    analysis_type = data.get("analysis_type", "error_summary")
    output_format = data.get("output_format", "markdown")
    output_path = Path(data.get("output_path", ""))
    
    # 分析実行
    if analysis_type == "error_summary":
        analysis_result = analyze_error_summary(log_file)
    elif analysis_type == "performance":
        analysis_result = analyze_performance(log_file)
    elif analysis_type == "pattern":
        pattern = data.get("pattern")
        analysis_result = analyze_pattern(log_file, pattern)
    else:
        return {"success": False, "error": f"不明な分析タイプ: {analysis_type}"}
    
    if not analysis_result.get("success"):
        return analysis_result
    
    # レポート生成
    if output_format == "markdown":
        report_content = generate_markdown_report(analysis_result, analysis_type)
    elif output_format == "json":
        report_content = json.dumps(analysis_result, ensure_ascii=False, indent=2)
    else:
        report_content = str(analysis_result)
    
    # ファイルに保存
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        return {
            "success": True,
            "analysis_result": analysis_result,
            "output_file": str(output_path)
        }
    except Exception as e:
        return {"success": False, "error": f"レポート保存エラー: {str(e)}"}


def send_slack_notification(action: str, result: Dict[str, Any]) -> bool:
    """Slack通知を送信"""
    if not SLACK_WEBHOOK_URL:
        print("⚠️  SLACK_WEBHOOK_URLが設定されていません。スキップします。")
        return False
    
    try:
        action_names = {
            "analyze": "ログ分析",
            "report": "ログレポート",
            "alert": "ログアラート"
        }
        action_name = action_names.get(action, action)
        
        message = f"📊 *ログ分析: {action_name}*\n\n"
        
        if result.get("success"):
            message += f"✅ 成功\n"
            analysis_result = result.get("analysis_result", {})
            if "total_errors" in analysis_result:
                message += f"エラー数: {analysis_result['total_errors']}\n"
            if "matches_count" in analysis_result:
                message += f"マッチ数: {analysis_result['matches_count']}\n"
            if "output_file" in result:
                message += f"レポート: {result['output_file']}\n"
        else:
            message += f"❌ 失敗: {result.get('error', '不明なエラー')}\n"
        
        payload = {
            "text": message,
            "username": "ManaOS Log Analysis",
            "icon_emoji": ":page_with_curl:"
        }
        
        response = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=10)
        
        if response.status_code == 200:
            print("✅ Slack通知送信完了")
            return True
        else:
            print(f"❌ Slack通知送信失敗: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Slack通知送信エラー: {e}")
        return False


def process_yaml_file(yaml_file: Path) -> bool:
    """YAMLファイルを処理"""
    print(f"\n📁 処理開始: {yaml_file}")
    
    # YAML読み込み
    try:
        with open(yaml_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
    except Exception as e:
        print(f"❌ YAMLファイル読み込みエラー: {e}")
        return False
    
    # バリデーション
    if data.get("kind") != "log_analysis":
        print("⚠️  kindが'log_analysis'ではありません。スキップします。")
        return False
    
    idempotency_key = data.get("idempotency_key")
    if not idempotency_key:
        print("⚠️  idempotency_keyが設定されていません。スキップします。")
        return False
    
    # 履歴チェック
    history = load_history()
    if is_already_processed(idempotency_key, history):
        print(f"⏭️  既に処理済みです: {idempotency_key}")
        return True
    
    # 処理実行
    action = data.get("action")
    result = {"success": False, "error": "不明なアクション"}
    
    try:
        if action == "analyze":
            result = analyze_logs(data)
        else:
            result = {"success": False, "error": f"未実装のアクション: {action}"}
    except Exception as e:
        result = {"success": False, "error": str(e)}
        print(f"❌ 処理エラー: {e}")
    
    # Slack通知
    if data.get("notify", {}).get("slack", False):
        send_slack_notification(action, result)
    else:
        print("⏭️  Slack通知はスキップされます")
    
    # 履歴に記録
    mark_as_processed(idempotency_key, history, result)
    save_history(history)
    
    if result.get("success"):
        print(f"✅ 処理完了: {yaml_file}")
        return True
    else:
        print(f"❌ 処理失敗: {yaml_file} - {result.get('error', '')}")
        return False


def main():
    """メイン処理"""
    if len(sys.argv) < 2:
        print(
            "使用方法: python apply_skill_log_analysis.py "
            "<yaml_file> [yaml_file2 ...]"
        )
        sys.exit(1)
    
    yaml_files = [Path(f) for f in sys.argv[1:]]
    
    success_count = 0
    for yaml_file in yaml_files:
        if not yaml_file.exists():
            print(f"❌ ファイルが見つかりません: {yaml_file}")
            continue
        
        if process_yaml_file(yaml_file):
            success_count += 1
    
    print(f"\n🎉 処理完了: {success_count}/{len(yaml_files)} ファイル")
    
    if success_count < len(yaml_files):
        sys.exit(1)


if __name__ == "__main__":
    main()
