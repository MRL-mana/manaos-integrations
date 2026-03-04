"""SVI × Wan 2.2 動作確認（pytest対応）"""

import importlib
import os

import pytest
import requests

try:
    from manaos_integrations._paths import UNIFIED_API_PORT
except Exception:
    try:
        from _paths import UNIFIED_API_PORT  # type: ignore
    except Exception:
        UNIFIED_API_PORT = int(os.getenv("UNIFIED_API_PORT", "9510"))


def _create_svi_client():
    module = None
    last_error = None
    for module_name in ("svi_wan22_video_integration", "svi.svi_wan22_video_integration"):
        try:
            module = importlib.import_module(module_name)
            break
        except Exception as exc:
            last_error = exc
    if module is None:
        pytest.skip(f"svi_wan22_video_integration 読み込み失敗: {last_error}")

    integration_cls = getattr(module, "SVIWan22VideoIntegration", None)
    if integration_cls is None:
        pytest.skip("SVIWan22VideoIntegration が見つからないためスキップ")

    try:
        return integration_cls(base_url="http://127.0.0.1:8188")
    except Exception as exc:
        pytest.skip(f"SVIクライアント初期化失敗: {exc}")


def test_comfyui_connection_smoke():
    svi = _create_svi_client()
    available = svi.is_available()
    assert isinstance(available, bool)


def test_queue_status_smoke():
    svi = _create_svi_client()
    if not svi.is_available():
        pytest.skip("ComfyUI未接続（環境依存のためスキップ）")

    queue_status = svi.get_queue_status()
    assert isinstance(queue_status, dict)


def test_api_endpoint_smoke():
    base_url = os.getenv("MANAOS_INTEGRATION_API_URL", f"http://127.0.0.1:{UNIFIED_API_PORT}")
    try:
        health = requests.get(f"{base_url}/health", timeout=5)
    except requests.RequestException as exc:
        pytest.skip(f"統合APIに接続できないためスキップ: {exc}")

    assert health.status_code == 200
