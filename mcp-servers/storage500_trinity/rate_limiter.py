#!/usr/bin/env python3
"""
Rate Limiter - レート制限システム

各操作の実行頻度を制限し、システム負荷を制御します。

機能:
- Token Bucket: トークンバケット方式
- Sliding Window: スライディングウィンドウ方式
- Fixed Window: 固定ウィンドウ方式
"""

import time
from datetime import datetime
from typing import Dict, Optional
from collections import deque


class TokenBucket:
    """トークンバケット方式のレート制限"""
    
    def __init__(self, capacity: int, refill_rate: float):
        """
        Args:
            capacity: バケットの最大容量
            refill_rate: 1秒あたりのトークン補充数
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.time()
        
    def consume(self, tokens: int = 1) -> bool:
        """
        トークンを消費
        
        Returns:
            True: 実行可能
            False: レート制限超過
        """
        self._refill()
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False
        
    def _refill(self):
        """トークンを補充"""
        now = time.time()
        elapsed = now - self.last_refill
        
        refill_amount = elapsed * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + refill_amount)
        
        self.last_refill = now
        
    def get_status(self) -> Dict:
        """現在の状態を取得"""
        self._refill()
        return {
            'tokens': self.tokens,
            'capacity': self.capacity,
            'utilization': 1.0 - (self.tokens / self.capacity)
        }


class SlidingWindowRateLimiter:
    """スライディングウィンドウ方式のレート制限"""
    
    def __init__(self, max_requests: int, window_seconds: int):
        """
        Args:
            max_requests: ウィンドウ内の最大リクエスト数
            window_seconds: ウィンドウサイズ（秒）
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = deque()
        
    def can_execute(self) -> bool:
        """
        実行可能かチェック
        
        Returns:
            True: 実行可能
            False: レート制限超過
        """
        now = time.time()
        
        # 古いリクエストを削除
        while self.requests and self.requests[0] < now - self.window_seconds:
            self.requests.popleft()
            
        # レート制限チェック
        if len(self.requests) < self.max_requests:
            self.requests.append(now)
            return True
            
        return False
        
    def get_status(self) -> Dict:
        """現在の状態を取得"""
        now = time.time()
        
        # 古いリクエストを削除
        while self.requests and self.requests[0] < now - self.window_seconds:
            self.requests.popleft()
            
        return {
            'current_requests': len(self.requests),
            'max_requests': self.max_requests,
            'utilization': len(self.requests) / self.max_requests,
            'window_seconds': self.window_seconds
        }


class RateLimiter:
    """統合レート制限システム"""
    
    def __init__(self):
        # 各操作のレート制限設定
        self.limiters = {
            'daily_reflection': TokenBucket(capacity=1, refill_rate=1/3600),  # 1時間に1回
            'auto_improvement': TokenBucket(capacity=2, refill_rate=1/1800),  # 30分に1回
            'consciousness_save': TokenBucket(capacity=10, refill_rate=1/60),  # 1分に1回
            'emotion_update': TokenBucket(capacity=60, refill_rate=1),  # 1秒に1回
            'db_write': TokenBucket(capacity=10, refill_rate=1/10),  # 10秒に1回
            'qsr_calculation': SlidingWindowRateLimiter(max_requests=60, window_seconds=3600)  # 1時間に60回
        }
        
        # 実行履歴
        self.execution_history = {}
        
    def can_execute(self, action: str) -> bool:
        """
        実行可能かチェック
        
        Args:
            action: アクション名
            
        Returns:
            True: 実行可能
            False: レート制限超過
        """
        if action not in self.limiters:
            # 制限が設定されていないアクションは常に実行可能
            return True
            
        limiter = self.limiters[action]
        
        if isinstance(limiter, TokenBucket):
            can_exec = limiter.consume()
        elif isinstance(limiter, SlidingWindowRateLimiter):
            can_exec = limiter.can_execute()
        else:
            can_exec = True
            
        # 履歴記録
        self._record_execution(action, can_exec)
        
        return can_exec
        
    def _record_execution(self, action: str, executed: bool):
        """実行履歴を記録"""
        if action not in self.execution_history:
            self.execution_history[action] = {
                'total_attempts': 0,
                'successful': 0,
                'rejected': 0,
                'last_execution': None
            }
            
        history = self.execution_history[action]
        history['total_attempts'] += 1
        
        if executed:
            history['successful'] += 1
            history['last_execution'] = datetime.now().isoformat()
        else:
            history['rejected'] += 1
            
    def get_stats(self) -> Dict:
        """統計情報を取得"""
        stats = {}
        
        for action, limiter in self.limiters.items():
            limiter_status = limiter.get_status()
            history = self.execution_history.get(action, {
                'total_attempts': 0,
                'successful': 0,
                'rejected': 0
            })
            
            stats[action] = {
                'limiter_status': limiter_status,
                'execution_history': history
            }
            
        return stats
        
    def print_stats(self):
        """統計情報を表示"""
        stats = self.get_stats()
        
        print("\n" + "="*60)
        print("🚦 Rate Limiter Stats")
        print("="*60)
        
        for action, data in stats.items():
            print(f"\n{action}:")
            
            limiter_status = data['limiter_status']
            if 'tokens' in limiter_status:
                print(f"  Tokens: {limiter_status['tokens']:.2f}/{limiter_status['capacity']}")
            elif 'current_requests' in limiter_status:
                print(f"  Requests: {limiter_status['current_requests']}/{limiter_status['max_requests']}")
                
            print(f"  Utilization: {limiter_status['utilization']:.1%}")
            
            history = data['execution_history']
            if history['total_attempts'] > 0:
                print(f"  Total attempts: {history['total_attempts']}")
                print(f"  Successful: {history['successful']}")
                print(f"  Rejected: {history['rejected']}")
                
        print("\n" + "="*60)


def test_rate_limiter():
    """テスト実行"""
    print("🧪 Rate Limiter Test\n")
    
    limiter = RateLimiter()
    
    # Test 1: Daily Reflection（1時間に1回）
    print("Test 1: Daily Reflection (1 per hour)")
    for i in range(3):
        can_exec = limiter.can_execute('daily_reflection')
        print(f"  Attempt {i+1}: {'✅ OK' if can_exec else '❌ REJECTED'}")
        
    print()
    
    # Test 2: Emotion Update（1秒に1回）
    print("Test 2: Emotion Update (1 per second)")
    for i in range(3):
        can_exec = limiter.can_execute('emotion_update')
        print(f"  Attempt {i+1}: {'✅ OK' if can_exec else '❌ REJECTED'}")
        if i == 0:
            time.sleep(1)  # 1秒待機
            
    print()
    
    # 統計表示
    limiter.print_stats()
    
    print("\n✅ Test complete")


if __name__ == '__main__':
    test_rate_limiter()

