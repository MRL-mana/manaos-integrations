#!/usr/bin/env python3
"""
🚦 ManaOS 動的レート制限システム
リソース使用率に基づく動的調整・ユーザー別レート制限・優先度に基づくレート制限
"""

import os
import json
import time
import psutil
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
from enum import Enum
from functools import wraps
import threading

# 統一モジュールのインポート
from manaos_logger import get_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity
from manaos_timeout_config import get_timeout_config

# ロガーの初期化
logger = get_logger(__name__)

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("DynamicRateLimiter")

# タイムアウト設定の取得
timeout_config = get_timeout_config()


class Priority(str, Enum):
    """優先度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class RateLimitConfig:
    """レート制限設定"""
    base_rate: int  # ベースレート（リクエスト/秒）
    max_rate: int  # 最大レート
    min_rate: int  # 最小レート
    cpu_threshold: float = 0.8  # CPU使用率閾値
    memory_threshold: float = 0.8  # メモリ使用率閾値
    priority_multiplier: Dict[str, float] = None  # 優先度別の倍率
    
    def __post_init__(self):
        if self.priority_multiplier is None:
            self.priority_multiplier = {
                "low": 0.5,
                "medium": 1.0,
                "high": 1.5,
                "urgent": 2.0
            }


@dataclass
class RateLimitInfo:
    """レート制限情報"""
    user_id: str
    priority: Priority
    current_rate: float
    allowed_requests: int
    window_start: datetime
    request_count: int = 0


class DynamicRateLimiter:
    """動的レート制限システム"""
    
    def __init__(
        self,
        config: Optional[RateLimitConfig] = None,
        config_path: Optional[Path] = None
    ):
        """
        初期化
        
        Args:
            config: レート制限設定
            config_path: 設定ファイルのパス
        """
        self.config = config or self._load_config(config_path)
        
        # ユーザー別レート制限情報
        self.user_limits: Dict[str, RateLimitInfo] = {}
        
        # リクエスト履歴（スライディングウィンドウ）
        self.request_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        
        # リソース監視
        self.resource_monitor_thread = None
        self.monitoring = False
        self.current_cpu_usage = 0.0
        self.current_memory_usage = 0.0
        
        # ロック
        self.lock = threading.Lock()
        
        logger.info(f"✅ Dynamic Rate Limiter初期化完了")
    
    def _load_config(self, config_path: Optional[Path] = None) -> RateLimitConfig:
        """設定を読み込む"""
        if config_path is None:
            config_path = Path(__file__).parent / "dynamic_rate_limiter_config.json"
        
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                return RateLimitConfig(
                    base_rate=config_data.get("base_rate", 10),
                    max_rate=config_data.get("max_rate", 100),
                    min_rate=config_data.get("min_rate", 1),
                    cpu_threshold=config_data.get("cpu_threshold", 0.8),
                    memory_threshold=config_data.get("memory_threshold", 0.8),
                    priority_multiplier=config_data.get("priority_multiplier", {
                        "low": 0.5,
                        "medium": 1.0,
                        "high": 1.5,
                        "urgent": 2.0
                    })
                )
            except Exception as e:
                error = error_handler.handle_exception(
                    e,
                    context={"config_file": str(config_path)},
                    user_message="設定ファイルの読み込みに失敗しました"
                )
                logger.warning(f"設定読み込みエラー: {error.message}")
        
        return RateLimitConfig(
            base_rate=10,
            max_rate=100,
            min_rate=1
        )
    
    def _calculate_dynamic_rate(self) -> float:
        """リソース使用率に基づいて動的レートを計算"""
        # CPU使用率とメモリ使用率を取得
        cpu_usage = psutil.cpu_percent(interval=0.1)
        memory_usage = psutil.virtual_memory().percent / 100
        
        self.current_cpu_usage = cpu_usage / 100
        self.current_memory_usage = memory_usage
        
        # リソース使用率が高い場合はレートを下げる
        resource_factor = 1.0
        
        if self.current_cpu_usage > self.config.cpu_threshold:
            # CPU使用率が閾値を超えている場合、レートを下げる
            cpu_factor = 1.0 - (self.current_cpu_usage - self.config.cpu_threshold) / (1.0 - self.config.cpu_threshold)
            resource_factor = min(resource_factor, cpu_factor)
        
        if self.current_memory_usage > self.config.memory_threshold:
            # メモリ使用率が閾値を超えている場合、レートを下げる
            memory_factor = 1.0 - (self.current_memory_usage - self.config.memory_threshold) / (1.0 - self.config.memory_threshold)
            resource_factor = min(resource_factor, memory_factor)
        
        # 動的レートを計算
        dynamic_rate = self.config.base_rate * resource_factor
        
        # 最小・最大レートの範囲内に制限
        dynamic_rate = max(self.config.min_rate, min(self.config.max_rate, dynamic_rate))
        
        return dynamic_rate
    
    def _get_user_rate_limit(
        self,
        user_id: str,
        priority: Priority
    ) -> RateLimitInfo:
        """ユーザー別レート制限情報を取得"""
        with self.lock:
            if user_id not in self.user_limits:
                # 新しいユーザーの場合、動的レートを計算
                base_rate = self._calculate_dynamic_rate()
                priority_multiplier = self.config.priority_multiplier.get(priority.value, 1.0)
                user_rate = base_rate * priority_multiplier
                
                self.user_limits[user_id] = RateLimitInfo(
                    user_id=user_id,
                    priority=priority,
                    current_rate=user_rate,
                    allowed_requests=int(user_rate),
                    window_start=datetime.now()
                )
            
            return self.user_limits[user_id]
    
    def _update_user_rate_limit(self, user_id: str):
        """ユーザー別レート制限を更新"""
        if user_id not in self.user_limits:
            return
        
        limit_info = self.user_limits[user_id]
        
        # ウィンドウが1秒経過したらリセット
        elapsed = (datetime.now() - limit_info.window_start).total_seconds()
        if elapsed >= 1.0:
            # 動的レートを再計算
            base_rate = self._calculate_dynamic_rate()
            priority_multiplier = self.config.priority_multiplier.get(limit_info.priority.value, 1.0)
            user_rate = base_rate * priority_multiplier
            
            limit_info.current_rate = user_rate
            limit_info.allowed_requests = int(user_rate)
            limit_info.window_start = datetime.now()
            limit_info.request_count = 0
    
    def check_rate_limit(
        self,
        user_id: str = "default",
        priority: Priority = Priority.MEDIUM
    ) -> bool:
        """
        レート制限をチェック
        
        Args:
            user_id: ユーザーID
            priority: 優先度
        
        Returns:
            リクエストが許可される場合True
        """
        limit_info = self._get_user_rate_limit(user_id, priority)
        self._update_user_rate_limit(user_id)
        
        # リクエスト数をチェック
        if limit_info.request_count >= limit_info.allowed_requests:
            logger.warning(f"レート制限超過: {user_id} ({limit_info.request_count}/{limit_info.allowed_requests})")
            return False
        
        # リクエスト数をインクリメント
        with self.lock:
            limit_info.request_count += 1
            self.request_history[user_id].append(datetime.now())
        
        return True
    
    def get_rate_limit_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """レート制限情報を取得"""
        if user_id not in self.user_limits:
            return None
        
        limit_info = self.user_limits[user_id]
        return {
            "user_id": limit_info.user_id,
            "priority": limit_info.priority.value,
            "current_rate": limit_info.current_rate,
            "allowed_requests": limit_info.allowed_requests,
            "request_count": limit_info.request_count,
            "remaining_requests": limit_info.allowed_requests - limit_info.request_count,
            "window_start": limit_info.window_start.isoformat(),
            "cpu_usage": self.current_cpu_usage,
            "memory_usage": self.current_memory_usage
        }
    
    def start_resource_monitoring(self):
        """リソース監視を開始"""
        if self.monitoring:
            return
        
        self.monitoring = True
        
        def monitor_loop():
            while self.monitoring:
                self._calculate_dynamic_rate()
                time.sleep(1)
        
        self.resource_monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self.resource_monitor_thread.start()
        logger.info("✅ リソース監視開始")
    
    def stop_resource_monitoring(self):
        """リソース監視を停止"""
        self.monitoring = False
        if self.resource_monitor_thread:
            self.resource_monitor_thread.join(timeout=5)
        logger.info("🛑 リソース監視停止")
    
    def rate_limit_decorator(
        self,
        user_id_key: str = "user_id",
        priority_key: str = "priority"
    ):
        """
        レート制限デコレータ
        
        Args:
            user_id_key: ユーザーIDを取得するキー
            priority_key: 優先度を取得するキー
        """
        def decorator(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                user_id = kwargs.get(user_id_key, "default")
                priority_str = kwargs.get(priority_key, "medium")
                priority = Priority(priority_str) if priority_str in [p.value for p in Priority] else Priority.MEDIUM
                
                if not self.check_rate_limit(user_id, priority):
                    raise Exception(f"レート制限に達しました: {user_id}")
                
                return await func(*args, **kwargs)
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                user_id = kwargs.get(user_id_key, "default")
                priority_str = kwargs.get(priority_key, "medium")
                priority = Priority(priority_str) if priority_str in [p.value for p in Priority] else Priority.MEDIUM
                
                if not self.check_rate_limit(user_id, priority):
                    raise Exception(f"レート制限に達しました: {user_id}")
                
                return func(*args, **kwargs)
            
            import asyncio
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper
        
        return decorator


# グローバルインスタンス
dynamic_rate_limiter = DynamicRateLimiter()

# デコレータのエクスポート
rate_limit = dynamic_rate_limiter.rate_limit_decorator

