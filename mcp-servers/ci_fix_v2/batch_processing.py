"""
バッチ処理システム
大量データの一括処理
"""

import json
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
import multiprocessing


class BatchProcessor:
    """バッチプロセッサ"""
    
    def __init__(self, max_workers: Optional[int] = None):
        """
        初期化
        
        Args:
            max_workers: 最大ワーカー数（Noneで自動）
        """
        self.max_workers = max_workers or multiprocessing.cpu_count()
        self.batch_history = []
        self.storage_path = Path("batch_processing_state.json")
        self._load_state()
    
    def _load_state(self):
        """状態を読み込み"""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    self.batch_history = state.get("history", [])[-100:]
            except Exception:
                self.batch_history = []
        else:
            self.batch_history = []
    
    def _save_state(self):
        """状態を保存"""
        try:
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "history": self.batch_history[-100:],
                    "last_updated": datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"状態保存エラー: {e}")
    
    def process_batch(
        self,
        data: List[Any],
        processor: Callable,
        use_multiprocessing: bool = False,
        batch_size: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        バッチを処理
        
        Args:
            data: データのリスト
            processor: プロセッサ関数
            use_multiprocessing: マルチプロセシングを使用するか
            batch_size: バッチサイズ（Noneで全データを一度に）
            
        Returns:
            処理結果
        """
        start_time = datetime.now()
        total_items = len(data)
        
        if batch_size:
            # バッチに分割
            batches = [data[i:i+batch_size] for i in range(0, len(data), batch_size)]
        else:
            batches = [data]
        
        results = []
        errors = []
        
        executor_class = ProcessPoolExecutor if use_multiprocessing else ThreadPoolExecutor
        
        with executor_class(max_workers=self.max_workers) as executor:
            futures = []
            
            for batch in batches:
                if use_multiprocessing:
                    future = executor.submit(self._process_batch_multiprocess, batch, processor)
                else:
                    future = executor.submit(self._process_batch_thread, batch, processor)
                futures.append(future)
            
            for future in as_completed(futures):
                try:
                    batch_results = future.result()
                    results.extend(batch_results)
                except Exception as e:
                    errors.append(str(e))
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        batch_record = {
            "batch_id": f"batch_{len(self.batch_history) + 1}_{int(start_time.timestamp())}",
            "total_items": total_items,
            "processed_items": len(results),
            "failed_items": len(errors),
            "duration_seconds": duration,
            "items_per_second": total_items / duration if duration > 0 else 0,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "errors": errors[:10]  # 最新10件のみ
        }
        
        self.batch_history.append(batch_record)
        self._save_state()
        
        return {
            "results": results,
            "summary": batch_record
        }
    
    def _process_batch_thread(self, batch: List[Any], processor: Callable) -> List[Any]:
        """スレッドでバッチを処理"""
        results = []
        for item in batch:
            try:
                result = processor(item)
                results.append(result)
            except Exception as e:
                results.append({"error": str(e), "item": item})
        return results
    
    def _process_batch_multiprocess(self, batch: List[Any], processor: Callable) -> List[Any]:
        """マルチプロセスでバッチを処理"""
        # 注意: マルチプロセシングでは、プロセッサ関数がpickle可能である必要があります
        results = []
        for item in batch:
            try:
                result = processor(item)
                results.append(result)
            except Exception as e:
                results.append({"error": str(e), "item": item})
        return results
    
    def process_image_batch(
        self,
        image_paths: List[str],
        processor: Callable,
        **kwargs
    ) -> Dict[str, Any]:
        """
        画像バッチを処理
        
        Args:
            image_paths: 画像パスのリスト
            processor: プロセッサ関数
            **kwargs: 追加引数
            
        Returns:
            処理結果
        """
        def image_processor(path):
            return processor(path, **kwargs)
        
        return self.process_batch(image_paths, image_processor)
    
    def process_text_batch(
        self,
        texts: List[str],
        processor: Callable,
        **kwargs
    ) -> Dict[str, Any]:
        """
        テキストバッチを処理
        
        Args:
            texts: テキストのリスト
            processor: プロセッサ関数
            **kwargs: 追加引数
            
        Returns:
            処理結果
        """
        def text_processor(text):
            return processor(text, **kwargs)
        
        return self.process_batch(texts, text_processor)
    
    def get_batch_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        バッチ履歴を取得
        
        Args:
            limit: 取得数
            
        Returns:
            バッチ履歴
        """
        return self.batch_history[-limit:]
    
    def get_statistics(self) -> Dict[str, Any]:
        """統計を取得"""
        if not self.batch_history:
            return {}
        
        total_batches = len(self.batch_history)
        total_items = sum(b["total_items"] for b in self.batch_history)
        total_processed = sum(b["processed_items"] for b in self.batch_history)
        total_failed = sum(b["failed_items"] for b in self.batch_history)
        total_duration = sum(b["duration_seconds"] for b in self.batch_history)
        
        return {
            "total_batches": total_batches,
            "total_items": total_items,
            "total_processed": total_processed,
            "total_failed": total_failed,
            "success_rate": (total_processed / total_items * 100) if total_items > 0 else 0,
            "average_items_per_second": total_items / total_duration if total_duration > 0 else 0,
            "average_batch_duration": total_duration / total_batches if total_batches > 0 else 0
        }


def main():
    """テスト用メイン関数"""
    print("バッチ処理システムテスト")
    print("=" * 60)
    
    processor = BatchProcessor(max_workers=4)
    
    # サンプルデータ
    data = [f"item_{i}" for i in range(100)]
    
    # プロセッサ関数
    def simple_processor(item):
        return {"processed": item, "length": len(item)}
    
    # バッチ処理を実行
    print("\nバッチ処理を実行中...")
    result = processor.process_batch(data, simple_processor, batch_size=10)
    
    print(f"\n処理結果:")
    print(f"  処理済みアイテム: {result['summary']['processed_items']}")
    print(f"  失敗アイテム: {result['summary']['failed_items']}")
    print(f"  処理時間: {result['summary']['duration_seconds']:.2f}秒")
    print(f"  アイテム/秒: {result['summary']['items_per_second']:.2f}")
    
    # 統計を表示
    stats = processor.get_statistics()
    print(f"\n統計:")
    print(f"  総バッチ数: {stats.get('total_batches', 0)}")
    print(f"  成功率: {stats.get('success_rate', 0):.1f}%")


if __name__ == "__main__":
    main()



















