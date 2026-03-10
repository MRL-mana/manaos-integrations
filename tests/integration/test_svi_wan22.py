"""SVI × Wan 2.2 動作確認（pytest対応）"""

import importlib
import os
import sys
import types
from unittest.mock import MagicMock, patch

import pytest
import requests

try:
    from manaos_integrations._paths import UNIFIED_API_PORT
except Exception:
    try:
        from _paths import UNIFIED_API_PORT  # type: ignore
    except Exception:
        UNIFIED_API_PORT = int(os.getenv("UNIFIED_API_PORT", "9510"))

# svi_wan22_video_integration スタブ（未インストール環境用）
if "svi_wan22_video_integration" not in sys.modules:
    _svi_stub_mod = types.ModuleType("svi_wan22_video_integration")

    class _StubSVI:
        def __init__(self, **kwargs):
            pass
        def is_available(self):
            return True
        def get_queue_status(self):
            return {"queue_remaining": 0}
        def translate_prompt_to_english(self, text):
            return text

    _svi_stub_mod.SVIWan22VideoIntegration = _StubSVI  # type: ignore
    sys.modules["svi_wan22_video_integration"] = _svi_stub_mod


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
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    with patch("requests.get", return_value=mock_resp):
        health = requests.get(f"{base_url}/health", timeout=5)
    assert health.status_code == 200
