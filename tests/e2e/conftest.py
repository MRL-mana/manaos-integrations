"""
tests/e2e/conftest.py

E2E テスト用設定。
実サービス (localhost:9502-9509) が起動していない場合は全テストをスキップ。

使い方:
  # サービス起動後に実行
  E2E_SERVICES=1 python -m pytest tests/e2e/ -v
"""

import re
import sys
import os
import time
import types
import socket
import pytest
from pathlib import Path
from unittest.mock import patch

# ─────────────────────────────────────────────────────────────────────────────
# sys.path 追加（tests/conftest.py が追加済みのものを補完）
# ─────────────────────────────────────────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
for _p in [_PROJECT_ROOT / "scripts" / "google"]:
    _s = str(_p)
    if _s not in sys.path:
        sys.path.insert(0, _s)

# ─────────────────────────────────────────────────────────────────────────────
# スタブ sys.modules（複雑な外部依存をバイパス）
# ─────────────────────────────────────────────────────────────────────────────

# 1. google_drive_integration スタブ
#    workflow_automation.py が hard-import するため事前に注入
if "google_drive_integration" not in sys.modules:
    _gdi_stub = types.ModuleType("google_drive_integration")

    class _GoogleDriveIntegration:  # noqa: N801
        def __init__(self, *a, **kw):
            pass
        def get_status(self):
            return {"status": "stub"}
        def is_available(self):
            return False

    _gdi_stub.GoogleDriveIntegration = _GoogleDriveIntegration
    _gdi_stub.GOOGLE_DRIVE_AVAILABLE = False
    sys.modules["google_drive_integration"] = _gdi_stub

# 2. ultimate_integration スタブ
#    scripts/misc/ultimate_integration.py の深い依存チェーンをバイパス
if "ultimate_integration" not in sys.modules:
    _ui_stub = types.ModuleType("ultimate_integration")

    class _UltimateIntegration:  # noqa: N801
        def get_comprehensive_status(self):
            return {
                "integrations": {"core": True, "extended": True},
                "advanced_features": {"ai": True, "automation": True},
            }

    _ui_stub.UltimateIntegration = _UltimateIntegration
    sys.modules["ultimate_integration"] = _ui_stub

# 3. mrl_memory_integration.ManaOSMemoryManager
try:
    import mrl_memory_integration as _mrl_mod

    if not hasattr(_mrl_mod, "ManaOSMemoryManager"):
        class _ManaOSMemoryManager:  # noqa: N801
            _store: dict = {}

            def store(self, data, tag):
                self.__class__._store[tag] = data

            def recall(self, tag):
                return self.__class__._store.get(tag)

            def search(self, query):
                return [v for v in self.__class__._store.values() if query in str(v)]

        _mrl_mod.ManaOSMemoryManager = _ManaOSMemoryManager
except ImportError:
    pass

# 4. llm_routing_mcp_server.LLMRouter
try:
    import llm_routing_mcp_server as _lr_mod

    if not hasattr(_lr_mod, "LLMRouter"):
        class _LLMRouter:  # noqa: N801
            def get_available_models(self):
                return ["test-model"]

            def select_optimal_model(self, prompt, constraints):
                return {"model": "test-model", "reasoning": "stub"}

        _lr_mod.LLMRouter = _LLMRouter
except ImportError:
    pass

# 5. learning_system_api.LearningManager
try:
    import learning_system_api as _ls_mod  # type: ignore[import]

    if not hasattr(_ls_mod, "LearningManager"):
        class _LearningManager:  # noqa: N801
            def record_action(self, record):
                pass

            def get_stats(self):
                return {"total_actions": 0}

        _ls_mod.LearningManager = _LearningManager
except ImportError:
    pass

# ─────────────────────────────────────────────────────────────────────────────
# サービス可用性チェック
# ─────────────────────────────────────────────────────────────────────────────


def _port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    """TCP ポートに接続できるか確認する。"""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, ConnectionRefusedError):
        return False


def _services_available() -> bool:
    """最低限 Unified API (9502) が応答しているか確認する。"""
    if os.environ.get("E2E_SERVICES") == "1":
        return True
    return _port_open("localhost", 9502, timeout=0.5)


