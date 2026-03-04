#!/usr/bin/env python3
"""
⚡ Realtime Learning System
リアルタイム学習システム

機能:
1. 使うたびに即座に学習
2. パターン即時認識
3. 好み即座反映
4. リアルタイム最適化
"""

import asyncio
import logging
from typing import Dict, List
from pathlib import Path
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RealtimeLearning")


class RealtimeLearning:
    """リアルタイム学習システム"""
    
    def __init__(self, unified_memory_api):
        logger.info("⚡ Realtime Learning 初期化中...")
        
        self.memory_api = unified_memory_api
        
        # リアルタイム学習DB
        self.rt_db = Path('/root/unified_memory_system/data/realtime_learning.json')
        self.rt_data = self._load_rt_data()
        
        # 学習カウンター
        self.learning_events = 0
        
        logger.info("✅ Realtime Learning 準備完了")
    
    def _load_rt_data(self) -> Dict:
        """データ読み込み"""
        if self.rt_db.exists():
            try:
                with open(self.rt_db, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        return {
            'patterns': {},
            'preferences': {},
            'optimization_history': []
        }
    
    def _save_rt_data(self):
        """データ保存"""
        try:
            self.rt_db.parent.mkdir(exist_ok=True, parents=True)
            with open(self.rt_db, 'w') as f:
                json.dump(self.rt_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"データ保存エラー: {e}")
    
    async def learn_from_interaction(self, interaction: Dict) -> Dict:
        """
        インタラクションから即座に学習
        
        Args:
            interaction: {
                'action': '実行したアクション',
                'context': '状況',
                'result': '結果',
                'user_reaction': 'positive/negative/neutral'
            }
            
        Returns:
            学習結果
        """
        logger.info(f"⚡ リアルタイム学習: {interaction.get('action', 'unknown')}")
        
        self.learning_events += 1
        
        action = interaction.get('action', '')
        context = interaction.get('context', '')
        user_reaction = interaction.get('user_reaction', 'neutral')
        
        # パターン学習
        pattern_key = f"{context}:{action}"
        
        if pattern_key not in self.rt_data['patterns']:
            self.rt_data['patterns'][pattern_key] = {
                'count': 0,
                'positive_reactions': 0,
                'negative_reactions': 0
            }
        
        self.rt_data['patterns'][pattern_key]['count'] += 1
        
        if user_reaction == 'positive':
            self.rt_data['patterns'][pattern_key]['positive_reactions'] += 1
        elif user_reaction == 'negative':
            self.rt_data['patterns'][pattern_key]['negative_reactions'] += 1
        
        # 好み学習
        if user_reaction == 'positive':
            # 成功パターンを好みとして記録
            if action not in self.rt_data['preferences']:
                self.rt_data['preferences'][action] = {'score': 0}
            
            self.rt_data['preferences'][action]['score'] += 1
        
        # 保存
        self._save_rt_data()
        
        # 統合記憶にも保存
        if user_reaction == 'positive':
            await self.memory_api.smart_store(
                content=f"成功パターン: {context} → {action}\nユーザー反応: {user_reaction}",
                title=f"学習: {action}",
                importance=8,
                tags=['realtime_learning', 'success_pattern', context],
                category='realtime_success'
            )
        
        learning_result = {
            'learned': True,
            'pattern': pattern_key,
            'total_occurrences': self.rt_data['patterns'][pattern_key]['count'],
            'confidence': self._calculate_confidence(pattern_key)
        }
        
        logger.info(f"  ✅ 学習完了（信頼度: {learning_result['confidence']:.0%}）")
        
        return learning_result
    
    def _calculate_confidence(self, pattern_key: str) -> float:
        """信頼度計算"""
        pattern = self.rt_data['patterns'].get(pattern_key, {})
        
        total = pattern.get('count', 0)
        positive = pattern.get('positive_reactions', 0)
        negative = pattern.get('negative_reactions', 0)
        
        if total == 0:
            return 0.5
        
        # 成功率ベース
        success_rate = positive / total if total > 0 else 0
        
        # 頻度ボーナス（よく使うほど信頼度アップ）
        frequency_bonus = min(0.3, total * 0.05)
        
        confidence = min(0.99, success_rate + frequency_bonus)
        
        return confidence
    
    async def get_top_preferences(self, limit: int = 10) -> List[Dict]:
        """トップ好みを取得"""
        prefs = self.rt_data.get('preferences', {})
        
        sorted_prefs = sorted(
            prefs.items(),
            key=lambda x: x[1]['score'],
            reverse=True
        )[:limit]
        
        return [
            {'action': action, 'score': data['score']}
            for action, data in sorted_prefs
        ]
    
    async def get_realtime_stats(self) -> Dict:
        """リアルタイム学習統計"""
        return {
            'total_learning_events': self.learning_events,
            'patterns_learned': len(self.rt_data.get('patterns', {})),
            'preferences_learned': len(self.rt_data.get('preferences', {})),
            'top_patterns': list(self.rt_data.get('patterns', {}).keys())[:10]
        }


# テスト
async def test_realtime():
    print("\n" + "="*70)
    print("🧪 Realtime Learning - テスト")
    print("="*70)
    
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.unified_memory_api import UnifiedMemoryAPI
    
    memory = UnifiedMemoryAPI()
    rt = RealtimeLearning(memory)
    
    # 学習テスト
    print("\n⚡ リアルタイム学習テスト")
    
    # 成功パターン
    result1 = await rt.learn_from_interaction({
        'action': 'カレンダー確認',
        'context': '朝9時',
        'result': '予定3件取得',
        'user_reaction': 'positive'
    })
    print(f"学習1: {result1['pattern']} (信頼度: {result1['confidence']:.0%})")
    
    # もう一度同じパターン
    result2 = await rt.learn_from_interaction({
        'action': 'カレンダー確認',
        'context': '朝9時',
        'result': '予定5件取得',
        'user_reaction': 'positive'
    })
    print(f"学習2: {result2['pattern']} (信頼度: {result2['confidence']:.0%})")
    
    # 統計
    print("\n📊 学習統計")
    stats = await rt.get_realtime_stats()
    print(f"学習イベント: {stats['total_learning_events']}回")
    print(f"パターン数: {stats['patterns_learned']}個")
    
    print("\n✅ テスト完了")


if __name__ == '__main__':
    asyncio.run(test_realtime())

