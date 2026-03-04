"""
⚖️ LLM負荷分散・フォールバックシステム
複数モデルへの分散と自動フォールバック
"""

import requests
import time
import random
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
from always_ready_llm_client import AlwaysReadyLLMClient, ModelType, TaskType, LLMResponse


class LoadBalanceStrategy(Enum):
    """負荷分散戦略"""
    ROUND_ROBIN = "round_robin"      # 順番に分散
    RANDOM = "random"                 # ランダム
    LEAST_CONNECTIONS = "least_conn"  # 接続数最小
    FASTEST_RESPONSE = "fastest"      # 最速応答優先


@dataclass
class ModelEndpoint:
    """モデルエンドポイント"""
    model: ModelType
    priority: int  # 優先度（低いほど優先）
    max_concurrent: int = 5
    timeout_seconds: int = 60
    health_check_url: Optional[str] = None
    is_healthy: bool = True
    last_used: float = 0.0
    active_connections: int = 0
    avg_latency_ms: float = 0.0
    success_count: int = 0
    failure_count: int = 0


class LLMLoadBalancer:
    """LLM負荷分散システム"""
    
    def __init__(
        self,
        endpoints: List[ModelEndpoint],
        strategy: LoadBalanceStrategy = LoadBalanceStrategy.ROUND_ROBIN,
        enable_fallback: bool = True
    ):
        """
        初期化
        
        Args:
            endpoints: モデルエンドポイントリスト
            strategy: 負荷分散戦略
            enable_fallback: フォールバックを有効にするか
        """
        self.endpoints = sorted(endpoints, key=lambda x: x.priority)
        self.strategy = strategy
        self.enable_fallback = enable_fallback
        self.current_index = 0
        self.clients: Dict[ModelType, AlwaysReadyLLMClient] = {}
        
        # 各モデル用のクライアントを作成
        for endpoint in self.endpoints:
            self.clients[endpoint.model] = AlwaysReadyLLMClient()
    
    def _select_endpoint(self) -> Optional[ModelEndpoint]:
        """エンドポイント選択"""
        # ヘルシーなエンドポイントのみフィルタ
        healthy_endpoints = [e for e in self.endpoints if e.is_healthy]
        
        if not healthy_endpoints:
            return None
        
        if self.strategy == LoadBalanceStrategy.ROUND_ROBIN:
            endpoint = healthy_endpoints[self.current_index % len(healthy_endpoints)]
            self.current_index += 1
            return endpoint
        
        elif self.strategy == LoadBalanceStrategy.RANDOM:
            return random.choice(healthy_endpoints)
        
        elif self.strategy == LoadBalanceStrategy.LEAST_CONNECTIONS:
            return min(healthy_endpoints, key=lambda x: x.active_connections)
        
        elif self.strategy == LoadBalanceStrategy.FASTEST_RESPONSE:
            return min(healthy_endpoints, key=lambda x: x.avg_latency_ms)
        
        return healthy_endpoints[0]
    
    def _health_check(self, endpoint: ModelEndpoint) -> bool:
        """ヘルスチェック"""
        if endpoint.health_check_url:
            try:
                response = requests.get(endpoint.health_check_url, timeout=2)
                return response.status_code == 200
            except Exception:
                return False
        
        # デフォルト: 成功率で判定
        total = endpoint.success_count + endpoint.failure_count
        if total == 0:
            return True
        
        success_rate = endpoint.success_count / total
        return success_rate > 0.5  # 50%以上でヘルシー
    
    def chat(
        self,
        message: str,
        task_type: TaskType = TaskType.CONVERSATION,
        max_retries: int = 3
    ) -> LLMResponse:
        """
        LLMチャット（負荷分散 + フォールバック）
        
        Args:
            message: メッセージ
            task_type: タスクタイプ
            max_retries: 最大リトライ回数
        
        Returns:
            LLMResponse
        """
        retry_count = 0
        tried_endpoints = []
        
        while retry_count < max_retries:
            # エンドポイント選択
            endpoint = self._select_endpoint()
            
            if not endpoint:
                # 全てのエンドポイントがダウン
                if tried_endpoints:
                    # 最後に試したエンドポイントを再試行
                    endpoint = tried_endpoints[-1]
                else:
                    raise Exception("利用可能なエンドポイントがありません")
            
            # 既に試したエンドポイントはスキップ
            if endpoint in tried_endpoints:
                retry_count += 1
                continue
            
            tried_endpoints.append(endpoint)
            
            # 接続数カウント増加
            endpoint.active_connections += 1
            endpoint.last_used = time.time()
            
            try:
                # LLM呼び出し
                start_time = time.time()
                client = self.clients[endpoint.model]
                response = client.chat(
                    message,
                    model=endpoint.model,
                    task_type=task_type
                )
                
                # 成功統計更新
                latency_ms = (time.time() - start_time) * 1000
                endpoint.success_count += 1
                endpoint.avg_latency_ms = (
                    (endpoint.avg_latency_ms * (endpoint.success_count - 1) + latency_ms) /
                    endpoint.success_count
                )
                
                return response
            
            except Exception as e:
                # 失敗統計更新
                endpoint.failure_count += 1
                endpoint.is_healthy = self._health_check(endpoint)
                
                # フォールバック有効で、まだ試していないエンドポイントがある場合
                if self.enable_fallback and retry_count < max_retries - 1:
                    retry_count += 1
                    continue
                else:
                    raise Exception(f"エンドポイント {endpoint.model.value} でエラー: {e}")
            
            finally:
                # 接続数カウント減少
                endpoint.active_connections -= 1
        
        raise Exception("全てのエンドポイントで失敗しました")
    
    def get_stats(self) -> Dict[str, Any]:
        """統計情報取得"""
        return {
            "strategy": self.strategy.value,
            "endpoints": [
                {
                    "model": e.model.value,
                    "priority": e.priority,
                    "is_healthy": e.is_healthy,
                    "active_connections": e.active_connections,
                    "success_count": e.success_count,
                    "failure_count": e.failure_count,
                    "success_rate": (
                        e.success_count / (e.success_count + e.failure_count)
                        if (e.success_count + e.failure_count) > 0 else 0
                    ),
                    "avg_latency_ms": e.avg_latency_ms
                }
                for e in self.endpoints
            ]
        }


# 使用例
if __name__ == "__main__":
    # エンドポイント設定
    endpoints = [
        ModelEndpoint(
            model=ModelType.LIGHT,
            priority=1,  # 最優先
            max_concurrent=10,
            timeout_seconds=30
        ),
        ModelEndpoint(
            model=ModelType.MEDIUM,
            priority=2,
            max_concurrent=5,
            timeout_seconds=60
        ),
        ModelEndpoint(
            model=ModelType.HEAVY,
            priority=3,  # 最後の手段
            max_concurrent=2,
            timeout_seconds=120
        )
    ]
    
    # 負荷分散システム初期化
    balancer = LLMLoadBalancer(
        endpoints=endpoints,
        strategy=LoadBalanceStrategy.ROUND_ROBIN,
        enable_fallback=True
    )
    
    # チャット実行
    print("=== 負荷分散チャット ===")
    try:
        response = balancer.chat(
            "こんにちは！",
            task_type=TaskType.CONVERSATION
        )
        print(f"レスポンス: {response.response}")
        print(f"モデル: {response.model}")
        print(f"ソース: {response.source}")
    except Exception as e:
        print(f"エラー: {e}")
    
    # 統計情報
    print("\n=== 統計情報 ===")
    stats = balancer.get_stats()
    import json
    print(json.dumps(stats, indent=2, ensure_ascii=False))






















