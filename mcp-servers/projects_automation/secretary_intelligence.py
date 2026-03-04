#!/usr/bin/env python3
"""
💼 Secretary Intelligence
高度秘書機能 - 先回り支援・スマート提案

機能:
- プロアクティブ支援（時間・感情・習慣ベース）
- スマートスケジューリング
- タスク自動分解
- 習慣トラッキング
- インテリジェント提案
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from collections import defaultdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SecretaryIntelligence:
    """高度秘書機能"""
    
    def __init__(self):
        # 習慣トラッキング
        self.habits = {
            'wake_up_time': None,
            'usual_work_start': None,
            'usual_lunch_time': None,
            'usual_work_end': None,
            'daily_review_done': False,
            'morning_briefing_done': False
        }
        
        # タスクパターン学習
        self.task_patterns = defaultdict(int)
        
        # 提案履歴
        self.suggestion_history = []
        
        logger.info("💼 Secretary Intelligence initialized")
    
    async def proactive_assistance(self, mana_context: Dict) -> List[Dict[str, Any]]:
        """
        先回り支援
        
        Args:
            mana_context: Manaの現在の状況
                {
                    'current_time': datetime,
                    'last_emotion': str,
                    'tasks': List[Dict],
                    'schedule': List[Dict],
                    'recent_activity': str
                }
        
        Returns:
            提案リスト
        """
        logger.info("💡 Generating proactive assistance...")
        
        suggestions = []
        now = mana_context.get('current_time', datetime.now())
        
        # 1. 時間ベースの提案
        time_suggestions = self._time_based_suggestions(now, mana_context)
        suggestions.extend(time_suggestions)
        
        # 2. タスク締切ベースの提案
        task_suggestions = self._task_deadline_suggestions(mana_context.get('tasks', []))
        suggestions.extend(task_suggestions)
        
        # 3. 感情ベースの提案
        emotion_suggestions = self._emotion_based_suggestions(
            mana_context.get('last_emotion', 'neutral')
        )
        suggestions.extend(emotion_suggestions)
        
        # 4. 習慣トラッキングの提案
        habit_suggestions = self._habit_tracking_suggestions(now, mana_context)
        suggestions.extend(habit_suggestions)
        
        # 5. インテリジェント提案
        smart_suggestions = self._intelligent_suggestions(mana_context)
        suggestions.extend(smart_suggestions)
        
        # 優先度でソート
        suggestions = sorted(suggestions, key=lambda x: x.get('priority', 5), reverse=True)
        
        logger.info(f"  ✅ Generated {len(suggestions)} suggestions")
        
        return suggestions
    
    def _time_based_suggestions(self, now: datetime, context: Dict) -> List[Dict]:
        """時間ベースの提案"""
        suggestions = []
        hour = now.hour
        
        # 朝の提案（6-10時）
        if 6 <= hour < 10:
            if not self.habits.get('morning_briefing_done'):
                suggestions.append({
                    'type': 'morning_briefing',
                    'priority': 9,
                    'message': '☀️ おはようございます！今日の予定とタスクを確認しましょうか？',
                    'actions': [
                        {'label': '予定確認', 'command': '/schedule'},
                        {'label': 'タスク確認', 'command': '/tasks'},
                        {'label': '今日の目標設定', 'command': '/goal'}
                    ]
                })
        
        # 昼休みの提案（12-13時）
        elif 12 <= hour < 13:
            suggestions.append({
                'type': 'lunch_break',
                'priority': 6,
                'message': '🍱 ランチタイムですね。午前中の作業お疲れ様でした！',
                'actions': [
                    {'label': '午後の予定確認', 'command': '/schedule afternoon'},
                    {'label': 'リフレッシュ', 'command': '/break'}
                ]
            })
        
        # 夕方の提案（17-19時）
        elif 17 <= hour < 19:
            if not self.habits.get('daily_review_done'):
                suggestions.append({
                    'type': 'daily_review',
                    'priority': 8,
                    'message': '📝 今日の振り返りをしましょうか？達成したことを記録すると明日の励みになります。',
                    'actions': [
                        {'label': '今日の振り返り', 'command': '/review'},
                        {'label': '達成リスト', 'command': '/achievements'},
                        {'label': '明日の準備', 'command': '/prepare_tomorrow'}
                    ]
                })
        
        # 夜の提案（21-24時）
        elif 21 <= hour < 24:
            suggestions.append({
                'type': 'evening_routine',
                'priority': 5,
                'message': '🌙 そろそろ一日の締めくくりですね。明日に備えて休息しましょう。',
                'actions': [
                    {'label': '明日の予定確認', 'command': '/schedule tomorrow'},
                    {'label': 'リラックスタイム', 'command': '/relax'}
                ]
            })
        
        return suggestions
    
    def _task_deadline_suggestions(self, tasks: List[Dict]) -> List[Dict]:
        """タスク締切ベースの提案"""
        suggestions = []
        now = datetime.now()
        
        for task in tasks:
            deadline = task.get('deadline')
            if not deadline:
                continue
            
            # 締切までの時間を計算
            if isinstance(deadline, str):
                try:
                    deadline = datetime.fromisoformat(deadline)
                except Exception:
                    continue
            
            time_until_deadline = deadline - now
            
            # 締切が24時間以内
            if timedelta(0) < time_until_deadline < timedelta(hours=24):
                suggestions.append({
                    'type': 'urgent_deadline',
                    'priority': 10,
                    'message': f'🔴 「{task.get("name", "タスク")}」の締切が近づいています（残り{int(time_until_deadline.total_seconds() / 3600)}時間）',
                    'actions': [
                        {'label': '今すぐやる', 'command': f'/start_task {task.get("id")}'},
                        {'label': '30分後にリマインド', 'command': f'/remind 30 {task.get("id")}'},
                        {'label': '締切延長を検討', 'command': f'/extend_deadline {task.get("id")}'}
                    ]
                })
            
            # 締切が3日以内
            elif timedelta(hours=24) < time_until_deadline < timedelta(days=3):
                suggestions.append({
                    'type': 'approaching_deadline',
                    'priority': 7,
                    'message': f'⚠️ 「{task.get("name", "タスク")}」の締切が近づいています（残り{time_until_deadline.days}日）',
                    'actions': [
                        {'label': 'スケジュールに組み込む', 'command': f'/schedule_task {task.get("id")}'},
                        {'label': 'タスク分解', 'command': f'/break_down {task.get("id")}'}
                    ]
                })
        
        return suggestions
    
    def _emotion_based_suggestions(self, emotion: str) -> List[Dict]:
        """感情ベースの提案"""
        suggestions = []
        
        if emotion == 'tired':
            suggestions.append({
                'type': 'wellness',
                'priority': 8,
                'message': '☕ お疲れのようですね。5分休憩しませんか？',
                'actions': [
                    {'label': '5分タイマー', 'command': '/timer 5'},
                    {'label': 'リラックス音楽', 'command': '/music relax'},
                    {'label': 'ストレッチ動画', 'command': '/stretch'}
                ]
            })
        
        elif emotion == 'worried':
            suggestions.append({
                'type': 'support',
                'priority': 7,
                'message': '😰 心配事があるようですね。一緒に整理しましょうか？',
                'actions': [
                    {'label': '問題を整理', 'command': '/organize_worries'},
                    {'label': '解決策を探す', 'command': '/find_solutions'},
                    {'label': 'リラックス法', 'command': '/relax_techniques'}
                ]
            })
        
        elif emotion == 'excited':
            suggestions.append({
                'type': 'momentum',
                'priority': 6,
                'message': '🎉 エネルギーに満ちていますね！この勢いで進めましょう！',
                'actions': [
                    {'label': '次のステップ', 'command': '/next_step'},
                    {'label': '計画を立てる', 'command': '/make_plan'},
                    {'label': 'チャレンジタスク', 'command': '/challenge_task'}
                ]
            })
        
        elif emotion == 'sad':
            suggestions.append({
                'type': 'comfort',
                'priority': 8,
                'message': '🤗 大変でしたね。無理せず、自分のペースで大丈夫ですよ。',
                'actions': [
                    {'label': '気分転換', 'command': '/distraction'},
                    {'label': '癒し動画', 'command': '/healing_video'},
                    {'label': '話を聞く', 'command': '/listen'}
                ]
            })
        
        return suggestions
    
    def _habit_tracking_suggestions(self, now: datetime, context: Dict) -> List[Dict]:
        """習慣トラッキングの提案"""
        suggestions = []
        
        # 日記の提案
        if not context.get('daily_log_done') and now.hour >= 21:
            suggestions.append({
                'type': 'habit',
                'priority': 6,
                'message': '📔 今日の3行日記を書きましょうか？',
                'actions': [
                    {'label': '今日の3行日記', 'command': '/journal_3lines'},
                    {'label': '達成したこと', 'command': '/achievements'},
                    {'label': '感謝リスト', 'command': '/gratitude'}
                ]
            })
        
        # 運動の提案
        if not context.get('exercise_done') and now.hour in [7, 12, 18]:
            suggestions.append({
                'type': 'wellness',
                'priority': 5,
                'message': '🏃 軽く体を動かしませんか？リフレッシュになりますよ。',
                'actions': [
                    {'label': '5分ストレッチ', 'command': '/exercise stretch'},
                    {'label': '散歩タイム', 'command': '/exercise walk'},
                    {'label': 'スキップ', 'command': '/skip_exercise'}
                ]
            })
        
        # 水分補給の提案（2時間ごと）
        if now.hour % 2 == 0 and now.minute < 10:
            suggestions.append({
                'type': 'health',
                'priority': 4,
                'message': '💧 水分補給の時間です。コップ一杯の水を飲みましょう。',
                'actions': [
                    {'label': '飲んだ', 'command': '/log_water'},
                    {'label': '後で', 'command': '/remind_water 30'}
                ]
            })
        
        return suggestions
    
    def _intelligent_suggestions(self, context: Dict) -> List[Dict]:
        """インテリジェント提案"""
        suggestions = []
        
        # 繰り返しタスクの検出
        if self._detect_repetitive_task(context):
            suggestions.append({
                'type': 'automation',
                'priority': 7,
                'message': '🤖 この作業、繰り返していますね。自動化できるかもしれません！',
                'actions': [
                    {'label': '自動化を検討', 'command': '/automate'},
                    {'label': 'テンプレート作成', 'command': '/create_template'},
                    {'label': '後で考える', 'command': '/skip'}
                ]
            })
        
        # 集中時間の提案
        tasks = context.get('tasks', [])
        urgent_tasks = [t for t in tasks if t.get('priority', 0) >= 8]
        
        if urgent_tasks and not context.get('focus_session_today'):
            suggestions.append({
                'type': 'productivity',
                'priority': 8,
                'message': '⏰ 集中タイム（ポモドーロ）で効率アップしませんか？',
                'actions': [
                    {'label': '25分集中', 'command': '/pomodoro 25'},
                    {'label': '50分集中', 'command': '/pomodoro 50'},
                    {'label': 'カスタム', 'command': '/pomodoro_custom'}
                ]
            })
        
        return suggestions
    
    def _detect_repetitive_task(self, context: Dict) -> bool:
        """繰り返しタスクを検出"""
        recent_activity = context.get('recent_activity', '')
        
        # 簡易的な検出（同じキーワードが頻出）
        self.task_patterns[recent_activity] += 1
        
        # 3回以上繰り返されたら提案
        return self.task_patterns[recent_activity] >= 3
    
    async def smart_scheduling(self, task: Dict, existing_schedule: List[Dict]) -> Dict[str, Any]:
        """
        スマートスケジューリング
        
        最適な時間帯を提案
        """
        logger.info(f"📅 Smart scheduling for: {task.get('name', 'task')}")
        
        task_name = task.get('name', '')
        estimated_duration = task.get('estimated_duration', 60)  # 分
        priority = task.get('priority', 5)
        
        # 1. 既存の予定との兼ね合いを確認
        available_slots = self._find_available_slots(existing_schedule, estimated_duration)
        
        # 2. タスクの種類に応じた最適時間帯
        optimal_time = self._get_optimal_time_for_task(task_name)
        
        # 3. 推奨スロット
        recommended_slots = []
        
        for slot in available_slots:
            score = 0
            
            # 最適時間帯に近い
            if optimal_time and abs(slot['start_hour'] - optimal_time) < 2:
                score += 10
            
            # 優先度が高ければ早い時間帯
            if priority >= 8 and slot['start_hour'] < 12:
                score += 5
            
            # バッファ時間がある
            if slot['duration'] > estimated_duration + 30:
                score += 3
            
            recommended_slots.append({
                'slot': slot,
                'score': score
            })
        
        # スコア順にソート
        recommended_slots = sorted(recommended_slots, key=lambda x: x['score'], reverse=True)
        
        result = {
            'task': task,
            'recommended_slots': [s['slot'] for s in recommended_slots[:3]],
            'optimal_time': optimal_time,
            'estimated_duration': estimated_duration
        }
        
        logger.info(f"  ✅ Found {len(result['recommended_slots'])} recommended slots")
        
        return result
    
    def _find_available_slots(self, schedule: List[Dict], duration: int) -> List[Dict]:
        """利用可能なスロットを検索"""
        available_slots = []
        
        # 作業時間帯（9-22時）
        work_hours = range(9, 22)
        
        for hour in work_hours:
            # 既存の予定と重複しないか確認
            slot_start = datetime.now().replace(hour=hour, minute=0, second=0)
            slot_end = slot_start + timedelta(minutes=duration)
            
            conflict = False
            for event in schedule:
                event_start = event.get('start')
                event_end = event.get('end')
                
                if isinstance(event_start, str):
                    event_start = datetime.fromisoformat(event_start)
                if isinstance(event_end, str):
                    event_end = datetime.fromisoformat(event_end)
                
                if not (slot_end <= event_start or slot_start >= event_end):
                    conflict = True
                    break
            
            if not conflict:
                available_slots.append({
                    'start': slot_start.isoformat(),
                    'start_hour': hour,
                    'duration': duration
                })
        
        return available_slots
    
    def _get_optimal_time_for_task(self, task_name: str) -> Optional[int]:
        """タスクの種類に応じた最適時間帯"""
        task_lower = task_name.lower()
        
        # 創造的な作業 → 午前中
        if any(kw in task_lower for kw in ['企画', 'アイデア', '創造', 'デザイン', '執筆']):
            return 10
        
        # ルーチン作業 → 午後
        if any(kw in task_lower for kw in ['メール', '整理', 'チェック', '確認']):
            return 14
        
        # 集中作業 → 午前中または夕方
        if any(kw in task_lower for kw in ['プログラミング', '分析', '勉強', '学習']):
            return 10
        
        # 会議・コミュニケーション → 午後
        if any(kw in task_lower for kw in ['会議', 'ミーティング', '打ち合わせ', '相談']):
            return 15
        
        return None
    
    async def intelligent_task_breakdown(self, big_task: str) -> List[Dict]:
        """タスクを自動分解"""
        logger.info(f"🔨 Breaking down task: {big_task}")
        
        subtasks = []
        
        # タスクの種類を判定
        if 'プレゼン' in big_task or '発表' in big_task:
            subtasks = [
                {'name': '目標・テーマ決定', 'estimated_duration': 30},
                {'name': '資料収集', 'estimated_duration': 60},
                {'name': 'アウトライン作成', 'estimated_duration': 45},
                {'name': 'スライド作成', 'estimated_duration': 120},
                {'name': '原稿作成', 'estimated_duration': 60},
                {'name': 'リハーサル', 'estimated_duration': 30}
            ]
        
        elif 'レポート' in big_task or '報告書' in big_task:
            subtasks = [
                {'name': 'テーマ決定', 'estimated_duration': 20},
                {'name': '情報収集', 'estimated_duration': 90},
                {'name': 'アウトライン作成', 'estimated_duration': 30},
                {'name': '執筆', 'estimated_duration': 180},
                {'name': '校正・推敲', 'estimated_duration': 60}
            ]
        
        elif 'プロジェクト' in big_task:
            subtasks = [
                {'name': 'プロジェクト計画', 'estimated_duration': 60},
                {'name': 'タスク分解', 'estimated_duration': 30},
                {'name': 'スケジュール作成', 'estimated_duration': 45},
                {'name': 'リソース確認', 'estimated_duration': 30},
                {'name': 'キックオフ', 'estimated_duration': 60}
            ]
        
        else:
            # 汎用的な分解
            subtasks = [
                {'name': f'{big_task} - 準備', 'estimated_duration': 30},
                {'name': f'{big_task} - 実行', 'estimated_duration': 90},
                {'name': f'{big_task} - 確認', 'estimated_duration': 30}
            ]
        
        logger.info(f"  ✅ Broke down into {len(subtasks)} subtasks")
        
        return subtasks


# テスト用
async def test_secretary():
    """秘書機能のテスト"""
    secretary = SecretaryIntelligence()
    
    print("\n" + "="*60)
    print("Secretary Intelligence - Test")
    print("="*60)
    
    # テスト1: プロアクティブ支援
    print("\n💡 Test 1: Proactive assistance")
    context = {
        'current_time': datetime.now().replace(hour=9, minute=0),
        'last_emotion': 'neutral',
        'tasks': [
            {
                'name': 'プレゼン資料作成',
                'deadline': (datetime.now() + timedelta(hours=6)).isoformat(),
                'priority': 9
            }
        ],
        'schedule': []
    }
    
    suggestions = await secretary.proactive_assistance(context)
    print(f"✅ Generated {len(suggestions)} suggestions:")
    for i, sug in enumerate(suggestions[:3], 1):
        print(f"  {i}. [{sug['type']}] {sug['message']}")
    
    # テスト2: タスク分解
    print("\n🔨 Test 2: Task breakdown")
    subtasks = await secretary.intelligent_task_breakdown("プロジェクトプレゼン準備")
    print(f"✅ Broke down into {len(subtasks)} subtasks:")
    for i, task in enumerate(subtasks, 1):
        print(f"  {i}. {task['name']} ({task['estimated_duration']}分)")


if __name__ == '__main__':
    import asyncio
    asyncio.run(test_secretary())