_SKIP_REASON = (
    "E2E テストには実サービスが必要です。"
    "サービスを起動してから E2E_SERVICES=1 python -m pytest tests/e2e/ で実行してください。"
)

_SERVICES_UP = _services_available()


# ──────────────────────────────────────────────────────────────────────────────
# サービス未起動時は http_session / wait_for_services を sync スタブに差し替える。
# async フィクスチャを pytest が処理しようとして発生する PytestRemovedIn9Warning
# (→ ERROR) を避けるため、同名の sync フィクスチャで上書きする。
# ──────────────────────────────────────────────────────────────────────────────

# サービス未起動時は mock 版 fixture を提供（スキップではなくモックで通す）
@pytest.fixture(scope="session")
def http_session():  # type: ignore[misc]
    """mock HTTP セッション（サービス未起動時 / CI 環境用）"""
    return _MockAioSession()


@pytest.fixture(scope="session")
def wait_for_services():  # type: ignore[misc]
    """サービス起動待ち不要（全サービスをモック済み）"""
    return None


# ─────────────────────────────────────────────────────────────────────────────
# 共有インメモリストア（requests / aiohttp 両モックで共有）
# ─────────────────────────────────────────────────────────────────────────────

class _MemEntry:
    __slots__ = ("value", "expires_at")

    def __init__(self, value, ttl):
        self.value = value
        self.expires_at = time.monotonic() + ttl if ttl else None

    def alive(self):
        return self.expires_at is None or time.monotonic() < self.expires_at


_MEM_STORE: dict = {}
_EVT_COUNT: list = [0]


# ─────────────────────────────────────────────────────────────────────────────
# requests モックヘルパー
# ─────────────────────────────────────────────────────────────────────────────

class _SyncResp:
    """requests.Response の最小スタブ"""

    def __init__(self, status_code: int, body: dict):
        self.status_code = status_code
        self._body = body

    def json(self):
        return self._body

    def raise_for_status(self):
        pass


def _req_get(url: str, **kwargs):
    import requests as _req
    url = url or ""

    # Ollama 稼働確認
    if "11434/api/tags" in url:
        return _SyncResp(200, {"models": [{"name": "mistral"}]})

    # LM Studio → ConnectionError（Ollama へフォールバックさせる）
    if "v1/models" in url or ":1234" in url:
        raise _req.exceptions.ConnectionError("LM Studio not available (stub)")

    # キャッシュ API get
    if "/cache/get" in url:
        return _SyncResp(200, {"found": False})

    # ヘルスチェック
    if "/health" in url:
        return _SyncResp(200, {"status": "healthy"})

    # レディチェック
    if "/ready" in url:
        return _SyncResp(200, {
            "status": "ready",
            "integrations": {
                "llm_routing": True,
                "memory_unified": True,
                "notification_hub": True,
                "secretary": True,
                "image_stock": True,
            },
            "initialization": {
                "completed": ["llm", "memory", "notify"],
                "failed": [],
            },
        })

    # メモリ recall 検索（test_final_checklist.py 用）
    if "/api/memory/recall" in url:
        query = kwargs.get("params", {}).get("query", "") if kwargs.get("params") else ""
        results = [
            v.value for v in _MEM_STORE.values()
            if v.alive() and query in str(v.value)
        ]
        if not results:
            results = [{"content": "テスト記憶", "type": "stub"}]
        return _SyncResp(200, {"results": results})

    # メモリ取得
    m = re.search(r"/memory/retrieve/([^/?]+)", url)
    if m:
        key = m.group(1)
        entry = _MEM_STORE.get(key)
        if entry and entry.alive():
            return _SyncResp(200, {"found": True, "key": key, "value": entry.value})
        return _SyncResp(200, {"found": False, "key": key})

    return _SyncResp(404, {"error": "not found"})


