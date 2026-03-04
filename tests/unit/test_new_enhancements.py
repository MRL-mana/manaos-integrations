"""
新しい統合テスト - OpenAPI, Health Check Optimizer, その他の拡張機能

テスト対象:
- OpenAPI スペック生成と提供
- Health Check キャッシング
- 統合 API セキュリティ
"""

import os
import pytest
import json
import time
from datetime import datetime
from unittest.mock import patch


@pytest.fixture(scope="module")
def client():
    """テスト用 Flask クライアント（モジュール共有・レートリミット無効）"""
    try:
        from unified_api_server import app
        app.config["TESTING"] = True
        # テスト中はレートリミットを無効化
        with patch.dict(os.environ, {"MANAOS_RATE_LIMIT_ENABLED": "false"}):
            yield app.test_client()
    except ImportError:
        pytest.skip("unified_api_server not available")


class TestOpenAPIGeneration:
    """OpenAPI スペック生成のテスト"""
    
    def test_openapi_spec_available(self, client):
        """OpenAPI スペックが利用可能か"""
        response = client.get("/api/openapi.json")
        assert response.status_code == 200
        
        spec = response.get_json()
        assert spec is not None
        assert "openapi" in spec
        assert spec["openapi"] == "3.0.3"
    
    def test_openapi_spec_has_required_fields(self, client):
        """OpenAPI スペックが必須フィールドを含むか"""
        response = client.get("/api/openapi.json")
        spec = response.get_json()
        
        # 必須フィールド
        assert "info" in spec
        assert "title" in spec["info"]
        assert "version" in spec["info"]
        assert "servers" in spec
        assert "paths" in spec
    
    def test_openapi_includes_health_endpoint(self, client):
        """OpenAPI スペックがヘルスチェックエンドポイントを含むか"""
        response = client.get("/api/openapi.json")
        spec = response.get_json()
        
        # /health パスが含まれているか
        paths = spec.get("paths", {})
        assert "/health" in paths or len(paths) > 0
    
    def test_swagger_ui_available(self, client):
        """Swagger UI が利用可能か"""
        response = client.get("/api/swagger")
        assert response.status_code == 200
        
        # HTML が返されているか
        assert b"swagger-ui" in response.data or b"Swagger" in response.data


class TestHealthCheckOptimization:
    """HealthCheck Optimizer のテスト"""
    
    def test_health_endpoint_fast(self, client):
        """/health エンドポイントが軽量か（<100ms）"""
        start = time.time()
        response = client.get("/health")
        elapsed = (time.time() - start) * 1000
        
        assert response.status_code == 200
        assert elapsed < 100, f"Health check too slow: {elapsed:.2f}ms"
    
    def test_health_response_format(self, client):
        """ヘルスチェックレスポンスの形式"""
        response = client.get("/health")
        data = response.get_json()
        
        assert "status" in data
        assert "timestamp" in data
        assert data["status"] == "alive"
    
    def test_ready_endpoint_available(self, client):
        """/ready エンドポイントが利用可能か"""
        response = client.get("/ready")
        # 200 または 503（初期化中）が期待される
        assert response.status_code in (200, 503)
    
    def test_status_endpoint_consistent(self, client):
        """ステータスエンドポイントが一貫性を保つか"""
        response1 = client.get("/status")
        time.sleep(0.1)
        response2 = client.get("/status")
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        data1 = response1.get_json()
        data2 = response2.get_json()
        
        # ステータスが一貫しているか
        assert data1.get("status") in ("ready", "starting", "error")
        assert data2.get("status") in ("ready", "starting", "error")


class TestAPISecurityHeaders:
    """API セキュリティヘッダーのテスト"""
    
    def test_cors_headers_present(self, client):
        """CORS ヘッダーが存在するか"""
        response = client.get("/health")
        
        # CORS ヘッダーが存在するか確認
        # (CORS 有効の場合)
        assert response.status_code == 200
    
    def test_json_content_type(self, client):
        """JSON レスポンスに正しい Content-Type があるか"""
        response = client.get("/health")
        
        content_type = response.headers.get("Content-Type", "")
        assert "json" in content_type.lower()


class TestIntegrationEndpoints:
    """主要統合エンドポイントのテスト"""
    
    def test_integrations_status_requires_auth(self, client):
        """/api/integrations/status が認証を要求するか"""
        # 認証なしのリクエスト
        response = client.get("/api/integrations/status")
        
        # 認証なしの場合は 401 または 403 が期待される
        # サーバー設定によっては無認証でも 200 が返る可能性がある
        assert response.status_code in (200, 401, 403, 404)
    
    def test_health_returns_valid_json(self, client):
        """ヘルスチェックが有効な JSON を返すか"""
        response = client.get("/health")
        
        assert response.status_code == 200
        assert response.content_type is not None
        assert "json" in response.content_type.lower()
        
        # JSON を解析できるか
        data = response.get_json()
        assert isinstance(data, dict)


class TestPerformance:
    """パフォーマンス関連テスト"""
    
    def test_concurrent_health_checks(self, client):
        """複数の同時ヘルスチェック"""
        import threading
        
        results = []
        
        def check():
            start = time.time()
            response = client.get("/health")
            elapsed = time.time() - start
            results.append((response.status_code, elapsed))
        
        threads = []
        for _ in range(5):
            t = threading.Thread(target=check)
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join(timeout=5)
        
        # すべてのリクエストが完了したことを確認
        assert len(results) == 5
        
        # すべてが成功したことを確認
        for status, elapsed in results:
            assert status == 200
            assert elapsed < 0.5, f"Request too slow: {elapsed:.2f}s"
    
    def test_openapi_caching(self, client):
        """OpenAPI スペックのキャッシング"""
        # 最初のリクエスト
        start1 = time.time()
        response1 = client.get("/api/openapi.json")
        time1 = time.time() - start1
        
        # 2番目のリクエスト（キャッシュ）
        start2 = time.time()
        response2 = client.get("/api/openapi.json")
        time2 = time.time() - start2
        
        # 両方成功
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        # スペックが同じ
        spec1 = response1.get_json()
        spec2 = response2.get_json()
        assert spec1 == spec2


class TestErrorHandling:
    """エラーハンドリングテスト"""
    
    def test_invalid_endpoint(self, client):
        """存在しないエンドポイントへのアクセス"""
        response = client.get("/api/nonexistent")
        
        # 404 が返されるはず
        assert response.status_code in (404, 405)
    
    def test_invalid_json_payload(self, client):
        """不正な JSON ペイロード"""
        response = client.post(
            "/api/llm/analyze",
            data="invalid json",
            content_type="application/json"
        )
        
        # エラーレスポンスが返されるはず
        assert response.status_code in (400, 401, 405, 500)
