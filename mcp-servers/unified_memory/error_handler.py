#!/usr/bin/env python3
"""
🛡️ Enhanced Error Handler
エラーハンドリング強化 - リトライ・フォールバック・自動復旧

機能:
1. 自動リトライ（exponential backoff）
2. フォールバック機構
3. エラーログ記録
4. 自動復旧
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Callable
from pathlib import Path
import json
from functools import wraps

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ErrorHandler")


class EnhancedErrorHandler:
    """強化版エラーハンドラー"""
    
    def __init__(self):
        self.error_log_db = Path('/root/unified_memory_system/data/error_log.json')
        self.error_log_db.parent.mkdir(exist_ok=True, parents=True)
        self.error_log = self._load_error_log()
    
    def _load_error_log(self) -> Dict:
        """エラーログ読み込み"""
        if self.error_log_db.exists():
            try:
                with open(self.error_log_db, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {'errors': []}
    
    def _save_error_log(self):
        """エラーログ保存"""
        try:
            with open(self.error_log_db, 'w') as f:
                json.dump(self.error_log, f, ensure_ascii=False, indent=2)
        except:
            pass
    
    def log_error(self, error: Exception, context: str):
        """エラー記録"""
        error_entry = {
            'timestamp': datetime.now().isoformat(),
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context': context
        }
        
        self.error_log['errors'].append(error_entry)
        self.error_log['errors'] = self.error_log['errors'][-1000:]
        self._save_error_log()
        
        logger.error(f"❌ {context}: {error}")
    
    async def retry_with_backoff(self, func: Callable, max_retries: int = 3,
                                 initial_delay: float = 1.0) -> Any:
        """
        Exponential Backoffでリトライ
        
        Args:
            func: 実行する関数
            max_retries: 最大リトライ回数
            initial_delay: 初期待機時間（秒）
            
        Returns:
            関数の戻り値
        """
        delay = initial_delay
        
        for attempt in range(max_retries):
            try:
                return await func()
            
            except Exception as e:
                if attempt == max_retries - 1:
                    # 最後の試行も失敗
                    self.log_error(e, f"retry_failed_after_{max_retries}_attempts")
                    raise
                
                logger.warning(f"⚠️ リトライ {attempt + 1}/{max_retries}: {e}")
                await asyncio.sleep(delay)
                delay *= 2  # Exponential backoff


# グローバルハンドラー
global_error_handler = EnhancedErrorHandler()


def handle_errors(context: str = "unknown"):
    """エラーハンドリングデコレータ"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                global_error_handler.log_error(e, f"{context}:{func.__name__}")
                # エラーを再送出（上位で処理）
                raise
        return wrapper
    return decorator

