"""
LLMバッチ処理システム
複数クエリの並列処理
"""

from manaos_logger import get_logger
import asyncio
from typing import List, Dict, Any, Callable, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

logger = get_service_logger("llm-batch")


class BatchProcessor:
    """バッチ処理クラス"""
    
    def __init__(self, max_workers: int = 4):
        """
        初期化
        
        Args:
            max_workers: 最大並列実行数
        """
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
    
    def process_batch(
        self,
        queries: List[str],
        process_func: Callable[[str], Dict[str, Any]],
        timeout: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        バッチ処理を実行
        
        Args:
            queries: クエリリスト
            process_func: 各クエリを処理する関数
            timeout: タイムアウト（秒）
            
        Returns:
            処理結果のリスト
        """
        results = []
        start_time = time.time()
        
        # 並列処理
        futures = {
            self.executor.submit(process_func, query): query
            for query in queries
        }
        
        for future in as_completed(futures, timeout=timeout):
            query = futures[future]
            try:
                result = future.result()
                result["query"] = query
                results.append(result)
            except Exception as e:
                logger.error(f"❌ バッチ処理エラー（クエリ: {query[:50]}...）: {e}")
                results.append({
                    "query": query,
                    "error": str(e),
                    "success": False
                })
        
        elapsed_time = time.time() - start_time
        logger.info(f"✅ バッチ処理完了: {len(queries)}件を{elapsed_time:.2f}秒で処理")
        
        return results
    
    def process_batch_async(
        self,
        queries: List[str],
        process_func: Callable[[str], Any],
        timeout: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        非同期バッチ処理を実行
        
        Args:
            queries: クエリリスト
            process_func: 各クエリを処理する非同期関数
            timeout: タイムアウト（秒）
            
        Returns:
            処理結果のリスト
        """
        async def _process_all():
            tasks = [process_func(query) for query in queries]
            return await asyncio.gather(*tasks, return_exceptions=True)
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            if timeout:
                results = loop.run_until_complete(
                    asyncio.wait_for(_process_all(), timeout=timeout)
                )
            else:
                results = loop.run_until_complete(_process_all())
        finally:
            loop.close()
        
        # 結果を整形
        formatted_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                formatted_results.append({
                    "query": queries[i],
                    "error": str(result),
                    "success": False
                })
            else:
                formatted_results.append({
                    "query": queries[i],
                    "result": result,
                    "success": True
                })
        
        return formatted_results
    
    def shutdown(self):
        """エグゼキューターをシャットダウン"""
        self.executor.shutdown(wait=True)

