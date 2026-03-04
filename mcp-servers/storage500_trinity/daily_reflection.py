#!/usr/bin/env python3
"""
Daily Reflection System - 24時間自動振り返りシステム

各AIエージェントが24時間ごとに自動で振り返りを行い、
学習内容を整理・統合します。

機能:
- 24時間の活動サマリー生成
- 成功/失敗パターンの抽出
- 改善点の自動提案
- 学習目標の再設定
"""

import sys
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import schedule
import time
import threading

# Reflection Engineをインポート
workspace = Path("/root/trinity_workspace")
sys.path.insert(0, str(workspace / "bridge"))
from reflection_engine import ReflectionEngine


class DailyReflection:
    """24時間振り返りシステム"""
    
    def __init__(self, workspace_path: str = "/root/trinity_workspace"):
        self.workspace = Path(workspace_path)
        self.engine = ReflectionEngine(workspace_path)
        self.memory_dir = self.workspace / "shared" / "memory"
        self.evolution_dir = self.workspace / "evolution"
        
        # データベース
        self.db_path = self.workspace / "shared" / "daily_reflections.db"
        self.init_database()
        
        # エージェントリスト
        self.agents = ['remi', 'luna', 'mina', 'aria']
        
        # スケジューラー
        self.scheduler_running = False
        
    def init_database(self):
        """データベース初期化"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 日次振り返りテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_reflections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                agent TEXT NOT NULL,
                qsr_score REAL,
                actions_count INTEGER,
                success_rate REAL,
                top_patterns TEXT,
                improvements TEXT,
                goals_for_tomorrow TEXT,
                summary TEXT,
                created_at TEXT NOT NULL
            )
        """)
        
        # 学習目標テーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS learning_goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent TEXT NOT NULL,
                goal TEXT NOT NULL,
                target_metric TEXT,
                target_value REAL,
                current_value REAL,
                deadline TEXT,
                status TEXT DEFAULT 'active',
                created_at TEXT NOT NULL,
                completed_at TEXT
            )
        """)
        
        conn.commit()
        conn.close()
        
    def run_daily_reflection(self, agent: str) -> Dict:
        """特定エージェントの日次振り返りを実行"""
        print(f"\n{'='*60}")
        print(f"🔍 Daily Reflection: {agent.upper()}")
        print(f"{'='*60}")
        print(f"Date: {datetime.now().strftime('%Y-%m-%d')}")
        print()
        
        # 1. 過去24時間の活動分析
        analysis = self._analyze_24h_activity(agent)
        
        # 2. パターン抽出
        patterns = self._extract_patterns(agent)
        
        # 3. 改善提案生成
        improvements = self.engine.generate_improvements(agent, days=1)
        
        # 4. 明日の目標設定
        goals = self._set_tomorrow_goals(agent, analysis)
        
        # 5. サマリー生成
        summary = self._generate_summary(agent, analysis, patterns, improvements)
        
        # 6. データベースに保存
        reflection = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'agent': agent,
            'qsr_score': analysis['qsr_score'],
            'actions_count': analysis['actions_count'],
            'success_rate': analysis['success_rate'],
            'top_patterns': json.dumps(patterns),
            'improvements': json.dumps([imp['suggestion'] for imp in improvements[:3]]),
            'goals_for_tomorrow': json.dumps(goals),
            'summary': summary
        }
        
        self._save_reflection(reflection)
        
        # 7. ファイルに出力
        self._export_reflection(agent, reflection)
        
        # 表示
        self._print_reflection(agent, reflection, improvements)
        
        return reflection
        
    def _analyze_24h_activity(self, agent: str) -> Dict:
        """過去24時間の活動分析"""
        conn = sqlite3.connect(self.engine.db_path)
        cursor = conn.cursor()
        
        since = (datetime.now() - timedelta(days=1)).isoformat()
        
        # アクション数
        cursor.execute("""
            SELECT COUNT(*) FROM actions
            WHERE agent = ? AND timestamp > ?
        """, (agent, since))
        actions_count = cursor.fetchone()[0]
        
        # 成功率
        cursor.execute("""
            SELECT 
                COUNT(CASE WHEN o.success = 1 THEN 1 END) as successes,
                COUNT(*) as total
            FROM actions a
            JOIN outcomes o ON a.id = o.action_id
            WHERE a.agent = ? AND a.timestamp > ?
        """, (agent, since))
        
        row = cursor.fetchone()
        success_rate = (row[0] / row[1]) if row[1] > 0 else 0.0
        
        # QSRスコア
        qsr = self.engine.calculate_qsr(agent, days=1)
        
        conn.close()
        
        return {
            'actions_count': actions_count,
            'success_rate': success_rate,
            'qsr_score': qsr['qsr_score'],
            'reflection_confidence': qsr['reflection_confidence']
        }
        
    def _extract_patterns(self, agent: str) -> List[Dict]:
        """パターン抽出"""
        conn = sqlite3.connect(self.engine.db_path)
        cursor = conn.cursor()
        
        # 成功率が高いパターンを抽出
        cursor.execute("""
            SELECT pattern_type, success_rate, usage_count, confidence
            FROM learned_patterns
            WHERE agent = ? AND usage_count > 0
            ORDER BY success_rate DESC, usage_count DESC
            LIMIT 5
        """, (agent,))
        
        patterns = []
        for row in cursor.fetchall():
            patterns.append({
                'type': row[0],
                'success_rate': row[1],
                'usage_count': row[2],
                'confidence': row[3]
            })
            
        conn.close()
        return patterns
        
    def _set_tomorrow_goals(self, agent: str, analysis: Dict) -> List[str]:
        """明日の目標設定"""
        goals = []
        
        # QSRスコアに基づく目標
        current_qsr = analysis['qsr_score']
        if current_qsr < 0.7:
            target_qsr = min(current_qsr + 0.1, 0.9)
            goals.append(f"QSRスコアを{current_qsr:.3f}から{target_qsr:.3f}に向上")
            
            # データベースに記録
            self._save_goal(agent, f"Improve QSR to {target_qsr:.3f}", 
                          'qsr_score', target_qsr, current_qsr)
        
        # 成功率に基づく目標
        current_success = analysis['success_rate']
        if current_success < 0.9:
            target_success = min(current_success + 0.05, 0.95)
            goals.append(f"成功率を{current_success:.1%}から{target_success:.1%}に向上")
            
            self._save_goal(agent, f"Improve success rate to {target_success:.1%}",
                          'success_rate', target_success, current_success)
        
        # アクション数に基づく目標
        if analysis['actions_count'] < 5:
            goals.append("より多くのタスクに取り組む（目標: 5件以上）")
            self._save_goal(agent, "Execute 5+ tasks", 
                          'actions_count', 5, analysis['actions_count'])
        
        return goals
        
    def _save_goal(self, agent: str, goal: str, metric: str, 
                   target: float, current: float):
        """目標をデータベースに保存"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 明日の日付を期限に
        deadline = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        
        cursor.execute("""
            INSERT INTO learning_goals
            (agent, goal, target_metric, target_value, current_value, deadline, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (agent, goal, metric, target, current, deadline, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
    def _generate_summary(self, agent: str, analysis: Dict, 
                         patterns: List[Dict], improvements: List[Dict]) -> str:
        """サマリー生成"""
        summary = f"【{agent.upper()}の1日】\n\n"
        
        # 活動量
        summary += f"タスク実行数: {analysis['actions_count']}件\n"
        summary += f"成功率: {analysis['success_rate']:.1%}\n"
        summary += f"QSRスコア: {analysis['qsr_score']:.3f}\n\n"
        
        # 強み
        if patterns:
            summary += "【強み】\n"
            for i, p in enumerate(patterns[:3], 1):
                summary += f"  {i}. {p['type']} (成功率{p['success_rate']:.1%})\n"
            summary += "\n"
        
        # 改善点
        if improvements:
            summary += "【改善点】\n"
            for i, imp in enumerate(improvements[:3], 1):
                summary += f"  {i}. {imp['suggestion']}\n"
            summary += "\n"
        
        # 総評
        if analysis['qsr_score'] >= 0.8:
            summary += "総評: 優秀な1日でした。このペースを維持しましょう。"
        elif analysis['qsr_score'] >= 0.6:
            summary += "総評: 良い1日でした。さらなる向上を目指しましょう。"
        else:
            summary += "総評: 改善の余地があります。明日はより良い結果を目指しましょう。"
            
        return summary
        
    def _save_reflection(self, reflection: Dict):
        """振り返りをデータベースに保存"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO daily_reflections
            (date, agent, qsr_score, actions_count, success_rate, 
             top_patterns, improvements, goals_for_tomorrow, summary, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            reflection['date'],
            reflection['agent'],
            reflection['qsr_score'],
            reflection['actions_count'],
            reflection['success_rate'],
            reflection['top_patterns'],
            reflection['improvements'],
            reflection['goals_for_tomorrow'],
            reflection['summary'],
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
        
    def _export_reflection(self, agent: str, reflection: Dict):
        """振り返りをファイルに出力"""
        date_str = datetime.now().strftime('%Y%m%d')
        output_file = self.memory_dir / f"reflection_{agent}_{date_str}.json"
        
        export_data = {
            **reflection,
            'top_patterns': json.loads(reflection['top_patterns']),
            'improvements': json.loads(reflection['improvements']),
            'goals_for_tomorrow': json.loads(reflection['goals_for_tomorrow'])
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
            
    def _print_reflection(self, agent: str, reflection: Dict, improvements: List[Dict]):
        """振り返りを表示"""
        print("📊 Activity Summary:")
        print(f"  - Tasks: {reflection['actions_count']}")
        print(f"  - Success Rate: {reflection['success_rate']:.1%}")
        print(f"  - QSR Score: {reflection['qsr_score']:.3f}")
        print()
        
        if improvements:
            print("💡 Top Improvements:")
            for i, imp in enumerate(improvements[:3], 1):
                print(f"  {i}. {imp['suggestion']}")
            print()
        
        goals = json.loads(reflection['goals_for_tomorrow'])
        if goals:
            print("🎯 Goals for Tomorrow:")
            for i, goal in enumerate(goals, 1):
                print(f"  {i}. {goal}")
            print()
        
        print("📝 Summary:")
        print(reflection['summary'])
        print()
        
    def run_all_agents(self):
        """全エージェントの振り返りを実行"""
        print("\n" + "="*60)
        print("🌅 Daily Reflection - All Agents")
        print("="*60)
        print()
        
        results = {}
        for agent in self.agents:
            results[agent] = self.run_daily_reflection(agent)
            
        # 全体サマリー
        self._print_overall_summary(results)
        
        return results
        
    def _print_overall_summary(self, results: Dict):
        """全体サマリー表示"""
        print("\n" + "="*60)
        print("📈 Trinity System Daily Summary")
        print("="*60)
        
        avg_qsr = sum(r['qsr_score'] for r in results.values()) / len(results)
        avg_success = sum(r['success_rate'] for r in results.values()) / len(results)
        total_actions = sum(r['actions_count'] for r in results.values())
        
        print(f"Average QSR Score: {avg_qsr:.3f}")
        print(f"Average Success Rate: {avg_success:.1%}")
        print(f"Total Actions: {total_actions}")
        print("="*60)
        print()
        
    def start_scheduler(self, hour: int = 3, minute: int = 0):
        """スケジューラーを開始（デフォルト: 毎日午前3時）"""
        schedule.clear()
        schedule.every().day.at(f"{hour:02d}:{minute:02d}").do(self.run_all_agents)
        
        self.scheduler_running = True
        
        def run_schedule():
            while self.scheduler_running:
                schedule.run_pending()
                time.sleep(60)
                
        scheduler_thread = threading.Thread(target=run_schedule, daemon=True)
        scheduler_thread.start()
        
        print(f"✅ Daily reflection scheduled at {hour:02d}:{minute:02d}")
        
    def stop_scheduler(self):
        """スケジューラーを停止"""
        self.scheduler_running = False
        schedule.clear()
        print("⏹️  Scheduler stopped")


def main():
    """メイン関数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Daily Reflection System')
    parser.add_argument('--agent', choices=['remi', 'luna', 'mina', 'aria'],
                       help='Run reflection for specific agent')
    parser.add_argument('--all', action='store_true',
                       help='Run reflection for all agents')
    parser.add_argument('--schedule', action='store_true',
                       help='Start scheduler (runs at 3:00 AM daily)')
    
    args = parser.parse_args()
    
    reflector = DailyReflection()
    
    if args.schedule:
        reflector.start_scheduler()
        print("🌙 Running in background. Press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            reflector.stop_scheduler()
            print("\n👋 Goodbye!")
    elif args.all:
        reflector.run_all_agents()
    elif args.agent:
        reflector.run_daily_reflection(args.agent)
    else:
        print("Usage: python3 daily_reflection.py --all | --agent <name> | --schedule")
        return 1
        
    return 0


if __name__ == '__main__':
    sys.exit(main())