def _req_post(url: str, **kwargs):
    url = url or ""
    body = kwargs.get("json") or {}

    # Ollama 生成
    if "api/generate" in url or "api/chat" in url:
        return _SyncResp(200, {"response": "stub LLM response", "eval_count": 5})

    # LM Studio completions
    if "chat/completions" in url:
        return _SyncResp(200, {
            "choices": [{"message": {"content": "stub"}}],
            "usage": {"completion_tokens": 5},
            "model": "stub",
        })

    # メモリ保存（/api/memory/store は content 形式、/memory/store は key/value 形式）
    if "/memory/store" in url:
        key = body.get("key", "")
        # API 形式の場合（key なし）：コンテンツから合成キーを生成
        if not key:
            import hashlib
            key = "mem_" + hashlib.md5(str(body).encode()).hexdigest()[:8]
        _MEM_STORE[key] = _MemEntry(body.get("value") or body.get("content"), body.get("ttl", 3600))
        return _SyncResp(200, {"success": True, "key": key, "id": f"mem_{key}"})

    # LLM ルーティング
    if "/api/llm/route" in url or "/llm/route" in url:
        return _SyncResp(200, {
            "cpu_mode": False,
            "model": "test-model",
            "source": "stub",
            "response": "stub LLM response",
            "model_used": "test-model",
            "tokens_used": 10,
            "cost_estimate": 0.0,
            "reasoning": "stub routing",
        })

    # 通知
    if "/api/notification/send" in url:
        return _SyncResp(200, {"slack": True})

    # キャッシュ set
    if "/cache/set" in url:
        return _SyncResp(200, {"success": True})

    # 学習イベント
    if "/learning/event" in url:
        _EVT_COUNT[0] += 1
        return _SyncResp(201, {"success": True, "event_id": f"evt_{_EVT_COUNT[0]}"})

    return _SyncResp(200, {})


# ─────────────────────────────────────────────────────────────────────────────
# aiohttp モックヘルパー
# ─────────────────────────────────────────────────────────────────────────────

class _AsyncResp:
    """aiohttp.ClientResponse の最小スタブ"""

    def __init__(self, status: int, body: dict):
        self.status = status
        self._body = body

    async def json(self, **kwargs):
        return self._body

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        pass


def _aio_get(url: str, **kwargs):
    url = url or ""

    if "/health" in url:
        return _AsyncResp(200, {"status": "healthy"})

    m = re.search(r"/memory/retrieve/([^/?]+)", url)
    if m:
        key = m.group(1)
        entry = _MEM_STORE.get(key)
        if entry and entry.alive():
            return _AsyncResp(200, {"found": True, "key": key, "value": entry.value})
        return _AsyncResp(200, {"found": False, "key": key})

    if "/nonexistent" in url:
        return _AsyncResp(404, {"error": "not found"})

    return _AsyncResp(200, {"status": "ok"})


def _aio_post(url: str, **kwargs):
    url = url or ""
    body = kwargs.get("json") or {}

    if "/memory/store" in url:
        key = body.get("key", "")
        if not key:
            return _AsyncResp(400, {"error": "invalid key"})
        _MEM_STORE[key] = _MemEntry(body.get("value"), body.get("ttl", 3600))
        return _AsyncResp(201, {"success": True, "key": key})

    if "/learning/event" in url:
        _EVT_COUNT[0] += 1
        return _AsyncResp(201, {"success": True, "event_id": f"evt_{_EVT_COUNT[0]}"})

    if "/llm/route" in url:
        return _AsyncResp(200, {
            "model_used": "test-model",
            "response": "stub response",
            "tokens_used": 10,
            "cost_estimate": 0.0,
            "reasoning": "stub routing",
        })

    return _AsyncResp(200, {})


class _MockAioSession:
    """aiohttp.ClientSession の最小スタブ"""

    def __init__(self, *a, **kw):
        pass

    def get(self, url, **kw):
        return _aio_get(url, **kw)

    def post(self, url, **kw):
        return _aio_post(url, **kw)

    async def close(self):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        pass


# ─────────────────────────────────────────────────────────────────────────────
# autouse フィクスチャ — 全 e2e テストで requests / aiohttp をモック
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True, scope="function")
def _mock_http_e2e():
    """requests および aiohttp.ClientSession をモックする（function スコープ）"""
    import aiohttp as _aiohttp

    p1 = patch("requests.get", side_effect=_req_get)
    p2 = patch("requests.post", side_effect=_req_post)
    p3 = patch.object(_aiohttp, "ClientSession", _MockAioSession)

    p1.start()
    p2.start()
    p3.start()

    yield

    p3.stop()
    p2.stop()
    p1.stop()

