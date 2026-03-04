#!/usr/bin/env python3
"""
🧠 Cross-System Learning Engine
Phase 2: システム間で知識を共有し、相互に強化

Mina（予測）+ AI Learning（知識）= ハイブリッド知能
"""

import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import json
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CrossSystemLearning")


class CrossSystemLearning:
    """
    クロスシステム学習エンジン
    
    機能:
    1. Mina予測 + AI Learning知識 → ハイブリッド提案
    2. 実行結果のフィードバックループ
    3. パターン学習の統合
    4. 予測精度の向上
    """
    
    def __init__(self, unified_memory_api):
        logger.info("🧠 Cross-System Learning Engine 初期化中...")
        
        self.memory_api = unified_memory_api
        
        # ManaOS v3 Insight (Mina) API
        self.manaos_insight_url = "http://localhost:9205"  # Dockerコンテナ外部ポート
        
        # フィードバックDB
        self.feedback_db = Path('/root/.cross_system_feedback.json')
        self.feedback_data = self._load_feedback()
        
        logger.info("✅ Cross-System Learning Engine 準備完了")
    
    def _load_feedback(self) -> Dict:
        """フィードバックデータ読み込み"""
        if self.feedback_db.exists():
            try:
                with open(self.feedback_db, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        return {
            'predictions': [],
            'executions': [],
            'learning_history': []
        }
    
    def _save_feedback(self):
        """フィードバックデータ保存"""
        try:
            with open(self.feedback_db, 'w') as f:
                json.dump(self.feedback_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"フィードバック保存エラー: {e}")
    
    async def hybrid_predict(self, context: str) -> Dict[str, Any]:
        """
        ハイブリッド予測
        Minaの時間帯予測 + AI Learningの知識 → 賢い提案
        
        Args:
            context: 現在のコンテキスト（例: "朝9時", "疲れている"）
            
        Returns:
            ハイブリッド予測結果
        """
        logger.info(f"🔮 ハイブリッド予測開始: '{context}'")
        
        result = {
            'timestamp': datetime.now().isoformat(),
            'context': context,
            'predictions': []
        }
        
        # 1. Minaから予測取得（時間帯パターン）
        mina_prediction = await self._get_mina_prediction()
        
        # 2. AI Learningから関連知識取得
        knowledge_results = await self.memory_api.unified_search(
            context,
            limit=5,
            filters={'importance_min': 6}
        )
        
        # 3. フィードバック履歴から成功パターン抽出
        success_patterns = self._get_success_patterns(context)
        
        # 4. ハイブリッド統合
        if mina_prediction and 'intent' in mina_prediction:
            # Minaの予測を基本に
            hybrid = {
                'action': mina_prediction['intent'],
                'confidence': mina_prediction.get('confidence', 0.5),
                'reason': mina_prediction.get('reason', ''),
                'source': 'mina_prediction'
            }
            
            # AI Learningの知識で補強
            if knowledge_results['total_hits'] > 0:
                # 知識があれば信頼度を上げる
                hybrid['confidence'] += 0.2
                hybrid['confidence'] = min(hybrid['confidence'], 0.95)
                hybrid['knowledge_support'] = True
                hybrid['related_knowledge'] = [
                    {
                        'content': r.get('content', '')[:100],
                        'importance': r.get('importance', 5)
                    }
                    for source_data in knowledge_results['sources'].values()
                    for r in source_data.get('results', [])[:2]
                ]
            
            # 成功パターンで更に補強
            if success_patterns:
                hybrid['confidence'] += 0.1
                hybrid['confidence'] = min(hybrid['confidence'], 0.99)
                hybrid['past_success_rate'] = success_patterns['success_rate']
            
            result['predictions'].append(hybrid)
        
        # 5. AI Learningのみの予測も追加（Minaが無い場合のフォールバック）
        if knowledge_results['total_hits'] > 0:
            for source_data in knowledge_results['sources'].values():
                for knowledge in source_data.get('results', [])[:3]:
                    result['predictions'].append({
                        'action': f"参考: {knowledge.get('title', knowledge.get('content', '')[:50])}",
                        'confidence': 0.6,
                        'reason': '過去の知識から提案',
                        'source': 'knowledge_based',
                        'importance': knowledge.get('importance', 5)
                    })
        
        # 6. 予測を記録（後でフィードバック）
        self.feedback_data['predictions'].append({
            'timestamp': result['timestamp'],
            'context': context,
            'predictions': result['predictions']
        })
        self._save_feedback()
        
        logger.info(f"✅ ハイブリッド予測完了: {len(result['predictions'])}件")
        
        return result
    
    async def _get_mina_prediction(self) -> Optional[Dict]:
        """Mina（ManaOS Insight）から次のアクション予測取得"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.manaos_insight_url}/predict/next_action",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"  ✅ Mina予測取得: {data.get('intent', 'なし')}")
                        return data
                    else:
                        logger.warning(f"  ⚠️ Mina応答なし: {response.status}")
                        return None
        except Exception as e:
            logger.warning(f"  ⚠️ Mina接続失敗: {e}")
            return None
    
    def _get_success_patterns(self, context: str) -> Optional[Dict]:
        """過去の成功パターン取得"""
        successes = [
            ex for ex in self.feedback_data.get('executions', [])
            if ex.get('success') and context.lower() in ex.get('context', '').lower()
        ]
        
        if not successes:
            return None
        
        total = len(successes)
        success_rate = total / max(1, len([
            ex for ex in self.feedback_data.get('executions', [])
            if context.lower() in ex.get('context', '').lower()
        ]))
        
        return {
            'count': total,
            'success_rate': success_rate,
            'recent_actions': [s.get('action') for s in successes[-3:]]
        }
    
    async def record_execution(self, action: str, context: str, 
                             success: bool, latency_ms: int = None,
                             notes: str = None) -> Dict:
        """
        実行結果を記録してフィードバックループを回す
        
        Args:
            action: 実行したアクション
            context: コンテキスト
            success: 成功したか
            latency_ms: 実行時間（ミリ秒）
            notes: 備考
            
        Returns:
            学習結果
        """
        logger.info(f"📝 実行結果記録: {action} → {'成功' if success else '失敗'}")
        
        execution = {
            'timestamp': datetime.now().isoformat(),
            'action': action,
            'context': context,
            'success': success,
            'latency_ms': latency_ms,
            'notes': notes
        }
        
        # 1. ローカルフィードバックDBに記録
        self.feedback_data['executions'].append(execution)
        self.feedback_data['executions'] = self.feedback_data['executions'][-1000:]  # 最新1000件
        self._save_feedback()
        
        # 2. Minaにも記録を送信（学習させる）
        await self._send_to_mina_insight(action, success, latency_ms)
        
        # 3. 成功した場合、AI Learningにも知識として保存
        if success:
            importance = 7 if latency_ms and latency_ms < 1000 else 6
            
            await self.memory_api.smart_store(
                content=f"実行成功: {action}\nコンテキスト: {context}\n結果: {notes or '成功'}",
                title=f"実行記録: {action}",
                importance=importance,
                tags=['execution_success', 'cross_learning'],
                category='execution_log',
                metadata={
                    'success': success,
                    'latency_ms': latency_ms,
                    'context': context
                }
            )
        
        # 4. 学習履歴に追加
        learning = {
            'timestamp': datetime.now().isoformat(),
            'action': action,
            'learned': f"{'成功パターン' if success else '失敗パターン'}として記録",
            'confidence_delta': 0.05 if success else -0.05
        }
        
        self.feedback_data['learning_history'].append(learning)
        self.feedback_data['learning_history'] = self.feedback_data['learning_history'][-100:]
        self._save_feedback()
        
        logger.info("✅ フィードバックループ完了")
        
        return {
            'recorded': True,
            'learning': learning,
            'total_executions': len(self.feedback_data['executions']),
            'success_rate': self._calculate_success_rate()
        }
    
    async def _send_to_mina_insight(self, action: str, success: bool, 
                                   latency_ms: Optional[int]):
        """Mina Insightに実行結果を送信"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.manaos_insight_url}/record",
                    json={
                        'intent': action,
                        'actor': 'cross_system_learning',
                        'success': success,
                        'latency_ms': latency_ms or 0,
                        'confidence': 0.8
                    },
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        logger.info("  ✅ Minaに学習データ送信完了")
                    else:
                        logger.warning(f"  ⚠️ Mina記録失敗: {response.status}")
        except Exception as e:
            logger.warning(f"  ⚠️ Mina送信失敗: {e}")
    
    def _calculate_success_rate(self) -> float:
        """全体の成功率計算"""
        executions = self.feedback_data.get('executions', [])
        if not executions:
            return 0.0
        
        successes = len([e for e in executions if e.get('success')])
        return successes / len(executions)
    
    async def get_learning_stats(self) -> Dict[str, Any]:
        """学習統計取得"""
        executions = self.feedback_data.get('executions', [])
        
        # 最近の実行（24時間以内）
        now = datetime.now()
        recent_threshold = (now - timedelta(hours=24)).isoformat()
        recent_executions = [
            e for e in executions
            if e.get('timestamp', '') >= recent_threshold
        ]
        
        # 成功率
        total_success = len([e for e in executions if e.get('success')])
        total_count = len(executions)
        overall_success_rate = (total_success / total_count * 100) if total_count > 0 else 0
        
        recent_success = len([e for e in recent_executions if e.get('success')])
        recent_count = len(recent_executions)
        recent_success_rate = (recent_success / recent_count * 100) if recent_count > 0 else 0
        
        # 人気アクション
        action_counts = {}
        for ex in executions:
            action = ex.get('action', 'unknown')
            action_counts[action] = action_counts.get(action, 0) + 1
        
        top_actions = sorted(
            action_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        return {
            'total_executions': total_count,
            'total_successes': total_success,
            'overall_success_rate': round(overall_success_rate, 2),
            'recent_24h': {
                'executions': recent_count,
                'successes': recent_success,
                'success_rate': round(recent_success_rate, 2)
            },
            'top_actions': [
                {'action': action, 'count': count}
                for action, count in top_actions
            ],
            'learning_history_count': len(self.feedback_data.get('learning_history', []))
        }


# テスト用
async def test_cross_system_learning():
    """クロスシステム学習テスト"""
    print("\n" + "="*70)
    print("🧪 Cross-System Learning Engine - テスト")
    print("="*70)
    
    # Unified Memory API import
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    from core.unified_memory_api import UnifiedMemoryAPI
    
    memory_api = UnifiedMemoryAPI()
    cross_learning = CrossSystemLearning(memory_api)
    
    # テスト1: ハイブリッド予測
    print("\n🔮 テスト1: ハイブリッド予測")
    prediction = await cross_learning.hybrid_predict("朝9時、カレンダー確認")
    print(f"予測数: {len(prediction['predictions'])}件")
    for idx, pred in enumerate(prediction['predictions'][:3], 1):
        print(f"  {idx}. {pred['action']} (信頼度: {pred['confidence']:.2f})")
    
    # テスト2: 実行記録
    print("\n📝 テスト2: 実行記録とフィードバック")
    result = await cross_learning.record_execution(
        action="カレンダー確認",
        context="朝9時",
        success=True,
        latency_ms=250,
        notes="予定3件確認完了"
    )
    print(f"成功率: {result['success_rate']:.2%}")
    print(f"総実行数: {result['total_executions']}件")
    
    # テスト3: 学習統計
    print("\n📊 テスト3: 学習統計")
    stats = await cross_learning.get_learning_stats()
    print(f"全体成功率: {stats['overall_success_rate']}%")
    print(f"24時間成功率: {stats['recent_24h']['success_rate']}%")
    print("人気アクション:")
    for action_data in stats['top_actions'][:3]:
        print(f"  • {action_data['action']}: {action_data['count']}回")
    
    print("\n✅ テスト完了")


if __name__ == '__main__':
    asyncio.run(test_cross_system_learning())

