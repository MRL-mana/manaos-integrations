#!/usr/bin/env python3
"""
🧬 Self-Evolution Memory Engine
Phase 3: 自己進化メモリ - 使うほど賢くなる

機能:
1. 行動追跡システム
2. 忘却曲線実装（重要度×アクセス頻度）
3. 自動復習・再学習
4. メモリ最適化
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List
from pathlib import Path
import json
import math

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SelfEvolution")


class SelfEvolutionMemory:
    """自己進化メモリエンジン"""
    
    def __init__(self, unified_memory_api):
        logger.info("🧬 Self-Evolution Memory Engine 初期化中...")
        
        self.memory_api = unified_memory_api
        
        # 行動追跡DB
        self.action_tracking_db = Path('/root/.action_tracking.json')
        self.action_data = self._load_action_data()
        
        # 忘却曲線パラメータ
        self.forgetting_curve = {
            'decay_rate': 0.5,  # 減衰率
            'review_boost': 0.3,  # 復習時の強化率
            'importance_weight': 2.0  # 重要度の重み
        }
        
        logger.info("✅ Self-Evolution Memory Engine 準備完了")
    
    def _load_action_data(self) -> Dict:
        """行動データ読み込み"""
        if self.action_tracking_db.exists():
            try:
                with open(self.action_tracking_db, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        return {
            'actions': [],
            'memory_access': {},
            'review_schedule': []
        }
    
    def _save_action_data(self):
        """行動データ保存"""
        try:
            with open(self.action_tracking_db, 'w') as f:
                json.dump(self.action_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"行動データ保存エラー: {e}")
    
    async def track_action(self, action: str, context: Dict = None,  # type: ignore
                          success: bool = True) -> Dict:
        """
        行動追跡
        
        Args:
            action: 実行したアクション
            context: コンテキスト情報
            success: 成功したか
            
        Returns:
            追跡結果 + 学習提案
        """
        logger.info(f"📍 行動追跡: {action}")
        
        tracked = {
            'timestamp': datetime.now().isoformat(),
            'action': action,
            'context': context or {},
            'success': success,
            'frequency': 1
        }
        
        # 同じアクションの頻度カウント
        similar_actions = [
            a for a in self.action_data['actions']
            if a['action'] == action
        ]
        
        if similar_actions:
            tracked['frequency'] = len(similar_actions) + 1
        
        self.action_data['actions'].append(tracked)
        
        # 最新10,000件のみ保持
        self.action_data['actions'] = self.action_data['actions'][-10000:]
        
        self._save_action_data()
        
        # パターン分析
        pattern = self._analyze_pattern(action)
        
        # 学習提案
        suggestions = await self._generate_learning_suggestions(action, pattern)
        
        return {
            'tracked': True,
            'frequency': tracked['frequency'],
            'pattern': pattern,
            'suggestions': suggestions
        }
    
    def _analyze_pattern(self, action: str) -> Dict:
        """パターン分析"""
        actions = [
            a for a in self.action_data['actions']
            if a['action'] == action
        ]
        
        if not actions:
            return {'pattern': 'new', 'confidence': 0.1}
        
        # 時間帯パターン
        hours = []
        for a in actions:
            try:
                dt = datetime.fromisoformat(a['timestamp'])
                hours.append(dt.hour)
            except:
                pass
        
        most_common_hour = max(set(hours), key=hours.count) if hours else None
        
        # 成功率
        successes = len([a for a in actions if a.get('success')])
        success_rate = successes / len(actions) if actions else 0
        
        # パターン判定
        if len(actions) >= 10:
            pattern_type = 'routine'
            confidence = min(0.95, 0.5 + (len(actions) * 0.05))
        elif len(actions) >= 3:
            pattern_type = 'emerging'
            confidence = 0.6
        else:
            pattern_type = 'occasional'
            confidence = 0.3
        
        return {
            'pattern': pattern_type,
            'confidence': confidence,
            'frequency': len(actions),
            'success_rate': success_rate,
            'typical_hour': most_common_hour
        }
    
    async def _generate_learning_suggestions(self, action: str, 
                                            pattern: Dict) -> List[str]:
        """学習提案生成"""
        suggestions = []
        
        # ルーチン化の提案
        if pattern['pattern'] == 'routine' and pattern['typical_hour']:
            suggestions.append(
                f"「{action}」は{pattern['typical_hour']}時頃によく実行されます。"
                f"自動実行を提案しますか？"
            )
        
        # 成功率改善の提案
        if pattern['success_rate'] < 0.8 and pattern['frequency'] >= 5:
            suggestions.append(
                f"「{action}」の成功率が{pattern['success_rate']:.1%}です。"
                f"実行方法の改善を学習しましょうか？"
            )
        
        # 頻度に応じた最適化提案
        if pattern['frequency'] >= 20:
            suggestions.append(
                f"「{action}」は{pattern['frequency']}回実行されています。"
                f"ショートカットやマクロ化を検討しませんか？"
            )
        
        return suggestions
    
    async def calculate_memory_retention(self, memory_id: int, 
                                        importance: int,
                                        last_access: str,
                                        access_count: int) -> Dict:
        """
        忘却曲線に基づく記憶保持率計算
        
        エビングハウスの忘却曲線: R(t) = e^(-t/S)
        S = 重要度 × アクセス頻度
        
        Args:
            memory_id: 記憶ID
            importance: 重要度 (1-10)
            last_access: 最終アクセス日時
            access_count: アクセス回数
            
        Returns:
            保持率 + 復習推奨
        """
        try:
            last_access_dt = datetime.fromisoformat(last_access)
        except:
            last_access_dt = datetime.now() - timedelta(days=365)
        
        # 経過時間（日数）
        days_elapsed = (datetime.now() - last_access_dt).days
        
        # 記憶強度 S = 重要度 × log(アクセス回数 + 1)
        memory_strength = importance * math.log(access_count + 1)
        
        # 忘却曲線: R(t) = e^(-t/S)
        retention = math.exp(-days_elapsed / max(1, memory_strength))
        
        # 復習推奨判定
        should_review = retention < 0.5 and importance >= 6
        
        # 次回復習推奨時期
        if should_review:
            # 記憶が弱まっているので早めに
            next_review_days = max(1, int(memory_strength * 0.5))
        else:
            # 記憶が強いので少し先でOK
            next_review_days = max(3, int(memory_strength * 1.5))
        
        return {
            'memory_id': memory_id,
            'retention': round(retention, 3),
            'memory_strength': round(memory_strength, 2),
            'should_review': should_review,
            'next_review_date': (
                datetime.now() + timedelta(days=next_review_days)
            ).isoformat(),
            'priority': 'high' if retention < 0.3 and importance >= 7 else 'normal'
        }
    
    async def generate_review_schedule(self) -> List[Dict]:
        """
        自動復習スケジュール生成
        
        Returns:
            復習すべき記憶のリスト
        """
        logger.info("📅 復習スケジュール生成中...")
        
        # 全記憶の統計取得
        stats = await self.memory_api.get_stats(force_refresh=True)
        
        review_list = []
        
        # AI Learning Systemから復習候補を抽出
        # （本来はベクトルDB全体をスキャンするが、簡易実装）
        
        # アクセス履歴から復習候補を生成
        for memory_id, access_data in self.action_data.get('memory_access', {}).items():
            retention_data = await self.calculate_memory_retention(
                memory_id=int(memory_id),
                importance=access_data.get('importance', 5),
                last_access=access_data.get('last_access', 
                                           (datetime.now() - timedelta(days=30)).isoformat()),
                access_count=access_data.get('count', 1)
            )
            
            if retention_data['should_review']:
                review_list.append(retention_data)
        
        # 優先度順にソート
        review_list.sort(
            key=lambda x: (
                x['priority'] == 'high',
                -x['retention']
            ),
            reverse=True
        )
        
        logger.info(f"✅ 復習推奨: {len(review_list)}件")
        
        return review_list
    
    async def optimize_memory(self) -> Dict:
        """
        メモリ最適化
        
        機能:
        1. 古くて重要度低い記憶をアーカイブ
        2. 重複記憶の統合
        3. アクセス頻度の低い記憶の削減
        
        Returns:
            最適化結果
        """
        logger.info("🔧 メモリ最適化開始...")
        
        result = {
            'timestamp': datetime.now().isoformat(),
            'archived': 0,
            'merged': 0,
            'optimized': 0
        }
        
        # アクション履歴の古いデータを削除
        cutoff_date = (datetime.now() - timedelta(days=180)).isoformat()
        
        old_actions = [
            a for a in self.action_data['actions']
            if a['timestamp'] < cutoff_date and not a.get('success')
        ]
        
        # 失敗した古い記録のみ削除
        self.action_data['actions'] = [
            a for a in self.action_data['actions']
            if a not in old_actions
        ]
        
        result['archived'] = len(old_actions)
        
        self._save_action_data()
        
        logger.info(f"✅ 最適化完了: {result['archived']}件アーカイブ")
        
        return result
    
    async def get_evolution_stats(self) -> Dict:
        """進化統計取得"""
        actions = self.action_data.get('actions', [])
        
        # 最近30日のアクション
        recent_threshold = (datetime.now() - timedelta(days=30)).isoformat()
        recent_actions = [a for a in actions if a['timestamp'] >= recent_threshold]
        
        # パターン分類
        patterns = {
            'routine': 0,
            'emerging': 0,
            'occasional': 0
        }
        
        # ユニークアクション
        unique_actions = set(a['action'] for a in actions)
        
        for action in unique_actions:
            pattern = self._analyze_pattern(action)
            patterns[pattern['pattern']] = patterns.get(pattern['pattern'], 0) + 1
        
        return {
            'total_actions_tracked': len(actions),
            'recent_30days': len(recent_actions),
            'unique_actions': len(unique_actions),
            'patterns': patterns,
            'most_frequent': self._get_most_frequent_actions(5)
        }
    
    def _get_most_frequent_actions(self, limit: int = 5) -> List[Dict]:
        """最頻出アクション取得"""
        action_counts = {}
        
        for action in self.action_data.get('actions', []):
            action_name = action['action']
            action_counts[action_name] = action_counts.get(action_name, 0) + 1
        
        sorted_actions = sorted(
            action_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:limit]
        
        return [
            {'action': action, 'count': count}
            for action, count in sorted_actions
        ]


# テスト
async def test_self_evolution():
    print("\n" + "="*70)
    print("🧪 Self-Evolution Memory Engine - テスト")
    print("="*70)
    
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    from core.unified_memory_api import UnifiedMemoryAPI
    
    memory_api = UnifiedMemoryAPI()
    evolution = SelfEvolutionMemory(memory_api)
    
    # テスト1: 行動追跡
    print("\n📍 テスト1: 行動追跡")
    result = await evolution.track_action("カレンダー確認", {"time": "朝9時"}, True)
    print(f"頻度: {result['frequency']}回")
    print(f"パターン: {result['pattern']['pattern']}")
    print(f"提案: {len(result['suggestions'])}件")
    
    # テスト2: 忘却曲線
    print("\n🧠 テスト2: 忘却曲線計算")
    retention = await evolution.calculate_memory_retention(
        memory_id=1,
        importance=8,
        last_access=(datetime.now() - timedelta(days=7)).isoformat(),
        access_count=5
    )
    print(f"保持率: {retention['retention']:.1%}")
    print(f"復習推奨: {'はい' if retention['should_review'] else 'いいえ'}")
    
    # テスト3: 進化統計
    print("\n📊 テスト3: 進化統計")
    stats = await evolution.get_evolution_stats()
    print(f"総追跡数: {stats['total_actions_tracked']}件")
    print(f"ユニークアクション: {stats['unique_actions']}個")
    
    print("\n✅ テスト完了")


if __name__ == '__main__':
    asyncio.run(test_self_evolution())

