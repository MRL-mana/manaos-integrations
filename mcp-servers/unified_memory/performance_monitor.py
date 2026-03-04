#!/usr/bin/env python3
"""
📊 Performance Monitor
パフォーマンス監視・最適化システム

機能:
1. リアルタイムパフォーマンス監視
2. ボトルネック自動検出
3. 最適化提案
4. アラート通知
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List
from pathlib import Path
import json
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PerformanceMonitor")


class PerformanceMonitor:
    """パフォーマンス監視システム"""
    
    def __init__(self, unified_memory_api):
        logger.info("📊 Performance Monitor 初期化中...")
        
        self.memory_api = unified_memory_api
        
        # パフォーマンスログ
        self.perf_log_db = Path('/root/unified_memory_system/data/performance_log.json')
        self.perf_log_db.parent.mkdir(exist_ok=True, parents=True)
        self.perf_log = self._load_perf_log()
        
        # 閾値設定
        self.thresholds = {
            'search_time_ms': 500,  # 検索は500ms以内
            'store_time_ms': 1000,  # 保存は1秒以内
            'memory_usage_mb': 500,  # メモリ500MB以内
        }
        
        logger.info("✅ Performance Monitor 準備完了")
    
    def _load_perf_log(self) -> Dict:
        """ログ読み込み"""
        if self.perf_log_db.exists():
            try:
                with open(self.perf_log_db, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        return {
            'operations': [],
            'alerts': [],
            'optimizations': []
        }
    
    def _save_perf_log(self):
        """ログ保存"""
        try:
            with open(self.perf_log_db, 'w') as f:
                json.dump(self.perf_log, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"ログ保存エラー: {e}")
    
    async def measure_search_performance(self, query: str) -> Dict:
        """検索パフォーマンス測定"""
        start_time = time.time()
        
        # 検索実行
        results = await self.memory_api.unified_search(query, limit=20)
        
        elapsed_ms = (time.time() - start_time) * 1000
        
        perf_data = {
            'timestamp': datetime.now().isoformat(),
            'operation': 'search',
            'query': query,
            'elapsed_ms': elapsed_ms,
            'hits': results.get('total_hits', 0),
            'threshold_ok': elapsed_ms < self.thresholds['search_time_ms']
        }
        
        # ログ記録
        self.perf_log['operations'].append(perf_data)
        self.perf_log['operations'] = self.perf_log['operations'][-1000:]
        
        # 閾値チェック
        if not perf_data['threshold_ok']:
            await self._create_alert(
                f"検索が遅い: {elapsed_ms:.0f}ms > {self.thresholds['search_time_ms']}ms",
                'performance',
                'warning'
            )
        
        self._save_perf_log()
        
        status = '✅' if perf_data['threshold_ok'] else '⚠️'
        logger.info(f"{status} 検索: {elapsed_ms:.0f}ms, {perf_data['hits']}件ヒット")
        
        return perf_data
    
    async def measure_store_performance(self, content: str, **kwargs) -> Dict:
        """保存パフォーマンス測定"""
        start_time = time.time()
        
        # 保存実行
        result = await self.memory_api.smart_store(content, **kwargs)
        
        elapsed_ms = (time.time() - start_time) * 1000
        
        perf_data = {
            'timestamp': datetime.now().isoformat(),
            'operation': 'store',
            'elapsed_ms': elapsed_ms,
            'saved_to': len(result.get('saved_to', [])),
            'threshold_ok': elapsed_ms < self.thresholds['store_time_ms']
        }
        
        # ログ記録
        self.perf_log['operations'].append(perf_data)
        self.perf_log['operations'] = self.perf_log['operations'][-1000:]
        self._save_perf_log()
        
        status = '✅' if perf_data['threshold_ok'] else '⚠️'
        logger.info(f"{status} 保存: {elapsed_ms:.0f}ms, {perf_data['saved_to']}箇所")
        
        return perf_data
    
    async def _create_alert(self, message: str, alert_type: str, 
                           severity: str) -> Dict:
        """アラート作成"""
        alert = {
            'timestamp': datetime.now().isoformat(),
            'type': alert_type,
            'severity': severity,
            'message': message
        }
        
        self.perf_log['alerts'].append(alert)
        self.perf_log['alerts'] = self.perf_log['alerts'][-100:]
        self._save_perf_log()
        
        logger.warning(f"⚠️ アラート: {message}")
        
        return alert
    
    async def detect_bottlenecks(self) -> List[Dict]:
        """ボトルネック検出"""
        logger.info("🔍 ボトルネック検出中...")
        
        operations = self.perf_log.get('operations', [])
        
        if not operations:
            return []
        
        bottlenecks = []
        
        # 最近100件の操作を分析
        recent_ops = operations[-100:]
        
        # 平均時間計算
        search_times = [op['elapsed_ms'] for op in recent_ops if op['operation'] == 'search']
        store_times = [op['elapsed_ms'] for op in recent_ops if op['operation'] == 'store']
        
        if search_times:
            avg_search = sum(search_times) / len(search_times)
            if avg_search > self.thresholds['search_time_ms']:
                bottlenecks.append({
                    'operation': 'search',
                    'avg_time_ms': avg_search,
                    'threshold_ms': self.thresholds['search_time_ms'],
                    'recommendation': 'インデックス最適化、キャッシュ導入を検討'
                })
        
        if store_times:
            avg_store = sum(store_times) / len(store_times)
            if avg_store > self.thresholds['store_time_ms']:
                bottlenecks.append({
                    'operation': 'store',
                    'avg_time_ms': avg_store,
                    'threshold_ms': self.thresholds['store_time_ms'],
                    'recommendation': 'バッチ保存、非同期化を検討'
                })
        
        logger.info(f"  ✅ ボトルネック: {len(bottlenecks)}個検出")
        
        return bottlenecks
    
    async def get_performance_report(self) -> Dict:
        """パフォーマンスレポート生成"""
        operations = self.perf_log.get('operations', [])
        
        if not operations:
            return {'message': 'データ不足'}
        
        # 最近の統計
        recent = operations[-100:]
        
        search_ops = [op for op in recent if op['operation'] == 'search']
        store_ops = [op for op in recent if op['operation'] == 'store']
        
        report = {
            'total_operations': len(operations),
            'recent_operations': len(recent),
            'search_stats': {
                'count': len(search_ops),
                'avg_ms': sum(op['elapsed_ms'] for op in search_ops) / len(search_ops) if search_ops else 0,
                'success_rate': len([op for op in search_ops if op['threshold_ok']]) / len(search_ops) * 100 if search_ops else 0
            },
            'store_stats': {
                'count': len(store_ops),
                'avg_ms': sum(op['elapsed_ms'] for op in store_ops) / len(store_ops) if store_ops else 0,
                'success_rate': len([op for op in store_ops if op['threshold_ok']]) / len(store_ops) * 100 if store_ops else 0
            },
            'alerts_count': len(self.perf_log.get('alerts', []))
        }
        
        return report


# テスト
async def test_performance():
    print("\n" + "="*70)
    print("🧪 Performance Monitor - テスト")
    print("="*70)
    
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    from core.unified_memory_api import UnifiedMemoryAPI
    
    memory = UnifiedMemoryAPI()
    monitor = PerformanceMonitor(memory)
    
    # 検索パフォーマンス測定
    print("\n🔍 検索パフォーマンス測定")
    perf1 = await monitor.measure_search_performance("X280")
    print(f"検索時間: {perf1['elapsed_ms']:.0f}ms")
    
    # 保存パフォーマンス測定
    print("\n💾 保存パフォーマンス測定")
    perf2 = await monitor.measure_store_performance(
        "パフォーマンステスト",
        importance=7
    )
    print(f"保存時間: {perf2['elapsed_ms']:.0f}ms")
    
    # レポート
    print("\n📊 パフォーマンスレポート")
    report = await monitor.get_performance_report()
    print(f"総操作数: {report['total_operations']}")
    print(f"検索平均: {report['search_stats']['avg_ms']:.0f}ms")
    print(f"保存平均: {report['store_stats']['avg_ms']:.0f}ms")
    
    print("\n✅ テスト完了")


if __name__ == '__main__':
    asyncio.run(test_performance())

