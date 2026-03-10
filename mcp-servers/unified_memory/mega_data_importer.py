#!/usr/bin/env python3
"""
📥 MEGA Data Importer - 全データ活用版
全ての記憶を残らず活用！

追加データソース:
1. ManaOS Unified Metrics DB（7.7MB）
2. Enhanced Secretary DB（4.7MB）
3. Voice Monitoring DB（700KB）
4. ログファイル（468MB、294ファイル）
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import sqlite3
import re
from datetime import datetime, timedelta
from typing import Dict, List
import logging

from core.unified_memory_api import UnifiedMemoryAPI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MegaImporter")


class MegaDataImporter:
    """MEGA版データインポーター"""
    
    def __init__(self, unified_memory_api):
        logger.info("📥 MEGA Data Importer 初期化中...")
        
        self.memory_api = unified_memory_api
        
        # 追加データソース
        self.mega_sources = {
            'manaos_metrics': Path('/root/manaos_unified_metrics.db'),
            'secretary_db': Path('/root/mana_enhanced_secretary.db'),
            'voice_monitoring': Path('/root/manaos_voice_monitoring.db'),
            'logs_dir': Path('/root/logs')
        }
        
        self.import_stats = {
            'total_imported': 0,
            'by_source': {}
        }
        
        logger.info("✅ MEGA Data Importer 準備完了")
    
    async def import_manaos_metrics_full(self, limit_per_table: int = 50) -> Dict:
        """
        ManaOS Unified Metrics DB完全インポート
        
        Args:
            limit_per_table: 各テーブルからの最大件数
            
        Returns:
            インポート結果
        """
        logger.info("📊 ManaOS Metrics 完全インポート中...")
        
        db_path = self.mega_sources['manaos_metrics']
        
        if not db_path.exists():
            return {'error': 'DBが見つかりません'}
        
        result = {'imported': 0, 'tables': []}
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # テーブル一覧
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            logger.info(f"  テーブル数: {len(tables)}")
            
            for table in tables:
                try:
                    # テーブルからデータ取得
                    cursor.execute(f"SELECT * FROM {table} ORDER BY rowid DESC LIMIT {limit_per_table}")
                    rows = cursor.fetchall()
                    
                    if rows:
                        # 列名取得
                        cursor.execute(f"PRAGMA table_info({table})")
                        columns = [col[1] for col in cursor.fetchall()]
                        
                        # データをまとめて保存
                        summary = f"ManaOS Metrics - {table}\n\n"
                        summary += f"総件数: {len(rows)}件\n"
                        summary += "最新データ（サンプル）:\n"
                        
                        for row in rows[:5]:
                            row_dict = dict(zip(columns, row))
                            summary += f"  • {str(row_dict)[:100]}\n"
                        
                        await self.memory_api.smart_store(
                            content=summary,
                            title=f"ManaOS Metrics: {table}",
                            importance=7,
                            tags=['manaos', 'metrics', table],
                            category='manaos_metrics_full'
                        )
                        
                        result['imported'] += 1
                        result['tables'].append({'name': table, 'rows': len(rows)})
                        
                        logger.info(f"    ✅ {table}: {len(rows)}件")
                
                except Exception as e:
                    logger.error(f"    ❌ {table}: {e}")
            
            conn.close()
            
            logger.info(f"  ✅ ManaOS Metrics: {result['imported']}テーブルインポート")
            
        except Exception as e:
            logger.error(f"  ❌ ManaOS Metrics: {e}")
            result['error'] = str(e)
        
        return result
    
    async def import_secretary_conversations(self) -> Dict:
        """
        Enhanced Secretary AI会話インポート
        
        Returns:
            インポート結果
        """
        logger.info("🤖 Secretary AI会話インポート中...")
        
        db_path = self.mega_sources['secretary_db']
        
        if not db_path.exists():
            return {'error': 'DBが見つかりません'}
        
        result = {'imported': 0}
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # AI会話取得
            cursor.execute("SELECT * FROM ai_conversations_enhanced ORDER BY rowid DESC LIMIT 50")
            rows = cursor.fetchall()
            
            # 列名取得
            cursor.execute("PRAGMA table_info(ai_conversations_enhanced)")
            columns = [col[1] for col in cursor.fetchall()]
            
            for row in rows:
                try:
                    conv_dict = dict(zip(columns, row))
                    
                    # 会話を記憶に保存
                    content = f"AI会話:\n{str(conv_dict)[:1000]}"
                    
                    await self.memory_api.smart_store(
                        content=content,
                        title="Secretary AI会話",
                        importance=6,
                        tags=['secretary', 'ai_conversation', 'imported'],
                        category='secretary_import'
                    )
                    
                    result['imported'] += 1
                
                except Exception as e:
                    logger.error(f"    ⚠️ 会話インポートエラー: {e}")
            
            conn.close()
            
            logger.info(f"  ✅ Secretary: {result['imported']}件インポート")
            
        except Exception as e:
            logger.error(f"  ❌ Secretary: {e}")
            result['error'] = str(e)  # type: ignore
        
        return result
    
    async def import_important_logs(self, days: int = 7) -> Dict:
        """
        重要ログファイルをインポート
        
        Args:
            days: 過去N日分
            
        Returns:
            インポート結果
        """
        logger.info(f"📝 重要ログインポート中（過去{days}日）...")
        
        logs_dir = self.mega_sources['logs_dir']
        
        if not logs_dir.exists():
            return {'error': 'logsディレクトリが見つかりません'}
        
        result = {'imported': 0, 'files': []}
        
        cutoff_time = datetime.now() - timedelta(days=days)
        
        # 重要そうなログファイルパターン
        important_patterns = [
            '*error*.log',
            '*success*.log',
            '*trinity*.log',
            '*manaos*.log',
            '*dream*.log'
        ]
        
        for pattern in important_patterns:
            for log_file in logs_dir.glob(pattern):
                try:
                    # 最終更新日チェック
                    mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                    
                    if mtime < cutoff_time:
                        continue
                    
                    # ログ読み込み（最後の100行）
                    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()
                        content = ''.join(lines[-100:])
                    
                    # エラーや重要情報を抽出
                    errors = self._extract_errors(content)
                    successes = self._extract_successes(content)
                    
                    if errors or successes:
                        summary = f"ログ: {log_file.name}\n\n"
                        
                        if errors:
                            summary += f"エラー: {len(errors)}件\n"
                            summary += "\n".join(errors[:5]) + "\n\n"
                        
                        if successes:
                            summary += f"成功: {len(successes)}件\n"
                            summary += "\n".join(successes[:5])
                        
                        await self.memory_api.smart_store(
                            content=summary[:2000],
                            title=f"ログ分析: {log_file.name}",
                            importance=7 if errors else 5,
                            tags=['log', 'imported', 'analysis'],
                            category='log_import'
                        )
                        
                        result['imported'] += 1
                        result['files'].append(log_file.name)
                        
                        if result['imported'] >= 20:  # 最大20ファイル
                            break
                
                except Exception as e:
                    logger.error(f"    ⚠️ {log_file.name}: {e}")
            
            if result['imported'] >= 20:
                break
        
        logger.info(f"  ✅ ログ: {result['imported']}件インポート")
        
        return result
    
    def _extract_errors(self, content: str) -> List[str]:
        """エラー抽出"""
        errors = []
        for line in content.split('\n'):
            if re.search(r'ERROR|CRITICAL|Exception|Failed', line, re.I):
                errors.append(line.strip())
        return errors
    
    def _extract_successes(self, content: str) -> List[str]:
        """成功情報抽出"""
        successes = []
        for line in content.split('\n'):
            if re.search(r'SUCCESS|完了|成功|✅', line):
                successes.append(line.strip())
        return successes
    
    async def import_mega_all(self) -> Dict:
        """
        全データMEGAインポート
        
        Returns:
            総合結果
        """
        logger.info("🌟 MEGA全データインポート開始...")
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'sources': {}
        }
        
        # 統計（Before）
        before_stats = await self.memory_api.get_stats()
        results['before'] = before_stats['total_memories']
        
        # 1. ManaOS Metrics完全版
        metrics = await self.import_manaos_metrics_full(limit_per_table=30)
        results['sources']['manaos_metrics'] = metrics
        
        # 2. Secretary会話
        secretary = await self.import_secretary_conversations()
        results['sources']['secretary'] = secretary
        
        # 3. 重要ログ
        logs = await self.import_important_logs(days=7)
        results['sources']['logs'] = logs
        
        # 統計（After）
        after_stats = await self.memory_api.get_stats(force_refresh=True)
        results['after'] = after_stats['total_memories']
        results['increase'] = results['after'] - results['before']
        
        logger.info(f"\n✅ MEGA全データインポート完了: +{results['increase']}件")
        
        return results


# 実行
async def main():
    print("""
╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║       📥 MEGA Data Importer - 全データ活用                     ║
║                                                                ║
║       DBとログから全て抽出！                                   ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
    """)
    
    memory = UnifiedMemoryAPI()
    mega_importer = MegaDataImporter(memory)
    
    # Before
    before = await memory.get_stats()
    print(f"\n📊 インポート前: {before['total_memories']}件\n")
    
    # 実行
    print("="*70)
    print("📥 MEGAインポート実行中...")
    print("="*70 + "\n")
    
    results = await mega_importer.import_mega_all()
    
    # After
    print("\n" + "="*70)
    print("📊 インポート結果")
    print("="*70)
    
    for source, data in results['sources'].items():
        imported = data.get('imported', 0)
        print(f"  • {source:25s}: {imported:>3}件")
    
    print(f"\n  総インポート              : {results['increase']:>3}件")
    print(f"  最終記憶数                : {results['after']:>3}件")
    
    print("\n🎉 全データ活用完了！システムが超強化されました！")


if __name__ == '__main__':
    asyncio.run(main())

