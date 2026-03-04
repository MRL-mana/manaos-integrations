#!/usr/bin/env python3
"""
作業分析システム
時間の使い方を可視化＆改善提案
"""

from datetime import datetime, timedelta
from pathlib import Path
import json

class WorkAnalytics:
    """作業分析"""
    
    def __init__(self):
        self.analytics_file = Path("/root/.work_analytics.json")
        self.activities = []
        self.load_analytics()
    
    def load_analytics(self):
        """分析データ読み込み"""
        if self.analytics_file.exists():
            with open(self.analytics_file, 'r', encoding='utf-8') as f:
                self.activities = json.load(f)
    
    def save_analytics(self):
        """分析データ保存"""
        with open(self.analytics_file, 'w', encoding='utf-8') as f:
            json.dump(self.activities, f, indent=2, ensure_ascii=False)
    
    def track_activity(self, activity_type, duration_minutes, description=""):
        """活動記録"""
        activity = {
            "timestamp": datetime.now().isoformat(),
            "type": activity_type,  # meeting, coding, email, break
            "duration": duration_minutes,
            "description": description,
            "hour": datetime.now().hour
        }
        
        self.activities.append(activity)
        self.save_analytics()
    
    def get_daily_summary(self, date=None):
        """日次サマリー"""
        if date is None:
            date = datetime.now().date()
        
        date_str = date.isoformat()
        day_activities = [a for a in self.activities if a["timestamp"].startswith(date_str)]
        
        # カテゴリ別集計
        summary = {}
        for activity in day_activities:
            atype = activity["type"]
            summary[atype] = summary.get(atype, 0) + activity["duration"]
        
        total_time = sum(summary.values())
        
        report = f"""
📊 {date.strftime('%Y年%m月%d日')} の作業分析

総作業時間: {total_time}分 ({total_time/60:.1f}時間)

カテゴリ別:
"""
        for atype, duration in sorted(summary.items(), key=lambda x: x[1], reverse=True):
            percentage = (duration / total_time * 100) if total_time > 0 else 0
            report += f"  {atype}: {duration}分 ({percentage:.1f}%)\n"
        
        # 生産性ピーク時間
        peak_hour = self._get_peak_hour(day_activities)
        report += f"\n💡 生産性ピーク: {peak_hour}時台"
        
        return report
    
    def get_weekly_summary(self):
        """週次サマリー"""
        today = datetime.now().date()
        week_start = today - timedelta(days=today.weekday())
        
        week_activities = [
            a for a in self.activities
            if datetime.fromisoformat(a["timestamp"]).date() >= week_start
        ]
        
        # 日別集計
        daily_totals = {}
        for activity in week_activities:
            day = datetime.fromisoformat(activity["timestamp"]).date()
            daily_totals[day] = daily_totals.get(day, 0) + activity["duration"]
        
        total_time = sum(daily_totals.values())
        avg_per_day = total_time / 7 if total_time > 0 else 0
        
        report = f"""
📊 今週の作業分析

総作業時間: {total_time}分 ({total_time/60:.1f}時間)
平均/日: {avg_per_day:.1f}分 ({avg_per_day/60:.1f}時間)

日別:
"""
        for day, duration in sorted(daily_totals.items()):
            report += f"  {day.strftime('%m/%d (%a)')}: {duration}分\n"
        
        # 改善提案
        report += "\n💡 改善提案:\n"
        report += self._generate_suggestions(week_activities)
        
        return report
    
    def _get_peak_hour(self, activities):
        """ピーク時間帯計算"""
        hour_totals = {}
        for activity in activities:
            hour = activity["hour"]
            hour_totals[hour] = hour_totals.get(hour, 0) + activity["duration"]
        
        if not hour_totals:
            return "データなし"
        
        peak_hour = max(hour_totals, key=hour_totals.get)
        return peak_hour
    
    def _generate_suggestions(self, activities):
        """改善提案生成"""
        suggestions = ""
        
        # 会議時間チェック
        meeting_time = sum(a["duration"] for a in activities if a["type"] == "meeting")
        total_time = sum(a["duration"] for a in activities)
        
        if total_time > 0 and meeting_time / total_time > 0.5:
            suggestions += "  • 会議時間が多いです（50%超）。効率化を検討してください。\n"
        
        # 作業の偏りチェック
        if len(set(a["type"] for a in activities)) < 3:
            suggestions += "  • 作業が偏っています。バランスを取りましょう。\n"
        
        if not suggestions:
            suggestions = "  • 良いバランスです！このペースを維持してください。\n"
        
        return suggestions

def main():
    analytics = WorkAnalytics()
    
    print("📊 作業分析システム\n")
    
    # テストデータ追加
    analytics.track_activity("meeting", 60, "チーム会議")
    analytics.track_activity("coding", 120, "機能実装")
    analytics.track_activity("email", 30, "メール処理")
    analytics.track_activity("break", 15, "休憩")
    
    # 日次サマリー
    print(analytics.get_daily_summary())
    
    print("\n✅ テスト完了")
    print(f"📁 分析データ: {analytics.analytics_file}")

if __name__ == "__main__":
    main()

