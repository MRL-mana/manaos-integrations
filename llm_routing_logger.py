"""
LLMルーティングシステム ログ記録
リクエスト、レスポンス、エラーを記録
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from collections import deque

# ログディレクトリ
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# ログファイル
REQUEST_LOG_FILE = LOG_DIR / "llm_routing_requests.jsonl"
ERROR_LOG_FILE = LOG_DIR / "llm_routing_errors.jsonl"
PERFORMANCE_LOG_FILE = LOG_DIR / "llm_routing_performance.jsonl"

# ログ履歴（メモリ内、最新100件）
request_history = deque(maxlen=100)
error_history = deque(maxlen=100)
performance_history = deque(maxlen=100)


class LLMRoutingLogger:
    """LLMルーティングロガー"""
    
    def __init__(self):
        # ファイルロガー
        self.request_logger = self._setup_file_logger("requests", REQUEST_LOG_FILE)
        self.error_logger = self._setup_file_logger("errors", ERROR_LOG_FILE)
        self.performance_logger = self._setup_file_logger("performance", PERFORMANCE_LOG_FILE)
    
    def _setup_file_logger(self, name: str, log_file: Path) -> logging.Logger:
        """ファイルロガーを設定"""
        logger = logging.getLogger(f"llm_routing_{name}")
        logger.setLevel(logging.INFO)
        
        # 既存のハンドラーをクリア
        logger.handlers.clear()
        
        # ファイルハンドラー
        handler = logging.FileHandler(log_file, encoding='utf-8')
        handler.setLevel(logging.INFO)
        
        # JSON形式で出力
        formatter = logging.Formatter('%(message)s')
        handler.setFormatter(formatter)
        
        logger.addHandler(handler)
        logger.propagate = False
        
        return logger
    
    def log_request(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        preferences: Optional[Dict[str, Any]] = None
    ):
        """リクエストをログ記録"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "request",
            "prompt": prompt[:200],  # 最初の200文字のみ
            "context": context,
            "preferences": preferences
        }
        
        # ファイルに記録
        self.request_logger.info(json.dumps(log_entry, ensure_ascii=False))
        
        # メモリに記録
        request_history.append(log_entry)
    
    def log_response(
        self,
        prompt: str,
        model: str,
        difficulty_score: float,
        response_time_ms: int,
        success: bool,
        response: Optional[str] = None,
        error: Optional[str] = None
    ):
        """レスポンスをログ記録"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "response",
            "prompt": prompt[:200],
            "model": model,
            "difficulty_score": difficulty_score,
            "response_time_ms": response_time_ms,
            "success": success,
            "response_length": len(response) if response else 0,
            "error": error
        }
        
        # ファイルに記録
        self.request_logger.info(json.dumps(log_entry, ensure_ascii=False))
        
        # パフォーマンスログ
        performance_entry = {
            "timestamp": datetime.now().isoformat(),
            "model": model,
            "response_time_ms": response_time_ms,
            "difficulty_score": difficulty_score,
            "success": success
        }
        self.performance_logger.info(json.dumps(performance_entry, ensure_ascii=False))
        performance_history.append(performance_entry)
        
        # エラーの場合
        if not success and error:
            error_entry = {
                "timestamp": datetime.now().isoformat(),
                "type": "error",
                "model": model,
                "error": error,
                "prompt": prompt[:200]
            }
            self.error_logger.info(json.dumps(error_entry, ensure_ascii=False))
            error_history.append(error_entry)
    
    def get_statistics(self) -> Dict[str, Any]:
        """統計情報を取得"""
        return {
            "request_count": len(request_history),
            "error_count": len(error_history),
            "performance_count": len(performance_history),
            "recent_requests": list(request_history)[-10:],
            "recent_errors": list(error_history)[-10:],
            "recent_performance": list(performance_history)[-10:]
        }


# グローバルロガーインスタンス
logger = LLMRoutingLogger()



















