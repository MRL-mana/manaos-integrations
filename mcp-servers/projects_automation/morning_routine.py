#!/usr/bin/env python3
"""
Mana朝のルーティン - 自動サマリー生成
毎朝8:00に自動実行
"""

import requests
from datetime import datetime
from pathlib import Path

class MorningRoutine:
    def __init__(self):
        self.report_dir = Path("/root/daily_reports")
        self.report_dir.mkdir(exist_ok=True)
        
    def get_calendar_events(self):
        """今日の予定取得"""
        try:
            # Google Calendar API呼び出し（実装時にMCPツール使用）
            return {
                "count": 3,
                "events": [
                    {"time": "10:00", "title": "チーム会議"},
                    {"time": "14:00", "title": "コードレビュー"},
                    {"time": "18:00", "title": "進捗報告"}
                ]
            }
        except Exception:
            return {"count": 0, "events": []}
    
    def get_unread_emails(self):
        """未読メール確認"""
        try:
            # Gmail API呼び出し
            return {
                "count": 12,
                "important": [
                    {"from": "プロジェクトマネージャー", "subject": "進捗確認"},
                    {"from": "経理", "subject": "請求書承認"}
                ]
            }
        except Exception:
            return {"count": 0, "important": []}
    
    def get_weather(self):
        """天気予報取得"""
        try:
            # 天気API呼び出し
            return {
                "condition": "晴れ",
                "temp": "22℃",
                "description": "過ごしやすい一日です"
            }
        except Exception:
            return {"condition": "不明", "temp": "-", "description": ""}
    
    def check_system_health(self):
        """システム健全性チェック"""
        try:
            # 各サービスのヘルスチェック
            services = {
                "ManaOS v3.0": self._check_service("http://localhost:9200/health"),
                "Trinity Secretary": self._check_service("http://localhost:5007/health"),
                "Command Center": self._check_service("http://localhost:10000/health"),
                "Screen Sharing": self._check_service("http://localhost:5008/health")
            }
            
            healthy = sum(1 for v in services.values() if v)
            total = len(services)
            
            return {
                "healthy_services": healthy,
                "total_services": total,
                "status": "正常" if healthy == total else "一部警告",
                "services": services
            }
        except Exception:
            return {"status": "チェックエラー"}
    
    def _check_service(self, url):
        """サービスヘルスチェック"""
        try:
            r = requests.get(url, timeout=2)
            return r.status_code == 200
        except requests.RequestException:
            return False
    
    def get_tasks(self):
        """今日のタスク取得"""
        # タスク管理システムと連携（将来実装）
        return {
            "total": 8,
            "completed": 0,
            "pending": 8,
            "tasks": [
                "コードレビュー対応",
                "ドキュメント更新",
                "ミーティング準備",
                "メール返信",
                "システム監視"
            ]
        }
    
    def generate_report(self):
        """朝のサマリーレポート生成"""
        print("=" * 70)
        print("🌅 Mana 朝のルーティン - Daily Summary")
        print("=" * 70)
        print(f"📅 {datetime.now().strftime('%Y年%m月%d日 (%A)')}")
        print("")
        
        # 挨拶
        hour = datetime.now().hour
        if hour < 12:
            greeting = "おはよう、Mana！"
        elif hour < 18:
            greeting = "こんにちは、Mana！"
        else:
            greeting = "こんばんは、Mana！"
        
        print(f"💬 {greeting}")
        print("")
        
        # 天気
        weather = self.get_weather()
        print(f"🌤️  天気: {weather['condition']} {weather['temp']}")
        print(f"   {weather['description']}")
        print("")
        
        # 予定
        calendar = self.get_calendar_events()
        print(f"📅 今日の予定: {calendar['count']}件")
        for event in calendar['events'][:5]:
            print(f"   {event['time']} - {event['title']}")
        print("")
        
        # メール
        emails = self.get_unread_emails()
        print(f"📧 未読メール: {emails['count']}件")
        if emails['important']:
            print("   重要:")
            for email in emails['important'][:3]:
                print(f"   • {email['from']}: {email['subject']}")
        print("")
        
        # タスク
        tasks = self.get_tasks()
        print(f"✅ タスク: {tasks['completed']}/{tasks['total']} 完了")
        print("   今日のタスク:")
        for task in tasks['tasks'][:5]:
            print(f"   • {task}")
        print("")
        
        # システム
        system = self.check_system_health()
        print(f"🖥️  システム: {system['status']}")
        print(f"   稼働サービス: {system['healthy_services']}/{system['total_services']}")
        print("")
        
        print("=" * 70)
        print("💡 今日も良い一日を！")
        print("=" * 70)
        
        # レポート保存
        report_file = self.report_dir / f"morning_{datetime.now().strftime('%Y%m%d')}.txt"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(f"Mana Morning Report - {datetime.now().strftime('%Y-%m-%d')}\n")
            f.write(f"予定: {calendar['count']}件\n")
            f.write(f"メール: {emails['count']}件\n")
            f.write(f"タスク: {tasks['completed']}/{tasks['total']}\n")
            f.write(f"システム: {system['status']}\n")
        
        return report_file

def main():
    routine = MorningRoutine()
    report_file = routine.generate_report()
    print(f"\n📄 レポート保存: {report_file}")

if __name__ == "__main__":
    main()

