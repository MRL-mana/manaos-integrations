"""
E2E テスト - 統合ワークフロー全体

主要なシステム統合を端から端までテストする
"""

import pytest
import time
import json
from datetime import datetime


class TestUnifiedAPIWorkflow:
    """統合API全体のワークフローテスト"""

    def test_health_check_flow(self, client):
        """ヘルスチェックワークフロー"""
        # 1. /health エンドポイントでプロセス確認
        response = client.get("/health")
        assert response.status_code == 200
        
        health = response.get_json()
        assert health["status"] == "alive"
        assert "timestamp" in health
        
        # 2. /ready エンドポイントで初期化確認
        response = client.get("/ready")
        assert response.status_code in (200, 503)
        
        # 3. /status で詳細ステータス確認
        response = client.get("/status")
        assert response.status_code == 200
        data = response.get_json()
        assert "status" in data
        assert data["status"] in ("ready", "starting", "error")
    
    def test_openapi_documentation_flow(self, client):
        """OpenAPI仕様の確認ワークフロー"""
        # 1. OpenAPI JSONを取得
        response = client.get("/api/openapi.json")
        assert response.status_code == 200
        
        spec = response.get_json()
        assert spec["openapi"] == "3.0.3"
        assert "info" in spec
        
        # 2. Swagger UI にアクセス
        response = client.get("/api/swagger")
        assert response.status_code == 200
        assert b"swagger-ui" in response.data or b"Swagger" in response.data
        
        # 3. スペックの整合性を確認
        assert "paths" in spec
        assert "servers" in spec
        assert "components" in spec
    
    def test_concurrent_requests_under_load(self, client):
        """負荷下での並行リクエストテスト"""
        import threading
        
        results = []
        errors = []
        
        def make_requests(count):
            for i in range(count):
                try:
                    start = time.time()
                    response = client.get("/health")
                    elapsed = time.time() - start
                    
                    if response.status_code == 200:
                        results.append(elapsed)
                    else:
                        errors.append(f"Status: {response.status_code}")
                except Exception as e:
                    errors.append(str(e))
        
        # 10スレッド × 5リクエスト = 50並行リクエスト
        threads = []
        for _ in range(10):
            t = threading.Thread(target=make_requests, args=(5,))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join(timeout=10)
        
        # 結果検証
        assert len(errors) == 0, f"エラー発生: {errors}"
        assert len(results) == 50, f"期待: 50リクエスト, 実際: {len(results)}"
        
        # パフォーマンス確認
        avg_time = sum(results) / len(results)
        max_time = max(results)
        
        assert avg_time < 0.1, f"平均応答時間が長い: {avg_time:.3f}s"
        assert max_time < 0.5, f"最大応答時間が長い: {max_time:.3f}s"


class TestMemorySystemIntegration:
    """メモリシステム統合テスト"""
    
    def test_memory_workflow(self):
        """メモリシステム全体のワークフロー"""
        try:
            from mrl_memory_integration import ManaOSMemoryManager
        except ImportError:
            pytest.skip("Memory integration not available")
        
        manager = ManaOSMemoryManager()
        
        # 1. メモリに情報を保存
        test_data = {
            "type": "test",
            "content": "E2E テストデータ",
            "metadata": {"timestamp": datetime.now().isoformat()}
        }
        
        manager.store(test_data, "e2e_test")
        
        # 2. メモリから情報を取得
        retrieved = manager.recall("e2e_test")
        assert retrieved is not None
        assert retrieved["content"] == "E2E テストデータ"
        
        # 3. メモリを検索
        results = manager.search("E2E")
        assert len(results) > 0
        assert any("E2E テストデータ" in str(r) for r in results)


