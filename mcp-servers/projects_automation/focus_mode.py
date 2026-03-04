#!/usr/bin/env python3
"""
集中モードシステム
作業タイマー、通知停止、BGM、サマリー生成
"""

import time
from datetime import datetime, timedelta
from pathlib import Path
import json

class FocusMode:
    """集中モード"""
    
    def __init__(self):
        self.sessions_file = Path("/root/.focus_sessions.json")
        self.current_session = None
        
    def start_session(self, task_name, duration_minutes=25):
        """集中セッション開始（ポモドーロ）"""
        self.current_session = {
            "task": task_name,
            "start_time": datetime.now().isoformat(),
            "duration_minutes": duration_minutes,
            "end_time": (datetime.now() + timedelta(minutes=duration_minutes)).isoformat(),
            "interruptions": 0,
            "completed": False
        }
        
        print("🎯 集中モード開始")
        print(f"タスク: {task_name}")
        print(f"時間: {duration_minutes}分")
        print(f"終了予定: {datetime.now() + timedelta(minutes=duration_minutes):%H:%M}")
        print("")
        print("⏰ タイマー開始...")
        print("🔕 通知を一時停止")
        print("")
        
        return self.current_session
    
    def run_timer(self, duration_minutes):
        """タイマー実行"""
        end_time = datetime.now() + timedelta(minutes=duration_minutes)
        
        while datetime.now() < end_time:
            remaining = (end_time - datetime.now()).total_seconds()
            minutes = int(remaining // 60)
            seconds = int(remaining % 60)
            
            print(f"\r⏱️  残り時間: {minutes:02d}:{seconds:02d}", end='', flush=True)
            time.sleep(1)
        
        print("\n\n🎉 集中時間終了！")
        self._play_notification_sound()
    
    def end_session(self, completed=True):
        """セッション終了"""
        if not self.current_session:
            return
        
        self.current_session["completed"] = completed
        self.current_session["actual_end_time"] = datetime.now().isoformat()
        
        # セッション保存
        self._save_session(self.current_session)
        
        # サマリー生成
        summary = self._generate_summary(self.current_session)
        
        print("\n" + "="*60)
        print("📊 集中セッション完了")
        print("="*60)
        print(summary)
        
        self.current_session = None
        
        return summary
    
    def quick_focus(self, task_name, duration=25):
        """クイック集中モード（タイマーのみ）"""
        print(f"🎯 集中モード: {task_name} ({duration}分)\n")
        
        session = self.start_session(task_name, duration)
        
        # 短時間なら実行、長時間ならスキップ
        if duration <= 5:
            self.run_timer(duration)
            self.end_session(completed=True)
        else:
            print(f"⏰ {duration}分のタイマーを設定しました")
            print("🔕 通知停止中")
            print(f"📍 {datetime.now() + timedelta(minutes=duration):%H:%M} に終了予定")
        
        return session
    
    def get_stats(self):
        """集中セッション統計"""
        sessions = self._load_all_sessions()
        
        if not sessions:
            return {"total_sessions": 0, "total_time": 0}
        
        total_time = sum(s.get('duration_minutes', 0) for s in sessions)
        completed = len([s for s in sessions if s.get('completed')])
        
        return {
            "total_sessions": len(sessions),
            "completed_sessions": completed,
            "total_time_minutes": total_time,
            "average_duration": total_time / len(sessions) if sessions else 0
        }
    
    def _generate_summary(self, session):
        """サマリー生成"""
        start = datetime.fromisoformat(session["start_time"])
        end = datetime.fromisoformat(session["actual_end_time"])
        actual_duration = (end - start).total_seconds() / 60
        
        summary = f"""
タスク: {session['task']}
予定時間: {session['duration_minutes']}分
実際の時間: {actual_duration:.1f}分
完了状態: {'✅ 完了' if session['completed'] else '⏸️ 中断'}
中断回数: {session['interruptions']}回
"""
        return summary
    
    def _save_session(self, session):
        """セッション保存"""
        sessions = self._load_all_sessions()
        sessions.append(session)
        
        with open(self.sessions_file, 'w', encoding='utf-8') as f:
            json.dump(sessions, f, indent=2, ensure_ascii=False)
    
    def _load_all_sessions(self):
        """全セッション読み込み"""
        if self.sessions_file.exists():
            with open(self.sessions_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    
    def _play_notification_sound(self):
        """通知音再生"""
        print("🔔 ピンポーン！")

def main():
    focus = FocusMode()
    
    print("🎯 集中モードシステム\n")
    
    # クイックテスト（3分）
    focus.quick_focus("テストタスク", duration=3)
    
    # 統計表示
    stats = focus.get_stats()
    print("\n📊 統計:")
    print(f"  総セッション数: {stats['total_sessions']}")
    print(f"  総時間: {stats['total_time_minutes']}分")

if __name__ == "__main__":
    main()

