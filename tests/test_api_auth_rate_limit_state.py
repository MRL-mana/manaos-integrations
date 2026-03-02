#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os

from api_auth import APIAuthManager


def test_rate_limit_state_is_capped_and_ttl_cleaned(monkeypatch):
    os.environ["MANAOS_API_KEYS"] = "test-key"

    now = [1000.0]
    monkeypatch.setattr("api_auth.time.time", lambda: now[0])

    manager = APIAuthManager(
        {
            "rate_limit_enabled": True,
            "rate_limit_requests": 1000,
            "rate_limit_window": 10,
            "rate_limit_max_clients": 50,
            "rate_limit_client_ttl": 30,
            "rate_limit_cleanup_interval": 1,
        }
    )

    for index in range(200):
        assert manager.check_rate_limit(f"client-{index}") is True

    assert len(manager.request_history) <= 100

    now[0] += 31
    assert manager.check_rate_limit("keepalive") is True

    assert "keepalive" in manager.request_history
    assert len(manager.request_history) == 1


def test_client_history_window_eviction(monkeypatch):
    os.environ["MANAOS_API_KEYS"] = "test-key"

    now = [2000.0]
    monkeypatch.setattr("api_auth.time.time", lambda: now[0])

    manager = APIAuthManager(
        {
            "rate_limit_enabled": True,
            "rate_limit_requests": 1000,
            "rate_limit_window": 10,
            "rate_limit_max_clients": 100,
            "rate_limit_client_ttl": 60,
            "rate_limit_cleanup_interval": 1,
        }
    )

    for _ in range(20):
        assert manager.check_rate_limit("same-client") is True

    assert len(manager.request_history["same-client"]) == 20

    now[0] += 11
    assert manager.check_rate_limit("same-client") is True

    assert len(manager.request_history["same-client"]) == 1
