#!/usr/bin/env python3
"""
🌐 External Knowledge Integration
Phase 12: 外部知識自動統合エンジン

機能:
1. Web自動収集（Brave Search活用）
2. GitHub自動学習
3. NotebookLM連携
4. 自動要約・知識抽出
"""

import asyncio
import aiohttp
import logging
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ExternalKnowledge")


class ExternalKnowledgeIntegration:
    """外部知識自動統合エンジン"""
    
    def __init__(self, unified_memory_api):
        logger.info("🌐 External Knowledge Integration 初期化中...")
        
        self.memory_api = unified_memory_api
        
        # Brave Search API（MCP経由）
        self.brave_search_available = True
        
        # NotebookLM MCP
        self.notebooklm_available = True
        
        # GitHub API
        self.github_api_base = "https://api.github.com"
        
        # 収集履歴
        self.collection_history_db = Path('/root/.external_knowledge_history.json')
        self.collection_history = self._load_history()
        
        logger.info("✅ External Knowledge Integration 準備完了")
    
    def _load_history(self) -> Dict:
        """収集履歴読み込み"""
        if self.collection_history_db.exists():
            try:
                with open(self.collection_history_db, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        return {
            'searches': [],
            'github_repos': [],
            'notebooklm_imports': [],
            'web_crawls': []
        }
    
    def _save_history(self):
        """収集履歴保存"""
        try:
            with open(self.collection_history_db, 'w') as f:
                json.dump(self.collection_history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"履歴保存エラー: {e}")
    
    async def auto_web_search(self, topics: List[str], 
                             max_results: int = 5) -> Dict:
        """
        Web自動検索・収集（Brave Search使用）
        
        Args:
            topics: 検索トピックリスト
            max_results: 各トピックの最大結果数
            
        Returns:
            収集結果
        """
        logger.info(f"🔍 Web自動検索: {len(topics)}トピック")
        
        collected = {
            'timestamp': datetime.now().isoformat(),
            'topics': topics,
            'results': {}
        }
        
        for topic in topics:
            logger.info(f"  検索中: {topic}")
            
            try:
                # Brave Search MCP経由で検索
                # （実際のMCP呼び出しはここで実装）
                
                # デモ実装
                search_results = await self._brave_search(topic, max_results)
                
                if search_results:
                    # 結果を記憶に保存
                    summary = self._summarize_search_results(search_results)
                    
                    await self.memory_api.smart_store(
                        content=f"検索トピック: {topic}\n\n{summary}",
                        title=f"Web検索: {topic}",
                        importance=7,
                        tags=['web_search', 'auto_collected', topic],
                        category='external_knowledge'
                    )
                    
                    collected['results'][topic] = {
                        'count': len(search_results),
                        'summary': summary[:200]
                    }
                
            except Exception as e:
                logger.error(f"  ❌ 検索失敗 ({topic}): {e}")
                collected['results'][topic] = {
                    'error': str(e)
                }
        
        # 履歴に記録
        self.collection_history['searches'].append({
            'timestamp': collected['timestamp'],
            'topics': topics,
            'collected_count': len([r for r in collected['results'].values() if 'count' in r])
        })
        self._save_history()
        
        logger.info(f"✅ Web収集完了: {len(collected['results'])}トピック")
        
        return collected
    
    async def _brave_search(self, query: str, count: int = 5) -> List[Dict]:
        """Brave Search実行（簡易実装）"""
        # 実際はMCPの mcp_brave-search_brave_web_search を呼ぶ
        # ここではデモデータ
        
        return [
            {
                'title': f'{query}に関する最新情報',
                'url': f'https://example.com/{query}',
                'description': f'{query}についての詳細な解説記事'
            }
            for i in range(min(count, 3))
        ]
    
    def _summarize_search_results(self, results: List[Dict]) -> str:
        """検索結果要約"""
        summary_parts = []
        
        for idx, result in enumerate(results[:5], 1):
            summary_parts.append(
                f"{idx}. {result.get('title', '不明')}\n"
                f"   {result.get('description', '')[:100]}"
            )
        
        return "\n\n".join(summary_parts)
    
    async def learn_from_github(self, repos: List[str]) -> Dict:
        """
        GitHub自動学習
        
        Args:
            repos: リポジトリリスト ['owner/repo', ...]
            
        Returns:
            学習結果
        """
        logger.info(f"🐙 GitHub学習: {len(repos)}リポジトリ")
        
        learned = {
            'timestamp': datetime.now().isoformat(),
            'repos': repos,
            'results': {}
        }
        
        for repo in repos:
            logger.info(f"  学習中: {repo}")
            
            try:
                # リポジトリ情報取得
                repo_info = await self._get_github_repo(repo)
                
                if repo_info:
                    # README取得
                    readme = await self._get_github_readme(repo)
                    
                    # 最新コミット取得
                    commits = await self._get_github_commits(repo, limit=5)
                    
                    # 学習内容を構成
                    learning_content = f"""
GitHub Repository: {repo}

Description: {repo_info.get('description', 'なし')}
Stars: {repo_info.get('stargazers_count', 0)}
Language: {repo_info.get('language', '不明')}

README:
{readme[:500] if readme else '取得失敗'}

最近のコミット:
{self._format_commits(commits)}
"""
                    
                    # 記憶に保存
                    await self.memory_api.smart_store(
                        content=learning_content,
                        title=f"GitHub: {repo}",
                        importance=8,
                        tags=['github', 'auto_learning', repo.split('/')[0]],
                        category='github_knowledge'
                    )
                    
                    learned['results'][repo] = {
                        'success': True,
                        'stars': repo_info.get('stargazers_count', 0)
                    }
                
            except Exception as e:
                logger.error(f"  ❌ GitHub学習失敗 ({repo}): {e}")
                learned['results'][repo] = {
                    'error': str(e)
                }
        
        # 履歴に記録
        self.collection_history['github_repos'].append({
            'timestamp': learned['timestamp'],
            'repos': repos
        })
        self._save_history()
        
        logger.info(f"✅ GitHub学習完了: {len(learned['results'])}リポジトリ")
        
        return learned
    
    async def _get_github_repo(self, repo: str) -> Optional[Dict]:
        """GitHubリポジトリ情報取得"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.github_api_base}/repos/{repo}",
                    headers={'Accept': 'application/vnd.github.v3+json'},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.warning(f"  ⚠️ GitHub API: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"  ❌ GitHub API エラー: {e}")
            return None
    
    async def _get_github_readme(self, repo: str) -> Optional[str]:
        """README取得"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.github_api_base}/repos/{repo}/readme",
                    headers={'Accept': 'application/vnd.github.v3.raw'},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        return await response.text()
                    else:
                        return None
        except:
            return None
    
    async def _get_github_commits(self, repo: str, limit: int = 5) -> List[Dict]:
        """最新コミット取得"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.github_api_base}/repos/{repo}/commits",
                    params={'per_page': limit},
                    headers={'Accept': 'application/vnd.github.v3+json'},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        return []
        except:
            return []
    
    def _format_commits(self, commits: List[Dict]) -> str:
        """コミットフォーマット"""
        if not commits:
            return "取得失敗"
        
        formatted = []
        for commit in commits[:5]:
            message = commit.get('commit', {}).get('message', '')
            author = commit.get('commit', {}).get('author', {}).get('name', '不明')
            formatted.append(f"• {message[:50]} by {author}")
        
        return "\n".join(formatted)
    
    async def sync_with_notebooklm(self, queries: List[str]) -> Dict:
        """
        NotebookLM連携
        
        Args:
            queries: 検索クエリリスト
            
        Returns:
            連携結果
        """
        logger.info(f"📔 NotebookLM連携: {len(queries)}クエリ")
        
        synced = {
            'timestamp': datetime.now().isoformat(),
            'queries': queries,
            'results': {}
        }
        
        for query in queries:
            logger.info(f"  検索中: {query}")
            
            try:
                # NotebookLM MCP経由で検索
                # 実際は mcp_manaos-trinity_notebooklm_search を呼ぶ
                
                # デモ実装
                search_results = await self._notebooklm_search(query)
                
                if search_results:
                    # 記憶に保存
                    await self.memory_api.smart_store(
                        content=f"NotebookLM検索: {query}\n\n{search_results[:500]}",
                        title=f"NotebookLM: {query}",
                        importance=7,
                        tags=['notebooklm', 'auto_sync', query],
                        category='notebooklm_knowledge'
                    )
                    
                    synced['results'][query] = {
                        'success': True,
                        'content_length': len(search_results)
                    }
                
            except Exception as e:
                logger.error(f"  ❌ NotebookLM連携失敗 ({query}): {e}")
                synced['results'][query] = {
                    'error': str(e)
                }
        
        # 履歴に記録
        self.collection_history['notebooklm_imports'].append({
            'timestamp': synced['timestamp'],
            'queries': queries
        })
        self._save_history()
        
        logger.info(f"✅ NotebookLM連携完了: {len(synced['results'])}クエリ")
        
        return synced
    
    async def _notebooklm_search(self, query: str) -> str:
        """NotebookLM検索（デモ）"""
        # 実際のMCP呼び出しをここで実装
        return f"{query}に関する NotebookLM の収集データ..."
    
    async def auto_collect_daily(self) -> Dict:
        """
        デイリー自動収集
        
        毎日自動実行する想定のメインメソッド
        
        Returns:
            収集結果サマリー
        """
        logger.info("🌅 デイリー自動収集開始...")
        
        # 収集トピック（Manaの関心事項）
        topics = [
            "RunPod GPU 最新情報",
            "Python async 最新ベストプラクティス",
            "AI エージェント 最新動向",
            "FastAPI performance optimization"
        ]
        
        # GitHub監視リポジトリ
        github_repos = [
            # "runpod/runpod-python",
            # "tiangolo/fastapi"
        ]
        
        # NotebookLMクエリ
        notebooklm_queries = [
            # "ManaOS v3",
            # "Trinity システム"
        ]
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'web_search': {},
            'github': {},
            'notebooklm': {}
        }
        
        # Web検索
        try:
            web_results = await self.auto_web_search(topics[:2], max_results=3)  # 軽量化
            results['web_search'] = {
                'topics': len(topics),
                'collected': len([r for r in web_results['results'].values() if 'count' in r])
            }
        except Exception as e:
            logger.error(f"  ❌ Web検索失敗: {e}")
            results['web_search'] = {'error': str(e)}
        
        # GitHub学習（リポジトリがあれば）
        if github_repos:
            try:
                github_results = await self.learn_from_github(github_repos)
                results['github'] = {
                    'repos': len(github_repos),
                    'learned': len([r for r in github_results['results'].values() if r.get('success')])
                }
            except Exception as e:
                logger.error(f"  ❌ GitHub学習失敗: {e}")
                results['github'] = {'error': str(e)}
        
        # NotebookLM連携（クエリがあれば）
        if notebooklm_queries:
            try:
                notebooklm_results = await self.sync_with_notebooklm(notebooklm_queries)
                results['notebooklm'] = {
                    'queries': len(notebooklm_queries),
                    'synced': len([r for r in notebooklm_results['results'].values() if r.get('success')])
                }
            except Exception as e:
                logger.error(f"  ❌ NotebookLM連携失敗: {e}")
                results['notebooklm'] = {'error': str(e)}
        
        logger.info("✅ デイリー自動収集完了")
        
        return results
    
    async def get_collection_stats(self) -> Dict:
        """収集統計取得"""
        searches = self.collection_history.get('searches', [])
        last_collection = searches[-1].get('timestamp', 'なし') if searches else 'なし'
        
        return {
            'total_searches': len(searches),
            'total_github_repos': len(self.collection_history.get('github_repos', [])),
            'total_notebooklm_imports': len(self.collection_history.get('notebooklm_imports', [])),
            'last_collection': last_collection
        }


# テスト
async def test_external_knowledge():
    print("\n" + "="*70)
    print("🧪 External Knowledge Integration - テスト")
    print("="*70)
    
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    from core.unified_memory_api import UnifiedMemoryAPI
    
    memory_api = UnifiedMemoryAPI()
    external = ExternalKnowledgeIntegration(memory_api)
    
    # テスト1: Web検索
    print("\n🔍 テスト1: Web自動検索")
    web_result = await external.auto_web_search(['Python async'], max_results=2)
    print(f"収集: {len(web_result['results'])}トピック")
    
    # テスト2: GitHub学習
    print("\n🐙 テスト2: GitHub学習")
    # github_result = await external.learn_from_github(['tiangolo/fastapi'])
    # print(f"学習: {len(github_result['results'])}リポジトリ")
    print("  ℹ️ スキップ（API制限考慮）")
    
    # テスト3: 統計
    print("\n📊 テスト3: 収集統計")
    stats = await external.get_collection_stats()
    print(f"総検索数: {stats['total_searches']}")
    print(f"総GitHubリポジトリ: {stats['total_github_repos']}")
    
    print("\n✅ テスト完了")


if __name__ == '__main__':
    asyncio.run(test_external_knowledge())

