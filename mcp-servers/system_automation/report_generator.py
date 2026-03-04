#!/usr/bin/env python3
"""
レポート生成システム
システム状態、メトリクス、統計のレポート生成
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ReportGenerator:
    """レポート生成システム"""
    
    def __init__(self, base_path: str = "/root"):
        self.base_path = Path(base_path)
        self.reports_path = self.base_path / "reports"
        self.reports_path.mkdir(exist_ok=True)
        
    def generate_daily_report(self) -> Dict:
        """日次レポート生成"""
        logger.info("📊 日次レポート生成中...")
        
        report = {
            "type": "daily",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "timestamp": datetime.now().isoformat(),
            "sections": {}
        }
        
        # システムメトリクス
        report["sections"]["metrics"] = self.get_system_metrics()
        
        # ファイル整理統計
        report["sections"]["file_organization"] = self.get_file_organization_stats()
        
        # メンテナンス履歴
        report["sections"]["maintenance"] = self.get_maintenance_history()
        
        # アラート統計
        report["sections"]["alerts"] = self.get_alert_stats()
        
        # ディスク使用状況
        report["sections"]["disk"] = self.get_disk_usage()
        
        # レポート保存
        report_path = self.reports_path / f"daily_report_{report['date']}.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ 日次レポート生成完了: {report_path}")
        
        return report
    
    def generate_weekly_report(self) -> Dict:
        """週次レポート生成"""
        logger.info("📊 週次レポート生成中...")
        
        report = {
            "type": "weekly",
            "week": datetime.now().strftime("%Y-W%U"),
            "timestamp": datetime.now().isoformat(),
            "sections": {}
        }
        
        # 週間統計
        report["sections"]["summary"] = self.get_weekly_summary()
        
        # トレンド分析
        report["sections"]["trends"] = self.get_trends()
        
        # パフォーマンス分析
        report["sections"]["performance"] = self.get_performance_analysis()
        
        # レポート保存
        report_path = self.reports_path / f"weekly_report_{report['week']}.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ 週次レポート生成完了: {report_path}")
        
        return report
    
    def generate_monthly_report(self) -> Dict:
        """月次レポート生成"""
        logger.info("📊 月次レポート生成中...")
        
        report = {
            "type": "monthly",
            "month": datetime.now().strftime("%Y-%m"),
            "timestamp": datetime.now().isoformat(),
            "sections": {}
        }
        
        # 月間統計
        report["sections"]["summary"] = self.get_monthly_summary()
        
        # 長期的トレンド
        report["sections"]["long_term_trends"] = self.get_long_term_trends()
        
        # 推奨事項
        report["sections"]["recommendations"] = self.get_recommendations()
        
        # レポート保存
        report_path = self.reports_path / f"monthly_report_{report['month']}.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ 月次レポート生成完了: {report_path}")
        
        return report
    
    def get_system_metrics(self) -> Dict:
        """システムメトリクス取得"""
        try:
            metrics_path = self.base_path / ".monitor_metrics.json"
            if metrics_path.exists():
                with open(metrics_path, 'r', encoding='utf-8') as f:
                    metrics = json.load(f)
                    return metrics.get("latest", {})
        except Exception as e:
            logger.error(f"メトリクス取得エラー: {e}")
        return {}
    
    def get_file_organization_stats(self) -> Dict:
        """ファイル整理統計取得"""
        try:
            stats_path = self.base_path / ".file_organizer_stats.json"
            if stats_path.exists():
                with open(stats_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"統計取得エラー: {e}")
        return {}
    
    def get_maintenance_history(self) -> Dict:
        """メンテナンス履歴取得"""
        try:
            log_path = self.base_path / "logs" / "maintenance.log"
            if log_path.exists():
                with open(log_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    return {
                        "total_lines": len(lines),
                        "recent": lines[-20:] if len(lines) > 20 else lines
                    }
        except Exception as e:
            logger.error(f"履歴取得エラー: {e}")
        return {}
    
    def get_alert_stats(self) -> Dict:
        """アラート統計取得"""
        try:
            alerts_path = self.base_path / ".monitor_alerts.json"
            if alerts_path.exists():
                with open(alerts_path, 'r', encoding='utf-8') as f:
                    alerts = json.load(f)
                    
                    # 24時間以内のアラート
                    now = datetime.now()
                    recent_alerts = [
                        a for a in alerts
                        if datetime.fromisoformat(a["timestamp"]) > now - timedelta(hours=24)
                    ]
                    
                    return {
                        "total": len(alerts),
                        "last_24h": len(recent_alerts),
                        "by_level": self._count_by_level(recent_alerts),
                        "by_type": self._count_by_type(recent_alerts)
                    }
        except Exception as e:
            logger.error(f"アラート統計取得エラー: {e}")
        return {}
    
    def _count_by_level(self, alerts: List) -> Dict:
        """レベル別カウント"""
        counts = {}
        for alert in alerts:
            level = alert.get("level", "UNKNOWN")
            counts[level] = counts.get(level, 0) + 1
        return counts
    
    def _count_by_type(self, alerts: List) -> Dict:
        """タイプ別カウント"""
        counts = {}
        for alert in alerts:
            type_ = alert.get("type", "UNKNOWN")
            counts[type_] = counts.get(type_, 0) + 1
        return counts
    
    def get_disk_usage(self) -> Dict:
        """ディスク使用状況取得"""
        try:
            import psutil
            disk = psutil.disk_usage(self.base_path)
            
            return {
                "total_gb": round(disk.total / (1024**3), 2),
                "used_gb": round(disk.used / (1024**3), 2),
                "free_gb": round(disk.free / (1024**3), 2),
                "percent": disk.percent
            }
        except Exception as e:
            logger.error(f"ディスク使用状況取得エラー: {e}")
        return {}
    
    def get_weekly_summary(self) -> Dict:
        """週間サマリー取得"""
        # 過去7日分の日次レポートを集計
        reports = []
        for i in range(7):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            report_path = self.reports_path / f"daily_report_{date}.json"
            
            if report_path.exists():
                try:
                    with open(report_path, 'r', encoding='utf-8') as f:
                        reports.append(json.load(f))
                except IOError:
                    pass
        
        return {
            "days_analyzed": len(reports),
            "total_alerts": sum(
                len(r.get("sections", {}).get("alerts", {}).get("last_24h", []))
                for r in reports
            ),
            "average_disk_usage": self._calculate_average(reports, "disk", "percent"),
            "total_files_organized": sum(
                r.get("sections", {}).get("file_organization", {}).get("total_files_organized", 0)
                for r in reports
            )
        }
    
    def get_monthly_summary(self) -> Dict:
        """月間サマリー取得"""
        # 過去30日分の日次レポートを集計
        reports = []
        for i in range(30):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            report_path = self.reports_path / f"daily_report_{date}.json"
            
            if report_path.exists():
                try:
                    with open(report_path, 'r', encoding='utf-8') as f:
                        reports.append(json.load(f))
                except IOError:
                    pass
        
        return {
            "days_analyzed": len(reports),
            "total_alerts": sum(
                len(r.get("sections", {}).get("alerts", {}).get("last_24h", []))
                for r in reports
            ),
            "average_disk_usage": self._calculate_average(reports, "disk", "percent"),
            "total_files_organized": sum(
                r.get("sections", {}).get("file_organization", {}).get("total_files_organized", 0)
                for r in reports
            )
        }
    
    def _calculate_average(self, reports: List, section: str, key: str) -> float:
        """平均値計算"""
        values = [
            r.get("sections", {}).get(section, {}).get(key, 0)
            for r in reports
            if r.get("sections", {}).get(section, {}).get(key) is not None
        ]
        return sum(values) / len(values) if values else 0
    
    def get_trends(self) -> Dict:
        """トレンド分析"""
        # 過去7日分のデータでトレンドを分析
        trends = {
            "disk_usage": "stable",
            "alert_frequency": "stable",
            "performance": "stable"
        }
        
        # TODO: 実際のトレンド分析ロジックを実装
        
        return trends
    
    def get_performance_analysis(self) -> Dict:
        """パフォーマンス分析"""
        return {
            "cpu_avg": 0,
            "memory_avg": 0,
            "disk_avg": 0,
            "recommendations": []
        }
    
    def get_long_term_trends(self) -> Dict:
        """長期的トレンド"""
        return {
            "disk_growth": "stable",
            "alert_trend": "decreasing",
            "performance_trend": "improving"
        }
    
    def get_recommendations(self) -> List[str]:
        """推奨事項"""
        recommendations = []
        
        # ディスク使用率チェック
        disk = self.get_disk_usage()
        if disk.get("percent", 0) > 80:
            recommendations.append("ディスク使用率が高いです。不要なファイルを削除してください。")
        
        # アラートチェック
        alerts = self.get_alert_stats()
        if alerts.get("last_24h", 0) > 10:
            recommendations.append("多数のアラートが発生しています。システムを確認してください。")
        
        return recommendations
    
    def generate_html_report(self, report: Dict) -> str:
        """HTML形式のレポート生成"""
        html = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ManaOS レポート - {report.get('date', report.get('month', 'Unknown'))}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #667eea;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #333;
            margin-top: 30px;
        }}
        .metric {{
            display: inline-block;
            background: #f8f9fa;
            padding: 15px 20px;
            margin: 10px;
            border-radius: 5px;
            border-left: 4px solid #667eea;
        }}
        .metric-label {{
            font-size: 0.9em;
            color: #666;
        }}
        .metric-value {{
            font-size: 1.5em;
            font-weight: bold;
            color: #333;
        }}
        .recommendation {{
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 15px;
            margin: 10px 0;
            border-radius: 5px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 ManaOS システムレポート</h1>
        <p><strong>日付:</strong> {report.get('date', report.get('month', 'Unknown'))}</p>
        <p><strong>生成時刻:</strong> {report.get('timestamp', 'Unknown')}</p>
        
        <h2>📈 システムメトリクス</h2>
        <div class="metric">
            <div class="metric-label">CPU使用率</div>
            <div class="metric-value">{report.get('sections', {}).get('metrics', {}).get('cpu', {}).get('cpu_percent', 0):.1f}%</div>
        </div>
        <div class="metric">
            <div class="metric-label">メモリ使用率</div>
            <div class="metric-value">{report.get('sections', {}).get('metrics', {}).get('memory', {}).get('memory_percent', 0):.1f}%</div>
        </div>
        <div class="metric">
            <div class="metric-label">ディスク使用率</div>
            <div class="metric-value">{report.get('sections', {}).get('disk', {}).get('percent', 0):.1f}%</div>
        </div>
        
        <h2>⚠️ アラート統計</h2>
        <p>過去24時間: <strong>{report.get('sections', {}).get('alerts', {}).get('last_24h', 0)}</strong>件</p>
        
        <h2>💡 推奨事項</h2>
        {''.join(f'<div class="recommendation">{rec}</div>' for rec in report.get('sections', {}).get('recommendations', []))}
    </div>
</body>
</html>
        """
        
        return html


