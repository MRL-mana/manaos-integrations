#!/usr/bin/env python3
"""
Circuit Breaker - サーキットブレーカー

障害を検知して自動的にシステムを保護します。

States:
- CLOSED: 正常動作（障害なし）
- OPEN: 障害発生（全リクエスト拒否）
- HALF_OPEN: 回復テスト中
"""

import time
from datetime import datetime
from enum import Enum
from typing import Callable, Any, Optional


class CircuitState(Enum):
    """サーキットブレーカーの状態"""
    CLOSED = "closed"  # 正常
    OPEN = "open"  # 障害発生
    HALF_OPEN = "half_open"  # 回復テスト中


class CircuitBreaker:
    """サーキットブレーカー"""
    
    def __init__(self, 
                 failure_threshold: int = 5,
                 recovery_timeout: int = 60,
                 success_threshold: int = 2):
        """
        Args:
            failure_threshold: OPENになる失敗回数
            recovery_timeout: OPEN後の回復待機時間（秒）
            success_threshold: HALF_OPENからCLOSEDになる成功回数
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.last_state_change = datetime.now()
        
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        関数を保護して実行
        
        Returns:
            関数の戻り値（失敗時はNone）
        """
        if self.state == CircuitState.OPEN:
            # OPEN状態：回復待機時間チェック
            if self._should_attempt_reset():
                self._transition_to_half_open()
            else:
                raise CircuitBreakerOpenError("Circuit breaker is OPEN")
                
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
            
        except Exception as e:
            self._on_failure()
            raise
            
    def _should_attempt_reset(self) -> bool:
        """リセット試行すべきか"""
        if self.last_failure_time is None:
            return False
            
        elapsed = time.time() - self.last_failure_time
        return elapsed >= self.recovery_timeout
        
    def _transition_to_half_open(self):
        """HALF_OPEN状態へ遷移"""
        self.state = CircuitState.HALF_OPEN
        self.success_count = 0
        self.last_state_change = datetime.now()
        print(f"🔄 Circuit Breaker: OPEN → HALF_OPEN")
        
    def _on_success(self):
        """成功時の処理"""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            
            if self.success_count >= self.success_threshold:
                self._transition_to_closed()
                
        self.failure_count = 0
        
    def _on_failure(self):
        """失敗時の処理"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitState.HALF_OPEN:
            # HALF_OPEN中の失敗：即座にOPEN
            self._transition_to_open()
            
        elif self.state == CircuitState.CLOSED:
            # CLOSED中の失敗：閾値チェック
            if self.failure_count >= self.failure_threshold:
                self._transition_to_open()
                
    def _transition_to_closed(self):
        """CLOSED状態へ遷移"""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_state_change = datetime.now()
        print(f"✅ Circuit Breaker: HALF_OPEN → CLOSED")
        
    def _transition_to_open(self):
        """OPEN状態へ遷移"""
        self.state = CircuitState.OPEN
        self.last_state_change = datetime.now()
        print(f"🚨 Circuit Breaker: {self.state.value} → OPEN")
        
    def get_status(self) -> dict:
        """現在の状態を取得"""
        return {
            'state': self.state.value,
            'failure_count': self.failure_count,
            'success_count': self.success_count,
            'last_state_change': self.last_state_change.isoformat()
        }


class CircuitBreakerOpenError(Exception):
    """サーキットブレーカーがOPEN状態の時のエラー"""
    pass


def test_circuit_breaker():
    """テスト実行"""
    print("🧪 Circuit Breaker Test\n")
    
    breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=2)
    
    def flaky_function(should_fail=False):
        if should_fail:
            raise Exception("Function failed!")
        return "Success"
    
    # Test 1: 正常動作
    print("Test 1: Normal operation")
    for i in range(2):
        try:
            result = breaker.call(flaky_function, should_fail=False)
            print(f"  Attempt {i+1}: {result}")
        except Exception as e:
            print(f"  Attempt {i+1}: Error - {e}")
    print()
    
    # Test 2: 連続失敗 → OPEN
    print("Test 2: Multiple failures → OPEN")
    for i in range(5):
        try:
            result = breaker.call(flaky_function, should_fail=True)
            print(f"  Attempt {i+1}: {result}")
        except CircuitBreakerOpenError as e:
            print(f"  Attempt {i+1}: {e}")
        except Exception as e:
            print(f"  Attempt {i+1}: Error")
    print()
    
    # Test 3: 回復待機 → HALF_OPEN
    print("Test 3: Recovery → HALF_OPEN → CLOSED")
    print(f"  Waiting {breaker.recovery_timeout} seconds...")
    time.sleep(breaker.recovery_timeout + 0.1)
    
    for i in range(3):
        try:
            result = breaker.call(flaky_function, should_fail=False)
            print(f"  Attempt {i+1}: {result}")
        except Exception as e:
            print(f"  Attempt {i+1}: Error - {e}")
    print()
    
    # ステータス表示
    status = breaker.get_status()
    print(f"Final State: {status['state']}")
    print(f"Failure Count: {status['failure_count']}")
    
    print("\n✅ Test complete")


if __name__ == '__main__':
    test_circuit_breaker()
