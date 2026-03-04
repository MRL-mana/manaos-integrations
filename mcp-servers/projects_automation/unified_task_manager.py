#!/usr/bin/env python3
"""
統合タスク管理システム
予定・メール・タスクを1つに統合して優先順位付け
"""

from datetime import datetime, timedelta
import json
from pathlib import Path

class UnifiedTaskManager:
    """統合タスク管理"""
    
    def __init__(self):
        self.tasks_file = Path("/root/.mana_tasks.json")
        self.load_tasks()
        
    def load_tasks(self):
        """タスク読み込み"""
        if self.tasks_file.exists():
            with open(self.tasks_file, 'r', encoding='utf-8') as f:
                self.tasks = json.load(f)
        else:
            self.tasks = []
    
    def save_tasks(self):
        """タスク保存"""
        with open(self.tasks_file, 'w', encoding='utf-8') as f:
            json.dump(self.tasks, f, indent=2, ensure_ascii=False)
    
    def add_task(self, title, source="manual", deadline=None, priority=None, description=""):
        """タスク追加"""
        task = {
            "id": datetime.now().strftime("%Y%m%d%H%M%S"),
            "title": title,
            "source": source,  # calendar, email, manual
            "deadline": deadline,
            "priority": priority or self._calculate_priority(deadline),
            "status": "pending",
            "description": description,
            "created_at": datetime.now().isoformat(),
            "completed_at": None
        }
        
        self.tasks.append(task)
        self.save_tasks()
        
        return task
    
    def get_today_tasks(self):
        """今日のタスク取得"""
        today = datetime.now().date()
        
        today_tasks = []
        for task in self.tasks:
            if task['status'] == 'pending':
                # 期限が今日か、期限なしのタスク
                if task.get('deadline'):
                    deadline = datetime.fromisoformat(task['deadline']).date()
                    if deadline <= today:
                        today_tasks.append(task)
                else:
                    today_tasks.append(task)
        
        # 優先度でソート
        today_tasks.sort(key=lambda x: self._priority_score(x['priority']), reverse=True)
        
        return today_tasks
    
    def get_task_dashboard(self):
        """タスクダッシュボード生成"""
        today_tasks = self.get_today_tasks()
        
        # 優先度別に分類
        urgent = [t for t in today_tasks if t['priority'] == 'urgent']
        high = [t for t in today_tasks if t['priority'] == 'high']
        medium = [t for t in today_tasks if t['priority'] == 'medium']
        low = [t for t in today_tasks if t['priority'] == 'low']
        
        dashboard = f"""
╔══════════════════════════════════════════════════════════╗
║  📋 今日のタスクダッシュボード                             ║
║  {datetime.now().strftime('%Y年%m月%d日 (%A)')}                              ║
╚══════════════════════════════════════════════════════════╝

🔴 緊急（{len(urgent)}件）
"""
        for task in urgent[:3]:
            deadline_str = self._format_deadline(task.get('deadline'))
            dashboard += f"  • {task['title']} {deadline_str}\n"
        
        dashboard += f"""
🟡 重要（{len(high)}件）
"""
        for task in high[:3]:
            deadline_str = self._format_deadline(task.get('deadline'))
            dashboard += f"  • {task['title']} {deadline_str}\n"
        
        dashboard += f"""
🟢 通常（{len(medium)}件）
"""
        for task in medium[:3]:
            deadline_str = self._format_deadline(task.get('deadline'))
            dashboard += f"  • {task['title']} {deadline_str}\n"
        
        if low:
            dashboard += f"\n⚪ 低優先度（{len(low)}件）\n"
        
        # 統計
        total = len(today_tasks)
        completed_today = len([t for t in self.tasks if t['status'] == 'completed' 
                              and t.get('completed_at', '').startswith(datetime.now().strftime('%Y-%m-%d'))])
        
        dashboard += f"""
──────────────────────────────────────────────────────────
📊 統計: 今日のタスク {total}件 | 完了 {completed_today}件
💡 推定所要時間: {self._estimate_time(today_tasks)}
──────────────────────────────────────────────────────────
"""
        
        return dashboard
    
    def complete_task(self, task_id):
        """タスク完了"""
        for task in self.tasks:
            if task['id'] == task_id:
                task['status'] = 'completed'
                task['completed_at'] = datetime.now().isoformat()
                self.save_tasks()
                return True
        return False
    
    def _calculate_priority(self, deadline):
        """期限から優先度を計算"""
        if not deadline:
            return "medium"
        
        deadline_dt = datetime.fromisoformat(deadline) if isinstance(deadline, str) else deadline
        now = datetime.now()
        hours_left = (deadline_dt - now).total_seconds() / 3600
        
        if hours_left < 4:
            return "urgent"
        elif hours_left < 24:
            return "high"
        elif hours_left < 72:
            return "medium"
        else:
            return "low"
    
    def _priority_score(self, priority):
        """優先度スコア"""
        scores = {"urgent": 4, "high": 3, "medium": 2, "low": 1}
        return scores.get(priority, 0)
    
    def _format_deadline(self, deadline):
        """期限フォーマット"""
        if not deadline:
            return ""
        
        deadline_dt = datetime.fromisoformat(deadline) if isinstance(deadline, str) else deadline
        now = datetime.now()
        diff = deadline_dt - now
        
        if diff.days > 0:
            return f"(あと{diff.days}日)"
        elif diff.total_seconds() > 0:
            hours = int(diff.total_seconds() / 3600)
            return f"(あと{hours}時間)"
        else:
            return "(期限超過)"
    
    def _estimate_time(self, tasks):
        """所要時間推定"""
        # 簡易推定：タスク数 × 30分
        hours = len(tasks) * 0.5
        if hours < 1:
            return f"{int(hours * 60)}分"
        else:
            return f"{hours:.1f}時間"

def main():
    manager = UnifiedTaskManager()
    
    print("🚀 統合タスク管理システム テスト\n")
    
    # テストタスク追加
    manager.add_task(
        "メール返信",
        source="email",
        deadline=(datetime.now() + timedelta(hours=2)).isoformat(),
        description="プロジェクト進捗の返信"
    )
    
    manager.add_task(
        "会議準備",
        source="calendar",
        deadline=(datetime.now() + timedelta(hours=1)).isoformat(),
        description="資料とアジェンダ確認"
    )
    
    manager.add_task(
        "コードレビュー",
        source="manual",
        deadline=(datetime.now() + timedelta(days=1)).isoformat()
    )
    
    # ダッシュボード表示
    dashboard = manager.get_task_dashboard()
    print(dashboard)
    
    print("\n✅ テスト完了")
    print(f"📁 タスクファイル: {manager.tasks_file}")

if __name__ == "__main__":
    main()

