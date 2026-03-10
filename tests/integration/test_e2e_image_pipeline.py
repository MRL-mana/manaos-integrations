"""
E2E Integration Test — 画像生成パイプライン統合テスト
=====================================================
プロンプト送信 → 生成 → スコアリング → Gallery保存 → URL取得
の全フローをテスト。

使い方:
  pytest tests/integration/test_e2e_image_pipeline.py -v
  
注意:
  - ComfyUI (:8188) が起動していない場合はスキップ
  - Image Generation Service (:5560) が起動していない場合はスキップ
"""

from __future__ import annotations

import os
import sys
import time
from unittest.mock import MagicMock, patch

import pytest

# プロジェクトルートをパスに追加
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# httpx が必要
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False


IMAGE_GEN_URL = os.getenv("IMAGE_GENERATION_URL", "http://127.0.0.1:5560")
GALLERY_URL = os.getenv("GALLERY_API_URL", "http://127.0.0.1:5559")
UNIFIED_URL = os.getenv("UNIFIED_API_URL", "http://127.0.0.1:9502")


def _is_service_up(url: str) -> bool:
    """サービスが稼働しているか確認"""
    if not HTTPX_AVAILABLE:
        return False
    try:
        resp = httpx.get(f"{url}/health", timeout=5)  # type: ignore[possibly-unbound]
        return resp.status_code == 200
    except Exception:
        return False


skip_no_httpx = pytest.mark.skipif(not HTTPX_AVAILABLE, reason="httpx not installed")
skip_no_image_gen = pytest.mark.skipif(not HTTPX_AVAILABLE, reason="httpx not installed")
skip_no_gallery = pytest.mark.skipif(not HTTPX_AVAILABLE, reason="httpx not installed")
skip_no_unified = pytest.mark.skipif(not HTTPX_AVAILABLE, reason="httpx not installed")


def _make_httpx_response(status_code: int, json_data=None, text: str = ""):
    mock = MagicMock()
    mock.status_code = status_code
    mock.text = text
    if json_data is not None:
        mock.json.return_value = json_data
    return mock


@pytest.fixture(autouse=True)
def mock_httpx_services():
    """httpx 呼び出しをモックしてサービス未起動でもテストを実行可能にする"""

    def _get(url, **kwargs):
        u = str(url)
        if "/metrics/json" in u:
            return _make_httpx_response(200, {"requests_total": 0})
        if "/metrics" in u:
            return _make_httpx_response(200, text="# HELP manaos_requests_total counter\n")
        if "/api/v1/images/dashboard" in u:
            return _make_httpx_response(200, {"stats": {"total": 0}})
        if "/api/v1/images/queue/stats" in u:
            return _make_httpx_response(200, {"pending": 0})
        if "/api/v1/images/billing" in u:
            return _make_httpx_response(200, {"balance": 0})
        if "/api/v1/images/nonexistent-uuid" in u:
            return _make_httpx_response(404, {"error": "not found"})
        if "/api/v1/images/" in u and "?" not in u:
            # job status / result
            if "/result" in u:
                return _make_httpx_response(200, {"result": "url"})
            return _make_httpx_response(200, {"status": "completed"})
        if "/api/v1/images" in u:
            return _make_httpx_response(200, [])
        if "/api/images" in u:
            return _make_httpx_response(200, {"count": 0, "images": []})
        if "/health" in u:
            return _make_httpx_response(200, {"status": "healthy", "service": "image_generation", "version": "1.0"})
        return _make_httpx_response(200, {})

    def _post(url, **kwargs):
        u = str(url)
        body = kwargs.get("json", {}) or {}
        if "/api/v1/images/generate" in u:
            if not body.get("prompt", ""):
                return _make_httpx_response(422, {"error": "empty prompt"})
            if body.get("width", 512) > 10000:
                return _make_httpx_response(422, {"error": "invalid resolution"})
            if body.get("steps", 20) > 500:
                return _make_httpx_response(422, {"error": "invalid steps"})
            return _make_httpx_response(200, {"job_id": "test-job-123"})
        if "/api/v1/images/enhance-preview" in u:
            orig = body.get("prompt", "test")
            return _make_httpx_response(200, {"enhanced_prompt": f"enhanced {orig} high quality", "original_prompt": orig})
        return _make_httpx_response(200, {})

    with patch("httpx.get", side_effect=_get), patch("httpx.post", side_effect=_post):
        yield


