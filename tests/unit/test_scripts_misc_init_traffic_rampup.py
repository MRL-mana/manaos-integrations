"""
Unit tests for scripts/misc/init_traffic_rampup.py
（httpx.AsyncClient を使った async サービスヘルスチェック）
"""
import asyncio
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from scripts.misc.init_traffic_rampup import check_services, SERVICES


class TestCheckServices:
    def _make_async_client(self, responses: dict):
        """service_name → (status_code, latency) のマップから AsyncClient モックを作成"""
        client = MagicMock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)

        async def _fake_get(url, **kwargs):
            # statusをURLから逆引き
            for svc_name, endpoint in SERVICES.items():
                if endpoint == url:
                    code, _ = responses.get(svc_name, (200, 5.0))
                    resp = MagicMock()
                    resp.status_code = code
                    return resp
            resp = MagicMock()
            resp.status_code = 200
            return resp

        client.get = _fake_get
        return client

    def test_returns_results_for_all_services(self):
        """全サービス分のキーが返される"""
        responses = {name: (200, 5.0) for name in SERVICES}
        mock_client = self._make_async_client(responses)
        with patch("scripts.misc.init_traffic_rampup.httpx.AsyncClient", return_value=mock_client):
            result = asyncio.run(check_services())
        assert set(result.keys()) == set(SERVICES.keys())

    def test_up_status_on_200(self):
        """HTTP 200 → status=UP"""
        responses = {name: (200, 5.0) for name in SERVICES}
        mock_client = self._make_async_client(responses)
        with patch("scripts.misc.init_traffic_rampup.httpx.AsyncClient", return_value=mock_client):
            result = asyncio.run(check_services())
        for svc in SERVICES:
            assert result[svc]["status"] == "UP"

    def test_down_status_on_non_200(self):
        """HTTP 500 → status=DOWN"""
        responses = {name: (500, 5.0) for name in SERVICES}
        mock_client = self._make_async_client(responses)
        with patch("scripts.misc.init_traffic_rampup.httpx.AsyncClient", return_value=mock_client):
            result = asyncio.run(check_services())
        for svc in SERVICES:
            assert result[svc]["status"] == "DOWN"

    def test_down_on_exception(self):
        """接続エラー → status=DOWN, error キーが存在"""
        client = MagicMock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        client.get = AsyncMock(side_effect=ConnectionRefusedError("refused"))
        with patch("scripts.misc.init_traffic_rampup.httpx.AsyncClient", return_value=client):
            result = asyncio.run(check_services())
        for svc in SERVICES:
            assert result[svc]["status"] == "DOWN"
            assert "error" in result[svc]

    def test_result_has_latency_ms_key(self):
        """成功時は latency_ms フィールドが含まれる"""
        responses = {name: (200, 5.0) for name in SERVICES}
        mock_client = self._make_async_client(responses)
        with patch("scripts.misc.init_traffic_rampup.httpx.AsyncClient", return_value=mock_client):
            result = asyncio.run(check_services())
        for svc in SERVICES:
            assert "latency_ms" in result[svc]
