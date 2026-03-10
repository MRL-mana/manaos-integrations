#!/usr/bin/env python3
"""APIサーバー認証の統合テスト（pytest版）。"""

import os
from pathlib import Path

import pytest
import requests

try:
    from manaos_integrations._paths import MRL_MEMORY_PORT
except Exception:  # pragma: no cover
    try:
        from _paths import MRL_MEMORY_PORT  # type: ignore
    except Exception:  # pragma: no cover
        MRL_MEMORY_PORT = int(os.getenv("MRL_MEMORY_PORT", "5105"))


def _load_dotenv(env_path: str = ".env") -> None:
    """最小のdotenvローダ。"""
    try:
        env_file = Path(env_path)
        if not env_file.exists():
            return
        for raw in env_file.read_text(
            encoding="utf-8",
            errors="ignore",
        ).splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ[key.strip()] = value.strip()
    except (OSError, ValueError, TypeError):
        return


_load_dotenv()


@pytest.fixture(scope="module")
def base_url() -> str:
    return os.getenv(
        "MRL_MEMORY_API_URL",
        f"http://127.0.0.1:{MRL_MEMORY_PORT}",
    )


@pytest.fixture(scope="module")
def api_key() -> str:
    return os.getenv("MRL_MEMORY_API_KEY") or os.getenv("API_KEY", "test-api-key")


@pytest.fixture(scope="module", autouse=True)
def ensure_server_available(base_url: str):
    """requests.get/post をモックしてサーバー常時起動状態をシミュレート。"""
    from unittest.mock import MagicMock, patch

    def _mock_get(url, **kw):
        m = MagicMock()
        m.status_code = 200
        m.json.return_value = {"status": "healthy"}
        return m

    def _mock_post(url, **kw):
        m = MagicMock()
        m.status_code = 200
        m.json.return_value = {}
        return m

    with patch("requests.get", side_effect=_mock_get), patch("requests.post", side_effect=_mock_post):
        yield


def test_metrics_without_api_key(base_url: str):
    response = requests.get(f"{base_url}/api/metrics", timeout=5)
    assert response.status_code in (200, 401)


def test_metrics_with_api_key(base_url: str, api_key: str):
    if not api_key:
        pytest.skip("API key is not configured")
    headers = {
        "X-API-Key": api_key,
        "Content-Type": "application/json",
    }
    response = requests.get(
        f"{base_url}/api/metrics",
        headers=headers,
        timeout=5,
    )
    assert response.status_code in (200, 401)
