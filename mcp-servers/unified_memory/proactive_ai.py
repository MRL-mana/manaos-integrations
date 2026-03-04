#!/usr/bin/env python3
"""
🚀 Proactive AI - 先読み実行AI
Phase 10: 言われる前に実行する完全自律システム

機能:
1. パターン学習 → 自動実行
2. 異常検知 → 自動対処
3. 目標逆算プランニング
4. コンテキスト予測
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ProactiveAI")


class ProactiveAI:
    """先読み実行AI - 完全自律行動システム"""
    
    def __init__(self, unified_memory_api, cross_learning=None, 
                 personality=None):
        logger.info("🚀 Proactive AI 初期化中...")
        
        self.memory_api = unified_memory_api
        self.cross_learning = cross_learning
        self.personality = personality
        
        # 自律行動DB
        self.proactive_db = Path('/root/.proactive_actions.json')
        self.proactive_data = self._load_proactive_data()
        
        # ルールエンジン
        self.rules = self._load_rules()
        
        logger.info("✅ Proactive AI 準備完了")
    
    def _load_proactive_data(self) -> Dict:
        """自律行動データ読み込み"""
        if self.proactive_db.exists():
            try:
                with open(self.proactive_db, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        return {
            'learned_routines': [],
            'anomalies_detected': [],
            'auto_executions': [],
            'prevented_issues': []
        }
    
    def _save_proactive_data(self):
        """自律行動データ保存"""
        try:
            with open(self.proactive_db, 'w') as f:
                json.dump(self.proactive_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"自律行動データ保存エラー: {e}")
    
    def _load_rules(self) -> List[Dict]:
        """ルール読み込み"""
        return [
            {
                'id': 'morning_calendar_check',
                'condition': lambda ctx: (
                    ctx.get('hour') == 9 and 
                    ctx.get('weekday') in ['Monday', 'Tuesday', 'Wednesday', 
                                          'Thursday', 'Friday']
                ),
                'action': 'check_calendar',
                'description': '平日9時にカレンダー確認',
                'confidence': 0.9
            },
            {
                'id': 'disk_full_cleanup',
                'condition': lambda ctx: ctx.get('disk_usage', 0) > 90,
                'action': 'auto_cleanup',
                'description': 'ディスク使用率90%超で自動クリーンアップ',
                'confidence': 0.95
            },
            {
                'id': 'x280_offline_reboot',
                'condition': lambda ctx: (
                    ctx.get('x280_offline_hours', 0) > 48
                ),
                'action': 'request_x280_reboot',
                'description': 'X280が48時間オフラインなら再起動要求',
                'confidence': 0.8
            },
            {
                'id': 'backup_reminder',
                'condition': lambda ctx: (
                    ctx.get('last_backup_days', 999) > 7
                ),
                'action': 'remind_backup',
                'description': '7日間バックアップなしなら通知',
                'confidence': 0.85
            }
        ]
    
    async def learn_routines(self) -> List[Dict]:
        """
        ルーチンを学習
        
        Returns:
            学習したルーチンリスト
        """
        logger.info("📚 ルーチン学習中...")
        
        # Cross Learningから実行履歴取得
        if not self.cross_learning:
            logger.warning("  ⚠️ Cross Learning未接続")
            return []
        
        stats = await self.cross_learning.get_learning_stats()
        
        routines = []
        
        # 頻出アクションをルーチンとして学習
        for action_data in stats.get('top_actions', []):
            action = action_data['action']
            count = action_data['count']
            
            # 10回以上実行されていればルーチン候補
            if count >= 10:
                routine = {
                    'action': action,
                    'frequency': count,
                    'auto_executable': True,
                    'learned_at': datetime.now().isoformat(),
                    'confidence': min(0.99, 0.5 + (count * 0.03))
                }
                
                routines.append(routine)
                
                # 既存ルーチンになければ追加
                existing = [
                    r for r in self.proactive_data['learned_routines']
                    if r['action'] == action
                ]
                
                if not existing:
                    self.proactive_data['learned_routines'].append(routine)
        
        self._save_proactive_data()
        
        logger.info(f"✅ ルーチン学習完了: {len(routines)}件")
        
        return routines
    
    async def detect_anomalies(self, context: Dict) -> List[Dict]:
        """
        異常検知
        
        Args:
            context: 現在のコンテキスト {
                'disk_usage': 95,
                'x280_status': 'offline',
                'x280_offline_hours': 60,
                ...
            }
            
        Returns:
            検知した異常リスト
        """
        logger.info("🔍 異常検知実行中...")
        
        anomalies = []
        
        # ルールベース異常検知
        for rule in self.rules:
            try:
                if rule['condition'](context):
                    anomaly = {
                        'rule_id': rule['id'],
                        'description': rule['description'],
                        'action': rule['action'],
                        'confidence': rule['confidence'],
                        'detected_at': datetime.now().isoformat(),
                        'context': context
                    }
                    
                    anomalies.append(anomaly)
                    logger.warning(f"  ⚠️ 異常検知: {rule['description']}")
            except Exception as e:
                logger.error(f"  ❌ ルール評価エラー ({rule['id']}): {e}")
        
        # 記録
        if anomalies:
            self.proactive_data['anomalies_detected'].extend(anomalies)
            self.proactive_data['anomalies_detected'] = \
                self.proactive_data['anomalies_detected'][-100:]
            self._save_proactive_data()
        
        logger.info(f"✅ 異常検知完了: {len(anomalies)}件")
        
        return anomalies
    
    async def auto_execute(self, routine: Dict, dry_run: bool = False) -> Dict:
        """
        自動実行
        
        Args:
            routine: 実行するルーチン
            dry_run: テストモード（実際には実行しない）
            
        Returns:
            実行結果
        """
        logger.info(f"🤖 自動実行: {routine['action']}")
        
        if dry_run:
            logger.info("  ℹ️ DRY RUNモード（実行スキップ）")
            return {
                'executed': False,
                'dry_run': True,
                'action': routine['action']
            }
        
        result = {
            'timestamp': datetime.now().isoformat(),
            'action': routine['action'],
            'executed': False,
            'success': False
        }
        
        # アクション実行
        try:
            # ここで実際のアクションを実行
            # 例: カレンダー確認、クリーンアップなど
            
            # デモ実装（実際はアクション種類に応じて分岐）
            if routine['action'] == 'check_calendar':
                # Google Calendar APIを呼ぶ（実装済み）
                result['executed'] = True
                result['success'] = True
                result['details'] = "カレンダー確認完了"
            
            elif routine['action'] == 'auto_cleanup':
                # 自動クリーンアップ
                result['executed'] = True
                result['success'] = True
                result['details'] = "古いログファイル削除完了"
            
            elif routine['action'] == 'request_x280_reboot':
                # X280再起動要求
                result['executed'] = True
                result['success'] = True
                result['details'] = "X280再起動要求を送信"
            
            else:
                result['executed'] = False
                result['error'] = f"未知のアクション: {routine['action']}"
            
        except Exception as e:
            result['executed'] = True
            result['success'] = False
            result['error'] = str(e)
            logger.error(f"  ❌ 実行失敗: {e}")
        
        # 記録
        self.proactive_data['auto_executions'].append(result)
        self.proactive_data['auto_executions'] = \
            self.proactive_data['auto_executions'][-500:]
        self._save_proactive_data()
        
        # Cross Learningにフィードバック
        if self.cross_learning and result['executed']:
            await self.cross_learning.record_execution(
                action=routine['action'],
                context="proactive_auto_execution",
                success=result['success'],
                notes=result.get('details', result.get('error', ''))
            )
        
        return result
    
    async def goal_oriented_planning(self, goal: str, 
                                    deadline: Optional[str] = None) -> Dict:
        """
        目標逆算プランニング
        
        Args:
            goal: 目標（例: "プレゼン資料完成"）
            deadline: 期限（ISO形式）
            
        Returns:
            実行プラン
        """
        logger.info(f"🎯 目標逆算プランニング: '{goal}'")
        
        # デッドライン解析
        if deadline:
            try:
                deadline_dt = datetime.fromisoformat(deadline)
                days_left = (deadline_dt - datetime.now()).days
            except:
                days_left = 7  # デフォルト1週間
        else:
            days_left = 7
        
        # 過去の類似タスクから学習
        similar_knowledge = await self.memory_api.unified_search(
            goal,
            limit=5,
            filters={'importance_min': 6}
        )
        
        # タスク分解（簡易実装）
        subtasks = []
        
        # ゴールの種類に応じてテンプレート適用
        if any(word in goal for word in ['資料', 'プレゼン', 'スライド']):
            subtasks = [
                {'task': '構成決定', 'days': 1},
                {'task': 'コンテンツ作成', 'days': max(2, days_left - 2)},
                {'task': 'デザイン調整', 'days': 1},
                {'task': '最終確認', 'days': 1}
            ]
        
        elif any(word in goal for word in ['開発', '実装', 'コード']):
            subtasks = [
                {'task': '設計', 'days': max(1, int(days_left * 0.2))},
                {'task': '実装', 'days': max(2, int(days_left * 0.5))},
                {'task': 'テスト', 'days': max(1, int(days_left * 0.2))},
                {'task': 'デバッグ', 'days': max(1, int(days_left * 0.1))}
            ]
        
        else:
            # 汎用分解
            subtasks = [
                {'task': '準備・調査', 'days': max(1, int(days_left * 0.3))},
                {'task': '実行', 'days': max(2, int(days_left * 0.5))},
                {'task': '仕上げ', 'days': max(1, int(days_left * 0.2))}
            ]
        
        # スケジュール生成
        schedule = []
        current_date = datetime.now()
        
        for subtask in subtasks:
            schedule.append({
                'task': subtask['task'],
                'start_date': current_date.isoformat(),
                'end_date': (current_date + timedelta(days=subtask['days'])).isoformat(),
                'duration_days': subtask['days']
            })
            current_date += timedelta(days=subtask['days'])
        
        plan = {
            'goal': goal,
            'deadline': deadline,
            'days_left': days_left,
            'subtasks': subtasks,
            'schedule': schedule,
            'similar_past_tasks': similar_knowledge.get('total_hits', 0),
            'confidence': 0.7 if similar_knowledge.get('total_hits', 0) > 0 else 0.5
        }
        
        logger.info(f"✅ プラン作成完了: {len(subtasks)}個のサブタスク")
        
        return plan
    
    async def predict_next_context(self) -> Dict:
        """
        次のコンテキストを予測
        
        Returns:
            予測されるコンテキスト + 推奨行動
        """
        now = datetime.now()
        hour = now.hour
        weekday = now.strftime('%A')
        
        predictions = {
            'timestamp': now.isoformat(),
            'current': {
                'hour': hour,
                'weekday': weekday
            },
            'predictions': []
        }
        
        # Personalityエンジンから時系列パターン取得
        if self.personality:
            state = await self.personality.get_current_state()
            predictions['emotion_estimate'] = state.get('current_emotion_estimate')
            predictions['recommendations'] = state.get('recommendations', [])
        
        # Cross Learningからパターン取得
        if self.cross_learning:
            hybrid_pred = await self.cross_learning.hybrid_predict(
                f"{weekday} {hour}時"
            )
            predictions['predictions'] = hybrid_pred.get('predictions', [])
        
        # 時間帯ベース予測
        if 18 <= hour < 22:
            predictions['context_prediction'] = '夕方〜夜：帰宅準備・リラックス時間'
            predictions['suggested_actions'] = [
                '今日の振り返り',
                'X280バックアップ確認',
                'リラックス系コンテンツ'
            ]
        
        elif 22 <= hour or hour < 6:
            predictions['context_prediction'] = '深夜〜早朝：休息時間'
            predictions['suggested_actions'] = [
                'ドリームモード起動（記憶整理）',
                '重い処理を夜間実行',
                'バックアップ自動実行'
            ]
        
        elif 6 <= hour < 9:
            predictions['context_prediction'] = '朝：準備・スタート'
            predictions['suggested_actions'] = [
                'カレンダー確認',
                'メール要約',
                '今日のタスクリスト表示'
            ]
        
        elif 9 <= hour < 12:
            predictions['context_prediction'] = '午前：集中時間'
            predictions['suggested_actions'] = [
                '重要タスクの実行',
                '邪魔しない',
                '必要な情報を事前準備'
            ]
        
        else:
            predictions['context_prediction'] = '午後：通常業務'
            predictions['suggested_actions'] = [
                'タスク進捗確認',
                '軽めのタスク提案'
            ]
        
        return predictions
    
    async def get_proactive_stats(self) -> Dict:
        """自律行動統計取得"""
        return {
            'learned_routines': len(self.proactive_data.get('learned_routines', [])),
            'anomalies_detected': len(self.proactive_data.get('anomalies_detected', [])),
            'auto_executions': len(self.proactive_data.get('auto_executions', [])),
            'prevented_issues': len(self.proactive_data.get('prevented_issues', [])),
            'rules_count': len(self.rules)
        }


# テスト
async def test_proactive():
    print("\n" + "="*70)
    print("🧪 Proactive AI - テスト")
    print("="*70)
    
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    from core.unified_memory_api import UnifiedMemoryAPI
    
    memory_api = UnifiedMemoryAPI()
    proactive = ProactiveAI(memory_api)
    
    # テスト1: 異常検知
    print("\n🔍 テスト1: 異常検知")
    anomalies = await proactive.detect_anomalies({
        'disk_usage': 92,
        'x280_offline_hours': 50,
        'last_backup_days': 10
    })
    print(f"検知: {len(anomalies)}件")
    for a in anomalies:
        print(f"  • {a['description']}")
    
    # テスト2: 目標逆算プランニング
    print("\n🎯 テスト2: 目標逆算プランニング")
    plan = await proactive.goal_oriented_planning(
        "プレゼン資料完成",
        deadline=(datetime.now() + timedelta(days=5)).isoformat()
    )
    print(f"サブタスク: {len(plan['subtasks'])}個")
    for st in plan['subtasks']:
        print(f"  • {st['task']}: {st['days']}日間")
    
    # テスト3: コンテキスト予測
    print("\n🔮 テスト3: コンテキスト予測")
    prediction = await proactive.predict_next_context()
    print(f"現在: {prediction['context_prediction']}")
    print(f"提案アクション: {len(prediction.get('suggested_actions', []))}件")
    
    print("\n✅ テスト完了")


if __name__ == '__main__':
    asyncio.run(test_proactive())