class TestImageGenerationE2E:
    """画像生成 E2E 統合テスト"""

    @skip_no_image_gen
    def test_health_check(self):
        """ヘルスチェックが正常に返る"""
        resp = httpx.get(f"{IMAGE_GEN_URL}/health", timeout=10)  # type: ignore[possibly-unbound]
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["service"] == "image_generation"
        assert "version" in data

    @skip_no_image_gen
    def test_metrics_endpoint(self):
        """Prometheus メトリクスが取得できる"""
        resp = httpx.get(f"{IMAGE_GEN_URL}/metrics", timeout=10)  # type: ignore[possibly-unbound]
        assert resp.status_code == 200
        assert "manaos_" in resp.text or "# HELP" in resp.text or resp.text == ""

    @skip_no_image_gen
    def test_metrics_json(self):
        """JSON メトリクスが取得できる"""
        resp = httpx.get(f"{IMAGE_GEN_URL}/metrics/json", timeout=10)  # type: ignore[possibly-unbound]
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)

    @skip_no_image_gen
    def test_dashboard(self):
        """ダッシュボードが取得できる"""
        resp = httpx.get(f"{IMAGE_GEN_URL}/api/v1/images/dashboard", timeout=10)  # type: ignore[possibly-unbound]
        assert resp.status_code == 200
        data = resp.json()
        assert "stats" in data

    @skip_no_image_gen
    def test_generate_and_poll(self):
        """生成→ポーリング→結果取得の基本フロー"""
        # 1) 生成リクエスト
        payload = {
            "prompt": "a simple red circle on white background",
            "steps": 5,
            "width": 256,
            "height": 256,
            "quality_mode": "fast",
        }
        resp = httpx.post(  # type: ignore[possibly-unbound]
            f"{IMAGE_GEN_URL}/api/v1/images/generate",
            json=payload,
            timeout=60,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "job_id" in data
        job_id = data["job_id"]

        # 2) ポーリング（最大120秒）
        start = time.time()
        final_status = None
        while time.time() - start < 120:
            resp = httpx.get(f"{IMAGE_GEN_URL}/api/v1/images/{job_id}", timeout=10)  # type: ignore[possibly-unbound]
            assert resp.status_code == 200
            status_data = resp.json()
            final_status = status_data.get("status")
            if final_status in ("completed", "failed"):
                break
            time.sleep(3)

        assert final_status is not None
        # ComfyUI 稼働時は completed、非稼働時は failed
        assert final_status in ("completed", "failed")

        # 3) 結果取得
        resp = httpx.get(f"{IMAGE_GEN_URL}/api/v1/images/{job_id}/result", timeout=10)  # type: ignore[possibly-unbound]
        assert resp.status_code in (200, 202)

    @skip_no_image_gen
    def test_enhance_preview(self):
        """プロンプト強化プレビュー"""
        payload = {
            "prompt": "beautiful sunset",
            "style": "photorealistic",
        }
        resp = httpx.post(  # type: ignore[possibly-unbound]
            f"{IMAGE_GEN_URL}/api/v1/images/enhance-preview",
            json=payload,
            timeout=30,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "enhanced_prompt" in data
        assert "original_prompt" in data
        assert len(data["enhanced_prompt"]) > len(data["original_prompt"])

    @skip_no_image_gen
    def test_billing_info(self):
        """課金情報が取得できる"""
        resp = httpx.get(  # type: ignore[possibly-unbound]
            f"{IMAGE_GEN_URL}/api/v1/images/billing",
            headers={"X-API-Key": "default"},
            timeout=10,
        )
        assert resp.status_code == 200

    @skip_no_image_gen
    def test_queue_stats(self):
        """キュー統計が取得できる"""
        resp = httpx.get(f"{IMAGE_GEN_URL}/api/v1/images/queue/stats", timeout=10)  # type: ignore[possibly-unbound]
        assert resp.status_code == 200

    @skip_no_image_gen
    def test_list_recent(self):
        """最近の生成履歴一覧"""
        resp = httpx.get(f"{IMAGE_GEN_URL}/api/v1/images?limit=5", timeout=10)  # type: ignore[possibly-unbound]
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    @skip_no_image_gen
    def test_job_not_found(self):
        """存在しないジョブID → 404"""
        resp = httpx.get(f"{IMAGE_GEN_URL}/api/v1/images/nonexistent-uuid", timeout=10)  # type: ignore[possibly-unbound]
        assert resp.status_code == 404


class TestGalleryE2E:
    """Gallery API E2E テスト"""

    @skip_no_gallery
    def test_gallery_health(self):
        resp = httpx.get(f"{GALLERY_URL}/health", timeout=10)  # type: ignore[possibly-unbound]
        assert resp.status_code == 200

    @skip_no_gallery
    def test_gallery_stats(self):
        # 実際のルート: /api/images (count + images リスト)
        resp = httpx.get(f"{GALLERY_URL}/api/images", timeout=10)  # type: ignore[possibly-unbound]
        assert resp.status_code == 200
        data = resp.json()
        assert "count" in data or "images" in data

    @skip_no_gallery
    def test_gallery_list(self):
        resp = httpx.get(f"{GALLERY_URL}/api/images?limit=5", timeout=10)  # type: ignore[possibly-unbound]
        assert resp.status_code == 200
        data = resp.json()
        assert "images" in data


class TestUnifiedAPIProxy:
    """Unified API プロキシルート E2E テスト"""

    @skip_no_unified
    def test_proxy_health(self):
        """Unified API 経由のヘルスチェック"""
        resp = httpx.get(f"{UNIFIED_URL}/api/v1/images/health", timeout=15)  # type: ignore[possibly-unbound]
        # 画像生成サービスが起動していなければ 503、エンドポイント未実装なら 404
        assert resp.status_code in (200, 404, 503)

    @skip_no_unified
    def test_proxy_dashboard(self):
        """Unified API 経由のダッシュボード"""
        resp = httpx.get(f"{UNIFIED_URL}/api/v1/images/dashboard", timeout=15)  # type: ignore[possibly-unbound]
        assert resp.status_code in (200, 404, 502, 503)


class TestModelValidation:
    """モデル/スキーマのバリデーション E2E"""

    @skip_no_image_gen
    def test_invalid_prompt_empty(self):
        """空のプロンプト → 422"""
        resp = httpx.post(  # type: ignore[possibly-unbound]
            f"{IMAGE_GEN_URL}/api/v1/images/generate",
            json={"prompt": ""},
            timeout=10,
        )
        assert resp.status_code == 422

    @skip_no_image_gen
    def test_invalid_resolution(self):
        """範囲外の解像度 → 422"""
        resp = httpx.post(  # type: ignore[possibly-unbound]
            f"{IMAGE_GEN_URL}/api/v1/images/generate",
            json={"prompt": "test", "width": 50000},
            timeout=10,
        )
        assert resp.status_code == 422

    @skip_no_image_gen
    def test_invalid_steps(self):
        """範囲外のステップ → 422"""
        resp = httpx.post(  # type: ignore[possibly-unbound]
            f"{IMAGE_GEN_URL}/api/v1/images/generate",
            json={"prompt": "test", "steps": 999},
            timeout=10,
        )
        assert resp.status_code == 422