class TestLLMRoutingIntegration:
    """LLM ルーティング統合テスト"""
    
    def test_llm_routing_workflow(self):
        """LLM ルーティング全体のワークフロー"""
        try:
            from llm_routing_mcp_server import LLMRouter
        except ImportError:
            pytest.skip("LLM routing not available")
        
        router = LLMRouter()
        
        # 1. モデル一覧を取得
        models = router.get_available_models()
        assert isinstance(models, list)
        
        # 2. 最適なモデルを選択
        optimal = router.select_optimal_model(
            prompt="テストプロンプト",
            constraints={"speed": "high", "quality": "medium"}
        )
        assert optimal is not None
        assert "model" in optimal


class TestLearningSystemIntegration:
    """学習システム統合テスト"""
    
    def test_learning_workflow(self):
        """学習システム全体のワークフロー"""
        try:
            from learning_system_api import LearningManager
        except ImportError:
            pytest.skip("Learning system not available")
        
        manager = LearningManager()
        
        # 1. 学習記録を追加
        learning_record = {
            "action": "test_action",
            "outcome": "success",
            "params": {"test": True},
            "timestamp": datetime.now().isoformat()
        }
        
        manager.record_action(learning_record)
        
        # 2. 学習統計を取得
        stats = manager.get_stats()
        assert isinstance(stats, dict)
        assert "total_actions" in stats


class TestErrorRecoveryWorkflow:
    """エラーリカバリーワークフロー"""
    
    def test_graceful_degradation(self, client):
        """グレースフルデグラデーション"""
        # 1. プライマリエンドポイントヘルスチェック
        response = client.get("/health")
        assert response.status_code == 200
        
        # 2. 複数エンドポイントのリトライ
        endpoints = ["/ready", "/status", "/api/openapi.json"]
        
        for endpoint in endpoints:
            for attempt in range(3):
                response = client.get(endpoint)
                if response.status_code in (200, 503):
                    break
                time.sleep(0.1)
            
            assert response.status_code in (200, 503, 404)
    
    def test_timeout_handling(self, client):
        """タイムアウト処理"""
        import threading
        
        def slow_request():
            try:
                # タイムアウト付きリクエスト
                client.get("/health", timeout=0.5)
            except Exception as e:
                pass
        
        thread = threading.Thread(target=slow_request)
        thread.start()
        thread.join(timeout=2)
        
        # スレッドが完了することを確認
        assert not thread.is_alive()


class TestPerformanceUnderLoad:
    """負荷下のパフォーマンステスト"""
    
    def test_latency_percentiles(self, client):
        """レイテンシパーセンタイル測定"""
        latencies = []
        
        for _ in range(100):
            start = time.time()
            response = client.get("/health")
            latency = (time.time() - start) * 1000  # ms
            
            if response.status_code == 200:
                latencies.append(latency)
        
        latencies.sort()
        
        # パーセンタイル計算
        p50 = latencies[len(latencies) // 2]
        p95 = latencies[int(len(latencies) * 0.95)]
        p99 = latencies[int(len(latencies) * 0.99)]
        
        # 性能要件確認（CI/開発環境にあわせた緩めの閾値）
        assert p50 < 500, f"P50: {p50:.2f}ms"
        assert p95 < 1000, f"P95: {p95:.2f}ms"
        assert p99 < 2000, f"P99: {p99:.2f}ms"
    
    def test_throughput_measurement(self, client):
        """スループット測定"""
        start_time = time.time()
        request_count = 0
        
        # 5秒間でできるだけ多くのリクエストを実行
        while time.time() - start_time < 5:
            response = client.get("/health")
            if response.status_code == 200:
                request_count += 1
        
        elapsed = time.time() - start_time
        throughput = request_count / elapsed
        
        # スループット要件確認
        assert throughput > 10, f"スループット: {throughput:.1f} req/s"


# Pytest fixture
@pytest.fixture(scope="module")
def client():
    """テスト用 Flask クライアント"""
    try:
        from unified_api_server import app
        app.config["TESTING"] = True
        yield app.test_client()
    except ImportError:
        pytest.skip("unified_api_server not available")
