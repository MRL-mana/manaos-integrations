#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
テスト: check_services_health
HTTP モックで各サービスの健全性チェックロジックを検証
"""

from unittest.mock import patch, MagicMock
import requests

import pytest

from check_services_health import check_service, check_all_services, SERVICES


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_service():
    """テスト用サービス定義"""
    return {
        "name": "TestService",
        "port": 9999,
        "path": "/health",
        "timeout": 2,
        "group": "core",
    }


# ---------------------------------------------------------------------------
# check_service
# ---------------------------------------------------------------------------


class TestCheckService:

    @patch("check_services_health.requests.get")
    def test_healthy_service(self, mock_get, mock_service):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"status": "ok"}
        mock_get.return_value = mock_resp

        success, detail, elapsed = check_service(mock_service)
        assert success is True
        assert elapsed is not None
        assert elapsed >= 0

    @patch("check_services_health.requests.get")
    def test_unhealthy_service_500(self, mock_get, mock_service):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.json.return_value = {"error": "internal"}
        mock_get.return_value = mock_resp

        success, detail, elapsed = check_service(mock_service)
        assert success is False

    @patch("check_services_health.requests.get")
    def test_connection_refused(self, mock_get, mock_service):
        mock_get.side_effect = requests.ConnectionError("Connection refused")

        success, detail, elapsed = check_service(mock_service)
        assert success is False
        assert "Connection" in detail or "refused" in detail.lower() or "error" in detail.lower()  # type: ignore[operator]

    @patch("check_services_health.requests.get")
    def test_timeout(self, mock_get, mock_service):
        mock_get.side_effect = requests.Timeout("Read timed out")

        success, detail, elapsed = check_service(mock_service)
        assert success is False


# ---------------------------------------------------------------------------
# SERVICES 定義の検証
# ---------------------------------------------------------------------------


class TestServicesConfig:

    def test_all_services_have_required_keys(self):
        for svc in SERVICES:
            assert "name" in svc, f"Missing 'name' in {svc}"
            assert "port" in svc, f"Missing 'port' in {svc}"
            assert "path" in svc, f"Missing 'path' in {svc}"
            assert "group" in svc, f"Missing 'group' in {svc}"

    def test_groups_are_valid(self):
        valid_groups = {"core", "infra", "optional"}
        for svc in SERVICES:
            assert svc["group"] in valid_groups, f"Invalid group '{svc['group']}' for {svc['name']}"

    def test_core_services_exist(self):
        core_names = {s["name"] for s in SERVICES if s["group"] == "core"}
        assert "MRL Memory" in core_names
        assert "Learning System" in core_names
        assert "LLM Routing" in core_names
        assert "Unified API" in core_names

    def test_no_duplicate_ports(self):
        keys = [(s["port"], s["path"]) for s in SERVICES]
        assert len(keys) == len(set(keys)), f"Duplicate (port,path): {keys}"


# ---------------------------------------------------------------------------
# check_all_services (統合)
# ---------------------------------------------------------------------------


class TestCheckAllServices:

    @patch("check_services_health.requests.get")
    def test_all_healthy(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"status": "ok"}
        mock_get.return_value = mock_resp

        result = check_all_services(retry_count=1, retry_delay=0)
        assert result is True

    @patch("check_services_health.requests.get")
    def test_optional_fail_still_passes(self, mock_get):
        """optional サービスが落ちていても core が OK なら True"""

        def side_effect(url, **kwargs):
            resp = MagicMock()
            if "8188" in url or "8088" in url:
                raise requests.ConnectionError("offline")
            resp.status_code = 200
            resp.json.return_value = {"status": "ok"}
            return resp

        mock_get.side_effect = side_effect
        result = check_all_services(retry_count=1, retry_delay=0)
        # core + infra が OK なら True のはず
        assert result is True

    @patch("check_services_health.requests.get")
    def test_core_fail_returns_false(self, mock_get):
        """core サービスが1つでも落ちていれば False"""

        def side_effect(url, **kwargs):
            if "5105" in url:  # MRL Memory
                raise requests.ConnectionError("down")
            resp = MagicMock()
            resp.status_code = 200
            resp.json.return_value = {"status": "ok"}
            return resp

        mock_get.side_effect = side_effect
        result = check_all_services(retry_count=1, retry_delay=0)
        assert result is False
