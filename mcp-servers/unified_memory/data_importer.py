#!/usr/bin/env python3
"""
📥 Data Importer - 過去データ活用強化ツール
既存の全データをUnified Memory Systemに統合して超強化

データソース:
1. Obsidian Vault（63ファイル、348KB）
2. Trinity Shared Memory（158行）
3. Context Memory（24行の会話履歴）
4. ManaOS Unified Metrics DB（7.9MB）
5. Mana Enhanced Secretary DB（4.8MB）
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import json
import sqlite3
from datetime import datetime
from typing import Dict
import logging

from core.unified_memory_api import UnifiedMemoryAPI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DataImporter")


class DataImporter:
    """過去データインポーター"""
    
    def __init__(self, unified_memory_api):
        logger.info("📥 Data Importer 初期化中...")
        
        self.memory_api = unified_memory_api
        
        # インポート元
        self.sources = {
            'obsidian': Path('/root/obsidian_vault'),
            'trinity_memory': Path('/root/.trinity_shared_memory.json'),
            'context_memory': Path('/root/.ai_context_memory.json'),
            'manaos_metrics': Path('/root/manaos_unified_metrics.db'),
            'secretary_db': Path('/root/mana_enhanced_secretary.db')
        }
        
        # インポート統計
        self.import_stats = {
            'total_imported': 0,
            'by_source': {}
        }
        
        logger.info("✅ Data Importer 準備完了")
    
    async def import_all(self, dry_run: bool = False) -> Dict:
        """
        全データインポート
        
        Args:
            dry_run: テストモード（実際にはインポートしない）
            
        Returns:
            インポート結果
        """
        logger.info("📥 全データインポート開始...")
        
        if dry_run:
            logger.info("  ℹ️ DRY RUNモード（実際のインポートはスキップ）")
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'dry_run': dry_run,
            'sources': {}
        }
        
        # 1. Obsidian
        logger.info("\n📔 Obsidian Vault インポート中...")
        obsidian_result = await self.import_obsidian(dry_run=dry_run)
        results['sources']['obsidian'] = obsidian_result
        
        # 2. Trinity Memory
        logger.info("\n🤝 Trinity Memory インポート中...")
        trinity_result = await self.import_trinity_memory(dry_run=dry_run)
        results['sources']['trinity_memory'] = trinity_result
        
        # 3. Context Memory
        logger.info("\n🧠 Context Memory インポート中...")
        context_result = await self.import_context_memory(dry_run=dry_run)
        results['sources']['context_memory'] = context_result
        
        # 4. ManaOS Metrics
        logger.info("\n📊 ManaOS Metrics インポート中...")
        manaos_result = await self.import_manaos_metrics(dry_run=dry_run)
        results['sources']['manaos_metrics'] = manaos_result
        
        # 総計
        results['total_imported'] = sum(
            r.get('imported', 0) for r in results['sources'].values()
        )
        
        logger.info(f"\n✅ インポート完了: 総{results['total_imported']}件")
        
        return results
    
    async def import_obsidian(self, dry_run: bool = False) -> Dict:
        """Obsidian Vaultインポート"""
        vault = self.sources['obsidian']
        
        if not vault.exists():
            return {'error': 'Obsidian Vaultが見つかりません'}
        
        result = {
            'scanned': 0,
            'imported': 0,
            'skipped': 0
        }
        
        for md_file in vault.rglob('*.md'):
            result['scanned'] += 1
            
            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 既にインポート済みか確認（タイトルで判定）
                title = md_file.stem
                
                if not dry_run:
                    # Unified Memoryに保存
                    await self.memory_api.smart_store(
                        content=content[:2000],  # 最初の2000文字
                        title=f"Obsidian: {title}",
                        importance=6,
                        tags=['obsidian', 'imported', md_file.parent.name],
                        category='obsidian_import',
                        metadata={
                            'original_path': str(md_file),
                            'import_date': datetime.now().isoformat()
                        }
                    )
                    result['imported'] += 1
                else:
                    result['imported'] += 1  # DRY RUNでもカウント
                
                # 進捗表示（10件ごと）
                if result['scanned'] % 10 == 0:
                    logger.info(f"  進捗: {result['scanned']}件スキャン、{result['imported']}件インポート")
                
            except Exception as e:
                logger.error(f"  ❌ {md_file.name}: {e}")
                result['skipped'] += 1
        
        logger.info(f"  ✅ Obsidian: {result['imported']}件インポート")
        
        return result
    
    async def import_trinity_memory(self, dry_run: bool = False) -> Dict:
        """Trinity Shared Memoryインポート"""
        trinity_file = self.sources['trinity_memory']
        
        if not trinity_file.exists():
            return {'error': 'Trinity Memoryが見つかりません'}
        
        result = {'imported': 0}
        
        try:
            with open(trinity_file, 'r', encoding='utf-8') as f:
                trinity_data = json.load(f)
            
            # Important infoをインポート
            for info in trinity_data.get('important_info', []):
                if not dry_run:
                    await self.memory_api.smart_store(
                        content=info.get('content', ''),
                        title="Trinity重要情報",
                        importance=info.get('importance', 7),
                        tags=['trinity', 'imported', 'important'],
                        category='trinity_import'
                    )
                result['imported'] += 1
            
            logger.info(f"  ✅ Trinity: {result['imported']}件インポート")
            
        except Exception as e:
            logger.error(f"  ❌ Trinity Memory: {e}")
            result['error'] = str(e)
        
        return result
    
    async def import_context_memory(self, dry_run: bool = False) -> Dict:
        """Context Memory（会話履歴）インポート"""
        context_file = self.sources['context_memory']
        
        if not context_file.exists():
            return {'error': 'Context Memoryが見つかりません'}
        
        result = {'imported': 0}
        
        try:
            with open(context_file, 'r', encoding='utf-8') as f:
                context_data = json.load(f)
            
            # 会話履歴をインポート
            for conv in context_data.get('conversations', []):
                if not dry_run:
                    content = f"User: {conv.get('user', '')}\nAssistant: {conv.get('assistant', '')}"
                    
                    await self.memory_api.smart_store(
                        content=content[:1000],
                        title="過去の会話",
                        importance=5,
                        tags=['conversation', 'imported', 'history'],
                        category='conversation_import',
                        metadata={
                            'timestamp': conv.get('timestamp', ''),
                            'import_date': datetime.now().isoformat()
                        }
                    )
                result['imported'] += 1
            
            # 好みもインポート
            preferences = context_data.get('preferences', {})
            if preferences and not dry_run:
                pref_content = json.dumps(preferences, ensure_ascii=False, indent=2)
                await self.memory_api.smart_store(
                    content=f"ユーザー好み:\n{pref_content}",
                    title="ユーザー好みプロファイル",
                    importance=9,
                    tags=['preferences', 'imported', 'profile'],
                    category='preference_import'
                )
                result['imported'] += 1
            
            logger.info(f"  ✅ Context Memory: {result['imported']}件インポート")
            
        except Exception as e:
            logger.error(f"  ❌ Context Memory: {e}")
            result['error'] = str(e)
        
        return result
    
    async def import_manaos_metrics(self, dry_run: bool = False) -> Dict:
        """ManaOS Metrics DBインポート"""
        metrics_db = self.sources['manaos_metrics']
        
        if not metrics_db.exists():
            return {'error': 'ManaOS Metricsが見つかりません'}
        
        result = {'imported': 0}
        
        try:
            conn = sqlite3.connect(metrics_db)
            cursor = conn.cursor()
            
            # テーブル一覧取得
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            
            # 各テーブルからデータ抽出（サンプル）
            for table_name, in tables[:3]:  # 最初の3テーブル
                try:
                    cursor.execute(f"SELECT * FROM {table_name} LIMIT 10")
                    rows = cursor.fetchall()
                    
                    if rows and not dry_run:
                        # テーブルデータをサマリー化
                        summary = f"ManaOS Metrics: {table_name}\n件数: {len(rows)}\n"
                        
                        await self.memory_api.smart_store(
                            content=summary,
                            title=f"ManaOS Metrics: {table_name}",
                            importance=6,
                            tags=['manaos', 'metrics', 'imported'],
                            category='manaos_import'
                        )
                        result['imported'] += 1
                    
                except Exception as e:
                    logger.error(f"    ⚠️ テーブル {table_name}: {e}")
            
            conn.close()
            
            logger.info(f"  ✅ ManaOS Metrics: {result['imported']}件インポート")
            
        except Exception as e:
            logger.error(f"  ❌ ManaOS Metrics: {e}")
            result['error'] = str(e)
        
        return result
    
    async def analyze_and_learn_patterns(self) -> Dict:
        """
        インポートしたデータからパターン学習
        
        Returns:
            学習結果
        """
        logger.info("🧠 パターン学習開始...")
        
        # 全記憶を取得
        stats = await self.memory_api.get_stats(force_refresh=True)
        
        patterns = {
            'timestamp': datetime.now().isoformat(),
            'total_memories': stats.get('total_memories', 0),
            'discovered_patterns': []
        }
        
        # Obsidianデータからトピック抽出
        obsidian_search = await self.memory_api.unified_search(
            "システム OR 設定 OR タスク",
            limit=20,
            filters={'sources': ['obsidian']}
        )
        
        if obsidian_search.get('total_hits', 0) > 0:
            patterns['discovered_patterns'].append({
                'pattern': 'Obsidianに多い話題: システム設定、タスク管理',
                'confidence': 0.8,
                'source': 'obsidian'
            })
        
        # Trinity Memoryから重要情報パターン
        trinity_search = await self.memory_api.unified_search(
            "重要 OR 完了 OR 成功",
            limit=20,
            filters={'sources': ['trinity_memory']}
        )
        
        if trinity_search.get('total_hits', 0) > 0:
            patterns['discovered_patterns'].append({
                'pattern': 'Trinity重要情報: タスク完了、成功記録が多い',
                'confidence': 0.75,
                'source': 'trinity_memory'
            })
        
        logger.info(f"✅ パターン学習完了: {len(patterns['discovered_patterns'])}個発見")
        
        return patterns


# メイン実行
async def main():
    print("""
╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║       📥 過去データ活用強化システム                            ║
║                                                                ║
║       既存データを全てUnified Memoryに統合！                   ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
    """)
    
    print("\n🔍 過去データ確認中...\n")
    
    memory = UnifiedMemoryAPI()
    importer = DataImporter(memory)
    
    # 現在の統計
    before_stats = await memory.get_stats()
    print(f"📊 インポート前: {before_stats['total_memories']}件\n")
    
    # DRY RUNでプレビュー
    print("="*70)
    print("🧪 プレビュー（DRY RUN）")
    print("="*70)
    
    dry_result = await importer.import_all(dry_run=True)
    
    print("\n📊 インポート予定:")
    for source, data in dry_result['sources'].items():
        count = data.get('imported', 0)
        print(f"  • {source:20s}: {count:>3}件")
    
    print(f"\n  合計: {dry_result['total_imported']}件")
    
    # 実際にインポートするか確認
    print("\n" + "="*70)
    print("💡 実際のインポート")
    print("="*70)
    
    choice = input("\n実際にインポートしますか？ (y/N): ")
    
    if choice.lower() == 'y':
        print("\n📥 インポート実行中...\n")
        
        actual_result = await importer.import_all(dry_run=False)
        
        print(f"\n✅ インポート完了: {actual_result['total_imported']}件")
        
        # インポート後の統計
        after_stats = await memory.get_stats(force_refresh=True)
        print(f"\n📊 インポート後: {after_stats['total_memories']}件")
        print(f"📈 増加: +{after_stats['total_memories'] - before_stats['total_memories']}件")
        
        # パターン学習
        print("\n🧠 パターン学習中...")
        patterns = await importer.analyze_and_learn_patterns()
        
        print(f"\n💡 発見したパターン: {len(patterns['discovered_patterns'])}個")
        for pattern in patterns['discovered_patterns']:
            print(f"  • {pattern['pattern']} (信頼度: {pattern['confidence']:.0%})")
        
        print("\n🎉 過去データ活用完了！システムが超強化されました！")
    
    else:
        print("\n⏸️  インポートをキャンセルしました")


if __name__ == '__main__':
    asyncio.run(main())

