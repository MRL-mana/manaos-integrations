#!/usr/bin/env python3
"""
🎲 A/B Testing Engine
Phase 13: A/Bテスト自動実験エンジン

機能:
1. Multi-Armed Bandit（最適選択肢を自動発見）
2. A/Bテスト自動実行
3. ベイズ最適化
4. 統計的有意性検定
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Tuple
from pathlib import Path
import json
import random
import math

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ABTesting")


class ABTestingEngine:
    """A/Bテスト自動実験エンジン"""
    
    def __init__(self, unified_memory_api):
        logger.info("🎲 A/B Testing Engine 初期化中...")
        
        self.memory_api = unified_memory_api
        
        # 実験DB
        self.experiments_db = Path('/root/.ab_experiments.json')
        self.experiments_data = self._load_experiments()
        
        logger.info("✅ A/B Testing Engine 準備完了")
    
    def _load_experiments(self) -> Dict:
        """実験データ読み込み"""
        if self.experiments_db.exists():
            try:
                with open(self.experiments_db, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        return {
            'active_experiments': [],
            'completed_experiments': [],
            'bandit_arms': {}
        }
    
    def _save_experiments(self):
        """実験データ保存"""
        try:
            with open(self.experiments_db, 'w') as f:
                json.dump(self.experiments_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"実験データ保存エラー: {e}")
    
    async def create_ab_test(self, name: str, variants: List[str],
                            metric: str, duration_days: int = 7) -> Dict:
        """
        A/Bテスト作成
        
        Args:
            name: テスト名
            variants: 変種リスト ['A', 'B', 'C']
            metric: 測定メトリクス
            duration_days: 実験期間（日数）
            
        Returns:
            作成されたテスト
        """
        logger.info(f"🧪 A/Bテスト作成: {name} ({len(variants)}変種)")
        
        test_id = f"ab_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        test = {
            'id': test_id,
            'name': name,
            'variants': variants,
            'metric': metric,
            'duration_days': duration_days,
            'start_date': datetime.now().isoformat(),
            'data': {variant: {'trials': 0, 'successes': 0} for variant in variants},
            'status': 'active'
        }
        
        self.experiments_data['active_experiments'].append(test)
        self._save_experiments()
        
        logger.info(f"✅ A/Bテスト作成完了: ID {test_id}")
        
        return test
    
    async def record_trial(self, test_id: str, variant: str, 
                          success: bool) -> Dict:
        """
        試行結果を記録
        
        Args:
            test_id: テストID
            variant: 変種
            success: 成功したか
            
        Returns:
            更新された統計
        """
        test = next(
            (t for t in self.experiments_data['active_experiments'] if t['id'] == test_id),
            None
        )
        
        if not test:
            return {'error': 'テストが見つかりません'}
        
        # データ更新
        test['data'][variant]['trials'] += 1
        if success:
            test['data'][variant]['successes'] += 1
        
        self._save_experiments()
        
        # 統計計算
        stats = self._calculate_stats(test)
        
        return {
            'test_id': test_id,
            'variant': variant,
            'trials': test['data'][variant]['trials'],
            'success_rate': stats[variant]['success_rate']
        }
    
    def _calculate_stats(self, test: Dict) -> Dict:
        """統計計算"""
        stats = {}
        
        for variant, data in test['data'].items():
            trials = data['trials']
            successes = data['successes']
            
            success_rate = (successes / trials) if trials > 0 else 0
            
            # 信頼区間（簡易実装）
            if trials > 0:
                se = math.sqrt(success_rate * (1 - success_rate) / trials)
                ci_lower = max(0, success_rate - 1.96 * se)
                ci_upper = min(1, success_rate + 1.96 * se)
            else:
                ci_lower = 0
                ci_upper = 1
            
            stats[variant] = {
                'trials': trials,
                'successes': successes,
                'success_rate': success_rate,
                'confidence_interval': (ci_lower, ci_upper)
            }
        
        return stats
    
    async def get_winner(self, test_id: str, 
                        confidence_level: float = 0.95) -> Dict:
        """
        勝者を判定
        
        Args:
            test_id: テストID
            confidence_level: 信頼水準
            
        Returns:
            勝者と統計
        """
        test = next(
            (t for t in self.experiments_data['active_experiments'] if t['id'] == test_id),
            None
        )
        
        if not test:
            return {'error': 'テストが見つかりません'}
        
        stats = self._calculate_stats(test)
        
        # 最高成功率の変種
        winner = max(stats.items(), key=lambda x: x[1]['success_rate'])
        
        # 統計的有意性チェック（簡易実装）
        is_significant = self._check_significance(stats, winner[0])
        
        result = {
            'test_id': test_id,
            'winner': winner[0],
            'winner_success_rate': winner[1]['success_rate'],
            'is_significant': is_significant,
            'all_stats': stats
        }
        
        logger.info(f"🏆 勝者: {winner[0]} (成功率: {winner[1]['success_rate']:.1%}, 有意: {is_significant})")
        
        return result
    
    def _check_significance(self, stats: Dict, winner: str) -> bool:
        """統計的有意性チェック（簡易実装）"""
        winner_rate = stats[winner]['success_rate']
        
        # 他の変種と比較
        for variant, data in stats.items():
            if variant == winner:
                continue
            
            # 信頼区間が重ならないか確認
            winner_ci = stats[winner]['confidence_interval']
            other_ci = data['confidence_interval']
            
            if winner_ci[0] > other_ci[1]:
                # 勝者の下限 > 他の上限 → 有意
                return True
        
        return False
    
    async def multi_armed_bandit(self, experiment_name: str,
                                arms: List[str],
                                trials: int = 100) -> Dict:
        """
        Multi-Armed Bandit
        
        複数の選択肢から最適なものを自動発見
        
        Args:
            experiment_name: 実験名
            arms: 選択肢リスト
            trials: 試行回数
            
        Returns:
            最適選択肢
        """
        logger.info(f"🎰 Multi-Armed Bandit: {experiment_name} ({len(arms)}選択肢, {trials}試行)")
        
        # Epsilon-Greedy戦略
        epsilon = 0.1  # 探索率
        
        # 各アームの統計
        arm_stats = {arm: {'pulls': 0, 'rewards': 0.0} for arm in arms}
        
        for trial in range(trials):
            # Epsilon-Greedy選択
            if random.random() < epsilon:
                # 探索: ランダム選択
                chosen_arm = random.choice(arms)
            else:
                # 活用: 最高平均報酬のアーム選択
                avg_rewards = {
                    arm: (stats['rewards'] / stats['pulls']) if stats['pulls'] > 0 else 0
                    for arm, stats in arm_stats.items()
                }
                chosen_arm = max(avg_rewards.items(), key=lambda x: x[1])[0]
            
            # 報酬取得（実際の報酬関数を使用）
            reward = self._get_reward(chosen_arm, experiment_name)
            
            # 統計更新
            arm_stats[chosen_arm]['pulls'] += 1
            arm_stats[chosen_arm]['rewards'] += reward
        
        # 最終結果
        final_stats = {}
        for arm, stats in arm_stats.items():
            avg_reward = (stats['rewards'] / stats['pulls']) if stats['pulls'] > 0 else 0
            final_stats[arm] = {
                'pulls': stats['pulls'],
                'total_reward': stats['rewards'],
                'avg_reward': avg_reward
            }
        
        # 最適アーム
        best_arm = max(final_stats.items(), key=lambda x: x[1]['avg_reward'])
        
        bandit_result = {
            'experiment_name': experiment_name,
            'best_arm': best_arm[0],
            'best_avg_reward': best_arm[1]['avg_reward'],
            'all_stats': final_stats,
            'trials': trials
        }
        
        # バンディット結果を保存
        self.experiments_data['bandit_arms'][experiment_name] = bandit_result
        self._save_experiments()
        
        logger.info(f"✅ 最適選択肢: {best_arm[0]} (平均報酬: {best_arm[1]['avg_reward']:.3f})")
        
        return bandit_result
    
    def _get_reward(self, arm: str, experiment_name: str) -> float:
        """報酬取得（実際の報酬関数）"""
        # 実装例: 各アームに固有の期待報酬を設定
        # 実際はユーザーの反応、成功率などを測定
        
        # デモ実装: アームごとに異なる報酬分布
        base_rewards = {
            0: 0.3,  # 最初のアーム
            1: 0.5,  # 2番目のアーム
            2: 0.7,  # 3番目のアーム（最適）
        }
        
        arm_index = hash(arm) % len(base_rewards)
        base = base_rewards.get(arm_index, 0.5)
        
        # ノイズ追加
        noise = random.gauss(0, 0.1)
        
        return max(0, min(1, base + noise))
    
    async def bayesian_optimization(self, parameter_name: str,
                                   search_range: Tuple[float, float],
                                   iterations: int = 20) -> Dict:
        """
        ベイズ最適化
        
        パラメータの最適値を効率的に探索
        
        Args:
            parameter_name: パラメータ名
            search_range: 探索範囲 (min, max)
            iterations: イテレーション数
            
        Returns:
            最適パラメータ
        """
        logger.info(f"📈 ベイズ最適化: {parameter_name} ({search_range})")
        
        min_val, max_val = search_range
        
        # 探索履歴
        history = []
        
        for i in range(iterations):
            # 獲得関数に基づいて次の探索点を選択
            # （簡易実装: Upper Confidence Bound風）
            
            if i < 3:
                # 最初はランダムサンプリング
                x = random.uniform(min_val, max_val)
            else:
                # UCBで次の探索点を選択
                x = self._select_next_point_ucb(history, min_val, max_val)
            
            # 目的関数評価
            y = self._objective_function(x, parameter_name)
            
            history.append({'x': x, 'y': y})
            
            logger.info(f"  イテレーション {i+1}/{iterations}: x={x:.3f}, y={y:.3f}")
        
        # 最適点
        best = max(history, key=lambda h: h['y'])
        
        optimization_result = {
            'parameter_name': parameter_name,
            'optimal_value': best['x'],
            'optimal_score': best['y'],
            'iterations': iterations,
            'history': history
        }
        
        logger.info(f"✅ 最適値: {best['x']:.3f} (スコア: {best['y']:.3f})")
        
        return optimization_result
    
    def _select_next_point_ucb(self, history: List[Dict], 
                               min_val: float, max_val: float) -> float:
        """Upper Confidence Boundで次の探索点を選択"""
        # 簡易実装: 最良点の近傍をサンプリング
        if history:
            best = max(history, key=lambda h: h['y'])
            
            # 最良点の周辺を探索
            std = (max_val - min_val) / 10
            x = random.gauss(best['x'], std)
            
            # 範囲内にクリップ
            return max(min_val, min(max_val, x))
        else:
            return random.uniform(min_val, max_val)
    
    def _objective_function(self, x: float, parameter_name: str) -> float:
        """目的関数（実際は実システムでの評価）"""
        # デモ: 二次関数（最適値は中央付近）
        optimal = 5.0  # 仮の最適値
        y = 1.0 - ((x - optimal) / 5.0) ** 2
        
        # ノイズ
        noise = random.gauss(0, 0.05)
        
        return max(0, min(1, y + noise))
    
    async def get_experiment_stats(self) -> Dict:
        """実験統計取得"""
        return {
            'active_experiments': len(self.experiments_data.get('active_experiments', [])),
            'completed_experiments': len(self.experiments_data.get('completed_experiments', [])),
            'bandit_experiments': len(self.experiments_data.get('bandit_arms', {}))
        }


# テスト
async def test_ab_testing():
    print("\n" + "="*70)
    print("🧪 A/B Testing Engine - テスト")
    print("="*70)
    
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    from core.unified_memory_api import UnifiedMemoryAPI
    
    memory_api = UnifiedMemoryAPI()
    ab = ABTestingEngine(memory_api)
    
    # テスト1: A/Bテスト
    print("\n🧪 テスト1: A/Bテスト作成")
    test = await ab.create_ab_test(
        "通知方法テスト",
        ['テキスト', '画像付き', '音声'],
        'クリック率'
    )
    print(f"テストID: {test['id']}")
    
    # 試行シミュレーション
    for _ in range(30):
        variant = random.choice(test['variants'])
        success = random.random() < 0.6  # 60%成功率
        await ab.record_trial(test['id'], variant, success)
    
    winner = await ab.get_winner(test['id'])
    print(f"勝者: {winner['winner']} ({winner['winner_success_rate']:.0%})")
    
    # テスト2: Multi-Armed Bandit
    print("\n🎰 テスト2: Multi-Armed Bandit")
    bandit = await ab.multi_armed_bandit(
        "UI配色最適化",
        ['青系', '緑系', '赤系'],
        trials=50
    )
    print(f"最適: {bandit['best_arm']} (報酬: {bandit['best_avg_reward']:.3f})")
    
    # テスト3: ベイズ最適化
    print("\n📈 テスト3: ベイズ最適化")
    bayesian = await ab.bayesian_optimization(
        "検索結果数",
        (1, 20),
        iterations=10
    )
    print(f"最適値: {bayesian['optimal_value']:.1f}")
    
    print("\n✅ テスト完了")


if __name__ == '__main__':
    asyncio.run(test_ab_testing())

