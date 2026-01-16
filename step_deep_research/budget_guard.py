#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
予算ガードシステム（コスト爆死防止）
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from enum import Enum
from datetime import datetime

from manaos_logger import get_logger
from .schemas import JobBudget

logger = get_logger(__name__)


class StopReason(str, Enum):
    """停止理由"""
    BUDGET_EXCEEDED = "budget_exceeded"
    QUALITY_PASSED = "quality_passed"
    TIMEOUT = "timeout"
    MAX_ITERATIONS = "max_iterations"
    MAX_SEARCHES = "max_searches"
    MAX_SOURCES = "max_sources"
    USER_CANCELLED = "user_cancelled"
    ERROR = "error"


@dataclass
class BudgetGuard:
    """予算ガード"""
    
    max_iterations: int = 10
    max_search_calls: int = 20
    max_sources: int = 50
    time_budget_sec: int = 3600  # 1時間
    token_budget: int = 50000
    
    # 使用量追跡
    current_iterations: int = 0
    current_search_calls: int = 0
    current_sources: int = 0
    start_time: Optional[datetime] = None
    tokens_used: int = 0
    
    def __post_init__(self):
        """初期化後処理"""
        if self.start_time is None:
            self.start_time = datetime.now()
    
    def check_budget(self, job_budget: Optional[JobBudget] = None) -> tuple[bool, Optional[StopReason], str]:
        """
        予算チェック
        
        Args:
            job_budget: ジョブ予算（オプション）
        
        Returns:
            (継続可能か, 停止理由, メッセージ)
        """
        # 時間チェック
        if self.start_time:
            elapsed = (datetime.now() - self.start_time).total_seconds()
            if elapsed > self.time_budget_sec:
                return False, StopReason.TIMEOUT, f"時間予算超過: {elapsed:.1f}秒 > {self.time_budget_sec}秒"
        
        # イテレーションチェック
        if self.current_iterations >= self.max_iterations:
            return False, StopReason.MAX_ITERATIONS, f"最大イテレーション到達: {self.current_iterations}/{self.max_iterations}"
        
        # 検索回数チェック
        if self.current_search_calls >= self.max_search_calls:
            return False, StopReason.MAX_SEARCHES, f"最大検索回数到達: {self.current_search_calls}/{self.max_search_calls}"
        
        # ソース数チェック
        if self.current_sources >= self.max_sources:
            return False, StopReason.MAX_SOURCES, f"最大ソース数到達: {self.current_sources}/{self.max_sources}"
        
        # トークンチェック
        if self.tokens_used >= self.token_budget:
            return False, StopReason.BUDGET_EXCEEDED, f"トークン予算超過: {self.tokens_used}/{self.token_budget}"
        
        # ジョブ予算チェック（あれば）
        if job_budget:
            if job_budget.used_tokens >= job_budget.max_tokens:
                return False, StopReason.BUDGET_EXCEEDED, f"ジョブトークン予算超過: {job_budget.used_tokens}/{job_budget.max_tokens}"
            
            if job_budget.used_searches >= job_budget.max_searches:
                return False, StopReason.MAX_SEARCHES, f"ジョブ検索予算超過: {job_budget.used_searches}/{job_budget.max_searches}"
            
            if job_budget.elapsed_seconds >= job_budget.max_time_minutes * 60:
                return False, StopReason.TIMEOUT, f"ジョブ時間予算超過: {job_budget.elapsed_seconds:.1f}秒"
        
        return True, None, "予算内"
    
    def record_iteration(self):
        """イテレーション記録"""
        self.current_iterations += 1
        logger.debug(f"Budget: iteration {self.current_iterations}/{self.max_iterations}")
    
    def record_search(self, count: int = 1):
        """検索記録"""
        self.current_search_calls += count
        logger.debug(f"Budget: search calls {self.current_search_calls}/{self.max_search_calls}")
    
    def record_sources(self, count: int):
        """ソース記録"""
        self.current_sources += count
        logger.debug(f"Budget: sources {self.current_sources}/{self.max_sources}")
    
    def record_tokens(self, count: int):
        """トークン記録"""
        self.tokens_used += count
        logger.debug(f"Budget: tokens {self.tokens_used}/{self.token_budget}")
    
    def get_spent_budget(self) -> Dict[str, Any]:
        """
        使用予算取得
        
        Returns:
            使用予算の辞書
        """
        elapsed_sec = 0
        if self.start_time:
            elapsed_sec = (datetime.now() - self.start_time).total_seconds()
        
        return {
            "iterations": {
                "used": self.current_iterations,
                "max": self.max_iterations,
                "remaining": self.max_iterations - self.current_iterations
            },
            "search_calls": {
                "used": self.current_search_calls,
                "max": self.max_search_calls,
                "remaining": self.max_search_calls - self.current_search_calls
            },
            "sources": {
                "used": self.current_sources,
                "max": self.max_sources,
                "remaining": self.max_sources - self.current_sources
            },
            "tokens": {
                "used": self.tokens_used,
                "max": self.token_budget,
                "remaining": self.token_budget - self.tokens_used
            },
            "time": {
                "elapsed_sec": elapsed_sec,
                "max_sec": self.time_budget_sec,
                "remaining_sec": max(0, self.time_budget_sec - elapsed_sec)
            }
        }
    
    def reset(self):
        """リセット"""
        self.current_iterations = 0
        self.current_search_calls = 0
        self.current_sources = 0
        self.tokens_used = 0
        self.start_time = datetime.now()



