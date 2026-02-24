#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ManaOS Moltbot 監査ログダッシュボード
実行履歴・実行統計・成功率等を可視化
"""

import os
import json
import glob
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Any


class MoltbotAuditDashboard:
    """監査ログから統計情報を抽出・ダッシュボード表示"""

    def __init__(self, audit_base_dir: str = None):
        if audit_base_dir is None:
            audit_base_dir = Path(__file__).parent / "moltbot_audit"
        self.audit_base_dir = Path(audit_base_dir)

    def get_all_audit_logs(self) -> List[Dict[str, Any]]:
        """全ての監査ログを取得"""
        logs = []
        
        # YYYY-MM-DD のディレクトリを探索
        for date_dir in sorted(self.audit_base_dir.glob("20*"), reverse=True):
            # plan-xxxxx のディレクトリを探索
            for plan_dir in sorted(date_dir.glob("plan-*"), reverse=True):
                result_file = plan_dir / "result.json"
                plan_file = plan_dir / "plan.json"
                
                if result_file.exists() and plan_file.exists():
                    try:
                        with open(result_file) as f:
                            result = json.load(f)
                        with open(plan_file) as f:
                            plan = json.load(f)
                        
                        logs.append({
                            "plan_id": result.get("plan_id"),
                            "plan_dir": str(plan_dir),
                            "status": result.get("status"),
                            "intent": plan.get("intent", "不明"),
                            "created_at": plan.get("created_at"),
                            "finished_at": result.get("finished_at"),
                            "steps_done": result.get("steps_done", 0),
                            "steps_total": result.get("steps_total", 0),
                            "duration_seconds": result.get("duration_seconds", 0),
                            "execute_events": result.get("execute_events", [])
                        })
                    except Exception as e:
                        print(f"[WARNING] Failed to load {plan_dir}: {e}")
        
        return logs

    def compute_statistics(self, logs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """統計情報を計算"""
        if not logs:
            return {
                "total_plans": 0,
                "success_rate": 0.0,
                "total_duration": 0.0,
                "avg_duration": 0.0,
                "by_status": {},
                "by_date": {}
            }

        # ステータス別集計
        by_status = defaultdict(int)
        status_counts = defaultdict(int)
        total_duration = 0.0
        
        # 日付別集計
        by_date = defaultdict(list)

        for log in logs:
            status = log["status"]
            by_status[status] += 1
            status_counts[status] += 1
            total_duration += log["duration_seconds"]
            
            # 日付抽出
            if log.get("finished_at"):
                date = log["finished_at"][:10]
                by_date[date].append(log)

        total_plans = len(logs)
        success_count = status_counts.get("completed", 0)
        success_rate = (success_count / total_plans * 100) if total_plans > 0 else 0

        return {
            "total_plans": total_plans,
            "success_rate": success_rate,
            "total_duration": total_duration,
            "avg_duration": total_duration / total_plans if total_plans > 0 else 0,
            "by_status": dict(by_status),
            "by_date": dict(by_date),
            "success_count": success_count,
            "failure_count": status_counts.get("failed", 0)
        }

    def generate_html_dashboard(self, output_file: str = None) -> str:
        """HTML ダッシュボードを生成"""
        logs = self.get_all_audit_logs()
        stats = self.compute_statistics(logs)

        if output_file is None:
            output_file = self.audit_base_dir.parent / "moltbot_dashboard.html"

        # HTML テンプレート
        html_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ManaOS Moltbot ダッシュボード</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        
        header {{
            background: rgba(255, 255, 255, 0.95);
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
        }}
        
        header h1 {{
            color: #667eea;
            margin-bottom: 10px;
        }}
        
        header p {{
            color: #666;
            font-size: 14px;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
        }}
        
        .stat-label {{
            color: #999;
            font-size: 12px;
            text-transform: uppercase;
            margin-bottom: 10px;
        }}
        
        .stat-value {{
            font-size: 32px;
            font-weight: bold;
            color: #333;
        }}
        
        .stat-value.success {{
            color: #28a745;
        }}
        
        .stat-value.warning {{
            color: #ffc107;
        }}
        
        .stat-value.danger {{
            color: #dc3545;
        }}
        
        .recent-logs {{
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
        }}
        
        .logs-header {{
            background: #f8f9fa;
            padding: 20px;
            border-bottom: 1px solid #dee2e6;
        }}
        
        .logs-header h2 {{
            color: #333;
            font-size: 18px;
        }}
        
        .logs-table {{
            width: 100%;
            border-collapse: collapse;
        }}
        
        .logs-table th {{
            background: #f8f9fa;
            padding: 15px;
            text-align: left;
            font-weight: 600;
            color: #666;
            font-size: 12px;
            border-bottom: 2px solid #dee2e6;
        }}
        
        .logs-table td {{
            padding: 15px;
            border-bottom: 1px solid #dee2e6;
        }}
        
        .logs-table tr:hover {{
            background: #f8f9fa;
        }}
        
        .status-badge {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
        }}
        
        .status-completed {{
            background: #d4edda;
            color: #155724;
        }}
        
        .status-failed {{
            background: #f8d7da;
            color: #721c24;
        }}
        
        .status-pending {{
            background: #fff3cd;
            color: #856404;
        }}
        
        footer {{
            margin-top: 30px;
            text-align: center;
            color: white;
            font-size: 12px;
        }}
        
        .refresh-button {{
            background: #667eea;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
            margin-top: 10px;
        }}
        
        .refresh-button:hover {{
            background: #764ba2;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🚀 ManaOS Moltbot ダッシュボード</h1>
            <p>計画実行履歴・統計情報・監査ログの可視化</p>
            <p style="margin-top: 10px; color: #999;">更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </header>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">総計画実行数</div>
                <div class="stat-value">{stats['total_plans']}</div>
            </div>
            
            <div class="stat-card">
                <div class="stat-label">成功率</div>
                <div class="stat-value success">{stats['success_rate']:.1f}%</div>
            </div>
            
            <div class="stat-card">
                <div class="stat-label">成功/失敗</div>
                <div class="stat-value">{stats['success_count']} / {stats['failure_count']}</div>
            </div>
            
            <div class="stat-card">
                <div class="stat-label">平均実行時間</div>
                <div class="stat-value">{stats['avg_duration']:.2f}s</div>
            </div>
        </div>
        
        <div class="recent-logs">
            <div class="logs-header">
                <h2>📋 最近の計画実行 (直近 20件)</h2>
            </div>
            <table class="logs-table">
                <thead>
                    <tr>
                        <th>計画ID</th>
                        <th>状態</th>
                        <th>計画内容</th>
                        <th>実行時刻</th>
                        <th>実行時間</th>
                    </tr>
                </thead>
                <tbody>
"""

        # 最近のログを表示（最新20件）
        for log in logs[:20]:
            status = log.get("status", "unknown")
            status_class = f"status-{status}"
            
            html_content += f"""                    <tr>
                        <td><code>{log['plan_id']}</code></td>
                        <td><span class="status-badge {status_class}">{status}</span></td>
                        <td>{log['intent']}</td>
                        <td>{log.get('finished_at', 'N/A')}</td>
                        <td>{log['duration_seconds']:.2f}s</td>
                    </tr>
"""

        html_content += """                </tbody>
            </table>
        </div>
        
        <footer>
            <p>ManaOS Moltbot Gateway | 監査ログ統計ダッシュボード</p>
            <p style="margin-top: 10px;">このダッシュボードは自動生成されています</p>
        </footer>
    </div>
</body>
</html>
"""

        # ファイルに保存
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)

        return str(output_file)

    def print_statistics(self):
        """コンソールに統計情報を出力"""
        logs = self.get_all_audit_logs()
        stats = self.compute_statistics(logs)

        print('╔═══════════════════════════════════════════════════════════╗')
        print('║  📊 ManaOS Moltbot 監査ログ統計                           ║')
        print('╚═══════════════════════════════════════════════════════════╝')
        print()
        print(f"総計画実行数: {stats['total_plans']}")
        print(f"成功数: {stats['success_count']}")
        print(f"失敗数: {stats['failure_count']}")
        print(f"成功率: {stats['success_rate']:.1f}%")
        print()
        print(f"合計実行時間: {stats['total_duration']:.2f}秒")
        print(f"平均実行時間: {stats['avg_duration']:.2f}秒")
        print()
        print("ステータス別:")
        for status, count in stats['by_status'].items():
            print(f"  {status}: {count}")
        print()
        print("最近の実行:")
        for log in logs[:5]:
            print(f"  {log['plan_id']} ({log['status']}) - {log['intent'][:50]}")


def main():
    dashboard = MoltbotAuditDashboard()
    
    # 統計情報を表示
    dashboard.print_statistics()
    print()
    
    # HTML ダッシュボードを生成
    html_file = dashboard.generate_html_dashboard()
    print(f"✅ ダッシュボード作成完了: {html_file}")
    print()
    print("使用方法:")
    print(f"  1. ブラウザで以下を開く: {html_file}")
    print("  2. リアルタイムで統計情報・実行履歴を確認")
    print()
    print("定期更新:")
    print("  毎時間または毎日、このスクリプトを実行してダッシュボードを更新してください")


if __name__ == "__main__":
    main()
