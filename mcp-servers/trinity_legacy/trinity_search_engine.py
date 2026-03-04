#!/usr/bin/env python3
"""
🔍 Trinity Unified Search Engine
全データソースを横断検索する統合検索エンジン

検索対象:
- 会話履歴（AI Learning System）
- Obsidianメモ・タスク・デイリーノート
- システムログ
- システムメトリクス（時系列データ）
- セキュリティレポート
"""

import asyncio
import logging
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TrinitySearchEngine:
    """Trinity統合検索エンジン"""
    
    def __init__(self):
        self.search_targets = {
            'conversations': {
                'source': 'AI Learning System',
                'endpoint': 'http://localhost:8600/search',
                'description': '過去の会話を検索'
            },
            'obsidian': {
                'source': 'Obsidian Vault',
                'path': '/root/obsidian_vault',
                'description': 'メモ・タスク・デイリーノートを検索'
            },
            'system_logs': {
                'source': 'System Logs',
                'path': '/root/logs',
                'description': 'システムログを検索'
            },
            'manaos_metrics': {
                'source': 'ManaOS Unified Monitor',
                'db': '/root/manaos_unified_metrics.db',
                'description': 'システムメトリクスを検索'
            },
            'security_reports': {
                'source': 'Security Reports',
                'path': '/root/security_reports',
                'description': 'セキュリティレポートを検索'
            }
        }
        
        logger.info("🔍 Trinity Search Engine initialized")
    
    async def universal_search(self, query: str, filters: Optional[Dict] = None) -> Dict[str, Any]:
        """
        全データソースを横断検索
        
        Args:
            query: 検索クエリ
            filters: 検索対象フィルター（例: {'sources': ['conversations', 'obsidian']}）
        
        Returns:
            検索結果
        """
        logger.info(f"🔍 Searching for: {query}")
        
        results = {
            'query': query,
            'timestamp': datetime.now().isoformat(),
            'matches': []
        }
        
        # 検索タスクを並列実行
        search_tasks = []
        
        # フィルター確認
        enabled_sources = filters.get('sources', []) if filters else []
        
        # 1. 会話履歴検索
        if not enabled_sources or 'conversations' in enabled_sources:
            search_tasks.append(self._search_conversations(query))
        
        # 2. Obsidian検索
        if not enabled_sources or 'obsidian' in enabled_sources:
            search_tasks.append(self._search_obsidian(query))
        
        # 3. システムメトリクス検索
        if not enabled_sources or 'metrics' in enabled_sources:
            search_tasks.append(self._search_metrics(query))
        
        # 4. ログ検索
        if not enabled_sources or 'logs' in enabled_sources:
            search_tasks.append(self._search_logs(query))
        
        # 5. セキュリティレポート検索
        if not enabled_sources or 'security' in enabled_sources:
            search_tasks.append(self._search_security_reports(query))
        
        # 並列実行
        all_results = await asyncio.gather(*search_tasks, return_exceptions=True)
        
        # 結果統合
        for result in all_results:
            if isinstance(result, dict) and 'items' in result:
                results['matches'].extend(result['items'])
            elif isinstance(result, Exception):
                logger.warning(f"Search task failed: {result}")
        
        # 関連度でソート
        results['matches'] = sorted(
            results['matches'], 
            key=lambda x: x.get('relevance_score', 0), 
            reverse=True
        )
        
        logger.info(f"✅ Found {len(results['matches'])} matches")
        
        return results
    
    async def _search_conversations(self, query: str) -> Dict:
        """会話履歴を検索（AI Learning System）"""
        logger.info("  🧠 Searching conversations...")
        
        try:
            response = requests.post(
                'http://localhost:8600/search',
                json={'query': query, 'limit': 10},
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                items = []
                
                for item in data.get('results', []):
                    items.append({
                        'type': 'conversation',
                        'content': item.get('content', ''),
                        'timestamp': item.get('created_at', ''),
                        'category': item.get('category', ''),
                        'relevance_score': item.get('similarity', 0) * 10  # 0-1を0-10に変換
                    })
                
                logger.info(f"    ✅ Found {len(items)} conversation matches")
                return {'source': 'conversations', 'items': items}
            
        except Exception as e:
            logger.warning(f"    ⚠️ Conversation search failed: {e}")
        
        return {'source': 'conversations', 'items': []}
    
    async def _search_obsidian(self, query: str) -> Dict:
        """Obsidianを検索"""
        logger.info("  📝 Searching Obsidian...")
        
        matches = []
        vault_path = Path('/root/obsidian_vault')
        
        if not vault_path.exists():
            return {'source': 'obsidian', 'items': []}
        
        try:
            query_lower = query.lower()
            
            # 全.mdファイルを検索
            for md_file in vault_path.rglob('*.md'):
                try:
                    content = md_file.read_text(encoding='utf-8')
                    
                    if query_lower in content.lower():
                        # マッチした行を抽出
                        lines = content.split('\n')
                        matched_lines = []
                        
                        for i, line in enumerate(lines):
                            if query_lower in line.lower():
                                # 前後の文脈も含める
                                context_start = max(0, i - 1)
                                context_end = min(len(lines), i + 2)
                                context = lines[context_start:context_end]
                                matched_lines.append(' '.join(context))
                        
                        matches.append({
                            'type': 'obsidian_note',
                            'file': str(md_file.relative_to(vault_path)),
                            'matched_lines': matched_lines[:3],  # 最大3行
                            'relevance_score': min(len(matched_lines), 10),
                            'modified': datetime.fromtimestamp(md_file.stat().st_mtime).isoformat()
                        })
                
                except Exception:
                    continue
            
            logger.info(f"    ✅ Found {len(matches)} Obsidian matches")
            
        except Exception as e:
            logger.warning(f"    ⚠️ Obsidian search failed: {e}")
        
        return {'source': 'obsidian', 'items': matches}
    
    async def _search_metrics(self, query: str) -> Dict:
        """システムメトリクスを検索（時系列データ）"""
        logger.info("  📊 Searching metrics...")
        
        matches = []
        db_path = '/root/manaos_unified_metrics.db'
        
        if not Path(db_path).exists():
            return {'source': 'metrics', 'items': []}
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # クエリ解析
            time_filter = self._parse_time_filter(query)
            metric_filter = self._parse_metric_filter(query)
            
            sql = 'SELECT * FROM system_metrics WHERE 1=1'
            params = []
            
            if time_filter:
                sql += ' AND timestamp > ?'
                params.append(time_filter)
            
            if metric_filter:
                sql += f' AND {metric_filter["column"]} > ?'
                params.append(metric_filter['threshold'])
            
            sql += ' ORDER BY timestamp DESC LIMIT 20'
            
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            for row in rows:
                matches.append({
                    'type': 'system_metric',
                    'timestamp': row[1],
                    'cpu': row[2],
                    'memory': row[3],
                    'memory_used_gb': row[4],
                    'disk': row[5],
                    'process_count': row[6],
                    'relevance_score': 7
                })
            
            conn.close()
            
            logger.info(f"    ✅ Found {len(matches)} metric matches")
            
        except Exception as e:
            logger.warning(f"    ⚠️ Metrics search failed: {e}")
        
        return {'source': 'metrics', 'items': matches}
    
    async def _search_logs(self, query: str) -> Dict:
        """ログファイルを検索"""
        logger.info("  📋 Searching logs...")
        
        matches = []
        log_dir = Path('/root/logs')
        
        if not log_dir.exists():
            return {'source': 'logs', 'items': []}
        
        try:
            query_lower = query.lower()
            
            # 最近のログファイルのみ（過去7日間）
            recent_logs = []
            for log_file in log_dir.rglob('*.log'):
                try:
                    days_old = (datetime.now() - datetime.fromtimestamp(log_file.stat().st_mtime)).days
                    if days_old < 7:
                        recent_logs.append(log_file)
                except IOError:
                    continue
            
            for log_file in recent_logs[:10]:  # 最大10ファイル
                try:
                    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()[-1000:]  # 最新1000行
                        
                        matched_lines = [
                            line.strip() for line in lines
                            if query_lower in line.lower()
                        ]
                        
                        if matched_lines:
                            matches.append({
                                'type': 'log',
                                'file': str(log_file.name),
                                'matched_lines': matched_lines[-5:],  # 最新5件
                                'relevance_score': min(len(matched_lines), 10)
                            })
                except IOError:
                    continue
            
            logger.info(f"    ✅ Found {len(matches)} log matches")
            
        except Exception as e:
            logger.warning(f"    ⚠️ Log search failed: {e}")
        
        return {'source': 'logs', 'items': matches}
    
    async def _search_security_reports(self, query: str) -> Dict:
        """セキュリティレポートを検索"""
        logger.info("  🔐 Searching security reports...")
        
        matches = []
        security_dir = Path('/root/security_reports')
        
        if not security_dir.exists():
            return {'source': 'security', 'items': []}
        
        try:
            query_lower = query.lower()
            
            # 最近のレポート（過去30日間）
            for report_file in security_dir.glob('*.json'):
                try:
                    days_old = (datetime.now() - datetime.fromtimestamp(report_file.stat().st_mtime)).days
                    if days_old > 30:
                        continue
                    
                    with open(report_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        
                        # JSON全体を文字列化して検索
                        content_str = json.dumps(data, ensure_ascii=False).lower()
                        
                        if query_lower in content_str:
                            matches.append({
                                'type': 'security_report',
                                'file': report_file.name,
                                'summary': data.get('summary', 'No summary'),
                                'timestamp': data.get('timestamp', ''),
                                'relevance_score': 8
                            })
                except IOError:
                    continue
            
            logger.info(f"    ✅ Found {len(matches)} security report matches")
            
        except Exception as e:
            logger.warning(f"    ⚠️ Security report search failed: {e}")
        
        return {'source': 'security', 'items': matches}
    
    def _parse_time_filter(self, query: str) -> Optional[str]:
        """時間フィルター解析"""
        now = datetime.now()
        query_lower = query.lower()
        
        if '1時間前' in query_lower or '1h' in query_lower:
            return (now - timedelta(hours=1)).isoformat()
        elif '今日' in query_lower or 'today' in query_lower:
            return now.replace(hour=0, minute=0, second=0).isoformat()
        elif '昨日' in query_lower or 'yesterday' in query_lower:
            return (now - timedelta(days=1)).replace(hour=0, minute=0).isoformat()
        elif '1週間' in query_lower or '7日' in query_lower or '1week' in query_lower:
            return (now - timedelta(days=7)).isoformat()
        elif '24時間' in query_lower or '24h' in query_lower:
            return (now - timedelta(hours=24)).isoformat()
        
        return None
    
    def _parse_metric_filter(self, query: str) -> Optional[Dict]:
        """メトリクスフィルター解析"""
        query_lower = query.lower()
        
        if 'cpu' in query_lower:
            if '高' in query_lower or 'high' in query_lower or '多' in query_lower:
                return {'column': 'cpu_percent', 'threshold': 70}
        
        if 'メモリ' in query_lower or 'memory' in query_lower or 'ram' in query_lower:
            if '高' in query_lower or 'high' in query_lower or '多' in query_lower:
                return {'column': 'memory_percent', 'threshold': 75}
        
        if 'ディスク' in query_lower or 'disk' in query_lower:
            if '高' in query_lower or 'high' in query_lower or '多' in query_lower:
                return {'column': 'disk_percent', 'threshold': 80}
        
        return None


# テスト用
async def test_search():
    """検索エンジンテスト"""
    engine = TrinitySearchEngine()
    
    # テスト1: 全検索
    print("\n" + "="*60)
    print("テスト1: 汎用検索")
    print("="*60)
    results = await engine.universal_search("Trinity")
    print(f"Found {len(results['matches'])} matches")
    
    for i, match in enumerate(results['matches'][:3], 1):
        print(f"\n{i}. {match['type']}")
        if match['type'] == 'obsidian_note':
            print(f"   File: {match['file']}")
        elif match['type'] == 'conversation':
            print(f"   Content: {match['content'][:80]}...")
    
    # テスト2: メトリクス検索
    print("\n" + "="*60)
    print("テスト2: CPU高い時間を検索")
    print("="*60)
    results = await engine.universal_search("CPU高い", {'sources': ['metrics']})
    print(f"Found {len(results['matches'])} matches")
    
    for i, match in enumerate(results['matches'][:3], 1):
        print(f"\n{i}. {match['timestamp']}")
        print(f"   CPU: {match['cpu']:.1f}% | RAM: {match['memory']:.1f}%")


if __name__ == '__main__':
    asyncio.run(test_search())



