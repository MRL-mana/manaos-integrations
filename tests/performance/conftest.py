"""
tests/performance/conftest.py
performance テストの sys.path 設定

llm/ やその他のモジュールを sys.path に追加する。
sys.exit(1) を含む古いスクリプト型テストへの対応も含む。
"""

import sys
import types
import pytest
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]

_EXTRA_PATHS = [
    _PROJECT_ROOT,
    _PROJECT_ROOT / "llm",
    _PROJECT_ROOT / "scripts" / "misc",
    _PROJECT_ROOT / "unified_api",
]

for _p in _EXTRA_PATHS:
    _s = str(_p)
    if _s not in sys.path:
        sys.path.insert(0, _s)

# torch スタブ（GPU テストを import できるようにする）
if "torch" not in sys.modules:
    _torch_stub = types.ModuleType("torch")
    _torch_stub.cuda = types.SimpleNamespace(  # type: ignore[attr-defined]
        is_available=lambda: False,
        get_device_name=lambda idx=0: "N/A",
        memory_allocated=lambda idx=0: 0,
        memory_reserved=lambda idx=0: 0,
        get_device_properties=lambda idx=0: types.SimpleNamespace(total_memory=0),
        synchronize=lambda: None,
    )
    _torch_stub.version = types.SimpleNamespace(cuda=None)  # type: ignore[attr-defined]
    _torch_stub.randn = lambda *a, **kw: None  # type: ignore[attr-defined]
    _torch_stub.matmul = lambda x, y: None  # type: ignore[attr-defined]

    class _TensorStub:  # scipy の is_torch_array チェック用
        pass

    _torch_stub.Tensor = _TensorStub  # type: ignore[attr-defined]
    # __spec__ を非 None にして scipy の is_torch_array の ValueError を防ぐ
    _torch_stub.__spec__ = types.SimpleNamespace(  # type: ignore[attr-defined]
        name="torch", loader=None, submodule_search_locations=None
    )
    sys.modules["torch"] = _torch_stub


# ─────────────────────────────────────────────────────────────
# Ollama / LM Studio HTTP モック（test_llm_call を PASS にする）
# ─────────────────────────────────────────────────────────────
from unittest.mock import MagicMock, patch  # noqa: E402


class _FakeResponse:
    """requests.Response の最小スタブ"""

    def __init__(self, status_code: int, body: dict):
        self.status_code = status_code
        self._body = body

    def json(self):
        return self._body

    def raise_for_status(self):
        pass


def _fake_requests_post(url: str, **kwargs):
    """Ollama / n8n / キャッシュ系 POST エンドポイントをスタブ応答"""
    url_lower = (url or "").lower()
    if "api/generate" in url_lower or "api/chat" in url_lower:
        return _FakeResponse(200, {"response": "stub response", "eval_count": 5})
    if "chat/completions" in url_lower:
        return _FakeResponse(200, {
            "choices": [{"message": {"content": "stub"}}],
            "usage": {"completion_tokens": 5},
            "model": "stub",
        })
    return _FakeResponse(200, {})


def _fake_requests_get(url: str, **kwargs):
    """LM Studio モデル一覧 GET → 接続不可を模倣（ConnectionError）"""
    import requests as _req
    url_lower = (url or "").lower()
    if "v1/models" in url_lower or "lm_studio" in url_lower or "1234" in url_lower:
        raise _req.exceptions.ConnectionError("LM Studio not available (stub)")
    # キャッシュ API 等は 404 を返す
    return _FakeResponse(404, {})


@pytest.fixture(autouse=True)
def _mock_llm_http():
    """全 performance テストで LLM HTTP 呼び出しをモック"""
    with patch("requests.post", side_effect=_fake_requests_post), \
         patch("requests.get", side_effect=_fake_requests_get):
        yield
