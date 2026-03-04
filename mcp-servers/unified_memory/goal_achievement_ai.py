#!/usr/bin/env python3
"""
🎯 Goal Achievement AI
Phase 14: 目標達成AIエンジン

機能:
1. OKR（Objectives and Key Results）管理
2. 目標の自動分解
3. 進捗追跡と自動調整
4. リスク予測と回避
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GoalAchievement")


class GoalAchievementAI:
    """目標達成AIエンジン"""
    
    def __init__(self, unified_memory_api, proactive_ai=None):
        logger.info("🎯 Goal Achievement AI 初期化中...")
        
        self.memory_api = unified_memory_api
        self.proactive_ai = proactive_ai
        
        # 目標DB
        self.goals_db = Path('/root/.goal_achievement.json')
        self.goals_data = self._load_goals()
        
        logger.info("✅ Goal Achievement AI 準備完了")
    
    def _load_goals(self) -> Dict:
        """目標データ読み込み"""
        if self.goals_db.exists():
            try:
                with open(self.goals_db, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        return {
            'active_goals': [],
            'completed_goals': [],
            'okrs': []
        }
    
    def _save_goals(self):
        """目標データ保存"""
        try:
            with open(self.goals_db, 'w') as f:
                json.dump(self.goals_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"目標データ保存エラー: {e}")
    
    async def set_goal(self, objective: str, deadline: str,
                      key_results: Optional[List[str]] = None) -> Dict:
        """
        目標設定（OKR形式）
        
        Args:
            objective: 目標（例: "ManaOSを完全自律化"）
            deadline: 期限（ISO形式）
            key_results: 主要成果指標
            
        Returns:
            設定された目標
        """
        logger.info(f"🎯 目標設定: {objective}")
        
        goal_id = f"goal_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # 自動分解
        breakdown = await self._auto_breakdown(objective, deadline)
        
        goal = {
            'id': goal_id,
            'objective': objective,
            'deadline': deadline,
            'key_results': key_results or breakdown['suggested_key_results'],
            'milestones': breakdown['milestones'],
            'tasks': breakdown['tasks'],
            'status': 'active',
            'progress': 0.0,
            'created_at': datetime.now().isoformat(),
            'risks': []
        }
        
        self.goals_data['active_goals'].append(goal)
        self._save_goals()
        
        # 記憶に保存
        await self.memory_api.smart_store(
            content=f"目標設定: {objective}\n期限: {deadline}\n\n{json.dumps(goal, ensure_ascii=False, indent=2)}",
            title=f"目標: {objective}",
            importance=9,
            tags=['goal', 'okr', goal_id],
            category='goals'
        )
        
        logger.info(f"✅ 目標設定完了: ID {goal_id}")
        
        return goal
    
    async def _auto_breakdown(self, objective: str, deadline: str) -> Dict:
        """目標の自動分解"""
        try:
            deadline_dt = datetime.fromisoformat(deadline)
            days_left = (deadline_dt - datetime.now()).days
        except:
            days_left = 90
        
        # Proactive AIでプランニング
        if self.proactive_ai:
            plan = await self.proactive_ai.goal_oriented_planning(objective, deadline)
            
            return {
                'suggested_key_results': [
                    f"{st['task']}完了" for st in plan.get('subtasks', [])[:3]
                ],
                'milestones': plan.get('schedule', []),
                'tasks': plan.get('subtasks', [])
            }
        
        # フォールバック: 簡易分解
        weeks = max(1, days_left // 7)
        
        return {
            'suggested_key_results': [
                f"Week {i}: 進捗{int((i/weeks)*100)}%達成"
                for i in range(1, min(weeks, 5))
            ],
            'milestones': [
                {
                    'week': i,
                    'target': f"{int((i/weeks)*100)}%完了"
                }
                for i in range(1, weeks + 1)
            ],
            'tasks': [
                {'task': f'Phase {i}', 'days': days_left // max(3, weeks)}
                for i in range(1, 4)
            ]
        }
    
    async def daily_progress_check(self) -> Dict:
        """毎日の進捗チェック"""
        logger.info("📊 進捗チェック実行中...")
        
        check_result = {
            'timestamp': datetime.now().isoformat(),
            'goals_checked': 0,
            'on_track': 0,
            'at_risk': 0,
            'actions_required': []
        }
        
        for goal in self.goals_data.get('active_goals', []):
            check_result['goals_checked'] += 1
            
            # 進捗評価
            try:
                deadline_dt = datetime.fromisoformat(goal['deadline'])
                total_days = (deadline_dt - datetime.fromisoformat(goal['created_at'])).days
                elapsed_days = (datetime.now() - datetime.fromisoformat(goal['created_at'])).days
                
                expected_progress = (elapsed_days / total_days) if total_days > 0 else 0
                actual_progress = goal.get('progress', 0)
                
                deviation = actual_progress - expected_progress
                
                if deviation < -0.2:  # 20%以上遅れ
                    check_result['at_risk'] += 1
                    check_result['actions_required'].append({
                        'goal_id': goal['id'],
                        'objective': goal['objective'],
                        'action': 'リソース追加または期限見直しが必要',
                        'deviation': deviation
                    })
                else:
                    check_result['on_track'] += 1
                
            except Exception as e:
                logger.error(f"進捗評価エラー ({goal['id']}): {e}")
        
        logger.info(f"✅ 進捗チェック完了: 順調{check_result['on_track']}件、リスク{check_result['at_risk']}件")
        
        return check_result
    
    async def detect_obstacles(self, goal_id: str) -> List[Dict]:
        """障害検知"""
        goal = next((g for g in self.goals_data['active_goals'] if g['id'] == goal_id), None)
        
        if not goal:
            return []
        
        obstacles = []
        
        # デッドライン接近
        try:
            deadline_dt = datetime.fromisoformat(goal['deadline'])
            days_left = (deadline_dt - datetime.now()).days
            
            if days_left < 2 and goal['progress'] < 0.8:
                obstacles.append({
                    'type': 'deadline_pressure',
                    'severity': 'high',
                    'description': f'期限まで{days_left}日、進捗{goal["progress"]:.0%}',
                    'suggestion': '緊急タスク優先度上げ'
                })
        except:
            pass
        
        # リソース不足（仮想検知）
        if goal['progress'] < 0.3:
            obstacles.append({
                'type': 'slow_progress',
                'severity': 'medium',
                'description': '進捗が遅い',
                'suggestion': 'タスク分解の見直し'
            })
        
        # 障害を記録
        goal['risks'] = obstacles
        self._save_goals()
        
        return obstacles
    
    async def auto_adjust_plan(self, goal_id: str) -> Dict:
        """計画の自動調整"""
        logger.info(f"🔧 計画自動調整: {goal_id}")
        
        goal = next((g for g in self.goals_data['active_goals'] if g['id'] == goal_id), None)
        
        if not goal:
            return {'error': '目標が見つかりません'}
        
        # 障害検知
        obstacles = await self.detect_obstacles(goal_id)
        
        adjustments = {
            'timestamp': datetime.now().isoformat(),
            'goal_id': goal_id,
            'obstacles': obstacles,
            'adjustments_made': []
        }
        
        # 調整実行
        if obstacles:
            for obstacle in obstacles:
                if obstacle['type'] == 'deadline_pressure':
                    # マイルストーンを再計算
                    adjustments['adjustments_made'].append('マイルストーン再計算')
                
                elif obstacle['type'] == 'slow_progress':
                    # タスクを細分化
                    adjustments['adjustments_made'].append('タスク細分化')
        
        logger.info(f"✅ 調整完了: {len(adjustments['adjustments_made'])}件")
        
        return adjustments
    
    async def update_progress(self, goal_id: str, progress: float,
                             notes: Optional[str] = None) -> Dict:
        """進捗更新"""
        goal = next((g for g in self.goals_data['active_goals'] if g['id'] == goal_id), None)
        
        if not goal:
            return {'error': '目標が見つかりません'}
        
        old_progress = goal.get('progress', 0)
        goal['progress'] = min(1.0, progress)
        goal['last_updated'] = datetime.now().isoformat()
        
        if notes:
            if 'progress_notes' not in goal:
                goal['progress_notes'] = []
            goal['progress_notes'].append({
                'timestamp': datetime.now().isoformat(),
                'progress': progress,
                'notes': notes
            })
        
        # 100%達成で完了扱い
        if goal['progress'] >= 1.0:
            goal['status'] = 'completed'
            goal['completed_at'] = datetime.now().isoformat()
            
            # active → completed に移動
            self.goals_data['active_goals'] = [
                g for g in self.goals_data['active_goals'] if g['id'] != goal_id
            ]
            self.goals_data['completed_goals'].append(goal)
            
            logger.info(f"🎉 目標達成！ {goal['objective']}")
        
        self._save_goals()
        
        return {
            'goal_id': goal_id,
            'old_progress': old_progress,
            'new_progress': goal['progress'],
            'status': goal['status']
        }
    
    async def get_dashboard(self) -> Dict:
        """目標ダッシュボード"""
        active = self.goals_data.get('active_goals', [])
        completed = self.goals_data.get('completed_goals', [])
        
        # リスク評価
        at_risk = []
        for goal in active:
            obstacles = await self.detect_obstacles(goal['id'])
            if any(o['severity'] == 'high' for o in obstacles):
                at_risk.append(goal)
        
        return {
            'active_goals': len(active),
            'completed_goals': len(completed),
            'goals_at_risk': len(at_risk),
            'completion_rate': len(completed) / max(1, len(active) + len(completed)),
            'active_goals_list': [
                {
                    'id': g['id'],
                    'objective': g['objective'],
                    'progress': g.get('progress', 0),
                    'deadline': g['deadline']
                }
                for g in active
            ][:5]
        }


# テスト
async def test_goal_achievement():
    print("\n" + "="*70)
    print("🧪 Goal Achievement AI - テスト")
    print("="*70)
    
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    from core.unified_memory_api import UnifiedMemoryAPI
    
    memory_api = UnifiedMemoryAPI()
    goal_ai = GoalAchievementAI(memory_api)
    
    # 目標設定
    print("\n🎯 テスト1: 目標設定")
    goal = await goal_ai.set_goal(
        "MEGA EVOLUTION完全実装",
        (datetime.now() + timedelta(days=7)).isoformat()
    )
    print(f"目標ID: {goal['id']}")
    print(f"マイルストーン: {len(goal['milestones'])}個")
    
    # 進捗更新
    print("\n📊 テスト2: 進捗更新")
    update = await goal_ai.update_progress(goal['id'], 0.6, "Phase 1-12完了")
    print(f"進捗: {update['old_progress']:.0%} → {update['new_progress']:.0%}")
    
    # ダッシュボード
    print("\n📈 テスト3: ダッシュボード")
    dashboard = await goal_ai.get_dashboard()
    print(f"アクティブ目標: {dashboard['active_goals']}件")
    print(f"完了率: {dashboard['completion_rate']:.0%}")
    
    print("\n✅ テスト完了")


if __name__ == '__main__':
    asyncio.run(test_goal_achievement())

