#!/usr/bin/env python3
"""
💎 Quality Optimizer - 記憶品質最適化ツール
量より質！本当に価値ある記憶だけを残す

実施内容:
1. テスト/デモデータ削除
2. 重複排除
3. 重要度の再評価
4. 低品質データのアーカイブ
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import sqlite3
from typing import Dict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("QualityOptimizer")


class QualityOptimizer:
    """記憶品質最適化"""
    
    def __init__(self):
        logger.info("💎 Quality Optimizer 初期化中...")
        
        self.db_path = Path('/root/ai_learning.db')
        
        logger.info("✅ Quality Optimizer 準備完了")
    
    async def analyze_quality(self) -> Dict:
        """品質分析"""
        logger.info("🔍 品質分析開始...")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        analysis = {
            'total': 0,
            'test_data': 0,
            'duplicates': 0,
            'low_importance': 0,
            'high_quality': 0
        }
        
        # 総数
        cursor.execute("SELECT COUNT(*) FROM knowledge")
        analysis['total'] = cursor.fetchone()[0]
        
        # テスト/デモデータ
        cursor.execute("""
            SELECT COUNT(*) FROM knowledge 
            WHERE title LIKE '%test%' 
               OR title LIKE '%テスト%' 
               OR title LIKE '%デモ%'
               OR title LIKE '%demo%'
               OR content LIKE '%テストデータ%'
        """)
        analysis['test_data'] = cursor.fetchone()[0]
        
        # 重要度5以下
        cursor.execute("SELECT COUNT(*) FROM knowledge WHERE importance <= 5")
        analysis['low_importance'] = cursor.fetchone()[0]
        
        # 高品質（重要度8以上、テストでない）
        cursor.execute("""
            SELECT COUNT(*) FROM knowledge 
            WHERE importance >= 8 
              AND title NOT LIKE '%test%'
              AND title NOT LIKE '%テスト%'
              AND title NOT LIKE '%デモ%'
        """)
        analysis['high_quality'] = cursor.fetchone()[0]
        
        conn.close()
        
        # 品質スコア計算
        if analysis['total'] > 0:
            quality_score = (analysis['high_quality'] / analysis['total']) * 100
            noise_ratio = (analysis['test_data'] / analysis['total']) * 100
        else:
            quality_score = 0
            noise_ratio = 0
        
        analysis['quality_score'] = quality_score
        analysis['noise_ratio'] = noise_ratio
        
        logger.info(f"  品質スコア: {quality_score:.1f}%")
        logger.info(f"  ノイズ率: {noise_ratio:.1f}%")
        
        return analysis
    
    async def remove_test_data(self, dry_run: bool = False) -> Dict:
        """テスト/デモデータ削除"""
        logger.info("🗑️  テスト/デモデータ削除中...")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 削除対象を確認
        cursor.execute("""
            SELECT id, title, importance FROM knowledge 
            WHERE (title LIKE '%test%' 
               OR title LIKE '%テスト%' 
               OR title LIKE '%デモ%'
               OR title LIKE '%demo%')
              AND importance < 9
        """)
        to_delete = cursor.fetchall()
        
        result = {
            'found': len(to_delete),
            'deleted': 0
        }
        
        if not dry_run:
            for row in to_delete:
                cursor.execute("DELETE FROM knowledge WHERE id = ?", (row[0],))
                result['deleted'] += 1
            
            conn.commit()
        
        conn.close()
        
        logger.info(f"  ✅ 削除: {result['deleted']}件")
        
        return result
    
    async def upgrade_importance(self) -> Dict:
        """重要度の再評価・アップグレード"""
        logger.info("⬆️  重要度再評価中...")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        result = {'upgraded': 0}
        
        # 特定キーワードを含む記憶は重要度アップ
        important_keywords = [
            ('RunPod', 8),
            ('X280', 8),
            ('Trinity', 8),
            ('ManaOS', 8),
            ('成功', 7),
            ('完了', 7),
            ('設定', 7),
            ('重要', 9)
        ]
        
        for keyword, target_importance in important_keywords:
            cursor.execute("""
                UPDATE knowledge 
                SET importance = ?
                WHERE (content LIKE ? OR title LIKE ?)
                  AND importance < ?
                  AND title NOT LIKE '%test%'
                  AND title NOT LIKE '%テスト%'
            """, (target_importance, f'%{keyword}%', f'%{keyword}%', target_importance))
            
            result['upgraded'] += cursor.rowcount
        
        conn.commit()
        conn.close()
        
        logger.info(f"  ✅ アップグレード: {result['upgraded']}件")
        
        return result
    
    async def remove_duplicates(self) -> Dict:
        """重複削除"""
        logger.info("🔄 重複削除中...")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 同じタイトルの重複を検出
        cursor.execute("""
            SELECT title, COUNT(*) as cnt 
            FROM knowledge 
            WHERE title IS NOT NULL
            GROUP BY title 
            HAVING cnt > 1
        """)
        duplicates = cursor.fetchall()
        
        result = {'found': len(duplicates), 'deleted': 0}
        
        for title, count in duplicates:
            # 最新のものだけ残して古いものを削除
            cursor.execute("""
                DELETE FROM knowledge 
                WHERE id NOT IN (
                    SELECT id FROM knowledge 
                    WHERE title = ? 
                    ORDER BY created_at DESC 
                    LIMIT 1
                ) AND title = ?
            """, (title, title))
            
            result['deleted'] += cursor.rowcount
        
        conn.commit()
        conn.close()
        
        logger.info(f"  ✅ 重複削除: {result['deleted']}件")
        
        return result
    
    async def optimize_all(self) -> Dict:
        """全品質最適化実行"""
        logger.info("💎 品質最適化開始...")
        
        # Before
        before = await self.analyze_quality()
        
        results = {
            'before': before,
            'operations': {}
        }
        
        # 1. テスト/デモデータ削除
        test_result = await self.remove_test_data(dry_run=False)
        results['operations']['test_removal'] = test_result
        
        # 2. 重複削除
        dup_result = await self.remove_duplicates()
        results['operations']['duplicate_removal'] = dup_result
        
        # 3. 重要度アップグレード
        upgrade_result = await self.upgrade_importance()
        results['operations']['importance_upgrade'] = upgrade_result
        
        # After
        after = await self.analyze_quality()
        results['after'] = after
        
        # 改善率
        results['improvement'] = {
            'quality_score': after['quality_score'] - before['quality_score'],
            'noise_reduction': before['noise_ratio'] - after['noise_ratio'],
            'total_reduction': before['total'] - after['total']
        }
        
        logger.info("✅ 品質最適化完了")
        
        return results


# 実行
async def main():
    print("""
╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║       💎 Quality Optimizer - 記憶品質最適化                    ║
║                                                                ║
║       量より質！本当に価値ある記憶だけを残す                   ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
    """)
    
    optimizer = QualityOptimizer()
    
    # Before分析
    print("\n📊 品質分析（最適化前）")
    print("="*70)
    
    before = await optimizer.analyze_quality()
    
    print(f"総記憶数      : {before['total']}件")
    print(f"高品質        : {before['high_quality']}件 ({before['quality_score']:.1f}%)")
    print(f"テスト/デモ   : {before['test_data']}件 ({before['noise_ratio']:.1f}%)")
    print(f"低重要度      : {before['low_importance']}件")
    
    # 最適化実行
    print("\n💎 品質最適化実行中...")
    print("="*70 + "\n")
    
    results = await optimizer.optimize_all()
    
    # After
    print("\n📊 最適化結果")
    print("="*70)
    
    print("削除:")
    print(f"  テスト/デモ   : {results['operations']['test_removal']['deleted']}件")
    print(f"  重複          : {results['operations']['duplicate_removal']['deleted']}件")
    print(f"  総削除        : {results['improvement']['total_reduction']}件")
    
    print("\nアップグレード:")
    print(f"  重要度向上    : {results['operations']['importance_upgrade']['upgraded']}件")
    
    print("\n最終状態:")
    print(f"  総記憶数      : {results['after']['total']}件")
    print(f"  高品質        : {results['after']['high_quality']}件 ({results['after']['quality_score']:.1f}%)")
    print(f"  ノイズ率      : {results['after']['noise_ratio']:.1f}%")
    
    print("\n改善:")
    print(f"  品質スコア    : {results['before']['quality_score']:.1f}% → {results['after']['quality_score']:.1f}% (+{results['improvement']['quality_score']:.1f}%)")
    print(f"  ノイズ削減    : {results['before']['noise_ratio']:.1f}% → {results['after']['noise_ratio']:.1f}% (-{results['improvement']['noise_reduction']:.1f}%)")
    
    print("\n🎉 品質最適化完了！量より質を実現！")


if __name__ == '__main__':
    asyncio.run(main())

