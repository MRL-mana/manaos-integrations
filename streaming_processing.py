"""
ストリーミング処理システム
リアルタイムデータ処理
"""

import json
import asyncio
from typing import Dict, List, Any, Optional, Callable, AsyncGenerator
from datetime import datetime
from pathlib import Path
from collections import deque
import queue
import threading


class StreamingProcessor:
    """ストリーミングプロセッサ"""
    
    def __init__(self, buffer_size: int = 1000):
        """
        初期化
        
        Args:
            buffer_size: バッファサイズ
        """
        self.buffer_size = buffer_size
        self.data_queue = queue.Queue(maxsize=buffer_size)
        self.processors = []
        self.is_running = False
        self.processed_count = 0
        self.storage_path = Path("streaming_processing_state.json")
        self._load_state()
    
    def _load_state(self):
        """状態を読み込み"""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    self.processed_count = state.get("processed_count", 0)
            except Exception:
                self.processed_count = 0
        else:
            self.processed_count = 0
    
    def _save_state(self, max_retries: int = 3):
        """状態を保存（リトライ機能付き）"""
        for attempt in range(max_retries):
            try:
                self.storage_path.parent.mkdir(parents=True, exist_ok=True)
                temp_path = self.storage_path.with_suffix('.tmp')
                with open(temp_path, 'w', encoding='utf-8') as f:
                    json.dump({
                        "processed_count": self.processed_count,
                        "last_updated": datetime.now().isoformat()
                    }, f, ensure_ascii=False, indent=2)
                temp_path.replace(self.storage_path)
                return
            except Exception as e:
                if attempt == max_retries - 1:
                    from manaos_logger import get_logger
                    logger = get_logger(__name__)
                    logger.warning(f"状態保存エラー（{max_retries}回リトライ後）: {e}")
                else:
                    import time
                    time.sleep(0.1 * (attempt + 1))
    
    def register_processor(self, processor: Callable, name: str = None):
        """
        プロセッサを登録
        
        Args:
            processor: プロセッサ関数
            name: プロセッサ名（オプション）
        """
        self.processors.append({
            "name": name or f"processor_{len(self.processors)}",
            "function": processor
        })
    
    def add_data(self, data: Any) -> bool:
        """
        データを追加
        
        Args:
            data: データ
            
        Returns:
            追加成功時True
        """
        try:
            self.data_queue.put_nowait(data)
            return True
        except queue.Full:
            return False
    
    def process_data(self, data: Any) -> List[Any]:
        """
        データを処理
        
        Args:
            data: データ
            
        Returns:
            処理結果のリスト
        """
        results = []
        
        for processor_info in self.processors:
            try:
                result = processor_info["function"](data)
                results.append({
                    "processor": processor_info["name"],
                    "result": result,
                    "timestamp": datetime.now().isoformat()
                })
            except Exception as e:
                results.append({
                    "processor": processor_info["name"],
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })
        
        self.processed_count += 1
        self._save_state()
        
        return results
    
    def start_processing(self):
        """処理を開始"""
        if self.is_running:
            return
        
        self.is_running = True
        
        def worker():
            while self.is_running:
                try:
                    data = self.data_queue.get(timeout=1)
                    results = self.process_data(data)
                    # 結果を処理（必要に応じて）
                except queue.Empty:
                    continue
                except Exception as e:
                    print(f"処理エラー: {e}")
        
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
    
    def stop_processing(self):
        """処理を停止"""
        self.is_running = False
    
    async def async_process_stream(
        self,
        data_stream: AsyncGenerator,
        batch_size: int = 10
    ) -> AsyncGenerator:
        """
        ストリームを非同期処理
        
        Args:
            data_stream: データストリーム
            batch_size: バッチサイズ
            
        Yields:
            処理結果
        """
        batch = []
        
        async for data in data_stream:
            batch.append(data)
            
            if len(batch) >= batch_size:
                results = []
                for item in batch:
                    results.extend(self.process_data(item))
                yield results
                batch = []
        
        # 残りのデータを処理
        if batch:
            results = []
            for item in batch:
                results.extend(self.process_data(item))
            yield results
    
    def get_status(self) -> Dict[str, Any]:
        """状態を取得"""
        return {
            "is_running": self.is_running,
            "queue_size": self.data_queue.qsize(),
            "processors_count": len(self.processors),
            "processed_count": self.processed_count,
            "buffer_size": self.buffer_size,
            "timestamp": datetime.now().isoformat()
        }


class DataStream:
    """データストリーム"""
    
    def __init__(self):
        """初期化"""
        self.data_buffer = deque(maxlen=1000)
    
    async def generate(self) -> AsyncGenerator:
        """
        データを生成
        
        Yields:
            データ
        """
        while True:
            if self.data_buffer:
                yield self.data_buffer.popleft()
            else:
                await asyncio.sleep(0.1)
    
    def add_data(self, data: Any):
        """
        データを追加
        
        Args:
            data: データ
        """
        self.data_buffer.append(data)


def main():
    """テスト用メイン関数"""
    print("ストリーミング処理システムテスト")
    print("=" * 60)
    
    processor = StreamingProcessor(buffer_size=100)
    
    # プロセッサを登録
    def simple_processor(data):
        return {"processed": data, "length": len(str(data))}
    
    processor.register_processor(simple_processor, "simple")
    
    # データを追加
    print("\nデータを追加中...")
    for i in range(10):
        processor.add_data(f"data_{i}")
    
    # 処理を開始
    print("\n処理を開始中...")
    processor.start_processing()
    
    import time
    time.sleep(2)
    
    # 状態を表示
    status = processor.get_status()
    print(f"\n状態: {status}")
    
    # 処理を停止
    processor.stop_processing()
    print("処理を停止しました")


if __name__ == "__main__":
    main()