def main():
    """メイン実行"""
    generator = ReportGenerator()
    
    print("=" * 60)
    print("📊 レポート生成システム")
    print("=" * 60)
    
    print("\n生成するレポートを選択:")
    print("  1. 日次レポート")
    print("  2. 週次レポート")
    print("  3. 月次レポート")
    print("  4. 全て生成")
    print("  0. 終了")
    
    choice = input("\n選択 (0-4): ").strip()
    
    if choice == "1":
        print("\n📊 日次レポート生成中...")
        report = generator.generate_daily_report()
        print(f"✅ 生成完了: {report['date']}")
        
        # HTMLレポートも生成
        html = generator.generate_html_report(report)
        html_path = generator.reports_path / f"daily_report_{report['date']}.html"
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"✅ HTMLレポート生成: {html_path}")
    
    elif choice == "2":
        print("\n📊 週次レポート生成中...")
        report = generator.generate_weekly_report()
        print(f"✅ 生成完了: {report['week']}")
    
    elif choice == "3":
        print("\n📊 月次レポート生成中...")
        report = generator.generate_monthly_report()
        print(f"✅ 生成完了: {report['month']}")
    
    elif choice == "4":
        print("\n📊 全レポート生成中...")
        generator.generate_daily_report()
        generator.generate_weekly_report()
        generator.generate_monthly_report()
        print("✅ 全レポート生成完了")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()

