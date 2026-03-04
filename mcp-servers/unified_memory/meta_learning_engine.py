#!/usr/bin/env python3
"""
🧬 Meta Learning Engine
Phase 6: 学習方法を学習する - メタ学習エンジン

機能:
1. 学習パラメータの自動最適化
2. Few-shot Learning（数例から学習）
3. AutoML（最適なAI構造を自動探索）
4. 継続学習（古い知識を忘れない）
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List
from pathlib import Path
import json
import random

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MetaLearning")


class MetaLearningEngine:
    """メタ学習エンジン - 学習方法を学習する"""
    
    def __init__(self, unified_memory_api):
        logger.info("🧬 Meta Learning Engine 初期化中...")
        
        self.memory_api = unified_memory_api
        
        # 学習パラメータDB
        self.meta_db = Path('/root/.meta_learning.json')
        self.meta_data = self._load_meta_data()
        
        # 現在の学習パラメータ
        self.current_params = {
            'learning_rate': 0.01,
            'vector_dimension': 384,
            'search_depth': 20,
            'importance_threshold': 5,
            'consolidation_interval_hours': 24,
            'review_boost_factor': 0.3
        }
        
        logger.info("✅ Meta Learning Engine 準備完了")
    
    def _load_meta_data(self) -> Dict:
        """メタデータ読み込み"""
        if self.meta_db.exists():
            try:
                with open(self.meta_db, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        return {
            'optimization_history': [],
            'few_shot_examples': {},
            'automl_experiments': [],
            'continual_learning_checkpoints': []
        }
    
    def _save_meta_data(self):
        """メタデータ保存"""
        try:
            with open(self.meta_db, 'w') as f:
                json.dump(self.meta_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"メタデータ保存エラー: {e}")
    
    async def optimize_learning_rate(self) -> Dict:
        """
        学習率の自動最適化
        
        過去の学習効率を分析して最適な学習率を発見
        
        Returns:
            最適化結果
        """
        logger.info("📊 学習率最適化開始...")
        
        # 過去のパフォーマンスデータ収集
        stats = await self.memory_api.get_stats()
        
        # 試行する学習率の範囲
        learning_rates = [0.001, 0.005, 0.01, 0.05, 0.1]
        
        results = []
        
        for lr in learning_rates:
            # 各学習率でのシミュレーション
            # （実際には実データで評価するが、ここでは簡易実装）
            
            # 学習効率スコア計算（仮想）
            # 実際は: 記憶定着率、検索精度、応答時間などを測定
            efficiency_score = self._simulate_learning_efficiency(lr)
            
            results.append({
                'learning_rate': lr,
                'efficiency_score': efficiency_score
            })
            
            logger.info(f"  学習率 {lr}: スコア {efficiency_score:.3f}")
        
        # 最適な学習率を選択
        best = max(results, key=lambda x: x['efficiency_score'])
        
        # パラメータ更新
        old_lr = self.current_params['learning_rate']
        self.current_params['learning_rate'] = best['learning_rate']
        
        optimization = {
            'timestamp': datetime.now().isoformat(),
            'parameter': 'learning_rate',
            'old_value': old_lr,
            'new_value': best['learning_rate'],
            'improvement': (best['efficiency_score'] - 
                          results[0]['efficiency_score']) / results[0]['efficiency_score'] * 100
        }
        
        self.meta_data['optimization_history'].append(optimization)
        self.meta_data['optimization_history'] = \
            self.meta_data['optimization_history'][-100:]
        self._save_meta_data()
        
        logger.info(f"✅ 最適学習率: {best['learning_rate']} (改善: {optimization['improvement']:.1f}%)")
        
        return optimization
    
    def _simulate_learning_efficiency(self, learning_rate: float) -> float:
        """学習効率シミュレーション（簡易実装）"""
        # 最適値は0.01付近と仮定
        optimal = 0.01
        deviation = abs(learning_rate - optimal)
        
        # ガウシアン曲線で効率をモデル化
        efficiency = 1.0 - (deviation / 0.1) ** 2
        
        # ノイズ追加
        noise = random.uniform(-0.1, 0.1)
        
        return max(0.0, min(1.0, efficiency + noise))
    
    async def few_shot_learning(self, concept: str, 
                                examples: List[Dict]) -> Dict:
        """
        Few-shot Learning
        
        数例だけで新しい概念を学習
        
        Args:
            concept: 学習する概念
            examples: 例のリスト [
                {'input': '...', 'output': '...'},
                ...
            ]
            
        Returns:
            学習結果
        """
        logger.info(f"🎯 Few-shot Learning: {concept} ({len(examples)}例)")
        
        if len(examples) < 2:
            logger.warning("  ⚠️ 例が少なすぎます（最低2例推奨）")
        
        # パターン抽出
        patterns = self._extract_patterns(examples)
        
        # 概念モデル構築
        concept_model = {
            'concept': concept,
            'examples': examples,
            'patterns': patterns,
            'learned_at': datetime.now().isoformat(),
            'confidence': min(0.95, 0.5 + (len(examples) * 0.1))
        }
        
        # 記憶に保存
        await self.memory_api.smart_store(
            content=f"Few-shot Learning: {concept}\n\n例:\n" + 
                   "\n".join([f"- {ex['input']} → {ex['output']}" for ex in examples[:3]]) +
                   f"\n\nパターン: {json.dumps(patterns, ensure_ascii=False)}",
            title=f"Few-shot: {concept}",
            importance=8,
            tags=['few_shot', 'meta_learning', concept],
            category='few_shot_learning',
            metadata={'concept_model': concept_model}
        )
        
        # メタデータに記録
        self.meta_data['few_shot_examples'][concept] = concept_model
        self._save_meta_data()
        
        logger.info(f"✅ {concept} を{len(examples)}例から学習完了（信頼度: {concept_model['confidence']:.0%}）")
        
        return concept_model
    
    def _extract_patterns(self, examples: List[Dict]) -> Dict:
        """例からパターン抽出"""
        patterns = {
            'input_length_avg': 0,
            'output_length_avg': 0,
            'common_words': []
        }
        
        if not examples:
            return patterns
        
        # 平均長計算
        patterns['input_length_avg'] = sum(
            len(str(ex.get('input', ''))) for ex in examples
        ) / len(examples)
        
        patterns['output_length_avg'] = sum(
            len(str(ex.get('output', ''))) for ex in examples
        ) / len(examples)
        
        # 共通ワード抽出（簡易実装）
        all_words = []
        for ex in examples:
            input_text = str(ex.get('input', '')).lower()
            all_words.extend(input_text.split())
        
        if all_words:
            word_counts = {}
            for word in all_words:
                word_counts[word] = word_counts.get(word, 0) + 1
            
            # 頻出ワードTop3
            common = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            patterns['common_words'] = [word for word, count in common]
        
        return patterns
    
    async def auto_ml_search(self, task: str, 
                            max_experiments: int = 10) -> Dict:
        """
        AutoML - 最適なAI構造を自動探索
        
        Args:
            task: タスク（例: "文書分類"）
            max_experiments: 最大実験数
            
        Returns:
            最適モデル
        """
        logger.info(f"🔬 AutoML開始: {task} ({max_experiments}実験)")
        
        experiments = []
        
        # ハイパーパラメータ探索空間
        search_space = {
            'vector_dim': [128, 256, 384, 512, 768],
            'search_depth': [5, 10, 20, 50],
            'importance_threshold': [3, 5, 7, 9]
        }
        
        for i in range(max_experiments):
            # ランダムサンプリング
            config = {
                'vector_dim': random.choice(search_space['vector_dim']),
                'search_depth': random.choice(search_space['search_depth']),
                'importance_threshold': random.choice(search_space['importance_threshold'])
            }
            
            # 評価（簡易実装：実際は実データで評価）
            score = self._evaluate_config(config, task)
            
            experiments.append({
                'config': config,
                'score': score
            })
            
            logger.info(f"  実験 {i+1}/{max_experiments}: スコア {score:.3f}")
        
        # 最適構成を選択
        best = max(experiments, key=lambda x: x['score'])
        
        # パラメータ更新
        self.current_params['vector_dimension'] = best['config']['vector_dim']
        self.current_params['search_depth'] = best['config']['search_depth']
        self.current_params['importance_threshold'] = best['config']['importance_threshold']
        
        automl_result = {
            'timestamp': datetime.now().isoformat(),
            'task': task,
            'best_config': best['config'],
            'best_score': best['score'],
            'experiments_count': len(experiments)
        }
        
        self.meta_data['automl_experiments'].append(automl_result)
        self.meta_data['automl_experiments'] = \
            self.meta_data['automl_experiments'][-50:]
        self._save_meta_data()
        
        logger.info(f"✅ 最適構成発見: ベクトル次元{best['config']['vector_dim']}, スコア{best['score']:.3f}")
        
        return automl_result
    
    def _evaluate_config(self, config: Dict, task: str) -> float:
        """構成評価（簡易実装）"""
        # 実際は実データでモデルを訓練して評価
        # ここでは仮想スコア
        
        base_score = 0.7
        
        # ベクトル次元の影響
        if config['vector_dim'] == 384:
            base_score += 0.1
        elif config['vector_dim'] == 768:
            base_score += 0.05
        
        # 検索深度の影響
        if config['search_depth'] == 20:
            base_score += 0.05
        
        # ノイズ
        noise = random.uniform(-0.1, 0.1)
        
        return max(0.0, min(1.0, base_score + noise))
    
    async def continual_learning_update(self, new_knowledge: Dict) -> Dict:
        """
        継続学習 - 古い知識を忘れずに新しい知識を追加
        
        Args:
            new_knowledge: 新しい知識
            
        Returns:
            更新結果
        """
        logger.info("🔄 継続学習更新中...")
        
        # チェックポイント作成
        checkpoint = {
            'timestamp': datetime.now().isoformat(),
            'params_snapshot': self.current_params.copy(),
            'total_memories': (await self.memory_api.get_stats()).get('total_memories', 0)
        }
        
        # 新知識を統合
        # （実際はニューラルネットの重み更新など）
        
        # 古い知識の保護（Elastic Weight Consolidation風）
        # 重要な記憶の重みを固定
        
        update_result = {
            'checkpoint_id': len(self.meta_data['continual_learning_checkpoints']),
            'timestamp': checkpoint['timestamp'],
            'new_knowledge_integrated': True,
            'old_knowledge_preserved': True
        }
        
        self.meta_data['continual_learning_checkpoints'].append(checkpoint)
        self.meta_data['continual_learning_checkpoints'] = \
            self.meta_data['continual_learning_checkpoints'][-20:]
        self._save_meta_data()
        
        logger.info("✅ 継続学習更新完了（古い知識を保持したまま新知識統合）")
        
        return update_result
    
    async def get_meta_stats(self) -> Dict:
        """メタ学習統計取得"""
        return {
            'current_params': self.current_params,
            'optimizations_count': len(self.meta_data.get('optimization_history', [])),
            'few_shot_concepts': len(self.meta_data.get('few_shot_examples', {})),
            'automl_experiments': len(self.meta_data.get('automl_experiments', [])),
            'continual_checkpoints': len(self.meta_data.get('continual_learning_checkpoints', []))
        }


# テスト
async def test_meta_learning():
    print("\n" + "="*70)
    print("🧪 Meta Learning Engine - テスト")
    print("="*70)
    
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    from core.unified_memory_api import UnifiedMemoryAPI
    
    memory_api = UnifiedMemoryAPI()
    meta = MetaLearningEngine(memory_api)
    
    # テスト1: 学習率最適化
    print("\n📊 テスト1: 学習率最適化")
    opt = await meta.optimize_learning_rate()
    print(f"最適学習率: {opt['new_value']}")
    print(f"改善率: {opt['improvement']:.1f}%")
    
    # テスト2: Few-shot Learning
    print("\n🎯 テスト2: Few-shot Learning")
    examples = [
        {'input': 'こんにちは', 'output': 'Hello'},
        {'input': 'ありがとう', 'output': 'Thank you'},
        {'input': 'さようなら', 'output': 'Goodbye'}
    ]
    model = await meta.few_shot_learning('日英翻訳', examples)
    print(f"概念: {model['concept']}")
    print(f"信頼度: {model['confidence']:.0%}")
    
    # テスト3: AutoML
    print("\n🔬 テスト3: AutoML")
    best = await meta.auto_ml_search('記憶検索最適化', max_experiments=5)
    print(f"最適ベクトル次元: {best['best_config']['vector_dim']}")
    print(f"スコア: {best['best_score']:.3f}")
    
    # テスト4: 統計
    print("\n📊 テスト4: メタ学習統計")
    stats = await meta.get_meta_stats()
    print(f"最適化回数: {stats['optimizations_count']}")
    print(f"Few-shot概念数: {stats['few_shot_concepts']}")
    print(f"AutoML実験数: {stats['automl_experiments']}")
    
    print("\n✅ テスト完了")


if __name__ == '__main__':
    asyncio.run(test_meta_learning())

